from utils.google_api import get_doc_content, get_docs_service
import re

def read_docs(url: str):
    # https://docs.google.com/document/d/12uJRjUsa1LuIndpS6dgFL5jBIO8qBpNc/edit
  print(f"Reading URL: {url}")
    
  # 1. Trích xuất ID từ URL
  # Regex này bắt ID nằm giữa /d/ và /edit hoặc kết thúc chuỗi
  m = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
  if not m:
      print("Error: Could not find Document ID in URL.")
      return

  doc_id = m.group(1)
  print(f"Document ID: {doc_id}")

  # 2. Gọi hàm lấy nội dung từ google_api
  content = get_doc_content(doc_id)
  
  if content:
      print("\n=== DOC CONTENT START ===")
      print(content)
      print("=== DOC CONTENT END ===")
  else:
      print("Error: Failed to retrieve content (check logs/credentials).")
        
        
if __name__ == "__main__":
  test_url = "https://docs.google.com/spreadsheets/d/1-ypUyKglUjblgy1Gy0gITcdHF4YLdJnaCNKM_6_fCrI/edit?gid=29840804#gid=29840804"
  read_docs(test_url)