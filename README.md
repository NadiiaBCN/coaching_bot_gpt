# Coaching Bot GPT

This project is a demonstration of a coaching bot that indexes documents from a local folder and stores them as a vector database using Pinecone. The bot automatically updates the cloud knowledge base when new or edited files are detected, saving time by eliminating manual uploads. Future enhancements can include moving documents to a server or adding a browser-based upload interface.

## Features
- Indexes PDF, TXT, and Word (.docx) documents from a local `docs/` folder.
- Automatically detects and processes new or changed files.
- Stores embeddings in a Pinecone vector index for efficient search.
- Provides a FastAPI endpoint for querying the knowledge base.
- Supports incremental updates using file hash tracking.
- Integrates with Telegram via webhook for user interaction.

## Prerequisites
- Python 3.8 or higher.
- Required libraries: `fastapi`, `uvicorn`, `python-dotenv`, `pinecone`, `openai`, `PyPDF2`, `python-docx`, `requests`.
- Install dependencies:
  ```bash
  pip install -r requirements.txt

## Environment variables:
Create a `.env` file with:
```bush
`PINECONE_API_KEY=your_pinecone_api_key`
`OPENAI_API_KEY=your_openai_api_key`
`TELEGRAM_BOT_TOKEN=your_telegram_bot_token`
```
Obtain API keys from Pinecone and OpenAI. Get TELEGRAM_BOT_TOKEN from @BotFather in Telegram.

## Setup

1. Clone the repository or copy the `main.py` file to your project directory.
2. Create a `docs/` folder and add your documents (PDF, TXT, .docx).
3. Set up the `.env` file with your API keys and Telegram bot token.
4. Run the bot:
```bush
    `uvicorn main:app --reload`
```

The bot will start on http://127.0.0.1:8000 and index documents automatically. Check logs for "Ingestion completed. Bot is ready."

## Deployment to Heroku

Install the Heroku CLI and log in: `heroku login`
Create a Heroku app: `heroku create coachingbot`
Set environment variables:
`heroku config:set PINECONE_API_KEY=your_pinecone_api_key`
`heroku config:set OPENAI_API_KEY=your_openai_api_key`
`heroku config:set TELEGRAM_BOT_TOKEN=your_telegram_bot_token`

Deploy the code:
```bush
git add
git commit -m "Initial deploy"
git push heroku main
heroku ps:scale web=1
```

## Usage
This bot allows users to create a personalized assistant based on their own documents. Here’s how a new user can set it up after downloading the repository:

- **Check Bot Status**: Visit `http://127.0.0.1:8000/` after starting the bot (returns `{"message": "Coaching bot is running"}`) to confirm it’s running locally.

- **Search the Knowledge Base**:
  - Use the `/search` endpoint with a query parameter, e.g., `http://127.0.0.1:8000/search?q=your_topic`. This returns `{"matches": [...]}` with relevant snippets from your documents.

- **Interact via Telegram**:
  - Create your own Telegram bot via @BotFather and obtain a token. Add it to your `.env` file as `TELEGRAM_BOT_TOKEN`.
  - Set up the webhook:
    ```bash
    curl -X POST "https://api.telegram.org/bot<YOUR_TELEGRAM_TOKEN>/setWebhook" -d "url=http://127.0.0.1:8000/telegram-webhook"

## How It Works
Documents are stored in the docs/ folder on your computer. The bot automatically checks this folder, indexes new or edited files into a Pinecone vector database, and uses OpenAI to generate responses.
Users interact via Telegram, where the bot processes queries and returns advice based on the indexed content.

## Scaling Options

**Pinecone Upgrade:** For higher accuracy and larger vector sizes, there is an option to upgrade to the Pinecone paid plan

**FAISS Alternative:** For local or custom scalability, there is an option to upgrade to FAISS, which supports precise dimensional control.

**Production Improvements:** Move documents to a server or implement a browser-based upload interface.


## Contributing
Feel free to suggest improvements or report issues. Fork the repository and submit pull requests! 🫶

## License
This project is licensed under the MIT License. See the LICENSE file for details.