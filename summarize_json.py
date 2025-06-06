from dotenv import load_dotenv
load_dotenv()
from dataclasses import dataclass
import os
import json
import re
import time
from datetime import datetime
from typing import List, Optional, Tuple, Dict
# Install required packages:
# pip install requests openai google-generativeai anthropic groq transformers torch

@dataclass
class SummaryResult:
    """Data class to store summary results"""
    title: str
    duration: str
    word_count: int
    summary: str
    key_points: List[str]
    ai_provider: str
    processing_time: float
    confidence_score: float = 0.0

class TranscriptSummarizer:
    """
    Multi-API transcript summarizer using various free AI services
    """

    def __init__(self, storage_dir: str = "summaries"):
        self.storage_dir = storage_dir
        self.ensure_storage_dir()

        # API configurations - Add your API keys here
        self.api_configs = {
            'openai': {
                'api_key': os.getenv('OPENAI_API_KEY', ''),
                'model': 'gpt-3.5-turbo',  # Free tier available
                'max_tokens': 4000
            },
            'gemini': {
                'api_key': os.getenv('GEMINI_API_KEY', ''),
                'model': 'gemini-1.5-flash',  # Free tier
                'max_tokens': 8000
            },
            'groq': {
                'api_key': os.getenv('GROQ_API_KEY', ''),
                'model': 'llama3-8b-8192',  # Free tier
                'max_tokens': 8000
            },
            'huggingface': {
                'api_key': os.getenv('HUGGINGFACE_API_KEY', ''),
                'model': 'microsoft/DialoGPT-large',
                'max_tokens': 2000
            }
        }

    def ensure_storage_dir(self):
        """Create storage directory if it doesn't exist"""
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)

    def load_transcript_from_json(self, json_file_path: str) -> Tuple[str, Dict]:
        """
        Load transcript from JSON file created by the extractor

        Args:
            json_file_path: Path to JSON transcript file

        Returns:
            Tuple of (transcript_text, metadata)
        """
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            transcript_text = data.get('transcript_plain', '')
            metadata = {
                'title': data.get('metadata', {}).get('title', 'Unknown Title'),
                'duration_minutes': data.get('duration_minutes', 0),
                'word_count': data.get('word_count', 0),
                'video_id': data.get('video_id', ''),
                'url': data.get('url', ''),
                'segment_count': data.get('segment_count', 0)
            }

            return transcript_text, metadata

        except Exception as e:
            print(f"Error loading transcript: {str(e)}")
            return "", {}

    def chunk_text(self, text: str, max_chunk_size: int = 3000) -> List[str]:
        """
        Split text into chunks for processing by AI APIs

        Args:
            text: Input text to chunk
            max_chunk_size: Maximum characters per chunk

        Returns:
            List of text chunks
        """
        if len(text) <= max_chunk_size:
            return [text]

        # Split by sentences first
        sentences = re.split(r'[.!?]+', text)
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # If adding this sentence would exceed limit, start new chunk
            if len(current_chunk) + len(sentence) + 2 > max_chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk += ". " + sentence if current_chunk else sentence

        # Add the last chunk
        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def summarize_with_openai(self, text: str, metadata: Dict) -> Optional[SummaryResult]:
        """Summarize using OpenAI GPT-3.5"""
        try:
            import openai

            api_key = self.api_configs['openai']['api_key']
            if not api_key:
                print("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
                return None

            client = openai.OpenAI(api_key=api_key)

            prompt = f"""
            Please analyze this YouTube video transcript and provide:

            1. A comprehensive summary (3-4 paragraphs) that captures the main content and flow
            2. Key takeaways as bullet points (5-8 main points)

            Video Title: {metadata.get('title', 'Unknown')}
            Duration: {metadata.get('duration_minutes', 0)} minutes

            Transcript:
            {text[:6000]}  # Limit for free tier

            Format your response as:
            SUMMARY:
            [Your summary here]

            KEY POINTS:
            • [Point 1]
            • [Point 2]
            etc.
            """

            start_time = time.time()

            response = client.chat.completions.create(
                model=self.api_configs['openai']['model'],
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500,
                temperature=0.7
            )

            processing_time = time.time() - start_time
            content = response.choices[0].message.content

            # Parse response
            summary, key_points = self._parse_ai_response(content)

            return SummaryResult(
                title=metadata.get('title', 'Unknown'),
                duration=f"{metadata.get('duration_minutes', 0)} minutes",
                word_count=metadata.get('word_count', 0),
                summary=summary,
                key_points=key_points,
                ai_provider="OpenAI GPT-3.5",
                processing_time=processing_time
            )

        except Exception as e:
            print(f"OpenAI summarization failed: {str(e)}")
            return None

    def summarize_with_gemini(self, text: str, metadata: Dict) -> Optional[SummaryResult]:
        """Summarize using Google Gemini"""
        try:
            import google.generativeai as genai

            api_key = self.api_configs['gemini']['api_key']
            if not api_key:
                print("Gemini API key not found. Set GEMINI_API_KEY environment variable.")
                return None

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')

            prompt = f"""
            Analyze this YouTube video transcript and provide:

            1. A comprehensive summary (3-4 paragraphs) covering the main content
            2. Key takeaways as bullet points (5-8 important points)

            Video: {metadata.get('title', 'Unknown')} ({metadata.get('duration_minutes', 0)} minutes)

            Transcript:
            {text}

            Format response as:
            SUMMARY:
            [Summary text]

            KEY POINTS:
            • [Point 1]
            • [Point 2]
            """

            start_time = time.time()
            response = model.generate_content(prompt)
            processing_time = time.time() - start_time

            summary, key_points = self._parse_ai_response(response.text)

            return SummaryResult(
                title=metadata.get('title', 'Unknown'),
                duration=f"{metadata.get('duration_minutes', 0)} minutes",
                word_count=metadata.get('word_count', 0),
                summary=summary,
                key_points=key_points,
                ai_provider="Google Gemini",
                processing_time=processing_time
            )

        except Exception as e:
            print(f"Gemini summarization failed: {str(e)}")
            return None

    def summarize_with_groq(self, text: str, metadata: Dict) -> Optional[SummaryResult]:
        """Summarize using Groq (very fast, free tier available)"""
        try:
            from groq import Groq

            api_key = self.api_configs['groq']['api_key']
            if not api_key:
                print("Groq API key not found. Set GROQ_API_KEY environment variable.")
                return None

            client = Groq(api_key=api_key)

            prompt = f"""
            Analyze this YouTube video transcript and create:

            1. A detailed summary (3-4 paragraphs) that captures the essence and main flow
            2. Key insights as bullet points (5-8 most important takeaways)

            Video: "{metadata.get('title', 'Unknown')}" ({metadata.get('duration_minutes', 0)} minutes)

            Transcript:
            {text}

            Response format:
            SUMMARY:
            [Your comprehensive summary]

            KEY POINTS:
            • [Key insight 1]
            • [Key insight 2]
            """

            start_time = time.time()

            completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                max_tokens=2000,
                temperature=0.7
            )

            processing_time = time.time() - start_time
            content = completion.choices[0].message.content

            summary, key_points = self._parse_ai_response(content)

            return SummaryResult(
                title=metadata.get('title', 'Unknown'),
                duration=f"{metadata.get('duration_minutes', 0)} minutes",
                word_count=metadata.get('word_count', 0),
                summary=summary,
                key_points=key_points,
                ai_provider="Groq Llama3",
                processing_time=processing_time
            )

        except Exception as e:
            print(f"Groq summarization failed: {str(e)}")
            return None

    def summarize_with_huggingface(self, text: str, metadata: Dict) -> Optional[SummaryResult]:
        """Summarize using Hugging Face Transformers (free, runs locally)"""
        try:
            from transformers import pipeline

            # Use summarization pipeline
            summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

            # Chunk text for processing
            chunks = self.chunk_text(text, 1000)  # BART has token limits
            chunk_summaries = []

            start_time = time.time()

            for chunk in chunks[:3]:  # Limit to first 3 chunks for speed
                try:
                    summary = summarizer(chunk, max_length=150, min_length=50, do_sample=False)
                    chunk_summaries.append(summary[0]['summary_text'])
                except Exception as e:
                    print(f"Error processing chunk: {str(e)}")
                    continue

            processing_time = time.time() - start_time

            # Combine chunk summaries
            combined_summary = " ".join(chunk_summaries)

            # Generate key points (simple extraction based on sentences)
            sentences = re.split(r'[.!?]+', combined_summary)
            key_points = [s.strip() for s in sentences if len(s.strip()) > 20][:6]

            return SummaryResult(
                title=metadata.get('title', 'Unknown'),
                duration=f"{metadata.get('duration_minutes', 0)} minutes",
                word_count=metadata.get('word_count', 0),
                summary=combined_summary,
                key_points=key_points,
                ai_provider="Hugging Face BART",
                processing_time=processing_time
            )

        except Exception as e:
            print(f"Hugging Face summarization failed: {str(e)}")
            return None

    def summarize_with_local_extractive(self, text: str, metadata: Dict) -> Optional[SummaryResult]:
        """
        Fallback: Simple extractive summarization (no API required)
        Uses sentence ranking based on word frequency
        """
        try:
            import re
            from collections import Counter

            start_time = time.time()

            # Clean and split into sentences
            sentences = re.split(r'[.!?]+', text)
            sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

            if len(sentences) < 5:
                return None

            # Calculate word frequencies
            words = re.findall(r'\w+', text.lower())
            word_freq = Counter(words)

            # Score sentences based on word frequencies
            sentence_scores = {}
            for i, sentence in enumerate(sentences):
                words_in_sentence = re.findall(r'\w+', sentence.lower())
                score = sum(word_freq[word] for word in words_in_sentence)
                sentence_scores[i] = score / len(words_in_sentence) if words_in_sentence else 0

            # Get top sentences for summary
            top_sentences = sorted(sentence_scores.items(), key=lambda x: x[1], reverse=True)
            summary_sentences = [sentences[i] for i, _ in top_sentences[:5]]
            summary = ". ".join(summary_sentences) + "."

            # Extract key points (top sentences)
            key_points = [sentences[i].strip() for i, _ in top_sentences[5:11]]

            processing_time = time.time() - start_time

            return SummaryResult(
                title=metadata.get('title', 'Unknown'),
                duration=f"{metadata.get('duration_minutes', 0)} minutes",
                word_count=metadata.get('word_count', 0),
                summary=summary,
                key_points=key_points,
                ai_provider="Local Extractive",
                processing_time=processing_time
            )

        except Exception as e:
            print(f"Local summarization failed: {str(e)}")
            return None

    def _parse_ai_response(self, response_text: str) -> Tuple[str, List[str]]:
        """Parse AI response to extract summary and key points"""
        try:
            # Split by sections
            sections = response_text.split('\n')

            summary = ""
            key_points = []
            current_section = None

            for line in sections:
                line = line.strip()
                if not line:
                    continue

                # Check for section headers
                if 'SUMMARY' in line.upper() or 'OVERVIEW' in line.upper():
                    current_section = 'summary'
                    continue
                elif 'KEY POINTS' in line.upper() or 'TAKEAWAYS' in line.upper():
                    current_section = 'points'
                    continue

                # Add content to appropriate section
                if current_section == 'summary':
                    summary += line + " "
                elif current_section == 'points':
                    # Clean bullet points
                    clean_point = re.sub(r'^[•\-\*\d+\.]\s*', '', line)
                    if clean_point:
                        key_points.append(clean_point)

            # Fallback parsing if sections not found
            if not summary and not key_points:
                lines = response_text.split('\n')
                summary_lines = []
                point_lines = []
                is_points_section = False

                for line in lines:
                    line = line.strip()
                    if line.startswith('•') or line.startswith('-') or line.startswith('*'):
                        is_points_section = True
                        clean_point = re.sub(r'^[•\-\*]\s*', '', line)
                        if clean_point:
                            point_lines.append(clean_point)
                    elif not is_points_section and line:
                        summary_lines.append(line)

                summary = " ".join(summary_lines)
                key_points = point_lines

            return summary.strip(), key_points

        except Exception as e:
            print(f"Error parsing AI response: {str(e)}")
            return response_text[:500] + "...", []

    def process_transcript(self, json_file_path: str, preferred_providers: List[str] = None) -> Optional[SummaryResult]:
        """
        Main method to process transcript with multiple AI providers

        Args:
            json_file_path: Path to transcript JSON file
            preferred_providers: List of preferred AI providers to try

        Returns:
            SummaryResult object or None if all methods fail
        """
        # Load transcript
        transcript_text, metadata = self.load_transcript_from_json(json_file_path)

        if not transcript_text:
            print("No transcript text found in JSON file")
            return None

        print(f"Processing: {metadata.get('title', 'Unknown')}")
        print(f"Duration: {metadata.get('duration_minutes', 0)} minutes")
        print(f"Word count: {metadata.get('word_count', 0)} words")

        # Default provider order
        if not preferred_providers:
            preferred_providers = ['groq', 'gemini', 'openai', 'huggingface', 'local']

        # Provider methods mapping
        provider_methods = {
            'openai': self.summarize_with_openai,
            'gemini': self.summarize_with_gemini,
            'groq': self.summarize_with_groq,
            'huggingface': self.summarize_with_huggingface,
            'local': self.summarize_with_local_extractive
        }

        # Try each provider
        for provider in preferred_providers:
            if provider not in provider_methods:
                continue

            print(f"\nTrying {provider.upper()}...")

            try:
                result = provider_methods[provider](transcript_text, metadata)
                if result and result.summary:
                    print(f"✓ Success with {provider.upper()}")
                    print(f"  Processing time: {result.processing_time:.2f} seconds")
                    return result
                else:
                    print(f"✗ {provider.upper()} returned no results")
            except Exception as e:
                print(f"✗ {provider.upper()} failed: {str(e)}")
                continue

        print("All AI providers failed")
        return None

    def save_summary(self, result: SummaryResult, video_id: str = None) -> str:
        """Save summary result to file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"summary_{video_id}_{timestamp}.json" if video_id else f"summary_{timestamp}.json"
        filepath = os.path.join(self.storage_dir, filename)

        # Convert to dictionary
        summary_data = {
            'title': result.title,
            'duration': result.duration,
            'word_count': result.word_count,
            'summary': result.summary,
            'key_points': result.key_points,
            'ai_provider': result.ai_provider,
            'processing_time': result.processing_time,
            'generated_at': datetime.now().isoformat(),
            'ready_for_qa': True
        }

        # Save JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)

        # Also save as readable text
        text_filepath = filepath.replace('.json', '.txt')
        with open(text_filepath, 'w', encoding='utf-8') as f:
            f.write(f"Title: {result.title}\n")
            f.write(f"Duration: {result.duration}\n")
            f.write(f"AI Provider: {result.ai_provider}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 50 + "\n\n")

            f.write("SUMMARY:\n")
            f.write("-" * 20 + "\n")
            f.write(result.summary + "\n\n")

            f.write("KEY POINTS:\n")
            f.write("-" * 20 + "\n")
            for i, point in enumerate(result.key_points, 1):
                f.write(f"{i}. {point}\n")

        print(f"Summary saved to: {filepath}")
        print(f"Text version saved to: {text_filepath}")

        return filepath

def setup_api_keys():
    """
    Helper function to set up API keys
    """
    print("API Key Setup Instructions:")
    print("=" * 40)
    print("1. GROQ (Recommended - Fast & Free):")
    print("   - Visit: https://console.groq.com/")
    print("   - Sign up and get free API key")
    print("   - Set: export GROQ_API_KEY='your_key_here'")
    print()
    print("2. Google Gemini (Free tier):")
    print("   - Visit: https://makersuite.google.com/app/apikey")
    print("   - Get free API key")
    print("   - Set: export GEMINI_API_KEY='your_key_here'")
    print()
    print("3. OpenAI (Free trial):")
    print("   - Visit: https://platform.openai.com/api-keys")
    print("   - Get API key (free trial available)")
    print("   - Set: export OPENAI_API_KEY='your_key_here'")
    print()
    print("4. Hugging Face (Free):")
    print("   - Visit: https://huggingface.co/settings/tokens")
    print("   - Create free account and token")
    print("   - Set: export HUGGINGFACE_API_KEY='your_token_here'")
    print()
    print("Note: Local extractive method works without any API keys")

def main():
    """
    Interactive main function
    """
    print("YouTube Transcript Summarizer")
    print("=" * 40)

    summarizer = TranscriptSummarizer()

    while True:
        print("\nOptions:")
        print("1. Summarize transcript from JSON file")
        print("2. Batch process multiple JSON files")
        print("3. Setup API keys help")
        print("4. Test with sample")
        print("5. Quit")

        choice = input("\nEnter your choice (1-5): ").strip()

        if choice == '1':
            json_path = input("Enter path to transcript JSON file: ").strip()

            if not json_path or not os.path.exists(json_path):
                print("File not found. Please check the path.")
                continue

            # Ask for preferred providers
            print("\nAvailable AI providers:")
            print("1. groq (Recommended - fast & free)")
            print("2. gemini (Google - free tier)")
            print("3. openai (ChatGPT - free trial)")
            print("4. huggingface (Free, runs locally)")
            print("5. local (No API needed, basic)")

            provider_choice = input("Enter preferred provider numbers (e.g., 1,2,3) or press Enter for default: ").strip()

            if provider_choice:
                provider_map = {'1': 'groq', '2': 'gemini', '3': 'openai', '4': 'huggingface', '5': 'local'}
                providers = [provider_map.get(p.strip(), 'local') for p in provider_choice.split(',')]
            else:
                providers = None

            print("\nProcessing...")
            result = summarizer.process_transcript(json_path, providers)

            if result:
                print("\n" + "=" * 50)
                print(f"TITLE: {result.title}")
                print(f"DURATION: {result.duration}")
                print(f"AI PROVIDER: {result.ai_provider}")
                print(f"PROCESSING TIME: {result.processing_time:.2f}s")
                print("=" * 50)

                print("\nSUMMARY:")
                print("-" * 20)
                print(result.summary)

                print("\nKEY POINTS:")
                print("-" * 20)
                for i, point in enumerate(result.key_points, 1):
                    print(f"{i}. {point}")

                # Save results
                video_id = os.path.basename(json_path).split('_')[0]
                summarizer.save_summary(result, video_id)

            else:
                print("❌ Failed to generate summary")

        elif choice == '2':
            input_dir = input("Enter directory containing JSON transcript files: ").strip()
            if not input_dir:
                input_dir = "transcripts"

            if not os.path.exists(input_dir):
                print(f"Directory not found: {input_dir}")
                continue

            json_files = [f for f in os.listdir(input_dir) if f.endswith('.json')]

            if not json_files:
                print(f"No JSON files found in {input_dir}")
                continue

            print(f"Found {len(json_files)} JSON files to process")

            for json_file in json_files:
                json_path = os.path.join(input_dir, json_file)
                print(f"\nProcessing: {json_file}")

                result = summarizer.process_transcript(json_path)
                if result:
                    video_id = json_file.split('_')[0]
                    summarizer.save_summary(result, video_id)
                    print("✓ Completed")
                else:
                    print("✗ Failed")

        elif choice == '3':
            setup_api_keys()

        elif choice == '4':
            print("Create a sample JSON file first using the transcript extractor, then use option 1")

        elif choice == '5':
            print("Goodbye!")
            break

        else:
            print("Invalid choice. Please enter 1-5.")

if __name__ == "__main__":
    main()