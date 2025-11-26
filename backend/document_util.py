import sqlite3
import os
from datetime import datetime

DB_NAME = "documents.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL UNIQUE,
            upload_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def get_all_documents():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM documents")
    rows = cursor.fetchall()
    documents = [dict(row) for row in rows]
    conn.close()
    return documents

def insert_document_record(filename):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO documents (filename) VALUES (?)", (filename,))
        conn.commit()
        file_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        file_id = None # Or handle as existing
    finally:
        conn.close()
    return file_id

def delete_document_record(file_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM documents WHERE id = ?", (file_id,))
    conn.commit()
    conn.close()

def get_document_by_filename(filename):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM documents WHERE filename = ?", (filename,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

# Initialize DB on module load (or call explicitly in main)
init_db()
