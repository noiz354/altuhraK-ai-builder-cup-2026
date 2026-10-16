"""Provider-outcome classification and failure-tolerance contracts.

These lock the rule that a fallback prediction is never reported as a model
inference, and that a provider failure degrades into manual review rather than
crashing or silently approving. MODEL_FREEZE is in effect: these tests assert
integration behaviour only, never model accuracy.
"""
import base64
import importlib.util
import io
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "src"
ROOT = HERE.parent.parent.parent.parent
for extra in (str(SRC), str(ROOT)):
    if extra not in sys.path:
        sys.path.insert(0, extra)

from PIL import Image, ImageDraw  # noqa: E402


def _load_api():
    """Import c05_api directly: it is not importable as a package module."""
    spec = importlib.util.spec_from_file_location("c05_api_contract", SRC / "c05_api.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _tray_png(filled: bool) -> bytes:
    img = Image.new("RGB", (640, 480), (238, 238, 238))
    d = ImageDraw.Draw(img)
    d.rectangle([24, 24, 616, 456], fill=(255, 255, 255))
    fill = (226, 196, 168) if filled else (250, 245, 235)
    for x, y in [(48, 60), (240, 60), (432, 60), (48, 260), (240, 260), (432, 260)]:
        d.rectangle([x, y, x + 160, y + 160], fill=fill)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class ProviderOutcomeContract(unittest.TestCase):
    """A real provider attempt and a successful inference are different claims."""

    @classmethod
    def setUpClass(cls):
        from shared_mvp.app import create_app
        from shared_mvp.testing import LocalClient

        import tempfile

        cls._tmp = tempfile.TemporaryDirectory()
        cls.app = _load_api().create_app(str(Path(cls._tmp.name) / "contract.sqlite"))
        cls.client = LocalClient(cls.app)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.client.close()
            cls.app.state.store.db.close()
        finally:
            cls._tmp.cleanup()

    def _create(self, filled=True):
        r = self.client.post("/api/inspections", json={
            "role": "CREW", "kitchen_id": "KITCHEN-A", "manifest_version": 1,
            "mime_type": "image/png",
            "data_base64": base64.b64encode(_tray_png(filled)).decode(),
        })
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()["inspection_id"]

    def test_baseline_is_never_reported_as_model_output(self):
        iid = self._create()
        rec = self.client.post(f"/api/inspections/{iid}/run",
                               json={"role": "CREW", "mode": "baseline"}).json()
        self.assertEqual(rec["inference_status"], "NOT_REQUESTED")
        self.assertEqual(rec["prediction_source"], "baseline")
        self.assertEqual(rec["model_version"], "baseline-local-v1")

    def test_prediction_source_matches_inference_status(self):
        """A 'model' source is only legal when inference actually succeeded."""
        iid = self._create()
        rec = self.client.post(f"/api/inspections/{iid}/run",
                               json={"role": "CREW", "mode": "ai"}).json()
        if rec["inference_status"] == "INFERENCE_SUCCEEDED":
            self.assertEqual(rec["prediction_source"], "model")
        else:
            self.assertNotEqual(rec["prediction_source"], "model",
                                "a non-succeeded inference must not claim model origin")

    def test_status_vocabulary_is_closed(self):
        allowed = {"NOT_REQUESTED", "INFERENCE_BLOCKED", "PROVIDER_INVOKED",
                   "PROVIDER_RESPONDED", "INFERENCE_SUCCEEDED", "INFERENCE_FAILED"}
        iid = self._create()
        rec = self.client.post(f"/api/inspections/{iid}/run",
                               json={"role": "CREW", "mode": "ai"}).json()
        self.assertIn(rec["inference_status"], allowed)

    def test_uploaded_image_survives_a_failed_or_blocked_inference(self):
        """Failure must not discard the evidence a human reviewer needs."""
        iid = self._create()
        rec = self.client.post(f"/api/inspections/{iid}/run",
                               json={"role": "CREW", "mode": "ai"}).json()
        detail = self.client.get(f"/api/inspections/{iid}").json()
        self.assertTrue(detail.get("image_id"))
        self.assertTrue(detail.get("storage_path"))

    def test_manual_review_remains_possible_when_inference_fails(self):
        """The core failure-tolerance guarantee: QC cannot be blocked by the model."""
        iid = self._create()
        self.client.post(f"/api/inspections/{iid}/run", json={"role": "CREW", "mode": "ai"})
        reviewed = self.client.post(f"/api/inspections/{iid}/review", json={
            "role": "ADMIN", "decision": "APPROVED", "qc_disposition": "ACCEPT",
            "comment": "manual review, model unavailable",
        })
        self.assertEqual(reviewed.status_code, 200, reviewed.text)
        self.assertEqual(reviewed.json()["review_status"], "APPROVED")

    def test_crew_cannot_approve_their_own_inspection(self):
        iid = self._create()
        self.client.post(f"/api/inspections/{iid}/run", json={"role": "CREW", "mode": "ai"})
        denied = self.client.post(f"/api/inspections/{iid}/review", json={
            "role": "CREW", "decision": "APPROVED", "qc_disposition": "ACCEPT",
        })
        self.assertEqual(denied.status_code, 403, denied.text)

    def test_report_is_not_official_before_an_authorised_review(self):
        """The report endpoint answers, but must not present itself as approved."""
        iid = self._create()
        self.client.post(f"/api/inspections/{iid}/run", json={"role": "CREW", "mode": "ai"})
        report = self.client.get(f"/api/reports/{iid}").json()
        self.assertNotEqual(report["report_status"], "OFFICIAL")
        self.assertIn("NOT APPROVED", report["report_status"])
        self.assertIsNone(report["reviewer_id"])

    def test_report_records_whether_the_prediction_came_from_the_model(self):
        """A baseline prediction must not be readable as a model finding."""
        iid = self._create()
        self.client.post(f"/api/inspections/{iid}/run", json={"role": "CREW", "mode": "ai"})
        report = self.client.get(f"/api/reports/{iid}").json()
        self.assertIn("inference_status", report)
        self.assertIn("prediction_source", report)
        if report["prediction_source"] != "model":
            self.assertNotEqual(report["inference_status"], "INFERENCE_SUCCEEDED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
