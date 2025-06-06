# YouTube Transcript Toolkit

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
    git clone https://github.com/yourusername/yt-transcript-toolkit.git
    cd yt-transcript-toolkit
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

4. **(Optional) Set up environment variables**  
   Create a `.env` file for any API keys required by your summarizer or QnA modules.

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
yt-transcript-toolkit/
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
