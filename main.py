import os
import time
import hashlib
import json
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI
from PyPDF2 import PdfReader
from docx import Document

# ------------------ Load environment variables ------------------
load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ------------------ Initialize clients ------------------
pc = Pinecone(api_key=PINECONE_API_KEY)
client = OpenAI(api_key=OPENAI_API_KEY)

INDEX_NAME = "coaching-knowledge"

# ------------------ FastAPI ------------------
app = FastAPI()


# ------------------ Utilities ------------------
def file_checksum(path: str) -> str:
    """Compute SHA256 hash of a file"""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_file_hashes() -> dict:
    """Load previous file hashes"""
    try:
        with open("file_hashes.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_file_hashes(hashes: dict):
    """Save file hashes"""
    with open("file_hashes.json", "w") as f:
        json.dump(hashes, f)


def extract_text_from_file(file_path: str) -> str:
    """Read text from txt, pdf, and docx files"""
    ext = os.path.splitext(file_path)[-1].lower()
    print(f"Processing file: {file_path}")
    try:
        if ext == ".txt":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        elif ext == ".pdf":
            reader = PdfReader(file_path)
            return "".join(page.extract_text() or "" for page in reader.pages)
        elif ext == ".docx":
            doc = Document(file_path)
            return "\n".join(para.text for para in doc.paragraphs)
        elif ext == ".doc":
            print(
                f"Warning: .doc files not supported. Convert {file_path} to .docx")
            return ""
        else:
            raise ValueError(f"Unsupported file type: {ext}")
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return ""


def embed_text(text: str):
    """Get embedding from OpenAI"""
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding


# ------------------ Pinecone integration ------------------
def ingest_documents(docs_path: str = "docs"):
    """Index documents in Pinecone"""
    if not os.path.exists(docs_path):
        print(f"Directory {docs_path} does not exist!")
        return

    # Create index if it does not exist
    existing_indexes = pc.list_indexes().names()
    if INDEX_NAME not in existing_indexes:
        print(f"Creating index {INDEX_NAME}...")
        pc.create_index(
            name=INDEX_NAME,
            dimension=1536,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
        time.sleep(10)

    index = pc.Index(INDEX_NAME)
    current_hashes = load_file_hashes()
    new_hashes = {}

    for fname in os.listdir(docs_path):
        path = os.path.join(docs_path, fname)
        if not os.path.isfile(path) or fname == ".DS_Store":
            continue

        current_hash = file_checksum(path)
        new_hashes[fname] = current_hash

        # Process files if they are new or changed
        if fname not in current_hashes or current_hashes[fname] != current_hash:
            print(f"Processing changed file: {fname}")
            try:
                text = extract_text_from_file(path)
                if not text:
                    continue

                # Split text into chunks
                chunks = [text[i:i+500] for i in range(0, len(text), 500)]

                vectors = []
                for i, chunk in enumerate(chunks):
                    vectors.append({
                        "id": f"{fname}-{i}",
                        "values": embed_text(chunk),
                        "metadata": {"source": fname, "text": chunk}
                    })

                # Upsert vectors into Pinecone index
                if vectors:
                    index.upsert(vectors=vectors)  # no namespace
                    print(f"Upserted {len(vectors)} vectors for {fname}")

            except Exception as e:
                print(f"Error processing {fname}: {e}")

    save_file_hashes(new_hashes)


def query_index(query: str):
    """Query Pinecone index"""
    index = pc.Index(INDEX_NAME)
    vector = embed_text(query)
    res = index.query(
        vector=vector,
        top_k=3,
        include_metadata=True
    )
    return res


# ------------------ FastAPI endpoints ------------------
@app.get("/")
def root():
    return {"message": "Coaching bot is running"}


@app.get("/search")
def search(q: str):
    if not q:
        raise HTTPException(
            status_code=400, detail="Query parameter 'q' is required")
    results = query_index(q)
    return {"matches": results.get("matches", [])}


# ------------------ Run ingestion at startup ------------------
@app.on_event("startup")
async def startup_event():
    print("Starting ingestion process...")
    ingest_documents()
    print("Ingestion completed. Bot is ready.")


if __name__ == "__main__":
    ingest_documents()
