import requests
import time
import os

BASE_URL = "http://localhost:8000"

def verify():
    # 1. Register or Login
    user_data = {
        "email": "tester@example.com",
        "full_name": "Test User",
        "password": "securepassword123"
    }
    
    print("Attempting registration...")
    register_url = f"{BASE_URL}/api/auth/register"
    r = requests.post(register_url, json=user_data)
    
    if r.status_code == 200 or r.status_code == 201:
        print("Registration successful!")
        token_data = r.json()
    else:
        print(f"Registration status: {r.status_code}. Attempting login...")
        login_url = f"{BASE_URL}/api/auth/login"
        r = requests.post(login_url, json={"email": user_data["email"], "password": user_data["password"]})
        if r.status_code == 200:
            print("Login successful!")
            token_data = r.json()
        else:
            print(f"Login failed: {r.text}")
            return False

    token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Upload document
    print("Uploading document test_academic.txt...")
    upload_url = f"{BASE_URL}/api/upload"
    test_file_path = r"d:\PlagX\test_academic.txt"
    
    with open(test_file_path, "rb") as f:
        files = {"file": (os.path.basename(test_file_path), f, "text/plain")}
        r = requests.post(upload_url, headers=headers, files=files)

    if r.status_code != 200:
        print(f"Upload failed: {r.text}")
        return False
        
    doc_data = r.json()
    doc_id = doc_data["id"]
    print(f"Document uploaded successfully! ID: {doc_id}")

    # 3. Start check
    print(f"Starting plagiarism check for document {doc_id}...")
    check_url = f"{BASE_URL}/api/check/{doc_id}"
    r = requests.post(check_url, headers=headers)
    if r.status_code != 200:
        print(f"Check initiation failed: {r.text}")
        return False

    print("Checking progress...")
    status_url = f"{BASE_URL}/api/check-status/{doc_id}"
    
    # 4. Poll status
    for attempt in range(30):
        r = requests.get(status_url, headers=headers)
        if r.status_code != 200:
            print(f"Failed to check status: {r.text}")
            return False
            
        status_info = r.json()
        status = status_info["status"]
        progress = status_info["progress"]
        stage = status_info.get("worker_stage", "Unknown")
        print(f"Attempt {attempt+1}: Status = {status}, Progress = {progress}%, Stage = {stage}")
        
        if status == "completed":
            print("Plagiarism check completed successfully!")
            break
        elif status == "failed":
            print(f"Plagiarism check failed! Message: {status_info.get('message')}")
            return False
            
        time.sleep(3)
    else:
        print("Polling timed out.")
        return False

    # Get final report details
    print(f"\nFetching report for document {doc_id}...")
    report_url = f"{BASE_URL}/api/report-by-document/{doc_id}"
    r = requests.get(report_url, headers=headers)
    if r.status_code != 200:
        print(f"Failed to fetch report: {r.text}")
        return False
        
    report = r.json()
    print("================ REPORT RESULTS ================")
    print(f"Overall Score: {report['overall_score']}%")
    print(f"Risk Level: {report['risk_level']}")
    print(f"Exact Score Breakdown: {report['exact_score']}%")
    print(f"Semantic Score Breakdown: {report['semantic_score']}%")
    print(f"Source Density: {report['source_density_score']}%")
    print(f"Total Sources: {report['total_sources']}")
    print(f"Words Analyzed: {report['total_words']}")
    print(f"Matched Words (Weighted): {report['matched_words']}")
    
    print("\nMatched Sources list:")
    for src in report['matched_sources']:
        print(f"- Index {src['source_index']}: {src['source_name']} ({src['match_percentage']:.1f}%), Color: {src['color']}")
        if src.get('matched_spans'):
            print(f"  Spans ({len(src['matched_spans'])}):")
            for span in src['matched_spans']:
                print(f"    * Char {span['start_char']}-{span['end_char']}, group: {span.get('group_type')}, similarity: {span['similarity']:.0%}")
                
    print("\nHighlights Spans (first 10):")
    for idx, hl in enumerate(report['highlights'][:10]):
        print(f"{idx+1}. {hl['match_type']} (Source {hl['source_index']}): group {hl.get('group_type')}, Char {hl['start_char']}-{hl['end_char']}")
        
    return True

if __name__ == "__main__":
    verify()
