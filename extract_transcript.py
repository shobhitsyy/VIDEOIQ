import os
import json
import re
import time
import random
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import requests
from urllib.parse import urlparse, parse_qs

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
except ImportError:
    print("Please install youtube-transcript-api: pip install youtube-transcript-api")
    exit(1)

class YouTubeTranscriptExtractor:
    def __init__(self, storage_dir: str = "transcripts"):
        """
        Initialize the YouTube Transcript Extractor
        
        Args:
            storage_dir: Directory to store extracted transcripts
        """
        self.storage_dir = storage_dir
        self.session = requests.Session()
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
        Extract video information from YouTube page
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Dictionary containing video information
        """
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
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
            
            # Extract duration
            duration = 0
            duration_tag = soup.find('meta', itemprop='duration')
            if duration_tag:
                duration_str = duration_tag.get('content', '')
                if duration_str.startswith('PT'):
                    duration_str = duration_str[2:]
                    if 'H' in duration_str:
                        hours = int(duration_str.split('H')[0])
                        duration += hours * 3600
                        duration_str = duration_str.split('H')[1]
                    if 'M' in duration_str:
                        minutes = int(duration_str.split('M')[0])
                        duration += minutes * 60
                        duration_str = duration_str.split('M')[1]
                    if 'S' in duration_str:
                        seconds = int(duration_str.replace('S', ''))
                        duration += seconds
            
            return {
                'title': title,
                'description': description,
                'duration': duration
            }
            
        except Exception as e:
            print(f"Error getting video info: {str(e)}")
            return {'title': 'Unknown Title', 'description': '', 'duration': 0}

    def get_available_languages(self, video_id: str) -> List[Dict]:
        """
        Get list of available transcript languages for a video
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            List of dicts with language info (code and name)
        """
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            languages = []
            
            # Get manually created transcripts
            for transcript in transcript_list.manual:
                languages.append({
                    'code': transcript.language_code,
                    'name': transcript.language,
                    'type': 'manual'
                })
            
            # Get auto-generated transcripts
            for transcript in transcript_list.generated:
                languages.append({
                    'code': transcript.language_code,
                    'name': transcript.language,
                    'type': 'generated'
                })
            
            return sorted(languages, key=lambda x: (x['type'] != 'manual', x['name']))
            
        except Exception as e:
            print(f"Error getting available languages: {str(e)}")
            return []

    def select_language(self, video_id: str) -> Optional[str]:
        """
        Interactive CLI function to display and select available languages
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Selected language code or None if no selection made
        """
        languages = self.get_available_languages(video_id)
        
        if not languages:
            print("No transcripts available for this video")
            return None
        
        print("\nAvailable languages:")
        print("-" * 50)
        print(f"{'#':>3} {'Language':<30} {'Type':<10}")
        print("-" * 50)
        
        for i, lang in enumerate(languages, 1):
            print(f"{i:>3} {lang['name']:<30} {lang['type']:<10}")
        
        while True:
            try:
                choice = input("\nSelect language number (or press Enter for English/auto): ").strip()
                
                if not choice:  # Default behavior
                    return None
                
                choice = int(choice)
                if 1 <= choice <= len(languages):
                    return languages[choice-1]['code']
                else:
                    print("Invalid choice. Please try again.")
            except ValueError:
                print("Please enter a valid number.")
            except Exception as e:
                print(f"Error: {str(e)}")
                return None

    def extract_transcript(self, video_id: str, language_code: Optional[str] = None) -> Optional[List[Dict]]:
        """
        Extract transcript using youtube-transcript-api
        
        Args:
            video_id: YouTube video ID
            language_code: Specific language code to use (optional)
            
        Returns:
            List of transcript segments or None if failed
        """
        try:
            # If language is specified, try that first
            if language_code:
                try:
                    transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[language_code])
                    if transcript:
                        print(f"Got transcript in specified language: {language_code}")
                        return transcript
                except Exception as e:
                    print(f"Could not get transcript in {language_code}: {str(e)}")
            
            # Try English variants first
            english_codes = ['en', 'en-US', 'en-GB']
            for lang in english_codes:
                try:
                    transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])
                    if transcript:
                        print(f"Got transcript in {lang}")
                        return transcript
                except Exception:
                    continue
            
            # If no English transcript, try auto-generated
            try:
                transcript = YouTubeTranscriptApi.get_transcript(video_id)
                if transcript:
                    print("Got auto-generated transcript")
                    return transcript
            except Exception as e:
                print(f"Could not get auto-generated transcript: {str(e)}")
            
            return None
            
        except Exception as e:
            print(f"Error extracting transcript: {str(e)}")
            return None
    
    def format_transcript(self, transcript: List[Dict]) -> str:
        """
        Format transcript segments into readable text with timestamps
        """
        if not transcript:
            return ""
        
        formatted_text = ""
        for segment in transcript:
            start_time = segment.get('start', 0)
            text = segment.get('text', '')
            
            # Convert seconds to MM:SS format
            minutes = int(start_time // 60)
            seconds = int(start_time % 60)
            timestamp = f"[{minutes:02d}:{seconds:02d}]"
            
            formatted_text += f"{timestamp} {text}\n"
        
        return formatted_text
    
    def get_plain_text(self, transcript: List[Dict]) -> str:
        """
        Get plain text without timestamps
        """
        if not transcript:
            return ""
        
        return " ".join([segment.get('text', '') for segment in transcript])
    
    def save_transcript(self, video_id: str, data: Dict) -> str:
        """
        Save transcript data to JSON file
        """
        filename = f"{video_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(self.storage_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return filepath
    
    def extract_and_save(self, youtube_url: str, language_code: Optional[str] = None) -> Tuple[bool, str, Dict]:
        """
        Main method to extract and save transcript
        
        Args:
            youtube_url: YouTube video URL
            language_code: Specific language code to use (optional)
            
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
        
        # Extract transcript
        transcript = self.extract_transcript(video_id, language_code)
        
        if not transcript:
            error_msg = "Could not extract transcript. Possible reasons:\n"
            error_msg += "- Video has no captions/subtitles available\n"
            error_msg += "- Video is private or restricted\n"
            error_msg += "- YouTube has blocked automated access\n"
            error_msg += "- Video URL is invalid"
            return False, error_msg, {}
        
        # Format transcript
        formatted_transcript = self.format_transcript(transcript)
        plain_text = self.get_plain_text(transcript)
        
        # Prepare data for storage
        data = {
            'video_id': video_id,
            'url': youtube_url,
            'metadata': metadata,
            'transcript_raw': transcript,
            'transcript_formatted': formatted_transcript,
            'transcript_plain': plain_text,
            'extracted_at': datetime.now().isoformat(),
            'word_count': len(plain_text.split()),
            'duration_minutes': round(metadata.get('duration', 0) / 60, 2),
            'segment_count': len(transcript)
        }
        
        # Save to file
        filepath = self.save_transcript(video_id, data)
        
        success_msg = f"Transcript extracted successfully!\n"
        success_msg += f"Title: {metadata.get('title', 'Unknown')}\n"
        success_msg += f"Duration: {data['duration_minutes']} minutes\n"
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
        
        video_id = extractor.extract_video_id(url)
        if video_id:
            # Show available languages
            print("\nChecking available languages...")
            languages = extractor.get_available_languages(video_id)
            if languages:
                print(f"Found {len(languages)} available languages:")
                for lang in languages:
                    print(f"- {lang['name']} ({lang['code']}) [{lang['type']}]")
            else:
                print("No transcripts available")
        
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
    print("YouTube Transcript Extractor")
    print("=" * 50)
    print("This tool can extract transcripts in multiple languages")
    print("=" * 50)
    
    extractor = YouTubeTranscriptExtractor()
    
    while True:
        print("\nOptions:")
        print("1. Extract transcript from URL")
        print("2. Test with sample videos")
        print("3. Quit")
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == '1':
            youtube_url = input("\nEnter YouTube URL: ").strip()
            
            if not youtube_url:
                print("Please enter a valid URL")
                continue
            
            # Get video ID
            video_id = extractor.extract_video_id(youtube_url)
            if not video_id:
                print("Invalid YouTube URL")
                continue
            
            # Show available languages and get selection
            language_code = extractor.select_language(video_id)
            
            print("\nProcessing...")
            success, message, data = extractor.extract_and_save(youtube_url, language_code)
            
            print(f"\n{message}")
            
            if success:
                # Show preview
                preview = data['transcript_plain'][:300] + "..." if len(data['transcript_plain']) > 300 else data['transcript_plain']
                print(f"\nTranscript Preview:\n{'-' * 20}\n{preview}\n{'-' * 20}")
        
        elif choice == '2':
            test_with_sample_videos()
        
        elif choice == '3':
            print("Goodbye!")
            break
        
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")

if __name__ == "__main__":
    main()
