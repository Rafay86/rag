from langchain_community.document_loaders import UnstructuredHTMLLoader
import traceback

try:
    print("Attempting to load HTML...")
    loader = UnstructuredHTMLLoader("test_upload.html")
    docs = loader.load()
    print("Successfully loaded HTML.")
    print(docs)
except Exception:
    traceback.print_exc()
