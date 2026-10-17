"""Gemini agent contracts: tool use is role-scoped, ungrounded or accusatory
answers fall back to the deterministic router, and provenance is reported."""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "src"
ROOT = HERE.parent.parent.parent.parent
for extra in (str(SRC), str(ROOT)):
    if extra not in sys.path:
        sys.path.insert(0, extra)


def _load_api():
    spec = importlib.util.spec_from_file_location("c05_api_agent", SRC / "c05_api.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def scripted(*turns):
    """Fake Gemini: returns the given parts lists in order and records requests."""
    seen = []

    async def call(body):
        seen.append(body)
        return {"candidates": [{"content": {"role": "model", "parts": turns[len(seen) - 1]}}]}
    call.seen = seen
    return call


class AgentContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from shared_mvp.testing import LocalClient
        cls._tmp = tempfile.TemporaryDirectory()
        cls.app = _load_api().create_app(str(Path(cls._tmp.name) / "agent.sqlite"))
        cls.client = LocalClient(cls.app)
        cls.client.post("/api/claims/demo-seed", json={"role": "ADMIN"})

    @classmethod
    def tearDownClass(cls):
        cls.app.state.store.close()
        cls._tmp.cleanup()

    def ask(self, model, role="ADMIN", question="Which incident needs attention first?"):
        self.app.state.agent_model = model
        try:
            return self.client.post("/api/agent/chat", json={"role": role, "question": question}).json()
        finally:
            self.app.state.agent_model = None

    def test_gemini_calls_tools_and_answers(self):
        incident = self.client.get("/api/claims/incidents?role=ADMIN").json()["incidents"][0]["incident_id"]
        model = scripted(
            [{"functionCall": {"name": "list_claim_incidents", "args": {}}}],
            [{"functionCall": {"name": "get_claim_incident", "args": {"incident_id": incident}}}],
            [{"text": "Start with the URGENT incident; confirm medical follow-up first."}],
        )
        body = self.ask(model)
        self.assertEqual(body["engine"], "gemini")
        self.assertEqual([t["tool"] for t in body["tool_calls"]], ["list_claim_incidents", "get_claim_incident"])
        self.assertIn("URGENT", body["answer"])
        # The tool result went back to the model as a functionResponse.
        reply = model.seen[1]["contents"][-1]["parts"][0]["functionResponse"]
        self.assertEqual(reply["name"], "list_claim_incidents")
        self.assertTrue(reply["response"]["content"]["incidents"])

    def test_ungrounded_answer_falls_back(self):
        body = self.ask(scripted([{"text": "There are 12 incidents."}]), question="Any poisoning claims?")
        self.assertEqual(body["engine"], "rules")
        self.assertEqual(body["fallback_reason"], "ungrounded_answer")
        self.assertEqual(body["tool_calls"][0]["tool"], "list_claim_incidents")

    def test_accusatory_answer_falls_back(self):
        body = self.ask(scripted([{"functionCall": {"name": "list_claim_incidents", "args": {}}}],
                                 [{"text": "These reports are a scam."}]))
        self.assertEqual(body["engine"], "rules")
        self.assertEqual(body["fallback_reason"], "rejected_answer")

    def test_tools_stay_role_scoped(self):
        model = scripted([{"functionCall": {"name": "list_claim_incidents", "args": {}}}],
                         [{"text": "You cannot see illness claims."}])
        body = self.ask(model, role="CREW")
        result = model.seen[1]["contents"][-1]["parts"][0]["functionResponse"]["response"]["content"]
        self.assertIn("error", result)
        self.assertEqual(body["engine"], "gemini")

    def test_unknown_tool_is_reported_not_executed(self):
        model = scripted([{"functionCall": {"name": "delete_everything", "args": {}}}],
                         [{"text": "I can only read records."}])
        self.ask(model)
        result = model.seen[1]["contents"][-1]["parts"][0]["functionResponse"]["response"]["content"]
        self.assertEqual(result, {"error": "unknown tool delete_everything"})

    def test_no_provider_uses_rules(self):
        body = self.client.post("/api/agent/chat", json={"role": "ADMIN", "question": "Any poisoning claims?"}).json()
        self.assertEqual(body["engine"], "rules")
        self.assertTrue(body["fallback_reason"])


if __name__ == "__main__":
    unittest.main()
