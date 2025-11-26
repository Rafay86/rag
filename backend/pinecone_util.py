from langchain_community.document_loaders import Docx2txtLoader, UnstructuredHTMLLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from pinecone import Pinecone, ServerlessSpec
from typing import List
from langchain_core.documents import Document
import os
from dotenv import load_dotenv
import fitz
from langdetect import detect 

load_dotenv()
text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=200, length_function=len)
embedding_function = OpenAIEmbeddings(model="text-embedding-3-large")

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

# Pinecone setup
pc = Pinecone(api_key=PINECONE_API_KEY)

index_name = "saama-laws"
dimension = 3072 

def index_exists(index_name):
    try:
        indexes = pc.list_indexes()
        return index_name in [i.name for i in indexes]
    except Exception as e:
        print(f"Error checking index existence: {e}")
        return False

if not index_exists(index_name):
    pc.create_index(
        name=index_name,
        dimension=dimension,
        metric="cosine",
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1"
        )
    )

index = pc.Index(index_name)
from langchain_pinecone import PineconeVectorStore
vectorstore = PineconeVectorStore(index_name=index_name, embedding=embedding_function)

def extract_text_from_pdf(file_path: str) -> List[Document]:
    """Extracts text from a PDF file using PyMuPDF (fitz) with fallback for empty pages."""
    doc = fitz.open(file_path)
    documents = []
    file_name = os.path.basename(file_path)

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        raw_text = page.get_text() # type: ignore
        cleaned_text = raw_text.strip()

        if not cleaned_text:
            cleaned_text = "[NO TEXT FOUND ON PAGE]"  # Fallback text

        # Safely detect language (use fallback if detection fails)
        try:
            language = detect(cleaned_text[:200])
        except:
            language = "unknown"

        documents.append(Document(
            page_content=cleaned_text,
            metadata={
                "page": page_num + 1,
                "source": file_name,
                "language": language
            }
        ))

    return documents
def load_and_split_document(file_path: str) -> List[Document]:
    """Loads and splits a document based on its file type, adding metadata."""
    if file_path.endswith('.pdf'):
        documents = extract_text_from_pdf(file_path)
    elif file_path.endswith('.docx'):
        loader = Docx2txtLoader(file_path)
        documents = loader.load()
    elif file_path.endswith('.html'):
        loader = UnstructuredHTMLLoader(file_path)
        documents = loader.load()
    else:
        raise ValueError(f"Unsupported file type: {file_path}")
    
    result_documents = []
    for document in documents:
        chunks = text_splitter.split_text(document.page_content)
        for chunk in chunks:
            result_documents.append(Document(
                page_content=chunk,
                metadata=document.metadata
            ))

    return result_documents

def index_document_to_pinecone(file_path: str, file_id: int) -> bool:
    try:
        splits = load_and_split_document(file_path)
        
        for split in splits:
            split.metadata['file_id'] = file_id
        
        vectorstore.add_documents(splits)
        return True
    except Exception as e:
        print(f"Error indexing document: {e}")
        return False

def delete_doc_from_pinecone(file_id: int) -> bool:
    try:
        index = pc.Index(index_name)

        vectors_to_delete = []
        next_token = None
        batch_size = 1000

        while True:
            query_results = index.query(
                vector=[0] * dimension,  # type: ignore
                top_k=batch_size,        
                include_metadata=True,   
                cursor=next_token
            )

            if query_results and "matches" in query_results: # type: ignore
                for match in query_results["matches"]: # type: ignore
                    metadata = match.get("metadata", {})
                    if metadata.get("file_id") == file_id:
                        vectors_to_delete.append(match["id"])

                next_token = query_results.get("next_page_token", None) # type: ignore

                if not next_token:
                    break
            else:
                return "No vectors found or metadata retrieval failed." # type: ignore

        if vectors_to_delete:
            index.delete(ids=vectors_to_delete)
            return f"Successfully deleted {len(vectors_to_delete)} vectors with file_id {file_id}." # type: ignore
        else:
            return f"No vectors found with file_id {file_id}." # type: ignore
    except Exception as e:
        return f"Error deleting vectors for file_id {file_id}: {str(e)}" # type: ignore

def show_metadata() -> List[dict]:
    try:
        query_results = index.query(
            vector=[0] * dimension,  # type: ignore
            top_k=5,
            include_metadata=True
        )

        if query_results and "matches" in query_results: # type: ignore
            metadata = []
            for match in query_results["matches"]: # type: ignore
                vector_id = match["id"]
                metadata_dict = match.get("metadata", {})
                metadata.append(
                    {"vector_id": vector_id, "metadata": metadata_dict})
            return metadata
        else:
            return "No matches found or metadata retrieval failed." # type: ignore
    except Exception as e:
        return f"Error retrieving vector metadata: {str(e)}" # type: ignore
