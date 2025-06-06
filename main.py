from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import tempfile
import shutil

from extract_transcript import YouTubeTranscriptExtractor
from summarize_json import TranscriptSummarizer
from groq_qna import ask_question

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ExtractRequest(BaseModel):
    youtube_url: str

class SummarizeRequest(BaseModel):
    transcript_json: str
    providers: Optional[List[str]] = None

class QnARequest(BaseModel):
    transcript: str
    question: str

@app.post("/extract-transcript")
async def extract_transcript(req: ExtractRequest):
    extractor = YouTubeTranscriptExtractor()
    success, message, data = extractor.extract_and_save(req.youtube_url)
    return {"success": success, "message": message, "data": data}

@app.post("/summarize")
async def summarize(req: SummarizeRequest):
    with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.json', encoding='utf-8') as f:
        f.write(req.transcript_json)
        temp_path = f.name

    summarizer = TranscriptSummarizer()
    result = summarizer.process_transcript(temp_path, req.providers)
    os.unlink(temp_path)
    if not result:
        return {"success": False, "message": "Summarization failed", "data": None}
    return {
        "success": True,
        "summary": result.summary,
        "key_points": result.key_points,
        "ai_provider": result.ai_provider,
        "processing_time": result.processing_time
    }

@app.post("/qna")
async def qna(req: QnARequest):
    answer = ask_question(req.transcript, req.question)
    return {"question": req.question, "answer": answer}