import os
import json
import re
import time
import random
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import requests
from urllib.parse import urlparse, parse_qs

# Install required packages:
# pip install youtube-transcript-api requests beautifulsoup4 lxml

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
    from youtube_transcript_api.formatters import TextFormatter, JSONFormatter
except ImportError:
    print("Please install youtube-transcript-api: pip install youtube-transcript-api")
    exit(1)

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Please install beautifulsoup4: pip install beautifulsoup4")
    exit(1)

class YouTubeTranscriptExtractor:
    def __init__(self, storage_dir: str = "transcripts"):
        """
        Initialize the YouTube Transcript Extractor focusing on YouTube Transcript API

        Args:
            storage_dir: Directory to store extracted transcripts
        """
        self.storage_dir = storage_dir
        self.session = requests.Session()
        # Add headers to mimic a real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.ensure_storage_dir()

    def ensure_storage_dir(self):
        """Create storage directory if it doesn't exist"""
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)

    def extract_video_id(self, url: str) -> Optional[str]:
        """
        Extract video ID from various YouTube URL formats

        Args:
            url: YouTube video URL

        Returns:
            Video ID string or None if invalid
        """
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/)([^&\n?#]+)',
            r'youtube\.com\/watch\?.*v=([^&\n?#]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return None

    def get_video_info_from_page(self, video_id: str) -> Dict:
        """
        Extract basic video information from YouTube page

        Args:
            video_id: YouTube video ID

        Returns:
            Dictionary containing video information
        """
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"

            # Add random delay to avoid rate limiting
            time.sleep(random.uniform(1, 3))

            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract title
            title_tag = soup.find('meta', property='og:title')
            title = title_tag['content'] if title_tag else 'Unknown Title'

            # Extract description
            desc_tag = soup.find('meta', property='og:description')
            description = desc_tag['content'] if desc_tag else ''

            # Extract duration from meta tag
            duration = 0
            try:
                duration_tag = soup.find('meta', itemprop='duration')
                if duration_tag:
                    duration_str = duration_tag.get('content', '')
                    # Parse ISO 8601 duration (PT4M33S)
                    if duration_str.startswith('PT'):
                        duration_str = duration_str[2:]  # Remove PT
                        duration = 0
                        if 'H' in duration_str:
                            parts = duration_str.split('H')
                            duration += int(parts[0]) * 3600
                            duration_str = parts[1]
                        if 'M' in duration_str:
                            parts = duration_str.split('M')
                            duration += int(parts[0]) * 60
                            duration_str = parts[1]
                        if 'S' in duration_str:
                            duration += int(duration_str.replace('S', ''))
            except:
                pass

            # Extract upload date and view count from JSON-LD
            upload_date = ''
            view_count = 0
            try:
                scripts = soup.find_all('script', type='application/ld+json')
                for script in scripts:
                    try:
                        data = json.loads(script.string)
                        if isinstance(data, list):
                            data = data[0]
                        if 'uploadDate' in data:
                            upload_date = data['uploadDate']
                        if 'interactionStatistic' in data:
                            for stat in data['interactionStatistic']:
                                if stat.get('interactionType', {}).get('@type') == 'WatchAction':
                                    view_count = int(stat.get('userInteractionCount', 0))
                        break
                    except:
                        continue
            except:
                pass

            return {
                'title': title,
                'description': description,
                'duration': duration,
                'upload_date': upload_date,
                'view_count': view_count
            }

        except Exception as e:
            print(f"Error getting video info: {str(e)}")
            return {'title': 'Unknown Title', 'description': '', 'duration': 0}

    def get_available_transcripts(self, video_id: str) -> Dict:
        """
        Get information about available transcripts for a video

        Args:
            video_id: YouTube video ID

        Returns:
            Dictionary with transcript availability info
        """
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            available_transcripts = {
                'manual': [],
                'generated': [],
                'translatable': []
            }
            
            for transcript in transcript_list:
                transcript_info = {
                    'language': transcript.language,
                    'language_code': transcript.language_code,
                    'is_generated': transcript.is_generated,
                    'is_translatable': transcript.is_translatable
                }
                
                if transcript.is_generated:
                    available_transcripts['generated'].append(transcript_info)
                else:
                    available_transcripts['manual'].append(transcript_info)
                
                if transcript.is_translatable:
                    available_transcripts['translatable'].append(transcript_info)
            
            return available_transcripts
            
        except Exception as e:
            print(f"Error getting transcript list: {str(e)}")
            return {'manual': [], 'generated': [], 'translatable': []}

    def extract_transcript_youtube_api(self, video_id: str, languages: List[str] = None, prefer_manual: bool = True) -> Tuple[Optional[List], str, str]:
        """
        Extract transcript using YouTube Transcript API with comprehensive language support

        Args:
            video_id: YouTube video ID
            languages: List of preferred language codes (e.g., ['en', 'es', 'fr'])
            prefer_manual: Whether to prefer manual transcripts over auto-generated ones

        Returns:
            Tuple of (transcript_data, language_used, transcript_type)
        """
        try:
            print("Getting available transcripts...")
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Get all available transcripts
            manual_transcripts = []
            generated_transcripts = []
            
            for transcript in transcript_list:
                if transcript.is_generated:
                    generated_transcripts.append(transcript)
                else:
                    manual_transcripts.append(transcript)
            
            print(f"Found {len(manual_transcripts)} manual and {len(generated_transcripts)} auto-generated transcripts")
            
            # Define language priority
            if languages is None:
                # Default language priority - comprehensive list
                languages = [
                    'en', 'en-US', 'en-GB', 'en-CA', 'en-AU',  # English variants
                    'es', 'es-ES', 'es-MX', 'es-AR',           # Spanish variants
                    'fr', 'fr-FR', 'fr-CA',                    # French variants
                    'de', 'de-DE', 'de-AT', 'de-CH',          # German variants
                    'it', 'it-IT',                            # Italian
                    'pt', 'pt-BR', 'pt-PT',                   # Portuguese variants
                    'ru', 'ru-RU',                            # Russian
                    'ja', 'ja-JP',                            # Japanese
                    'ko', 'ko-KR',                            # Korean
                    'zh', 'zh-CN', 'zh-TW', 'zh-HK',         # Chinese variants
                    'hi', 'hi-IN',                            # Hindi
                    'ar', 'ar-SA',                            # Arabic
                    'nl', 'nl-NL', 'nl-BE',                   # Dutch
                    'sv', 'sv-SE',                            # Swedish
                    'no', 'nb-NO', 'nn-NO',                   # Norwegian
                    'da', 'da-DK',                            # Danish
                    'fi', 'fi-FI',                            # Finnish
                    'pl', 'pl-PL',                            # Polish
                    'tr', 'tr-TR',                            # Turkish
                    'he', 'he-IL',                            # Hebrew
                    'th', 'th-TH',                            # Thai
                    'vi', 'vi-VN',                            # Vietnamese
                    'id', 'id-ID',                            # Indonesian
                    'ms', 'ms-MY',                            # Malay
                    'tl', 'tl-PH',                            # Filipino
                    'uk', 'uk-UA',                            # Ukrainian
                    'cs', 'cs-CZ',                            # Czech
                    'sk', 'sk-SK',                            # Slovak
                    'hu', 'hu-HU',                            # Hungarian
                    'ro', 'ro-RO',                            # Romanian
                    'bg', 'bg-BG',                            # Bulgarian
                    'hr', 'hr-HR',                            # Croatian
                    'sr', 'sr-RS',                            # Serbian
                    'sl', 'sl-SI',                            # Slovenian
                    'et', 'et-EE',                            # Estonian
                    'lv', 'lv-LV',                            # Latvian
                    'lt', 'lt-LT',                            # Lithuanian
                    'el', 'el-GR',                            # Greek
                    'mt', 'mt-MT',                            # Maltese
                ]
            
            # Try to find transcript in preferred order
            transcript_sources = []
            if prefer_manual:
                transcript_sources = [(manual_transcripts, "Manual"), (generated_transcripts, "Auto-generated")]
            else:
                transcript_sources = [(generated_transcripts, "Auto-generated"), (manual_transcripts, "Manual")]
            
            for transcript_group, transcript_type in transcript_sources:
                for lang_code in languages:
                    for transcript in transcript_group:
                        if transcript.language_code == lang_code:
                            print(f"Found {transcript_type.lower()} transcript in {transcript.language} ({lang_code})")
                            try:
                                transcript_data = transcript.fetch()
                                return transcript_data, transcript.language, transcript_type
                            except Exception as e:
                                print(f"Error fetching transcript in {lang_code}: {str(e)}")
                                continue
            
            # If no exact match found, try any available transcript
            all_transcripts = manual_transcripts + generated_transcripts
            if all_transcripts:
                transcript = all_transcripts[0]  # Take the first available
                transcript_type = "Manual" if not transcript.is_generated else "Auto-generated"
                print(f"Using first available transcript: {transcript_type} in {transcript.language} ({transcript.language_code})")
                try:
                    transcript_data = transcript.fetch()
                    return transcript_data, transcript.language, transcript_type
                except Exception as e:
                    print(f"Error fetching fallback transcript: {str(e)}")
            
            # Try translation if original transcript is translatable
            print("Trying translation options...")
            for transcript in all_transcripts:
                if transcript.is_translatable:
                    for lang_code in languages[:5]:  # Try top 5 preferred languages
                        try:
                            print(f"Trying to translate to {lang_code}...")
                            translated = transcript.translate(lang_code)
                            transcript_data = translated.fetch()
                            return transcript_data, f"{transcript.language} (translated to {lang_code})", f"Translated {transcript_type}"
                        except Exception as e:
                            print(f"Translation to {lang_code} failed: {str(e)}")
                            continue
            
            return None, "", ""

        except TranscriptsDisabled:
            print("Transcripts are disabled for this video")
            return None, "", ""
        except NoTranscriptFound:
            print("No transcripts found for this video")
            return None, "", ""
        except VideoUnavailable:
            print("Video is unavailable")
            return None, "", ""
        except Exception as e:
            print(f"Error with YouTube Transcript API: {str(e)}")
            return None, "", ""

    def format_transcript(self, transcript: List, include_timestamps: bool = True) -> str:
        """
        Format transcript segments into readable text with optional timestamps
        """
        if not transcript:
            return ""

        formatted_text = ""
        for segment in transcript:
            # Handle both dict and FetchedTranscriptSnippet objects
            if hasattr(segment, 'start'):
                start_time = segment.start
                text = segment.text
            else:
                start_time = segment.get('start', 0)
                text = segment.get('text', '')

            if include_timestamps:
                # Convert seconds to MM:SS format
                minutes = int(start_time // 60)
                seconds = int(start_time % 60)
                timestamp = f"[{minutes:02d}:{seconds:02d}]"
                formatted_text += f"{timestamp} {text}\n"
            else:
                formatted_text += f"{text} "

        return formatted_text.strip()

    def get_plain_text(self, transcript: List) -> str:
        """
        Get plain text without timestamps
        """
        if not transcript:
            return ""

        text_parts = []
        for segment in transcript:
            # Handle both dict and FetchedTranscriptSnippet objects
            if hasattr(segment, 'text'):
                text_parts.append(segment.text)
            else:
                text_parts.append(segment.get('text', ''))

        return " ".join(text_parts)

    def save_transcript(self, video_id: str, data: Dict) -> str:
        """
        Save transcript data to JSON file
        """
        filename = f"{video_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(self.storage_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return filepath

    def extract_and_save(self, youtube_url: str, languages: List[str] = None, prefer_manual: bool = True, include_timestamps: bool = True) -> Tuple[bool, str, Dict]:
        """
        Main method to extract and save transcript using YouTube Transcript API

        Args:
            youtube_url: YouTube video URL
            languages: List of preferred language codes
            prefer_manual: Whether to prefer manual transcripts over auto-generated ones
            include_timestamps: Whether to include timestamps in formatted output

        Returns:
            Tuple of (success, message, data)
        """
        # Extract video ID
        video_id = self.extract_video_id(youtube_url)
        if not video_id:
            return False, "Invalid YouTube URL", {}

        print(f"Extracting transcript for video: {video_id}")

        # Get video metadata
        print("Getting video metadata...")
        metadata = self.get_video_info_from_page(video_id)

        # Get available transcripts info
        available_transcripts = self.get_available_transcripts(video_id)

        # Extract transcript using YouTube Transcript API
        print("\nExtracting transcript using YouTube Transcript API...")
        transcript, language_used, transcript_type = self.extract_transcript_youtube_api(
            video_id, languages, prefer_manual
        )

        if not transcript:
            error_msg = "Could not extract transcript. Possible reasons:\n"
            error_msg += "- Video has no captions/subtitles available\n"
            error_msg += "- Video is private or restricted\n"
            error_msg += "- Transcripts are disabled for this video\n"
            error_msg += "- Video is unavailable"
            return False, error_msg, {}

        # Format transcript
        formatted_transcript = self.format_transcript(transcript, include_timestamps)
        plain_text = self.get_plain_text(transcript)

        # Convert transcript to serializable format for storage
        transcript_for_storage = []
        for segment in transcript:
            if hasattr(segment, 'start'):
                # FetchedTranscriptSnippet object
                transcript_for_storage.append({
                    'start': segment.start,
                    'duration': getattr(segment, 'duration', 0),
                    'text': segment.text
                })
            else:
                # Already a dict
                transcript_for_storage.append(segment)

        # Prepare data for storage
        data = {
            'video_id': video_id,
            'url': youtube_url,
            'metadata': metadata,
            'transcript_info': {
                'language': language_used,
                'type': transcript_type,
                'available_transcripts': available_transcripts
            },
            'transcript_raw': transcript_for_storage,
            'transcript_formatted': formatted_transcript,
            'transcript_plain': plain_text,
            'extracted_at': datetime.now().isoformat(),
            'word_count': len(plain_text.split()),
            'duration_minutes': round(metadata.get('duration', 0) / 60, 2),
            'segment_count': len(transcript_for_storage)
        }

        # Save to file
        filepath = self.save_transcript(video_id, data)

        success_msg = f"Transcript extracted successfully!\n"
        success_msg += f"Title: {metadata.get('title', 'Unknown')}\n"
        success_msg += f"Duration: {data['duration_minutes']} minutes\n"
        success_msg += f"Language: {language_used}\n"
        success_msg += f"Type: {transcript_type}\n"
        success_msg += f"Segments: {data['segment_count']}\n"
        success_msg += f"Word Count: {data['word_count']}\n"
        success_msg += f"Saved to: {filepath}"

        return True, success_msg, data

def test_with_sample_videos():
    """
    Test the extractor with some sample videos
    """
    extractor = YouTubeTranscriptExtractor()

    # Sample videos that typically have captions
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Never Gonna Give You Up
        "https://youtu.be/jNQXAC9IVRw",  # Me at the zoo (first YouTube video)
        "https://www.youtube.com/watch?v=9bZkp7q19f0",  # PSY - Gangnam Style
    ]

    print("Testing YouTube Transcript Extractor with sample videos...")
    print("=" * 60)

    for i, url in enumerate(test_urls, 1):
        print(f"\nTest {i}: {url}")
        print("-" * 40)

        success, message, data = extractor.extract_and_save(url)
        print(message)

        if success:
            # Show first 200 characters of transcript
            preview = data['transcript_plain'][:200] + "..." if len(data['transcript_plain']) > 200 else data['transcript_plain']
            print(f"\nPreview: {preview}")

        print("\n" + "=" * 60)

def main():
    """
    Interactive usage of the YouTube Transcript Extractor
    """
    print("YouTube Transcript Extractor (API-focused)")
    print("=" * 50)
    print("This tool uses YouTube Transcript API to extract transcripts")
    print("in multiple languages with high accuracy.")
    print("=" * 50)

    extractor = YouTubeTranscriptExtractor()

    while True:
        print("\nOptions:")
        print("1. Extract transcript from URL")
        print("2. Extract with language preference")
        print("3. Test with sample videos")
        print("4. Quit")

        choice = input("\nEnter your choice (1-4): ").strip()

        if choice == '1':
            youtube_url = input("\nEnter YouTube URL: ").strip()

            if not youtube_url:
                print("Please enter a valid URL")
                continue

            print("\nProcessing...")
            success, message, data = extractor.extract_and_save(youtube_url)

            print(f"\n{message}")

            if success:
                # Show preview
                preview = data['transcript_plain'][:300] + "..." if len(data['transcript_plain']) > 300 else data['transcript_plain']
                print(f"\nTranscript Preview:\n{'-' * 20}\n{preview}\n{'-' * 20}")

        elif choice == '2':
            youtube_url = input("\nEnter YouTube URL: ").strip()
            if not youtube_url:
                print("Please enter a valid URL")
                continue

            languages_input = input("\nEnter preferred languages (comma-separated, e.g., 'en,es,fr') or press Enter for auto: ").strip()
            languages = [lang.strip() for lang in languages_input.split(',')] if languages_input else None

            prefer_manual = input("\nPrefer manual transcripts over auto-generated? (y/n, default=y): ").strip().lower()
            prefer_manual = prefer_manual != 'n' if prefer_manual else True

            include_timestamps = input("\nInclude timestamps in formatted output? (y/n, default=y): ").strip().lower()
            include_timestamps = include_timestamps != 'n' if include_timestamps else True

            print("\nProcessing...")
            success, message, data = extractor.extract_and_save(
                youtube_url, languages, prefer_manual, include_timestamps
            )

            print(f"\n{message}")

            if success:
                # Show preview
                preview = data['transcript_plain'][:300] + "..." if len(data['transcript_plain']) > 300 else data['transcript_plain']
                print(f"\nTranscript Preview:\n{'-' * 20}\n{preview}\n{'-' * 20}")

        elif choice == '3':
            test_with_sample_videos()

        elif choice == '4':
            print("Goodbye!")
            break

        else:
            print("Invalid choice. Please enter 1, 2, 3, or 4.")

if __name__ == "__main__":
    main()
