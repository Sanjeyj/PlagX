import httpx
import time
import random

BASE_URL = "http://localhost:8000/api"

def run_test():
    # 1. Register a new user with a random email
    email = f"test_{random.randint(1000, 9999)}@example.com"
    print(f"Registering user: {email}")
    register_payload = {
        "email": email,
        "full_name": "Test User",
        "password": "securepassword123"
    }
    
    resp = httpx.post(f"{BASE_URL}/auth/register", json=register_payload)
    if resp.status_code != 200:
        print("Registration failed:", resp.text)
        return
        
    auth_data = resp.json()
    token = auth_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("User registered successfully. Token obtained.")

    # 2. Upload document
    print("Uploading test.txt...")
    files = {"file": ("test.txt", open("d:/PlagX/test.txt", "rb"), "text/plain")}
    resp = httpx.post(f"{BASE_URL}/upload", headers=headers, files=files)
    if resp.status_code != 200:
        print("Upload failed:", resp.text)
        return
        
    doc_data = resp.json()
    doc_id = doc_data["id"]
    print(f"Document uploaded. ID: {doc_id}")

    # 3. Start check
    print(f"Starting check for document {doc_id}...")
    resp = httpx.post(f"{BASE_URL}/check/{doc_id}", headers=headers)
    if resp.status_code != 200:
        print("Failed to start check:", resp.text)
        return
        
    check_data = resp.json()
    print("Check response:", check_data)

    # 4. Poll status
    print("Polling check status...")
    for _ in range(30):
        time.sleep(1)
        resp = httpx.get(f"{BASE_URL}/check-status/{doc_id}", headers=headers)
        if resp.status_code != 200:
            print("Status fetch failed:", resp.text)
            break
            
        status_data = resp.json()
        print(f"Status: {status_data['status']} | Progress: {status_data['progress']}% | Stage: {status_data['worker_stage']} | Message: {status_data['message']}")
        
        if status_data["status"] == "completed":
            print("Check completed successfully!")
            
            # Fetch report
            report_resp = httpx.get(f"{BASE_URL}/report-by-document/{doc_id}", headers=headers)
            if report_resp.status_code == 200:
                report_data = report_resp.json()
                print("--- Report ---")
                print("Overall Score:", report_data["overall_score"])
                print("Risk Level:", report_data["risk_level"])
                print("AI Probability:", report_data.get("ai_score") or report_data.get("ai_probability"))
                print("Sources Found:", len(report_data["matched_sources"]))
            else:
                print("Failed to fetch report:", report_resp.text)
            break
        elif status_data["status"] == "failed":
            print("Check failed! Error message:", status_data.get("message"))
            break
    else:
        print("Polling timed out.")

if __name__ == "__main__":
    run_test()
