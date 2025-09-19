# Enhanced Coaching Bot GPT

A production-ready coaching bot that intelligently indexes documents from a local folder and creates a powerful vector database using Pinecone. The bot features automatic knowledge base updates, smart document processing, and seamless Telegram integration for user interactions.

## Features

### Core Functionality
- **Multi-format Support**: Processes PDF, TXT, and Word (.docx) documents from local `docs/` folder
- **Smart Change Detection**: Automatically detects and processes new or modified files using SHA256 hashing
- **Intelligent Text Chunking**: Respects sentence boundaries for better semantic understanding
- **Vector Search**: Stores embeddings in Pinecone vector database for efficient similarity search
- **Incremental Updates**: Only processes changed files, saving time and API costs

### Advanced Capabilities
- **Production-Ready Architecture**: Comprehensive error handling, logging, and monitoring
- **Telegram Integration**: Full webhook support with command handling (`/start`, `/help`)
- **Async Processing**: Non-blocking document ingestion and Telegram communication
- **Batch Processing**: Efficient handling of large document collections
- **Health Monitoring**: Built-in health checks and system status endpoints
- **Smart Response Generation**: Context-aware responses with source attribution

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Documents     │────│  Enhanced Bot    │────│   Pinecone      │
│   (docs/)       │    │  (FastAPI)       │    │   Vector DB     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                │
                       ┌──────────────────┐
                       │   Telegram       │
                       │   Integration    │
                       └──────────────────┘
```

## Prerequisites

### System Requirements
- Python 3.8 or higher
- 4GB+ RAM recommended for large document collections
- Stable internet connection for API calls

### API Keys & Services
- **Pinecone Account**: [Sign up here](https://www.pinecone.io/)
- **OpenAI API Key**: [Get your key](https://platform.openai.com/api-keys)
- **Telegram Bot Token**: Create bot via [@BotFather](https://t.me/botfather)

### Dependencies
Install required packages:
```bash
pip install -r requirements.txt
```

**requirements.txt:**
```
fastapi
uvicorn
gunicorn
openai
python-dotenv
pinecone
PyPDF2
python-docx
requests
aiohttp
```

## Setup & Configuration

### 1. Environment Configuration
Create a `.env` file in the project root:

```bash
# Required API Keys
PINECONE_API_KEY=your_pinecone_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
```

### 2. Project Structure
```
coaching-bot/
├── main.py                 # Main application file
├── requirements.txt        # Dependencies
├── .env                    # Environment variables
├── file_hashes.json        # Auto-generated file tracking
├── docs/                   # Your documents folder
│   ├── coaching_guide.pdf
│   ├── best_practices.docx
│   └── tips.txt
└── README.md
```

### 3. Document Preparation
- Create a `docs/` folder in your project directory
- Add your documents (PDF, TXT, .docx files)
- Ensure documents are well-structured for better chunking

## Quick Start

### Local Development
1. **Clone and setup:**
```bash
git clone <repository-url>
cd coaching-bot
pip install -r requirements.txt
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. **Run the application:**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

4. **Verify installation:**
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "pinecone": "connected"
}
```

### Initial Document Processing
The bot automatically processes documents on startup. Monitor the logs:

```
INFO - Starting Enhanced Coaching Bot...
INFO - Processing new file: coaching_guide.pdf
INFO - Successfully processed coaching_guide.pdf: 45 vectors created
INFO - Ingestion completed: 3 files processed, 0 files skipped
INFO - Bot initialization completed successfully! 🚀
```

## API Endpoints

### Core Endpoints

#### `GET /`
Returns bot status and available endpoints.

**Example:**
```bash
curl http://localhost:8000/
```

#### `GET /health`
System health check for monitoring.

**Example:**
```bash
curl http://localhost:8000/health
```

#### `GET /search?q=<query>`
Search the knowledge base.

**Example:**
```bash
curl "http://localhost:8000/search?q=How to improve productivity"
```

**Response:**
```json
{
  "query": "How to improve productivity",
  "matches_found": 3,
  "matches": [...],
  "response": "Based on your documents, here are key productivity strategies:\n\n1. Time blocking: Schedule focused work sessions...\n\n*Sources: productivity_guide.pdf, best_practices.docx*"
}
```

#### `POST /telegram-webhook`
Handles Telegram bot interactions (set up automatically).

## Telegram Integration

### Setting Up Telegram Bot

1. **Create your bot:**
   - Message [@BotFather](https://t.me/botfather) on Telegram
   - Use `/newbot` command
   - Follow the instructions to get your bot token

2. **Configure webhook (for production):**
```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://your-domain.com/telegram-webhook"}'
```

3. **For local testing with ngrok:**
```bash
# Install ngrok
npm install -g ngrok

# In terminal 1: Start your bot
uvicorn main:app --reload

# In terminal 2: Expose local server
ngrok http 8000

# Set webhook with ngrok URL
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://your-ngrok-id.ngrok.io/telegram-webhook"}'
```

### Bot Commands
- `/start` - Welcome message and introduction
- `/help` - Usage instructions and tips
- Any question - Searches knowledge base and provides answer

### Example Conversation
```
User: /start
Bot: Welcome to the Enhanced Coaching Bot! 🤖

I can help answer questions based on your uploaded documents. Just send me your question and I'll search through the knowledge base.

User: How can I manage my time better?
Bot: Based on your documents, here are effective time management strategies:

1. **Time Blocking**: Schedule specific time slots for different activities...
2. **Priority Matrix**: Use the Eisenhower method to categorize tasks...
3. **Eliminate Distractions**: Create a focused work environment...

*Sources: time_management.pdf, productivity_tips.docx*
```

## Deployment

### Heroku Deployment

1. **Prepare for deployment:**
```bash
# Create Procfile
echo "web: uvicorn main:app --host 0.0.0.0 --port \$PORT" > Procfile

# Create runtime.txt
echo "python-3.11.9" > runtime.txt
```

2. **Deploy to Heroku:**
```bash
# Login to Heroku
heroku login

# Create app
heroku create your-coaching-bot

# Set environment variables
heroku config:set PINECONE_API_KEY=your_key
heroku config:set OPENAI_API_KEY=your_key  
heroku config:set TELEGRAM_BOT_TOKEN=your_token

# Deploy
git add .
git commit -m "Initial deployment"
git push heroku main
```

3. **Set up Telegram webhook:**
```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://your-coaching-bot.herokuapp.com/telegram-webhook"}'
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# Build and run
docker build -t coaching-bot .
docker run -p 8000:8000 --env-file .env coaching-bot
```

## Configuration Options

The bot can be customized via the `Config` class in `main.py`:

```python
class Config:
    CHUNK_SIZE = 500          # Text chunk size for embeddings
    CHUNK_OVERLAP = 50        # Overlap between chunks
    TOP_K = 3                 # Number of search results
    MAX_QUERY_LENGTH = 1000   # Maximum query length
    MAX_RESPONSE_TOKENS = 500 # Maximum response length
    TEMPERATURE = 0.7         # Response creativity (0-1)
```

## Monitoring & Logging

### Log Levels
```python
# View logs in real-time
tail -f bot.log

# Check specific error types
grep "ERROR" bot.log
```

### Health Monitoring
Set up monitoring for the `/health` endpoint:

```bash
# Simple health check script
#!/bin/bash
response=$(curl -s http://localhost:8000/health)
if [[ $response == *"healthy"* ]]; then
    echo "Bot is healthy"
else
    echo "Bot is unhealthy"
    exit 1
fi
```

## Troubleshooting

### Common Issues

#### 1. Documents Not Processing
**Symptoms:** Files in `docs/` folder not being indexed

**Solutions:**
- Check file permissions: `chmod 644 docs/*`
- Verify supported formats: `.txt`, `.pdf`, `.docx` only
- Check logs for specific error messages
- Ensure files aren't corrupted

#### 2. Pinecone Connection Issues
**Symptoms:** `Health check failed` or connection errors

**Solutions:**
```bash
# Verify API key
curl -H "Api-Key: YOUR_PINECONE_KEY" https://api.pinecone.io/
  
# Check index status
python -c "
from pinecone import Pinecone
pc = Pinecone(api_key='YOUR_KEY')
print(pc.list_indexes())
"
```

#### 3. Telegram Webhook Issues
**Symptoms:** Bot not responding to messages

**Solutions:**
```bash
# Check webhook status
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"

# Remove webhook (for testing)
curl -X POST "https://api.telegram.org/bot<TOKEN>/deleteWebhook"

# Test with polling instead of webhook (development only)
# Modify telegram integration to use polling
```

#### 4. OpenAI API Errors
**Symptoms:** Embedding or response generation failures

**Solutions:**
- Check API key validity and billing status
- Monitor rate limits: `openai.error.RateLimitError`
- Verify model availability: `text-embedding-3-small`, `gpt-3.5-turbo`

### Performance Optimization

1. **Large Document Collections:**
```python
# Increase batch size for faster processing
Config.BATCH_SIZE = 200

# Use more powerful embedding model
Config.EMBEDDING_MODEL = "text-embedding-3-large"
```

2. **Response Time:**
```python
# Reduce number of search results
Config.TOP_K = 2

# Decrease response length
Config.MAX_RESPONSE_TOKENS = 300
```

## Scaling Options

### Database Alternatives

#### FAISS (Local Vector DB)
For offline or high-privacy scenarios:
```python
import faiss
import numpy as np

# Replace Pinecone with FAISS
index = faiss.IndexFlatIP(1536)  # dimension for text-embedding-3-small
```

#### Weaviate (Open Source)
For advanced semantic search:
```python
import weaviate

client = weaviate.Client("http://localhost:8080")
```

### Model Upgrades

#### Better Embeddings
```python
# GPT-4 level embeddings
Config.EMBEDDING_MODEL = "text-embedding-3-large"
Config.EMBEDDING_DIMENSION = 3072
```

#### Advanced Language Models
```python
# More capable responses
Config.LLM_MODEL = "gpt-4"
Config.MAX_RESPONSE_TOKENS = 1000
```

## Contributing

We welcome contributions! Here's how to get started:

1. **Fork the repository**
2. **Create a feature branch:**
```bash
git checkout -b feature/amazing-improvement
```

3. **Make your changes** following these guidelines:
   - Add comprehensive error handling
   - Include unit tests for new features
   - Update documentation
   - Follow existing code style

4. **Test thoroughly:**
```bash
# Run tests (when implemented)
pytest tests/

# Test with different document types
# Test Telegram integration
# Verify API endpoints
```

5. **Submit a pull request** with:
   - Clear description of changes
   - Before/after behavior
   - Testing steps

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Set up pre-commit hooks
pre-commit install

# Run code formatting
black main.py
flake8 main.py
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **OpenAI** for GPT models and embeddings API
- **Pinecone** for vector database infrastructure  
- **FastAPI** for the robust web framework
- **Telegram** for bot platform and API