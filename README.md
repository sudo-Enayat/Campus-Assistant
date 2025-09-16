🏫 Campus Assistant - Multilingual RAG Chatbot

A self-hosted, multilingual conversational assistant designed for college campuses. This AI-powered chatbot answers student queries about fees, admissions, courses,semester and campus policies using a local knowledge base of official documents.

✨ Features

    🤖 AI-Powered Responses: Uses local LLM models via llama-cpp-python for intelligent conversations

    🌍 Multilingual Support: Automatically detects and responds in user's language (English, Hindi, Bengali, Hindlish .... )

    📚 RAG Pipeline: Retrieves relevant information from local document knowledge base

    ⚡ Real-time Streaming: Live response streaming with animated status indicators

    🎨 Beautiful UI: Modern gradient design with smooth animations

    👨‍💼 Admin Panel: Easy model management and document synchronization

    📱 Responsive Design: Works seamlessly on desktop and mobile devices

    🔒 Simple Authentication: Password-protected admin access

🚀 Quick Start
Prerequisites

    Python 3.8+
    install c++ using vs_BuildTools
    At least 8GB RAM
    GGUF format language model (Gemma 3 4b recommended)


Installation

  Clone the repository
    
    git clone https://github.com/your-username/campus-assistant.git
    
    cd campus-assistant

Create virtual environment

    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate

Install dependencies

    pip install -r requirements.txt

Download an LLM


  👍recommended to use gemma 3 4b (140+ laguage supports) from huggingface
  
  🚀for speed use LLAMA 3.2 1b

Add your documents

    # Create data directory and add your FAQ files
    mkdir data
    # Place your .txt, .md files in data/ folder
Run the application

    python app.py

Access the application

    Chat Interface: http://localhost:5000

    Admin Panel: http://localhost:5000/admin (password: admin123)


  📁 Project Structure
    
      campus-assistant/
    ├── app.py                 # Main Flask application
    ├── simple_rag.py          # RAG pipeline implementation
    ├── config.py              # Configuration settings
    ├── requirements.txt       # Python dependencies
    ├── README.md              # Project documentation
    ├── .gitignore            # Git ignore file
    │
    ├── models/               # Place .gguf model files here
    │   └── gemma-3-4b-it-Q4_K_M.gguf (example)
    │
    ├── data/                 # Place your document files here
    │   ├── fees_faq.txt (example data)
    │   ├── admission_faq.txt 
    │   └── courses_info.md
    │
    ├── static/               # Frontend assets
    │   ├── css/
    │   │   └── style.css     # Styling and animations
    │   └── js/
    │       └── main.js       # Frontend JavaScript
    │
    ├── templates/            # HTML templates
    │   ├── index.html        # Main chat interface
    │   └── admin.html        # Admin panel
    │
    └── chroma_db/            # Vector database (auto-created)
        └── (ChromaDB files)
🔧 Configuration

Model Settings

Edit simple_rag.py to adjust model parameters:

    self.llm = Llama(
        model_path=model_path,
        n_ctx=1024,          # Context window size
        n_threads=6,         # CPU threads (adjust for your system)
        n_batch=256,         # Batch size
        use_mlock=True,      # Keep model in memory
    )

Document Processing

Supported file formats:

    .txt - Plain text files

    .md - Markdown files

Documents should be in English for optimal retrieval performance.


Admin Authentication

Change the default admin password in app.py:
    
    if password == 'your-new-password':  # Change from 'admin123'

📋 Usage Guide
For Students (Chat Interface)

    Visit the Chat: Go to http://localhost:5000

    Ask Questions: Type your question in any supported language

    Get Answers: The bot will respond in your language with relevant information

    View Sources: See which documents were used to generate the answer

Example Queries:

    "What are the semester fees?"

    "फीस की जानकारी दें" (Hindi)

    "ভর্তির নিয়ম কি?" (Bengali)

For Administrators (Admin Panel)

    Access Admin Panel: Go to http://localhost:5000/admin

    Login: Use password admin123 (or your custom password)

    Load Model: Select a .gguf model and click "Load Model"

    Sync Documents: Click "Sync Documents" to update knowledge base

    Monitor Status: Check model and sync status indicators

Adding New Documents

    Place Files: Add .txt or .md files to the data/ folder

    Sync Knowledge Base: Go to admin panel and click "Sync Documents"

    Test: Ask questions related to the new content

🎨 UI Features
Chat Interface

    Gradient Background: Beautiful purple-blue gradient theme

    Animated Messages: Smooth slide-in animations for messages

    Status Indicators: Real-time processing status with wave animations

        🤔 Processing your question...

        🔍 Checking sources...

        ✍️ Formulating response...

    Streaming Responses: Words appear progressively as the AI generates them

    Responsive Design: Adapts to all screen sizes

Admin Panel

    Model Management: Dropdown selection and loading status

    Sync Controls: Animated sync button with spinning arrows → checkmark

    Status Display: Real-time feedback with color-coded messages

    Instructions: Built-in guidance for non-technical users


🛠️ Development
Requirements.txt

    
    flask==2.3.3
    llama-cpp-python==0.2.11
    chromadb==0.4.15
    sentence-transformers==2.2.2
    pathlib

Adding New Languages

  The system automatically supports any language that Gemma can understand. No additional configuration needed.
  
  Just add new LLMs to model folder and get all the languages it can understand without additional setup.

Performance Optimization

    Model Size: Use Q4_K_M quantization for best speed/quality balance

    Context Window: Reduce n_ctx for faster responses

    Document Chunks: Limit chunk size to 500 characters

    Response Length: Cap at 150 tokens for quick responses

🐛 Troubleshooting
Common Issues

"No model loaded" error

    Solution: Go to admin panel and load a model first

Model loading is slow

    Solution: Ensure you have enough RAM and use a smaller model

Documents not found during sync

    Solution: Check that files are in data/ folder with .txt or .md extension

Chat responses are slow

    Solution: Reduce max_tokens in simple_rag.py or use a smaller model

Admin panel not accessible

    Solution: Check the URL (http://localhost:5000/admin) and password

Performance Tips

    Use SSD storage for faster model loading

    Increase RAM for better performance with larger models

    Adjust thread count based on your CPU cores

    Limit document size for faster retrieval

    
🙏 Acknowledgments

    Google for the Gemma model family

    llama.cpp project for efficient model inference

    ChromaDB for vector storage

    Flask web framework

    Hugging Face for model hosting and sentence transformers
