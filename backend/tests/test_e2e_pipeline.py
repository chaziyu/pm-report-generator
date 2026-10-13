import zipfile
import io
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from docx import Document
from app.main import app
from fastapi.testclient import TestClient
from app.config import settings

import unittest

client = TestClient(app)

class TestE2EPipeline(unittest.TestCase):
    def test_full_pm_pipeline(self):
        # 1. Create session
        resp = client.post("/api/sessions/")
        self.assertEqual(resp.status_code, 200, resp.text)
        session_data = resp.json()
        session_id = session_data["id"]
        print(f"1. Created test session: {session_id}")

        # 2. Extract sample CPU and Memory images from template to use as real uploads
        z = zipfile.ZipFile(settings.templates_dir / "preventive-maintenance.docx")
        cpu_bytes = z.read("word/media/image8.png")   # CPU widget
        mem_bytes = z.read("word/media/image9.png")   # Memory widget

        resp_up1 = client.post(
            f"/api/sessions/{session_id}/screenshots",
            files={"file": ("Screenshot_CPU.png", cpu_bytes, "image/png")}
        )
        self.assertEqual(resp_up1.status_code, 200, resp_up1.text)
        print("2. Uploaded CPU screenshot:", resp_up1.json()["filename"])

        resp_up2 = client.post(
            f"/api/sessions/{session_id}/screenshots",
            files={"file": ("Screenshot_Mem.png", mem_bytes, "image/png")}
        )
        self.assertEqual(resp_up2.status_code, 200, resp_up2.text)
        print("3. Uploaded Memory screenshot:", resp_up2.json()["filename"])

        # 3. Trigger Analysis
        resp_analyze = client.post(f"/api/sessions/{session_id}/analyze")
        self.assertEqual(resp_analyze.status_code, 200, resp_analyze.text)
        analyzed = resp_analyze.json()
        print("4. Analysis completed. Status:", analyzed["status"])
        print("   Detected CPU usage:", analyzed["pm_data"]["hardware"]["cpu_usage"]["value"])
        print("   Detected Memory usage:", analyzed["pm_data"]["hardware"]["memory_usage"]["value"])
        print("   Appendix 1 evidence:", analyzed["pm_data"]["appendices"]["1"]["status"])
        print("   Appendix 2 evidence:", analyzed["pm_data"]["appendices"]["2"]["status"])

        # 4. Field update test
        resp_edit = client.patch(
            f"/api/sessions/{session_id}/fields",
            json={"field_path": "application.hostname", "value": "HQ_TEST_FG200F"}
        )
        self.assertEqual(resp_edit.status_code, 200, resp_edit.text)
        print("5. Edited hostname field.")

        # 5. Validation check
        resp_val = client.post(f"/api/sessions/{session_id}/validate")
        self.assertEqual(resp_val.status_code, 200, resp_val.text)
        val_data = resp_val.json()
        print("6. Validation result. Is valid:", val_data["is_valid"], "Issues count:", val_data["total_issues"])

        # 6. Generate DOCX
        resp_gen = client.post(f"/api/sessions/{session_id}/reports")
        self.assertEqual(resp_gen.status_code, 200, resp_gen.text)
        gen_data = resp_gen.json()
        print("7. Report generated:", gen_data["filename"])

        # 7. Verify generated document
        report_file_path = settings.workspace_dir / session_id / "reports" / gen_data["filename"]
        self.assertTrue(report_file_path.exists())
        doc = Document(report_file_path)
        self.assertEqual(len(doc.tables), 15)
        print("8. Generated DOCX opened and validated with python-docx!")
        print("\nALL PIPELINE TESTS PASSED!")

if __name__ == "__main__":
    unittest.main()
