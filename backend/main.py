from flask import Flask, request, jsonify
from pinecone_util import index_document_to_pinecone, delete_doc_from_pinecone, show_metadata
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from pydantic_models import QueryInput, QueryResponse, DeleteFileRequest
from langchain_util import get_rag_chain, get_simple_chain
from document_util import get_all_documents, insert_document_record, delete_document_record, get_document_by_filename
import os
import logging
# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Set up logging
logging.basicConfig(level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s')


@app.route("/")
def home():
    return "Hello from Personal RAG Chatbot!"

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    try:
        query_input = QueryInput(**data)
    except Exception as e:
        logging.error(f"Error in input data: {str(e)}")
        return jsonify({"error": "Invalid input data"}), 400

    session_id = query_input.session_id
    if not session_id:
        return jsonify({"error": "No session assigned"}), 400

    chat_history = []
    if query_input.history:
        chat_history = [entry.model_dump() for entry in query_input.history]

    simple_chain = get_simple_chain()
    general_response = simple_chain.invoke({
        "input": query_input.question,
        "chat_history": chat_history
    })

    response_text = general_response['text']
    response_lines = response_text.splitlines()

    if response_lines[0].strip() == "False":  
        source = response_lines[1].strip() if len(response_lines) > 1 else ""
    else:
        return jsonify({
            "answer": response_text,
            "highlighted_contexts": []
        })

    rag_chain = get_rag_chain(source)
    rag_response = rag_chain.invoke({
        "input": query_input.question,
        "chat_history": chat_history
    })

    highlighted_contexts = []
    data = rag_response.get("answer")

    for context in rag_response.get("context", []):
        if hasattr(context, 'page_content'):
            context_text = context.page_content
            metadata = context.metadata if hasattr(context, 'metadata') else {}

            highlighted_contexts.append({
                "file_id": metadata.get("file_id"),
                "page": metadata.get("page", None), 
                "source": metadata.get("source", None),
                "language": metadata.get("language", None),
                "context_text": context_text 
            })

    return jsonify({
        "answer": data,
        "highlighted_contexts": highlighted_contexts,
    })


@app.route("/upload-doc", methods=["POST"])
def index_document():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in request"}), 400

    files = request.files.getlist('file')
    allowed_extensions = ['.pdf', '.docx', '.html']
    results = []

    for file in files:
        filename = file.filename
        file_extension = os.path.splitext(filename)[1].lower() # type: ignore

        if file_extension not in allowed_extensions:
            results.append({
                "filename": filename,
                "status": "error",
                "message": f"Unsupported file type: {file_extension}"
            })
            continue

        try:
            existing_document = get_document_by_filename(filename)
            if existing_document:
                results.append({
                    "filename": filename,
                    "status": "exists",
                    "file_id": existing_document['id'],
                    "message": "File already uploaded"
                })
                continue

            temp_file_path = filename  # no path change

            file.save(temp_file_path) # type: ignore

            file_id = insert_document_record(filename)
            success = index_document_to_pinecone(temp_file_path, file_id)  # type: ignore

            os.remove(temp_file_path) # type: ignore

            if success:
                results.append({
                    "filename": filename,
                    "status": "success",
                    "file_id": file_id,
                    "message": "Indexed successfully"
                })
            else:
                delete_document_record(file_id)
                results.append({
                    "filename": filename,
                    "status": "error",
                    "message": "Failed to index"
                })

        except Exception as e:
            results.append({
                "filename": filename,
                "status": "error",
                "message": str(e)
            })

    return jsonify({
        "summary": {
            "total_files": len(files),
            "success": sum(1 for r in results if r["status"] == "success"),
            "errors": sum(1 for r in results if r["status"] == "error"),
            "duplicates": sum(1 for r in results if r["status"] == "exists")
        },
        "results": results
    })

@app.route('/delete-doc', methods=['DELETE'])
def delete_document():
    try:

        data = request.get_json()
        file_id = data.get('file_id')

        if not file_id:
            return jsonify({"error": "file_id is required"}), 400

        response = DeleteFileRequest(**data)

        message = delete_doc_from_pinecone(response.file_id)

        if "Successfully deleted" in message:  # type: ignore
            delete_document_record(file_id)
            return jsonify({"message": message}), 200
        else:
            return jsonify({"error": message}), 500
    except Exception as e:
        logging.error(f"Error deleting document: {str(e)}", exc_info=True)
        return jsonify({"error": "An error occurred while deleting the document"}), 500


@app.route("/list-docs", methods=["GET"])
def list_documents():
    documents = get_all_documents()
    return jsonify(documents)


@app.route("/show-docs", methods=["GET"])
def show_metaData():
    documents = show_metadata()
    return jsonify(documents)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
