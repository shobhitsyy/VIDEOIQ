from extract_transcript import YouTubeTranscriptExtractor
from summarize_json import TranscriptSummarizer
import tempfile
import json
import os

youtube_url = input("Enter YouTube URL: ")

# Extract transcript
extractor = YouTubeTranscriptExtractor(storage_dir=tempfile.gettempdir())
success, message, data = extractor.extract_and_save(youtube_url)
print(message)

if success:
    # Save transcript to a temp file for summarizer
    with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.json', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
        temp_json_path = f.name

    summarizer = TranscriptSummarizer()
    result = summarizer.process_transcript(temp_json_path, preferred_providers=["gemini", "groq"])
    os.unlink(temp_json_path)

    if result:
        print("Summary:", result.summary)
        print("Key Points:", result.key_points)
    else:
        print("Failed to generate summary.")
else:
    print("Transcript extraction failed.")
