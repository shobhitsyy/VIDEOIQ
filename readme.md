# VIDEOIQ

A Python-based toolkit for extracting, summarizing, and querying YouTube video transcripts.  
Includes both a backend API and a user-friendly Streamlit interface.

---

## Features

- **Extract Transcript**:  
  Provide a YouTube URL and extract its transcript automatically.

- **Summarize Transcript**:  
  Generate a concise summary and key points of the transcript using various AI providers.

- **Q&A Chatbot**:  
  Ask questions about the video and get AI-generated answers based on the transcript.

---

## Technology Stack

- **Python 3.8+**
- Streamlit - Interactive UI for the toolkit.
- FastAPI *(optional, for backend API endpoints)*
- Custom modules for extraction, summarization, and Q&A.

---

## Setup & Installation

1. **Clone the repository**
    ```bash
    git clone https://github.com/yourusername/VIDEOIQ.git
    cd VIDEOIQ
    ```

2. **Create and activate a virtual environment (recommended)**
    ```bash
    python -m venv venv
    source venv/bin/activate   # On Windows: venv\Scripts\activate
    ```

3. **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4. **Set up environment variables**  
   You must create a `.env` file in the project root directory with your API keys.  
   The following keys are required:

    ```
    GROQ_API_KEY=your_groq_api_key
    GEMINI_API_KEY=your_gemini_api_key
    ```

    You can copy the provided `.env.example` file and fill in your API keys.

---

## Usage

### 1. Run the Streamlit App

This is the easiest way to use all features in one place.

```bash
streamlit run streamlit_app.py
```

Visit [http://localhost:8501](http://localhost:8501) in your browser.

### 2. Run Backend API (Optional)

If you want to use the backend as an API (for custom frontends):

```bash
uvicorn main:app --reload
```

---

## Project Structure

```
VIDEOIQ/
│
├── extract_transcript.py
├── summarize_json.py
├── groq_qna.py
├── main.py               # (FastAPI backend)
├── streamlit_app.py      # (Streamlit frontend)
├── requirements.txt
├── .env                  # (not committed)
├── .gitignore
└── README.md
```

---

## Contributing

Pull requests are welcome!  
Feel free to open an issue for questions, ideas, or feature requests.

---

## License

This project is licensed under the MIT License.

---

## Acknowledgements

- Streamlit
- FastAPI
- OpenAI
- Groq
- Google Gemini
- And all open-source contributors!
