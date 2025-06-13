from dotenv import load_dotenv
import os

load_dotenv()  # Will load environment variables from a .env file
import streamlit as st
from pathlib import Path
import json

from extract_transcript import YouTubeTranscriptExtractor
from summarize_json import TranscriptSummarizer
from qna import ask_question_with_fallback, ask_gemini, ask_groq

st.set_page_config(page_title="VideoIQ: AI Summarization & Q&A for YouTube Content", layout="wide")

# --- Custom CSS for headings, sections, and a beautiful reviews box, with dark background ---
st.markdown("""
    <style>
        body, .stApp {
            background-color: #101217 !important;
        }
        .big-title {
            font-size: 2rem !important;
            font-weight: 700;
            margin-bottom: 0.8em;
        }
        .section-header {
            font-size: 1.25rem !important;
            font-weight: 600;
            margin-bottom: 0.2em;
        }
        .question-box {
            background-color: #f4f6fa;
            padding: 1.1em 1.3em;
            border-radius: 8px;
            margin-bottom: 1em;
            border: 1px solid #e3e7ed;
        }
        .answer-box {
            background-color: #e9f8f0;
            padding: 1.1em 1.3em;
            border-radius: 8px;
            margin-bottom: 1em;
            border: 1px solid #b7eed1;
        }
        .history-label {
            color: #576574;
            font-size: 0.95rem;
            margin-bottom: 0.3em;
        }
        .stRadio > div {
            flex-direction: row;
        }
        .stTextInput>div>div>input {
            font-size: 1.01rem;
        }
        .star-rating {
            color: #f5c518;
            font-size: 1.15em;
            letter-spacing: 0.02em;
            vertical-align: middle;
        }
        .review-list {
            margin-top: 1.5em;
        }
        .review-card {
            background: #181b20;
            color: #fff;
            padding: 1.2em 1.4em;
            border-radius: 16px;
            margin-bottom: 1.3em;
            border: 1px solid #23242a;
            box-shadow: 0 2px 8px 0 rgba(60,60,80,0.06);
        }
        .review-header {
            display: flex;
            align-items: center;
            margin-bottom: 0.3em;
        }
        .review-name {
            font-weight: 900;
            margin-right: 0.7em;
            font-size: 1.13em;
            color: #ffe066;
            letter-spacing: 0.03em;
        }
        .review-rating {
            font-size: 1.10em;
            margin-right: 0.5em;
        }
        .review-content {
            margin-top: 0.2em;
            font-size: 1.05em;
            color: #dde1f2;
        }
        .review-divider {
            margin: 1.5em 0 0.6em 0;
            border-bottom: 1.5px solid #26282f;
        }
        .review-label {
            font-size: 1.35em;
            font-weight: 700;
            color: #fff;
            margin-bottom: 0.4em;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="big-title">🎬 VideoIQ: AI Summarization & Q&A for YouTube Content</div>', unsafe_allow_html=True)
st.write(
    "Extract transcripts from YouTube, summarize with AI, and ask questions using Gemini or Groq (Llama 3), or use fallback mode (Gemini → Groq)."
)

def get_plain_text_from_json_data(json_data):
    return json_data.get("transcript_plain", "")

# --- Review Storage ---
if 'reviews' not in st.session_state:
    st.session_state['reviews'] = []

def render_review_section(form_key):
    st.markdown(
        '<div style="margin-top:1.7em;"></div>'
        '<span style="font-size:1.55em;font-weight:700;color:#ffe066;">⭐</span> '
        '<span style="font-size:1.35em;font-weight:700;color:#fff;">Rate & Review this Extraction</span>',
        unsafe_allow_html=True
    )
    with st.form(form_key, clear_on_submit=True):
        name = st.text_input("Your Name", key=f"{form_key}_name")
        rating = st.slider("Your Rating (1-5 Stars)", min_value=1, max_value=5, value=5, format="%d", key=f"{form_key}_rating")
        review = st.text_area("Write a review (optional)", key=f"{form_key}_review")
        submitted = st.form_submit_button("Submit Review")
        if submitted:
            if not name.strip():
                st.warning("Please enter your name before submitting a review.")
            else:
                st.session_state.reviews.append({
                    "name": name.strip(),
                    "rating": rating,
                    "review": review.strip()
                })
                st.success("Thank you for your feedback!")

    if st.session_state['reviews']:
        st.markdown('<div class="review-list"><div class="review-label">Recent Reviews</div></div>', unsafe_allow_html=True)
        for r in reversed(st.session_state['reviews']):
            name_initial = r["name"][0].upper() if r["name"] else ""
            stars = "★" * r['rating'] + "☆" * (5 - r['rating'])
            review_html = f'''
            <div class="review-card">
                <div class="review-header">
                    <span class="review-name">{name_initial}</span>
                    <span class="star-rating review-rating">{stars}</span>
                </div>
                <div class="review-content">{r["review"] if r["review"] else '<span style="color:#888;">(No review)</span>'}</div>
            </div>
            '''
            st.markdown(review_html, unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["1️⃣ Extract Transcript", "2️⃣ Summarize", "3️⃣ Q&A"])

# Step 1: Extract Transcript
with tab1:
    st.markdown('<div class="section-header">Step 1: Extract YouTube Transcript</div>', unsafe_allow_html=True)
    yt_url = st.text_input("Enter YouTube video URL:")
    if 'transcript_extracted' not in st.session_state:
        st.session_state['transcript_extracted'] = False
    extract_btn = st.button("Extract and Save Transcript")
    extractor = YouTubeTranscriptExtractor()
    if extract_btn and yt_url:
        with st.spinner("Extracting transcript..."):
            success, message, data = extractor.extract_and_save(yt_url)
            if success:
                st.success("Transcript extracted and saved!")
                st.session_state['transcript_extracted'] = True
                st.write(message)
                video_id = data["video_id"]
                json_filename = f"{video_id}_streamlit.json"
                os.makedirs("transcripts", exist_ok=True)
                json_path = os.path.join("transcripts", json_filename)
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                st.session_state['last_transcript_json_path'] = json_path
                st.session_state['last_transcript_data'] = data
                st.session_state['transcript_data'] = data  # for QnA compatibility
                st.download_button("Download Transcript JSON", data=json.dumps(data, ensure_ascii=False, indent=2), file_name=json_filename)
                st.text_area("Transcript Preview", data.get("transcript_plain", "")[:1000] + "...")
            else:
                st.session_state['transcript_extracted'] = False
                st.error(message)
    render_review_section("review_form_tab1")

# Step 2: Summarize Transcript
with tab2:
    st.markdown('<div class="section-header">Step 2: Summarize Transcript</div>', unsafe_allow_html=True)
    st.write("Upload a transcript JSON file (from Step 1) to summarize, or use the last extracted transcript.")

    transcript_available = False
    json_path = None
    data = None

    if 'last_transcript_json_path' in st.session_state and Path(st.session_state['last_transcript_json_path']).exists():
        transcript_available = True
        json_path = st.session_state['last_transcript_json_path']
        data = st.session_state.get('last_transcript_data')
        st.success(f"Using last extracted transcript: {os.path.basename(json_path)}")
    else:
        uploaded_json = st.file_uploader("Choose transcript JSON file", type="json")
        if uploaded_json:
            json_path = f"temp_uploaded_{uploaded_json.name}"
            with open(json_path, "wb") as f:
                f.write(uploaded_json.getbuffer())
            transcript_available = True

    if transcript_available and json_path:
        summarizer = TranscriptSummarizer()
        with st.spinner("Summarizing transcript..."):
            result = summarizer.process_transcript(json_path)
            if result:
                st.success("Summary generated!")
                st.write(f"**Title:** {result.title}")
                st.write(f"**AI Provider:** {result.ai_provider}")
                st.write("### Summary")
                st.write(result.summary)
                st.write("### Key Points")
                for i, kp in enumerate(result.key_points, 1):
                    st.write(f"{i}. {kp}")
            else:
                st.error("Failed to summarize transcript.")

    render_review_section("review_form_tab2")

# Step 3: Q&A on Transcript
with tab3:
    st.markdown('<div class="section-header">Step 3: Q&A on Transcript</div>', unsafe_allow_html=True)
    st.write("Ask questions about the last extracted/summarized transcript or upload a transcript file (txt or JSON).")

    if 'qna_history' not in st.session_state:
        st.session_state.qna_history = []

    transcript_text = ""
    json_data = None

    if 'last_transcript_data' in st.session_state:
        json_data = st.session_state['last_transcript_data']
        transcript_text = get_plain_text_from_json_data(json_data)
        st.session_state.transcript_data = json_data
        st.success("Using last extracted transcript for Q&A.")
    elif 'transcript_data' in st.session_state and st.session_state.transcript_data.get("transcript_plain"):
        json_data = st.session_state.transcript_data
        transcript_text = get_plain_text_from_json_data(json_data)
        st.success("Using loaded transcript for Q&A.")
    else:
        qna_file = st.file_uploader("Upload transcript file (txt or JSON)", type=["txt", "json"], key="qna_file")
        if qna_file:
            file_type = qna_file.name.split('.')[-1]
            if file_type == "txt":
                transcript_text = qna_file.read().decode("utf-8")
                st.session_state.transcript_data = {"transcript_plain": transcript_text}
            elif file_type == "json":
                json_data = json.load(qna_file)
                transcript_text = get_plain_text_from_json_data(json_data)
                st.session_state.transcript_data = json_data

    if transcript_text:
        with st.expander("Click to watch transcript preview"):
            st.text_area("Transcript Preview", transcript_text[:1000]+"...", height=200, key="preview_area")

        st.header("3. Ask Questions about the Transcript")
        st.write("Ask any question about the transcript. Choose your preferred AI model or let the app try Gemini first, then Groq if needed.")

        qna_input = st.text_input("Your Question", key="qna_input")        

        api_choice = st.radio(
            "Choose AI Model",
            ("Default (Gemini → Groq fallback)", "Gemini only", "Groq only"),
            horizontal=True
        )

        if st.button("Ask Question"):
            transcript = st.session_state.transcript_data.get("transcript_plain", "")
            answer = None
            if transcript and qna_input.strip():
                with st.spinner("Generating answer..."):
                    if api_choice.startswith("Default"):
                        answer = ask_question_with_fallback(transcript, qna_input)
                    elif api_choice == "Gemini only":
                        answer = ask_gemini(transcript, qna_input)
                    elif api_choice == "Groq only":
                        answer = ask_groq(transcript, qna_input)
                st.session_state.qna_history.append({"question": qna_input, "answer": answer})
            elif not transcript:
                st.error("No transcript loaded. Please extract or upload a transcript first.")
            elif not qna_input.strip():
                st.error("Please enter a question.")

        if st.session_state.qna_history:
            st.subheader("Q&A History")
            for qa in reversed(st.session_state.qna_history):
                st.markdown(f"**Q:** {qa['question']}")
                st.write(f"**A:** {qa['answer']}")
                st.markdown("---")

    render_review_section("review_form_tab3")

st.sidebar.title("About")
st.sidebar.info(
    "VideoIQ is a simple frontend for extracting, summarizing, and querying YouTube video transcripts using Gemini and Groq LLM APIs. "
    "Built with Streamlit. Make sure your API keys are set as environment variables."
)
