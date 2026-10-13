"""
Model Manifest for Local AI subsystem.
Single source of truth for model metadata, runtime specs, and verification hashes.
"""

from typing import Optional
from pydantic import BaseModel

class ModelManifest(BaseModel):
    model_id: str
    display_name: str
    filename: str
    runtime: str
    expected_sha256: str
    context_size: int
    max_output_tokens: int
    prompt_version: str
    model_revision: str
    download_url: Optional[str] = None
    expected_size_bytes: int = 0

# Default Bundled Model: Qwen3-1.7B-Q4_K_M.gguf
DEFAULT_MODEL_MANIFEST = ModelManifest(
    model_id="qwen3-1.7b-instruct-q4_k_m",
    display_name="Qwen3 1.7B Instruct (Q4_K_M)",
    filename="Qwen3-1.7B-Q4_K_M.gguf",
    runtime="llama.cpp",
    # SHA-256 for the verified Qwen3-1.7B-Q4_K_M.gguf file
    expected_sha256="d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5",
    context_size=4096,
    max_output_tokens=512,
    prompt_version="v1",
    model_revision="2026-qwen3-1.7b-q4km",
    download_url="https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf",
    expected_size_bytes=1282439264,
)
