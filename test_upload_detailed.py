import httpx
import json
from pathlib import Path

# Create a test PDF file  
test_pdf = Path("test_sample.pdf")
test_pdf.write_bytes(b"%PDF-1.4\n%Test PDF content")

try:
    with httpx.Client(timeout=30.0) as client:
        with open(test_pdf, "rb") as f:
            files = {"files": (test_pdf.name, f, "application/pdf")}
            response = client.post("http://localhost:8000/api/documents/upload", files=files)
            print(f"Status: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            print(f"Response Body: {response.text}")
            
            # Try to parse as JSON for more info
            try:
                resp_json = response.json()
                print(f"Parsed JSON: {json.dumps(resp_json, indent=2)}")
            except:
                pass
                
except Exception as e:
    import traceback
    print(f"Error: {type(e).__name__}: {str(e)}")
    traceback.print_exc()
finally:
    test_pdf.unlink(missing_ok=True)
