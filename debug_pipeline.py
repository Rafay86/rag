import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from backend.pinecone_util import index_document_to_pinecone
import traceback
import os
from dotenv import load_dotenv

load_dotenv()

print(f"Pinecone Key present: {bool(os.getenv('PINECONE_API_KEY'))}")
print(f"OpenAI Key present: {bool(os.getenv('OPENAI_API_KEY'))}")

try:
    print("Attempting to index document...")
    # Use a dummy file_id 999
    success = index_document_to_pinecone("test_upload.html", 999)
    print(f"Indexing success: {success}")
except Exception:
    traceback.print_exc()
