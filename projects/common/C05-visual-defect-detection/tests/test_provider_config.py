"""Swappable-provider regression tests.

These lock the contract that lets C05 switch between the Gemini Developer API
and Vertex AI by configuration alone. They must never require a network call,
a real credential, or a provisioned cloud resource.
"""
import json
import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "src"
ROOT = HERE.parent.parent.parent.parent  # workspace root holding shared_mvp/
for extra in (str(SRC), str(HERE), str(ROOT)):
    if extra not in sys.path:
        sys.path.insert(0, extra)

import c05_gemini  # noqa: E402

class ProviderResolution(unittest.TestCase):
    def setUp(self):
        # Force ADC presence so resolution logic is testable on a machine without
        # credentials. Restored in tearDown.
        self._adc = c05_gemini._adc_present
        c05_gemini._adc_present = lambda: True

    def tearDown(self):
        c05_gemini._adc_present = self._adc

    def cfg(self, **env):
        base = dict(GEMINI_MODEL="gemini-2.0-flash")
        base.update(env)
        return c05_gemini.load_config(base)

    def test_auto_prefers_vertex_when_project_present(self):
        cfg = self.cfg(GOOGLE_CLOUD_PROJECT="p", GEMINI_API_KEY="k")
        self.assertEqual(cfg.resolved, "vertex")

    def test_auto_falls_back_to_api_key(self):
        cfg = self.cfg(GEMINI_API_KEY="k")
        self.assertEqual(cfg.resolved, "gemini-api")

    def test_auto_prefers_vertex_over_api_key(self):
        cfg = self.cfg(GOOGLE_CLOUD_PROJECT="p", GEMINI_API_KEY="k")
        self.assertEqual(cfg.resolved, "vertex")

    def test_forced_api_key_without_key_is_blocked(self):
        cfg = self.cfg(C05_GEMINI_PROVIDER="gemini-api", GOOGLE_CLOUD_PROJECT="p")
        self.assertIsNone(cfg.resolved)
        self.assertTrue(any("GEMINI_API_KEY" in b for b in cfg.blocking()))

    def test_forced_vertex_without_project_is_blocked(self):
        cfg = self.cfg(C05_GEMINI_PROVIDER="vertex")
        self.assertIsNone(cfg.resolved)
        self.assertTrue(any("GOOGLE_CLOUD_PROJECT" in b for b in cfg.blocking()))

    def test_invalid_provider_string_falls_back_to_auto(self):
        cfg = self.cfg(C05_GEMINI_PROVIDER="bogus", GEMINI_API_KEY="k")
        self.assertEqual(cfg.provider, "auto")
        self.assertEqual(cfg.resolved, "gemini-api")

    def test_ready_config_reports_no_blockers(self):
        cfg = self.cfg(GOOGLE_CLOUD_PROJECT="p", GEMINI_API_KEY="k")
        self.assertTrue(cfg.resolved)
        self.assertEqual(cfg.blocking(), [])

    def test_unused_fallback_path_is_not_reported_as_a_blocker(self):
        cfg = self.cfg(GEMINI_API_KEY="k")
        self.assertEqual(cfg.resolved, "gemini-api")
        self.assertEqual(cfg.blocking(), [])

    def test_missing_model_blocks_even_with_credentials(self):
        cfg = self.cfg(GOOGLE_CLOUD_PROJECT="p", GEMINI_API_KEY="k", GEMINI_MODEL="")
        self.assertIsNone(cfg.resolved)
        self.assertTrue(any("model" in b.lower() for b in cfg.blocking()))

    def test_timeout_falls_back_to_default_on_garbage(self):
        cfg = self.cfg(GEMINI_API_KEY="k", GEMINI_TIMEOUT_SECONDS="not-a-number")
        self.assertEqual(cfg.timeout_s, c05_gemini.DEFAULT_TIMEOUT)


class ReadinessSafety(unittest.TestCase):
    def test_readiness_never_exposes_secret_values(self):
        secret = "super-secret-key-value-1234"
        cfg = c05_gemini.load_config({"GEMINI_API_KEY": secret, "GEMINI_MODEL": "gemini-2.0-flash"})
        payload = c05_gemini.readiness_payload(cfg)
        rendered = repr(payload)
        self.assertNotIn(secret, rendered)
        self.assertTrue(payload["credentials"]["gemini_api_key"])

    def test_readiness_reports_billing_difference(self):
        payload = c05_gemini.readiness_payload(c05_gemini.load_config({}))
        self.assertIn("Cloud Billing", payload["billing_note"])

    def test_structured_generation_config_forces_json(self):
        cfg = c05_gemini.structured_generation_config({"type": "object"})
        self.assertEqual(cfg["responseMimeType"], "application/json")
        self.assertEqual(cfg["temperature"], 0)


class TransportHeaders(unittest.TestCase):
    def test_api_key_transport_uses_key_header(self):
        import os

        cfg = c05_gemini.GeminiConfig(
            provider="gemini-api", model="gemini-2.0-flash", api_key_present=True
        )
        os.environ["GEMINI_API_KEY"] = "placeholder-not-real"
        try:
            url, headers, mode = c05_gemini.auth_headers(cfg)
        finally:
            os.environ.pop("GEMINI_API_KEY", None)
        self.assertIn("generativelanguage.googleapis.com", url)
        self.assertEqual(mode, "api-key")
        self.assertIn("x-goog-api-key", headers)

    def test_unconfigured_provider_raises_without_leaking(self):
        cfg = c05_gemini.load_config({})
        with self.assertRaises(c05_gemini.ProviderNotConfigured):
            c05_gemini.auth_headers(cfg)


class VertexWireContract(unittest.TestCase):
    """Locks the Vertex request shape that the shared provider hands to httpx.

    Every assertion here corresponds to an incompatibility that was measured
    against the live endpoint, not to a stylistic preference.
    """

    def _schema(self):
        from shared_mvp.app import locate
        from shared_mvp.contracts import model

        spec = (locate("C05") / "config" / "project.json").read_text()
        cfg = json.loads(spec)
        return c05_gemini.c05_vertex_schema(model(cfg["output"], "C05Output").model_json_schema())

    def test_schema_has_no_defs_or_ref(self):
        # Vertex rejects $defs with a 400; the flatten step must inline them.
        blob = json.dumps(self._schema())
        self.assertNotIn("$defs", blob)
        self.assertNotIn("$ref", blob)

    def test_nullable_is_not_a_type_array(self):
        # `type: ["number","null"]` is a 400 on Vertex; `anyOf` is the accepted form.
        confidence = self._schema()["properties"]["confidence_score"]
        self.assertNotIsInstance(confidence.get("type"), list)
        self.assertIn("anyOf", confidence)

    def test_label_vocabulary_is_pinned_to_the_domain(self):
        # domain.validate_output is the authority and must stay authoritative; the
        # enum only stops the model spending a live call on an unusable label.
        label = self._schema()["properties"]["predicted_label"]
        self.assertEqual(label["enum"], list(c05_gemini.C05_LABELS))
        self.assertEqual(label["format"], "enum")

    def test_vertex_contents_declare_a_role(self):
        # Omitting role returns 400 "Please use a valid role: user, model."
        contents = c05_gemini.vertex_contents([{"text": "hi"}])
        self.assertEqual(contents[0]["role"], "user")


class ThinkingConfigCompatibility(unittest.TestCase):
    """Gemini 2.5 and Gemini 3 do not accept the same thinking control.

    All expectations below were measured against the live global endpoint. The
    third is the one that bites: `thinkingBudget: 0` is silently ignored on
    Gemini 3, so it returns 200 while thinking still runs and burns the budget.
    """

    def setUp(self):
        self._saved = {
            k: os.environ.pop(k, None)
            for k in ("C05_GEMINI_THINKING_CONFIG", "C05_GEMINI_THINKING_LEVEL")
        }

    def tearDown(self):
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_gemini_25_uses_thinking_budget(self):
        self.assertEqual(c05_gemini.thinking_config_for("gemini-2.5-flash"),
                         {"thinkingBudget": 0})

    def test_gemini_3_uses_thinking_level(self):
        # thinkingBudget:0 on Gemini 3.8 returns 200 but leaves thinking running,
        # so the level spelling is required even though both are accepted.
        self.assertEqual(c05_gemini.thinking_config_for("gemini-3.8-flash"),
                         {"thinkingLevel": "LOW"})

    def test_thinking_level_is_configurable(self):
        os.environ["C05_GEMINI_THINKING_LEVEL"] = "MEDIUM"
        self.assertEqual(c05_gemini.thinking_config_for("gemini-3.8-flash"),
                         {"thinkingLevel": "MEDIUM"})

    def test_explicit_override_wins_and_degrades_safely(self):
        os.environ["C05_GEMINI_THINKING_CONFIG"] = '{"thinkingLevel":"HIGH"}'
        self.assertEqual(c05_gemini.thinking_config_for("gemini-3.8-flash"),
                         {"thinkingLevel": "HIGH"})
        os.environ["C05_GEMINI_THINKING_CONFIG"] = "not-json"
        # A malformed override must not break inference; it degrades to the default.
        self.assertEqual(c05_gemini.thinking_config_for("gemini-3.8-flash"),
                         {"thinkingLevel": "LOW"})


if __name__ == "__main__":
    unittest.main(verbosity=2)