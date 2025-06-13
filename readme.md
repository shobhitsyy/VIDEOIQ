# VIDEOIQ

A Python-based toolkit for extracting, summarizing, and querying YouTube video transcripts.  
Includes both a backend API and a user-friendly Streamlit interface.

<p align="center">
  <a href="https://www.youtube.com/watch?v=b2CpCJYBX1I">
    <img src="https://img.youtube.com/vi/b2CpCJYBX1I/0.jpg" alt="Project Demo">
  </a>
</p>

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
- Streamlit - Interactive UI for the toolkit
- FastAPI *(optional, for backend API endpoints)*
- Custom modules for extraction, summarization, and Q&A

---

## Setup & Installation

1. **Clone the repository**
    ```bash
    git clone https://github.com/shobhitsy/VIDEOIQ.git
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
   Create a `.env` file in the project root directory with your API keys:
    ```
    GROQ_API_KEY=your_groq_api_key
    GEMINI_API_KEY=your_gemini_api_key
    ```
   You can copy the provided `.env.example` file and fill in your API keys.

---

## Usage

### Local Development

1. **Run the Streamlit App (Recommended)**
   ```bash
   streamlit run streamlit_app.py
   ```
   Visit [http://localhost:8501](http://localhost:8501) in your browser.

2. **Using ngrok for Remote Access (Optional)**
   If you want to make your local instance accessible remotely:
   
   a. Install ngrok:
   ```bash
   # On Windows (using chocolatey):
   choco install ngrok
   
   # On macOS (using homebrew):
   brew install ngrok
   ```
   
   b. Run Streamlit:
   ```bash
   streamlit run streamlit_app.py
   ```
   
   c. In a new terminal, create an ngrok tunnel:
   ```bash
   ngrok http 8501
   ```
   
   This will provide you with a public URL that can temporarily access your local instance.
   
   Note: The ngrok URL changes each time you restart ngrok, and requires your local machine to be running the application.

### API Backend (Optional)

If you want to use the backend as an API:
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

## Demo

Check out the [project demo video](https://www.youtube.com/watch?v=b2CpCJYBX1I) to see VIDEOIQ in action!

Note: The demo uses ngrok for temporary remote access. When you run the project locally, you'll access it through localhost or your own ngrok tunnel.

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
- Groq
- Google Gemini
- And all open-source contributors!
