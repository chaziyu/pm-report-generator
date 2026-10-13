import urllib.request
import json
import urllib.parse
from uuid import uuid4

print("Creating session...")
req = urllib.request.Request("http://localhost:8000/api/sessions/", method="POST")
with urllib.request.urlopen(req) as response:
    session = json.loads(response.read())
    session_id = session['id']
    print(f"Created session: {session_id}")

print("Uploading test image...")
image_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\x0d\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
boundary = uuid4().hex
body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="file"; filename="test.png"\r\n'
    f"Content-Type: image/png\r\n\r\n".encode()
    + image_content
    + f"\r\n--{boundary}--\r\n".encode()
)
req2 = urllib.request.Request(
    f"http://localhost:8000/api/sessions/{session_id}/screenshots",
    data=body,
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    method="POST"
)
with urllib.request.urlopen(req2) as response:
    print(f"Upload response: {json.loads(response.read())}")
