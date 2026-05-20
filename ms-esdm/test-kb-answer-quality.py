"""
Test chatbot knowledge by generating Q&A from documents and evaluating responses.
you need google credential to run this file
"""

import os
import json
import csv
import tempfile
import requests
import subprocess
import google.generativeai as genai
import dotenv
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

dotenv.load_dotenv()

# Configuration
KB_BASE_URL = "http://108.136.169.18"
DRIVE_FOLDER_ID = "1MYii1qA_TVhgL77IwEp7OPAnAHmvN9_h"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
KB_API_TOKEN = os.environ.get("KB_TOKEN", "")
MAX_DOCUMENTS = 30

ALLOWED_TYPES = {
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
}

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def convert_to_pdf(file_path, original_filename):
    """Convert DOC/DOCX to PDF and return new path."""
    ext = os.path.splitext(original_filename)[1].lower()
    
    if ext == '.pdf':
        return file_path
    
    if ext not in ['.doc', '.docx']:
        print(f"[WARN] Unsupported file type for conversion: {ext}")
        return None
    
    print(f"[CONVERT] Converting {original_filename} to PDF...")
    
    # Create output directory for PDF
    output_dir = tempfile.mkdtemp()
    
    try:
        # Use LibreOffice to convert
        cmd = [
            'soffice',
            '--headless',
            '--convert-to', 'pdf',
            '--outdir', output_dir,
            file_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            print(f"[ERROR] LibreOffice conversion failed: {result.stderr}")
            return None
        
        # Find the generated PDF
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        pdf_path = os.path.join(output_dir, f"{base_name}.pdf")
        
        if not os.path.exists(pdf_path):
            print(f"[ERROR] PDF not created at expected path: {pdf_path}")
            return None
        
        # Remove original temp file
        os.remove(file_path)
        
        print(f"[SUCCESS] Converted to PDF")
        return pdf_path
        
    except subprocess.TimeoutExpired:
        print(f"[ERROR] Conversion timeout")
        return None
    except Exception as e:
        print(f"[ERROR] Conversion failed: {e}")
        return None
    
def get_drive_service():
    """Authenticate and return Drive service."""
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("oauth_client.json", SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open("token.json", "w") as f:
            f.write(creds.to_json())
    
    return build("drive", "v3", credentials=creds, cache_discovery=False)

def fetch_kb_documents():
    """Get documents metadata from KB."""
    print("[INFO] Fetching KB documents...")
    documents = []
    page = 1
    
    while True:
        resp = requests.get(
            f"{KB_BASE_URL}/api/knowledge/documents",
            params={"page": page, "limit": 1000},
            timeout=60
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        
        documents.extend(items)
        
        if len(items) < 1000:
            break
        page += 1
    
    print(f"[INFO] KB documents loaded: {len(documents)}")
    return documents

def list_all_drive_files(service, folder_id):
    """Recursively list all files in Drive folder and create a mapping."""
    print("[INFO] Building Drive file index...")
    file_map = {}  # filename -> file_id
    folders = [folder_id]
    visited = set()
    
    while folders:
        current = folders.pop()
        if current in visited:
            continue
        visited.add(current)
        
        page_token = None
        
        while True:
            resp = service.files().list(
                q=f"'{current}' in parents and trashed=false",
                fields="nextPageToken, files(id, name, mimeType, shortcutDetails(targetId, targetMimeType))",
                pageSize=1000,
                pageToken=page_token,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            
            for f in resp.get("files", []):
                mime = f.get("mimeType", "")
                
                if mime == "application/vnd.google-apps.folder":
                    folders.append(f["id"])
                elif mime == "application/vnd.google-apps.shortcut":
                    shortcut = f.get("shortcutDetails", {})
                    target_id = shortcut.get("targetId")
                    target_mime = shortcut.get("targetMimeType")
                    if target_mime == "application/vnd.google-apps.folder" and target_id:
                        folders.append(target_id)
                else:
                    file_map[f["name"]] = f["id"]
            
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
    
    print(f"[INFO] Indexed {len(file_map)} files from Drive")
    return file_map

def find_drive_file_id(filename, file_map):
    """Find file ID from map by removing KB prefix."""
    # Remove KB prefix if exists (e.g., "123_document.pdf" -> "document.pdf")
    search_name = filename.split("_", 1)[1] if "_" in filename else filename
    return file_map.get(search_name)

def download_drive_file(service, file_id, original_filename):
    """Download file from Drive to temp file and return path."""
    # Preserve original extension
    _, ext = os.path.splitext(original_filename)
    temp_fd, temp_path = tempfile.mkstemp(suffix=ext)
    os.close(temp_fd)
    
    request = service.files().get_media(fileId=file_id)
    with open(temp_path, "wb") as f:
        downloader = MediaIoBaseDownload(f, request, chunksize=10*1024*1024)
        done = False
        while not done:
            _, done = downloader.next_chunk()
    
    return temp_path

def generate_qa_pairs(documents_data):
    """Generate Q&A pairs for all documents using Gemini."""
    print(f"[INFO] Generating Q&A pairs for {len(documents_data)} documents...")
    
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash-lite")
    
    # Upload all documents to Gemini
    uploaded_files = []
    for filename, file_path in documents_data:
        print(f"[UPLOAD] Uploading to Gemini: {filename}")
        uploaded_file = genai.upload_file(file_path)
        uploaded_files.append((filename, uploaded_file))
    
    # Create prompt for batch Q&A generation
    prompt = f"""You are given {len(uploaded_files)} documents. For each document, generate ONE specific question and its expected answer based on the document's content.

Requirements:
- Each question should test knowledge of key facts, concepts, or details from that specific document
- Questions should be clear and answerable from the document
- Expected answers should be concise (2-3 sentences) and accurate

Format your response as a JSON array with this exact structure:
[
  {{
    "document": "filename1.pdf",
    "question": "What is...",
    "expected_answer": "The answer is..."
  }},
  {{
    "document": "filename2.pdf",
    "question": "How does...",
    "expected_answer": "It works by..."
  }}
]

Generate exactly {len(uploaded_files)} Q&A pairs, one for each document in order.

Documents:
"""
    for i, (filename, _) in enumerate(uploaded_files, 1):
        prompt += f"{i}. {filename}\n"
    
    # Generate Q&A pairs
    content = [prompt] + [uf[1] for uf in uploaded_files]
    response = model.generate_content(content)
    
    # Parse response
    import json
    response_text = response.text.strip()
    # Remove markdown code blocks if present
    if response_text.startswith("```"):
        response_text = response_text.split("```")[1]
        if response_text.startswith("json"):
            response_text = response_text[4:]
    
    qa_pairs = json.loads(response_text.strip())
    print(f"[SUCCESS] Generated {len(qa_pairs)} Q&A pairs")
    
    return qa_pairs

def ask_chatbot(question):
    """Send question to chatbot API and get response."""
    headers = {}
    if KB_API_TOKEN:
        headers["Authorization"] = f"Bearer {KB_API_TOKEN}"
    
    resp = requests.post(
        f"{KB_BASE_URL}/api/knowledge/analyze",
        json={"user_input": question},
        headers=headers,
        timeout=60
    )
    resp.raise_for_status()
    data = resp.json()
    
    # The API returns the answer in "output" field
    return data.get("output", "")

def save_qa_pairs_to_json(qa_pairs, output_file="qa_pairs.json"):
    """Save Q&A pairs to JSON file."""
    print(f"[INFO] Saving Q&A pairs to {output_file}...")
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(qa_pairs, f, indent=2, ensure_ascii=False)
    
    print(f"[SUCCESS] Q&A pairs saved to {output_file}")

def load_qa_pairs_from_json(input_file="qa_pairs.json"):
    """Load Q&A pairs from JSON file."""
    if not os.path.exists(input_file):
        print(f"[ERROR] File not found: {input_file}")
        return None
    
    print(f"[INFO] Loading Q&A pairs from {input_file}...")
    with open(input_file, "r", encoding="utf-8") as f:
        qa_pairs = json.load(f)
    
    print(f"[SUCCESS] Loaded {len(qa_pairs)} Q&A pairs")
    return qa_pairs

def evaluate_answers(qa_results):
    """Evaluate all chatbot answers using Gemini."""
    print(f"[INFO] Evaluating {len(qa_results)} answers...")
    
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash-lite")
    
    prompt = f"""You are an expert evaluator analyzing {len(qa_results)} chatbot responses. Evaluate each response carefully and provide nuanced scores.

SCORING GUIDELINES:

Answer Relevancy (0-10):
- 9-10: Directly answers the question with all key information
- 7-8: Answers the question but missing minor details
- 5-6: Partially answers, some relevant information present
- 3-4: Tangentially related but doesn't fully address question
- 1-2: Barely relevant to the question
- 0: Completely irrelevant or error

Faithfulness (0-10):
- 9-10: Fully aligned with expected answer, all facts correct
- 7-8: Mostly aligned, minor discrepancies or missing details
- 5-6: Partially aligned, some correct facts but incomplete
- 3-4: Some overlap but significant differences or inaccuracies
- 1-2: Minimal alignment, mostly different information
- 0: Contradicts expected answer or completely wrong

IMPORTANT: Use the full 0-10 range. Avoid only giving 0 or 10. Be critical and precise.

Format your response as a JSON array:
[
  {{
    "answer_relevancy": 7,
    "faithfulness": 6,
    "comments": [
      "Addresses main question about X correctly",
      "Missing specific details about Y from context",
      "Provides extra information not in expected answer"
    ]
  }}
]

Evaluate these Q&A pairs:

"""
    
    for i, qa in enumerate(qa_results, 1):
        prompt += f"""
---
{i}. Document: {qa['filename']}

Question: {qa['question']}

Expected Answer: {qa['expected_answer']}

Chatbot Answer: {qa['answer']}

"""
    
    response = model.generate_content(prompt)
    
    # Parse response
    response_text = response.text.strip()
    if response_text.startswith("```"):
        response_text = response_text.split("```")[1]
        if response_text.startswith("json"):
            response_text = response_text[4:]
    
    evaluations = json.loads(response_text.strip())
    print(f"[SUCCESS] Evaluated {len(evaluations)} answers")
    
    return evaluations

def save_results_to_csv(results, output_file="test_results.csv"):
    """Save test results to CSV."""
    print(f"[INFO] Saving results to {output_file}...")
    
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "filename", "question", "expected_answer", "answer",
            "answer_relevancy", "faithfulness", "comments"
        ])
        writer.writeheader()
        
        for row in results:
            # Convert comments list to string if exists
            if "comments" in row and isinstance(row["comments"], list):
                row["comments"] = " | ".join(row["comments"])
            elif "comments" not in row:
                row["comments"] = ""
            
            # Ensure all required fields exist
            row.setdefault("answer", "")
            row.setdefault("answer_relevancy", "N/A")
            row.setdefault("faithfulness", "N/A")
            
            writer.writerow(row)
    
    print(f"[SUCCESS] Results saved to {output_file}")


def main():
    if not GEMINI_API_KEY:
        print("[ERROR] GEMINI_API_KEY environment variable not set")
        return
    
    if not KB_API_TOKEN:
        print("[WARN] KB_API_TOKEN not set, requests may fail")
    
    # Check if we should load existing Q&A pairs
    load_existing = input("\n[INPUT] Load existing qa_pairs.json? (y/n, default: n): ").strip().lower()
    
    if load_existing == 'y':
        qa_pairs = load_qa_pairs_from_json()
        if not qa_pairs:
            print("[ERROR] Failed to load Q&A pairs")
            return
    else:
        # Step 1: Fetch KB documents
        kb_docs = fetch_kb_documents()
        
        # Limit to MAX_DOCUMENTS
        kb_docs = kb_docs[:MAX_DOCUMENTS]
        print(f"[INFO] Testing with {len(kb_docs)} documents")
        
        # Step 2: Build Drive file index
        drive_service = get_drive_service()
        drive_file_map = list_all_drive_files(drive_service, DRIVE_FOLDER_ID)
        
        # Step 3: Download documents from Drive
        documents_data = []
            
        for i, doc in enumerate(kb_docs, 1):
            filename = doc.get("filename", "")
            if not filename:
                continue
            
            # Check if file type is PDF or DOC/DOCX
            ext = os.path.splitext(filename)[1].lower()
            if ext not in ['.pdf', '.doc', '.docx']:
                print(f"[{i}/{len(kb_docs)}] SKIP (not pdf/doc/docx): {filename}")
                continue
            
            print(f"[{i}/{len(kb_docs)}] Processing: {filename}")
            
            # Find file ID from map
            file_id = find_drive_file_id(filename, drive_file_map)
            if not file_id:
                print(f"[SKIP] File not found in Drive: {filename}")
                continue
            
            print(f"[DOWNLOAD] {filename}")
            try:
                file_path = download_drive_file(drive_service, file_id, filename)
                
                # Convert to PDF if needed
                pdf_path = convert_to_pdf(file_path, filename)
                if not pdf_path:
                    print(f"[SKIP] Conversion failed for {filename}")
                    continue
                
                documents_data.append((filename, pdf_path))
            except Exception as e:
                print(f"[ERROR] Failed to process {filename}: {e}")
        
        if not documents_data:
            print("[ERROR] No documents downloaded")
            return
        
        try:
            # Step 4: Generate Q&A pairs
            qa_pairs = generate_qa_pairs(documents_data)
            
            # Save Q&A pairs to JSON
            save_qa_pairs_to_json(qa_pairs)
            
        finally:
            # Cleanup temp files
            for _, file_path in documents_data:
                if os.path.exists(file_path):
                    os.remove(file_path)
    
    try:
        # Step 5: Ask chatbot for each question
        qa_results = []
        print(f"\n[INFO] Asking chatbot {len(qa_pairs)} questions...")
        
        for i, qa in enumerate(qa_pairs, 1):
            question = qa["question"]
            filename = qa["document"]
            expected = qa["expected_answer"]
            
            print(f"[{i}/{len(qa_pairs)}] Asking: {question[:60]}...")
            
            try:
                answer = ask_chatbot(question)
                print(f"[RESPONSE] {answer[:100]}...")  # Debug: print first 100 chars
                qa_results.append({
                    "filename": filename,
                    "question": question,
                    "expected_answer": expected,
                    "answer": answer
                })
            except Exception as e:
                print(f"[ERROR] Failed to get answer: {e}")
                qa_results.append({
                    "filename": filename,
                    "question": question,
                    "expected_answer": expected,
                    "answer": f"ERROR: {str(e)}"
                })
        
        # Step 6: Evaluate answers
        try:
            evaluations = evaluate_answers(qa_results)
            
            # Merge evaluations with results
            for i, evaluation in enumerate(evaluations):
                if i < len(qa_results):
                    qa_results[i].update(evaluation)
        except Exception as e:
            print(f"[ERROR] Evaluation failed: {e}")
            # Add default evaluation values
            for result in qa_results:
                result.setdefault("answer_relevancy", "N/A")
                result.setdefault("faithfulness", "N/A")
                result.setdefault("comments", "Evaluation failed")
        
        # Step 7: Save to CSV
        save_results_to_csv(qa_results)
        
        print(f"\n[DONE] Pipeline completed successfully!")
        print(f"[DONE] Tested {len(qa_results)} questions")
        
    except Exception as e:
        print(f"[ERROR] Pipeline failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()