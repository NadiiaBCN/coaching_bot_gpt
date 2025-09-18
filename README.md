# Coaching Bot GPT

This project is a demonstration of a coaching bot that indexes documents from a local folder and stores them as a vector database using Pinecone. The bot automatically updates the cloud knowledge base when new or edited files are detected, saving time by eliminating manual uploads. Future enhancements can include moving documents to a server or adding a browser-based upload interface.

## Features
- Indexes PDF, TXT, and Word (.docx) documents from a local `docs/` folder.
- Automatically detects and processes new or changed files.
- Stores embeddings in a Pinecone vector index for efficient search.
- Provides a FastAPI endpoint for querying the knowledge base.
- Supports incremental updates using file hash tracking.

## Prerequisites
- Python 3.8 or higher.
- Required libraries: `fastapi`, `uvicorn`, `python-dotenv`, `pinecone-client`, `openai`, `PyPDF2`, `python-docx`.
- Install dependencies:

    `pip install -r requirements.txt`

## Environment variables:

Create a `.env` file with:
`PINECONE_API_KEY=your_pinecone_api_key`
`OPENAI_API_KEY=your_openai_api_key`

Obtain API keys from Pinecone and OpenAI.

## Setup

1. Clone the repository or copy the `main.py` file to your project directory.
2. Create a `docs/` folder and add your documents (PDF, TXT, .docx).
3. Set up the `.env` file with your API keys.
4. Run the bot:

    `uvicorn main:app --reload`

    The bot will start on http://127.0.0.1:8000


## How It Works
Your documents (PDF, TXT, Word) are stored on your computer in a folder. Bot automatically checks this folder: if you add a new file or edit an existing one, it immediately updates the cloud knowledge base. This saves time, as there’s no need to manually upload files. 

In production, there is an option to move documents to a server or add a browser-based upload interface.

The bot computes SHA256 hashes of files to detect changes.

Text is extracted from supported file types and split into 500-character chunks.

OpenAI embeddings are generated for each chunk.
Vectors are upserted into the Pinecone coaching-knowledge index.

## Scaling Options

**Pinecone Upgrade:** For higher accuracy and larger vector sizes, there is an option to upgrade to the Pinecone paid plan

**FAISS Alternative:** For local or custom scalability, there is an option to upgrade to FAISS, which supports precise dimensional control.

**Production Improvements:** Move documents to a server or implement a browser-based upload interface.


## Contributing
Feel free to suggest improvements or report issues. Fork the repository and submit pull requests! 🫶

## License
This project is licensed under the MIT License. See the LICENSE file for details.