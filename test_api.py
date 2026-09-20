import requests

url = "http://localhost:8000/api/v1/runs/run_f66c1afeefdd/reports/generate"
payload = {
    "report_type": "full_technical",
    "format": "docx",
    "sections": ["performance", "calibration"]
}
response = requests.post(url, json=payload)
print(response.status_code)
print(response.text)
