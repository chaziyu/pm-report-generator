"""
Runtime Manifest for bundled / local llama.cpp runtime.
Single source of truth for runtime metadata, download URLs, executable names, and required files.
"""

from typing import List, Optional
from pydantic import BaseModel

class RuntimeManifest(BaseModel):
    runtime_id: str
    runtime_name: str
    runtime_version: str
    platform: str
    architecture: str
    release_source: str
    download_url: str
    archive_filename: str
    expected_sha256: Optional[str] = None  # None when official upstream does not publish a checksum
    executable_name: str
    required_files: List[str]
    license: str

# Default verified CPU-only Windows x64 runtime from official llama.cpp release
DEFAULT_RUNTIME_MANIFEST = RuntimeManifest(
    runtime_id="llama-cpp-b11200-win-cpu-x64",
    runtime_name="llama.cpp Windows x64 CPU Runtime",
    runtime_version="b11200",
    platform="win32",
    architecture="x64",
    release_source="https://github.com/ggml-org/llama.cpp/releases/tag/b11200",
    download_url="https://github.com/ggml-org/llama.cpp/releases/download/b11200/llama-b11200-bin-win-cpu-x64.zip",
    archive_filename="llama-b11200-bin-win-cpu-x64.zip",
    expected_sha256=None,  # Official release does not publish sha256; structural & executable checks enforced
    executable_name="llama-server.exe",
    required_files=[
        "llama-server.exe",
        "llama-server-impl.dll",
        "llama.dll",
        "llama-common.dll",
        "ggml.dll",
        "ggml-base.dll",
        "libomp.dll",
    ],
    license="MIT",
)
