import streamlit as st
from extract_transcript import YouTubeTranscriptExtractor
from summarize_json import TranscriptSummarizer
from groq_qna import ask_question
import tempfile
import os
import json

st.title("YouTube Transcript Toolkit")

# --- SESSION STATE ---
if 'transcript_data' not in st.session_state:
    st.session_state['transcript_data'] = None
if 'summary' not in st.session_state:
    st.session_state['summary'] = ""
if 'key_points' not in st.session_state:
    st.session_state['key_points'] = []
if 'qna_history' not in st.session_state:
    st.session_state['qna_history'] = []
if 'available_languages' not in st.session_state:
    st.session_state['available_languages'] = []

# --- EXTRACT TRANSCRIPT ---
st.header("1. Extract Transcript from YouTube")
youtube_url = st.text_input("YouTube URL", key="youtube_url")

# Create extractor instance
extractor = YouTubeTranscriptExtractor()

# When URL is entered, fetch available languages
if youtube_url:
    video_id = extractor.extract_video_id(youtube_url)
    if video_id:
        languages = extractor.get_available_languages(video_id)
        st.session_state['available_languages'] = languages
        
        if languages:
            # Create language selection dropdown
            lang_options = [f"{lang['name']} ({lang['type']})" for lang in languages]
            lang_options.insert(0, "Auto (Try English first)")
            selected_lang = st.selectbox(
                "Select transcript language",
                options=lang_options,
                index=0
            )
            
            # Get the language code if a specific language was selected
            selected_lang_code = None
            if selected_lang != "Auto (Try English first)":
                selected_idx = lang_options.index(selected_lang) - 1  # -1 for the "Auto" option
                selected_lang_code = languages[selected_idx]['code']
        else:
            st.warning("No transcripts available for this video")

if st.button("Extract Transcript"):
    if youtube_url:
        # Get selected language code from above
        lang_code = selected_lang_code if 'selected_lang_code' in locals() else None
        
        success, message, data = extractor.extract_and_save(youtube_url, lang_code)
        st.write(message)
        if success:
            st.session_state.transcript_data = data
            st.text_area("Transcript", data["transcript_plain"], height=200)
        else:
            st.session_state.transcript_data = None
    else:
        st.error("Please enter a YouTube URL")

# --- DISPLAY TRANSCRIPT IF ALREADY EXTRACTED ---
if st.session_state.transcript_data:
    st.header("2. Summarize Transcript")
    provider = st.selectbox(
        "Choose AI provider for summary (fallbacks automatically if fails)",
        ["groq", "gemini", "openai", "huggingface", "local"],
        index=0,
        key="summary_provider"
    )

    if st.button("Summarize Transcript"):
        # Save transcript data as temp JSON file for summarizer
        with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.json', encoding='utf-8') as f:
            json.dump(st.session_state.transcript_data, f, ensure_ascii=False)
            temp_json_path = f.name

        summarizer = TranscriptSummarizer()
        result = summarizer.process_transcript(temp_json_path, preferred_providers=[provider])
        os.unlink(temp_json_path)

        if result:
            st.session_state.summary = result.summary
            st.session_state.key_points = result.key_points
            st.success(f"Summary generated using {result.ai_provider} in {result.processing_time:.2f} seconds.")
        else:
            st.session_state.summary = ""
            st.session_state.key_points = []
            st.error("Failed to generate summary.")

    if st.session_state.summary:
        st.subheader("Summary")
        st.write(st.session_state.summary)
        st.subheader("Key Points")
        for idx, point in enumerate(st.session_state.key_points, 1):
            st.markdown(f"{idx}. {point}")

    # --- QNA CHATBOT ---
    st.header("3. Ask Questions about the Transcript")
    st.write("Ask any question about the transcript. The answer will be generated using Groq (Llama 3).")
    qna_input = st.text_input("Your Question", key="qna_input")
    if st.button("Ask Question"):
        transcript = st.session_state.transcript_data.get("transcript_plain", "")
        answer = ask_question(transcript, qna_input)
        st.session_state.qna_history.append({"question": qna_input, "answer": answer})

    if st.session_state.qna_history:
        st.subheader("Q&A History")
        for qa in reversed(st.session_state.qna_history):
            st.markdown(f"**Q:** {qa['question']}")
            st.markdown(f"**A:** {qa['answer']}")
            st.markdown("---")
