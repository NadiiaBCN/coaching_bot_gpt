import os
import time
import hashlib
import json
import logging
import aiohttp
import asyncio
from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException, Request
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI
from PyPDF2 import PdfReader
from docx import Document

# ------------------ Configuration ------------------


class Config:
    """Configuration class for the coaching bot"""
    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 50
    TOP_K = 3
    EMBEDDING_MODEL = "text-embedding-3-small"
    LLM_MODEL = "gpt-3.5-turbo"
    MAX_QUERY_LENGTH = 1000
    MAX_RESPONSE_TOKENS = 500
    TEMPERATURE = 0.7

    # File processing settings
    SUPPORTED_EXTENSIONS = ['.txt', '.pdf', '.docx']
    DOCS_FOLDER = 'docs'
    HASHES_FILE = 'file_hashes.json'

    # Pinecone settings
    INDEX_NAME = "coaching-knowledge"
    EMBEDDING_DIMENSION = 1536
    PINECONE_CLOUD = "aws"
    PINECONE_REGION = "us-east-1"

# ------------------ Setup logging ------------------


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ------------------ Load environment variables ------------------

load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Validate required environment variables
if not all([PINECONE_API_KEY, OPENAI_API_KEY, TELEGRAM_BOT_TOKEN]):
    raise ValueError(
        "Missing required environment variables: PINECONE_API_KEY, OPENAI_API_KEY, TELEGRAM_BOT_TOKEN"
    )

# ------------------ Initialize clients ------------------

pc = Pinecone(api_key=PINECONE_API_KEY)
client = OpenAI(api_key=OPENAI_API_KEY)

# ------------------ FastAPI ------------------

app = FastAPI(
    title="Enhanced Coaching Bot",
    description="A smart coaching bot with document indexing and Telegram integration",
    version="2.0.0"
)

# ------------------ Utilities ------------------


def file_checksum(path: str) -> str:
    """
    Compute SHA256 hash of a file to detect changes

    Args:
        path (str): Path to the file

    Returns:
        str: SHA256 hash of the file
    """
    try:
        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        logger.error(f"Error computing checksum for {path}: {e}")
        return ""


def load_file_hashes() -> Dict[str, str]:
    """
    Load previous file hashes from file_hashes.json

    Returns:
        dict: Dictionary of filename -> hash mappings
    """
    try:
        with open(Config.HASHES_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.info("No previous file hashes found, starting fresh")
        return {}
    except Exception as e:
        logger.error(f"Error loading file hashes: {e}")
        return {}


def save_file_hashes(hashes: Dict[str, str]) -> None:
    """
    Save file hashes to file_hashes.json

    Args:
        hashes (dict): Dictionary of filename -> hash mappings
    """
    try:
        with open(Config.HASHES_FILE, "w") as f:
            json.dump(hashes, f, indent=2)
        logger.info("File hashes saved successfully")
    except Exception as e:
        logger.error(f"Error saving file hashes: {e}")


def extract_text_from_file(file_path: str) -> str:
    """
    Extract text from txt, pdf, and docx files

    Args:
        file_path (str): Path to the file

    Returns:
        str: Extracted text content
    """
    ext = os.path.splitext(file_path)[-1].lower()

    if ext not in Config.SUPPORTED_EXTENSIONS:
        logger.warning(f"Unsupported file type: {ext} for file {file_path}")
        return ""

    logger.info(f"Processing file: {file_path}")

    try:
        if ext == ".txt":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

        elif ext == ".pdf":
            reader = PdfReader(file_path)
            text = ""
            for page_num, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text() or ""
                    text += page_text
                except Exception as e:
                    logger.warning(
                        f"Error extracting text from page {page_num} of {file_path}: {e}")
            return text

        elif ext == ".docx":
            doc = Document(file_path)
            paragraphs = []
            for para in doc.paragraphs:
                if para.text.strip():  # Skip empty paragraphs
                    paragraphs.append(para.text)
            return "\n".join(paragraphs)

    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        return ""


def smart_chunk_text(text: str, max_chunk_size: int = Config.CHUNK_SIZE, overlap: int = Config.CHUNK_OVERLAP) -> List[str]:
    """
    Smart text chunking that respects sentence boundaries

    Args:
        text (str): Text to chunk
        max_chunk_size (int): Maximum size of each chunk
        overlap (int): Overlap between chunks

    Returns:
        List[str]: List of text chunks
    """
    if not text.strip():
        return []

    # Split by sentences (basic approach)
    sentences = []
    current_sentence = ""

    for char in text:
        current_sentence += char
        # Avoid splitting on abbreviations
        if char in '.!?' and len(current_sentence) > 10:
            sentences.append(current_sentence.strip())
            current_sentence = ""

    # Add remaining text as last sentence
    if current_sentence.strip():
        sentences.append(current_sentence.strip())

    # Combine sentences into chunks
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        # If adding this sentence exceeds max size, save current chunk
        if current_chunk and len(current_chunk + " " + sentence) > max_chunk_size:
            chunks.append(current_chunk.strip())

            # Start new chunk with overlap from previous chunk
            if overlap > 0 and len(current_chunk) > overlap:
                current_chunk = current_chunk[-overlap:] + " " + sentence
            else:
                current_chunk = sentence
        else:
            if current_chunk:
                current_chunk += " " + sentence
            else:
                current_chunk = sentence

    # Add final chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    # Handle very long sentences that exceed max_chunk_size
    final_chunks = []
    for chunk in chunks:
        if len(chunk) <= max_chunk_size:
            final_chunks.append(chunk)
        else:
            # Split long chunks by character count
            for i in range(0, len(chunk), max_chunk_size):
                final_chunks.append(chunk[i:i + max_chunk_size])

    return final_chunks


def embed_text(text: str) -> List[float]:
    """
    Get embedding for text using OpenAI

    Args:
        text (str): Text to embed

    Returns:
        List[float]: Embedding vector
    """
    try:
        response = client.embeddings.create(
            input=text,
            model=Config.EMBEDDING_MODEL
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error creating embedding: {e}")
        raise

# ------------------ Vector Cleanup Functions ------------------


def delete_vectors_for_file(index, filename: str) -> bool:
    """
    Delete all vectors associated with a specific file

    Args:
        index: Pinecone index object
        filename (str): Name of the file to delete vectors for

    Returns:
        bool: True if deletion was successful
    """
    try:
        # Delete vectors with IDs matching pattern filename-*
        # We'll attempt to delete up to 1000 possible chunk IDs
        batch_size = 100
        deleted_count = 0

        # Assume max 1000 chunks per file
        for start_idx in range(0, 1000, batch_size):
            ids_batch = [
                f"{filename}-{i}" for i in range(start_idx, min(start_idx + batch_size, 1000))]

            try:
                index.delete(ids=ids_batch)
                # Note: Pinecone delete doesn't return count, but doesn't error for non-existent IDs
                deleted_count += batch_size
            except Exception as e:
                logger.debug(f"Batch deletion completed for {filename}: {e}")
                break

        logger.info(f"Attempted to delete vectors for file: {filename}")
        return True

    except Exception as e:
        logger.error(f"Error deleting vectors for {filename}: {e}")
        return False


async def cleanup_deleted_files(docs_path: str = Config.DOCS_FOLDER) -> None:
    """
    Remove vectors for files that no longer exist in the docs folder

    Args:
        docs_path (str): Path to documents folder
    """
    try:
        current_hashes = load_file_hashes()

        # Get current files in docs folder
        current_files = set()
        if os.path.exists(docs_path):
            for fname in os.listdir(docs_path):
                path = os.path.join(docs_path, fname)
                if os.path.isfile(path) and not fname.startswith('.'):
                    ext = os.path.splitext(fname)[-1].lower()
                    if ext in Config.SUPPORTED_EXTENSIONS:
                        current_files.add(fname)

        # Find files that were tracked but no longer exist
        tracked_files = set(current_hashes.keys())
        deleted_files = tracked_files - current_files

        if deleted_files:
            logger.info(
                f"Found {len(deleted_files)} deleted files: {deleted_files}")

            index = pc.Index(Config.INDEX_NAME)

            # Delete vectors for each deleted file
            for filename in deleted_files:
                logger.info(
                    f"Cleaning up vectors for deleted file: {filename}")
                success = delete_vectors_for_file(index, filename)

                if success:
                    logger.info(
                        f"Successfully cleaned up vectors for: {filename}")
                else:
                    logger.warning(
                        f"Failed to clean up vectors for: {filename}")

            # Update file hashes to remove deleted files
            updated_hashes = {
                k: v for k, v in current_hashes.items() if k in current_files}
            save_file_hashes(updated_hashes)

            logger.info(
                f"Cleanup completed for {len(deleted_files)} deleted files")
        else:
            logger.info("No deleted files found, no cleanup needed")

    except Exception as e:
        logger.error(f"Error during cleanup of deleted files: {e}")

# ------------------ Telegram integration ------------------


async def send_telegram_message(chat_id: int, text: str) -> bool:
    """
    Send message to Telegram chat using aiohttp

    Args:
        chat_id (int): Telegram chat ID
        text (str): Message text to send

    Returns:
        bool: True if message sent successfully
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    logger.info(f"Message sent successfully to chat {chat_id}")
                    return True
                else:
                    logger.error(
                        f"Failed to send message to chat {chat_id}: {response.status}")
                    return False
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")
        return False

# ------------------ Pinecone integration ------------------


async def ensure_index_exists() -> None:
    """
    Ensure Pinecone index exists, create if it doesn't
    """
    try:
        existing_indexes = pc.list_indexes().names()
        if Config.INDEX_NAME not in existing_indexes:
            logger.info(f"Creating index {Config.INDEX_NAME}...")
            pc.create_index(
                name=Config.INDEX_NAME,
                dimension=Config.EMBEDDING_DIMENSION,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud=Config.PINECONE_CLOUD,
                    region=Config.PINECONE_REGION
                )
            )
            # Wait for index to be ready
            while Config.INDEX_NAME not in pc.list_indexes().names():
                logger.info("Waiting for index to be created...")
                await asyncio.sleep(5)
            logger.info(f"Index {Config.INDEX_NAME} created successfully")
        else:
            logger.info(f"Index {Config.INDEX_NAME} already exists")
    except Exception as e:
        logger.error(f"Error ensuring index exists: {e}")
        raise


async def ingest_documents(docs_path: str = Config.DOCS_FOLDER) -> None:
    """
    Asynchronously index documents in Pinecone with improved error handling and cleanup

    Args:
        docs_path (str): Path to documents folder
    """
    if not os.path.exists(docs_path):
        logger.error(f"Directory {docs_path} does not exist!")
        return

    await ensure_index_exists()

    # First, cleanup vectors for deleted files
    await cleanup_deleted_files(docs_path)

    index = pc.Index(Config.INDEX_NAME)
    current_hashes = load_file_hashes()
    new_hashes = {}

    processed_files = 0
    skipped_files = 0

    for fname in os.listdir(docs_path):
        path = os.path.join(docs_path, fname)

        # Skip directories and system files
        if not os.path.isfile(path) or fname.startswith('.'):
            continue

        # Check if file extension is supported
        ext = os.path.splitext(fname)[-1].lower()
        if ext not in Config.SUPPORTED_EXTENSIONS:
            logger.warning(f"Skipping unsupported file type: {fname}")
            skipped_files += 1
            continue

        current_hash = file_checksum(path)
        new_hashes[fname] = current_hash

        # Skip if file hasn't changed
        if fname in current_hashes and current_hashes[fname] == current_hash:
            logger.info(f"File {fname} unchanged, skipping")
            continue

        # If file has changed, delete old vectors first
        if fname in current_hashes:
            logger.info(f"File {fname} has changed, removing old vectors...")
            delete_vectors_for_file(index, fname)

        logger.info(
            f"Processing {'changed' if fname in current_hashes else 'new'} file: {fname}")

        try:
            text = extract_text_from_file(path)
            if not text.strip():
                logger.warning(f"No text extracted from {fname}")
                continue

            # Use smart chunking
            chunks = smart_chunk_text(text)
            if not chunks:
                logger.warning(f"No chunks created from {fname}")
                continue

            # Create vectors
            vectors = []
            for i, chunk in enumerate(chunks):
                try:
                    embedding = embed_text(chunk)
                    vectors.append({
                        "id": f"{fname}-{i}",
                        "values": embedding,
                        "metadata": {
                            "source": fname,
                            "text": chunk,
                            "chunk_index": i,
                            "total_chunks": len(chunks)
                        }
                    })
                except Exception as e:
                    logger.error(
                        f"Error creating embedding for chunk {i} of {fname}: {e}")
                    continue

            # Upsert vectors in batches
            if vectors:
                batch_size = 100
                for i in range(0, len(vectors), batch_size):
                    batch = vectors[i:i + batch_size]
                    try:
                        index.upsert(vectors=batch)
                        logger.info(
                            f"Upserted batch {i//batch_size + 1} for {fname}")
                    except Exception as e:
                        logger.error(f"Error upserting batch for {fname}: {e}")

                logger.info(
                    f"Successfully processed {fname}: {len(vectors)} vectors created")
                processed_files += 1

        except Exception as e:
            logger.error(f"Error processing {fname}: {e}")

    save_file_hashes(new_hashes)
    logger.info(
        f"Ingestion completed: {processed_files} files processed, {skipped_files} files skipped")


def query_index(query: str) -> Dict:
    """
    Query Pinecone index for relevant matches with improved error handling

    Args:
        query (str): Search query

    Returns:
        dict: Query results
    """
    try:
        index = pc.Index(Config.INDEX_NAME)
        vector = embed_text(query)

        result = index.query(
            vector=vector,
            top_k=Config.TOP_K,
            include_metadata=True
        )

        logger.info(
            f"Query executed successfully, found {len(result.get('matches', []))} matches")
        return result

    except Exception as e:
        logger.error(f"Error querying index: {e}")
        return {"matches": []}


def generate_response(query: str, matches: List[Dict]) -> str:
    """
    Generate a natural response based on query and matches with improved prompting

    Args:
        query (str): User query
        matches (List[Dict]): Search results from Pinecone

    Returns:
        str: Generated response
    """
    if not matches:
        return ("I couldn't find relevant information in your documents to answer this question. "
                "Please try rephrasing your query or check if the relevant documents are uploaded.")

    # Prepare context with source attribution
    context_parts = []
    sources = set()

    for match in matches:
        metadata = match.get("metadata", {})
        text = metadata.get("text", "")
        source = metadata.get("source", "unknown")

        if text and source:
            context_parts.append(f"From {source}:\n{text}")
            sources.add(source)

    context = "\n\n".join(context_parts)
    sources_list = ", ".join(sorted(sources))

    system_prompt = """You are a helpful coaching assistant. Provide practical, actionable advice based on the provided documents.

Guidelines:
- Give specific, practical recommendations
- Reference the source documents when relevant
- If the information is insufficient, be honest about limitations
- Keep responses focused and helpful
- Use a friendly, professional tone
- Structure your response clearly with actionable steps when appropriate"""

    try:
        response = client.chat.completions.create(
            model=Config.LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Query: {query}\n\nContext from documents:\n{context}"}
            ],
            temperature=Config.TEMPERATURE,
            max_tokens=Config.MAX_RESPONSE_TOKENS
        )

        answer = response.choices[0].message.content

        # Add source attribution
        if sources:
            answer += f"\n\n*Sources: {sources_list}*"

        return answer

    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return ("I encountered an error while generating a response. "
                "Please try again or contact support if the problem persists.")

# ------------------ FastAPI endpoints ------------------


@app.get("/")
def root():
    """Return API status and basic information"""
    return {
        "message": "Enhanced Coaching Bot is running",
        "version": "2.0.0",
        "status": "healthy",
        "endpoints": {
            "search": "/search?q=your_question",
            "telegram_webhook": "/telegram-webhook",
            "health": "/health",
            "stats": "/stats",
            "cleanup": "/cleanup"
        }
    }


@app.get("/health")
def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Quick test of Pinecone connection
        pc.list_indexes()
        return {"status": "healthy", "pinecone": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")


@app.get("/stats")
def get_index_stats():
    """
    Get current Pinecone index statistics
    """
    try:
        index = pc.Index(Config.INDEX_NAME)
        stats = index.describe_index_stats()

        # Get file information
        current_hashes = load_file_hashes()

        return {
            "index_name": Config.INDEX_NAME,
            "total_vectors": stats.get('total_vector_count', 0),
            "index_fullness": stats.get('index_fullness', 0),
            "dimension": stats.get('dimension', 0),
            "tracked_files": len(current_hashes),
            "files": list(current_hashes.keys()) if current_hashes else []
        }
    except Exception as e:
        logger.error(f"Error getting index stats: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to get index stats")


@app.post("/cleanup")
async def manual_cleanup():
    """
    Manually trigger cleanup of deleted files
    """
    try:
        await cleanup_deleted_files()
        return {"status": "cleanup_completed", "message": "Successfully cleaned up vectors for deleted files"}
    except Exception as e:
        logger.error(f"Manual cleanup failed: {e}")
        raise HTTPException(status_code=500, detail="Cleanup failed")


@app.get("/search")
def search(q: str):
    """
    Search the knowledge base with enhanced validation and error handling

    Args:
        q (str): Search query parameter

    Returns:
        dict: Search results with matches
    """
    # Validate query
    if not q or not q.strip():
        raise HTTPException(
            status_code=400,
            detail="Query parameter 'q' is required and must not be empty"
        )

    query = q.strip()

    if len(query) > Config.MAX_QUERY_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Query too long. Maximum length is {Config.MAX_QUERY_LENGTH} characters"
        )

    try:
        results = query_index(query)
        matches = results.get("matches", [])

        # Enhanced response format
        return {
            "query": query,
            "matches_found": len(matches),
            "matches": matches,
            "response": generate_response(query, matches)
        }

    except Exception as e:
        logger.error(f"Error in search endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during search"
        )


@app.post("/telegram-webhook")
async def telegram_webhook(request: Request):
    """
    Handle incoming messages from Telegram with comprehensive error handling

    Args:
        request (Request): FastAPI request object

    Returns:
        dict: Processing status
    """
    try:
        data = await request.json()

        # Validate message structure
        if not data.get("message"):
            return {"status": "no_message"}

        message = data["message"]

        if not message.get("text"):
            return {"status": "no_text_message"}

        query = message["text"].strip()
        chat_id = message["chat"]["id"]
        user_info = message.get("from", {})
        username = user_info.get("username", "unknown")

        logger.info(
            f"Received message from @{username} (chat_id: {chat_id}): {query[:100]}...")

        # Validate query length
        if len(query) > Config.MAX_QUERY_LENGTH:
            response = (f"Your message is too long ({len(query)} characters). "
                        f"Please keep it under {Config.MAX_QUERY_LENGTH} characters.")
            await send_telegram_message(chat_id, response)
            return {"status": "query_too_long"}

        # Handle commands
        if query.startswith('/'):
            if query == '/start':
                response = ("Welcome to the Enhanced Coaching Bot!\n\n"
                            "I can help answer questions based on your uploaded documents. "
                            "Just send me your question and I'll search through the knowledge base.")
            elif query == '/help':
                response = ("*How to use this bot:*\n\n"
                            "• Simply type your question\n"
                            "• I'll search through uploaded documents\n"
                            "• Ask follow-up questions anytime\n"
                            "• Use /start to see this welcome message again")
            else:
                response = "Unknown command. Type /help for available commands."

            await send_telegram_message(chat_id, response)
            return {"status": "command_processed"}

        # Process regular query
        try:
            results = query_index(query)
            response = generate_response(query, results.get("matches", []))

            success = await send_telegram_message(chat_id, response)

            if success:
                logger.info(f"Successfully processed query for @{username}")
                return {"status": "processed"}
            else:
                logger.error(f"Failed to send response to @{username}")
                return {"status": "send_failed"}

        except Exception as e:
            logger.error(f"Error processing query for @{username}: {e}")
            error_response = ("I encountered an error while processing your request. "
                              "Please try rephrasing your question or try again later.")
            await send_telegram_message(chat_id, error_response)
            return {"status": "processing_error"}

    except Exception as e:
        logger.error(f"Error in telegram_webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ------------------ Startup event ------------------


@app.on_event("startup")
async def startup_event():
    """
    Initialize the application with document ingestion
    """
    logger.info("Starting Enhanced Coaching Bot...")
    logger.info(f"Configuration: {Config.INDEX_NAME}, {Config.DOCS_FOLDER}")

    try:
        await ingest_documents()
        logger.info("Bot initialization completed successfully!")
    except Exception as e:
        logger.error(f"Failed to initialize bot: {e}")
        raise

# ------------------ Manual execution ------------------

if __name__ == "__main__":
    """Run ingestion manually if script is executed directly"""
    logger.info("Running manual document ingestion...")
    asyncio.run(ingest_documents())
    logger.info("Manual ingestion completed!")
