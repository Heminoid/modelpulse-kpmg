from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
response = client.post(
    "/api/v1/runs/run_f66c1afeefdd/reports/generate",
    json={"report_type": "full_technical", "format": "docx", "sections": ["performance"]}
)
print("STATUS CODE:", response.status_code)
print("RESPONSE TEXT:", response.text)
