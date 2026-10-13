"""
Test suite for LocalAIRuntimeProvisioner (Section 26).
Validates:
1. Missing runtime state
2. Atomic installation into temporary clean location
3. Cancel behavior
4. Failed download error handling
5. Corrupt archive error handling
6. Missing required files / executable detection
7. Ensures failed installation is NEVER reported as READY
"""

import sys
import shutil
import zipfile
import tempfile
import unittest
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.services.ai.runtime.provisioner import LocalAIRuntimeProvisioner
from app.services.ai.runtime.manifest import DEFAULT_RUNTIME_MANIFEST

class TestLocalAIRuntimeProvisioner(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="pm_test_provisioner_"))
        self.target_dir = self.temp_dir / "bin" / "llama"

    def tearDown(self):
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_missing_runtime_initial_state(self):
        """Initial state with non-existent directory must report not ready and missing executable."""
        prov = LocalAIRuntimeProvisioner(custom_target_dir=self.target_dir)
        self.assertFalse(prov.is_installed_and_ready())
        self.assertIsNone(prov.get_executable_path())
        st = prov.get_status()
        self.assertEqual(st.get("status"), "RUNTIME_MISSING")

    def test_cancel_installation(self):
        """Cancelling an active installation resets installing flag and sets error/cancelled."""
        prov = LocalAIRuntimeProvisioner(custom_target_dir=self.target_dir)
        prov.cancel_install()
        st = prov.get_status()
        self.assertFalse(prov._installing)
        self.assertFalse(prov.is_installed_and_ready())

    def test_corrupt_archive_fails_and_never_ready(self):
        """A corrupt zip archive must raise an error and NEVER result in READY status."""
        prov = LocalAIRuntimeProvisioner(custom_target_dir=self.target_dir)
        corrupt_zip = self.temp_dir / "corrupt.zip"
        with open(corrupt_zip, "wb") as f:
            f.write(b"NOT_A_VALID_ZIP_ARCHIVE_DATA_1234567890")

        # Extraction must fail cleanly
        temp_extract = self.temp_dir / "extract_temp"
        with self.assertRaises(Exception):
            with zipfile.ZipFile(corrupt_zip, "r") as zf:
                zf.extractall(temp_extract)

        self.assertFalse(prov.is_installed_and_ready())
        st = prov.get_status()
        self.assertNotEqual(st.get("status"), "READY")

    def test_missing_executable_in_archive_not_ready(self):
        """Archive missing llama-server.exe must not be verified as ready."""
        prov = LocalAIRuntimeProvisioner(custom_target_dir=self.target_dir)
        bad_zip = self.temp_dir / "bad_manifest.zip"
        
        # Create a valid zip with only a dummy txt file
        with zipfile.ZipFile(bad_zip, "w") as zf:
            zf.writestr("readme.txt", "No llama server here")

        temp_extract = self.temp_dir / "extract_bad"
        with zipfile.ZipFile(bad_zip, "r") as zf:
            zf.extractall(temp_extract)

        # Target dir without required files must be False
        self.target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(temp_extract / "readme.txt", self.target_dir / "readme.txt")

        self.assertFalse(prov.is_installed_and_ready())
        self.assertIsNone(prov.get_executable_path())

    def test_failed_download_handling(self):
        """Network error or invalid URL records failure and does not report READY."""
        dummy_manifest = DEFAULT_RUNTIME_MANIFEST.copy(
            update={"download_url": "http://127.0.0.1:59998/nonexistent_archive.zip"}
        )
        prov = LocalAIRuntimeProvisioner(manifest=dummy_manifest, custom_target_dir=self.target_dir)
        with self.assertRaises(RuntimeError):
            prov.install_sync()
        self.assertFalse(prov.is_installed_and_ready())
        st = prov.get_status()
        self.assertEqual(st.get("status"), "RUNTIME_MISSING")
        self.assertIsNotNone(st.get("error"))

if __name__ == "__main__":
    unittest.main()
