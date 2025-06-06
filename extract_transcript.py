import os
import json
import re
import time
import random
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import requests
from urllib.parse import urlparse, parse_qs
import xml.etree.ElementTree as ET

# Install required packages:
# pip install requests beautifulsoup4 lxml

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Please install beautifulsoup4: pip install beautifulsoup4")
    exit(1)

class YouTubeTranscriptExtractor:
    def __init__(self, storage_dir: str = "transcripts"):
        """
        Initialize the YouTube Transcript Extractor with multiple fallback methods
        
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
      Extract video information from YouTube page with improved duration extraction

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

          page_content = response.text
          soup = BeautifulSoup(response.content, 'html.parser')

          # Extract title
          title_tag = soup.find('meta', property='og:title')
          title = title_tag['content'] if title_tag else 'Unknown Title'

          # Extract description
          desc_tag = soup.find('meta', property='og:description')
          description = desc_tag['content'] if desc_tag else ''

          # Extract duration using multiple methods
          duration = 0

          # Method 1: Try to find duration in ytInitialPlayerResponse
          try:
              player_response_pattern = r'"lengthSeconds":"(\d+)"'
              duration_match = re.search(player_response_pattern, page_content)
              if duration_match:
                  duration = int(duration_match.group(1))
          except:
              pass

          # Method 2: Try to find duration in videoDetails
          if duration == 0:
              try:
                  video_details_pattern = r'"videoDetails".*?"lengthSeconds":"(\d+)"'
                  duration_match = re.search(video_details_pattern, page_content)
                  if duration_match:
                      duration = int(duration_match.group(1))
              except:
                  pass

          # Method 3: Try to find duration in microformat
          if duration == 0:
              try:
                  microformat_pattern = r'"microformat".*?"lengthSeconds":"(\d+)"'
                  duration_match = re.search(microformat_pattern, page_content)
                  if duration_match:
                      duration = int(duration_match.group(1))
              except:
                  pass

          # Method 4: Try to find duration in meta tag
          if duration == 0:
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

          # Method 5: Try to find duration in JSON-LD
          if duration == 0:
              try:
                  scripts = soup.find_all('script', type='application/ld+json')
                  for script in scripts:
                      try:
                          data = json.loads(script.string)
                          if isinstance(data, list):
                              data = data[0]
                          if 'duration' in data:
                              duration_str = data['duration']
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
                                  break
                      except:
                          continue
              except:
                  pass

          # Extract additional metadata
          try:
              metadata_pattern = r'{"uploadDate":"([^"]+)","viewCount":"([^"]+)"'
              metadata_match = re.search(metadata_pattern, page_content)
              if metadata_match:
                  upload_date = metadata_match.group(1)
                  view_count = int(metadata_match.group(2))
              else:
                  upload_date = ''
                  view_count = 0
          except:
              upload_date = ''
              view_count = 0

          # Extract tags and categories
          tags = []
          categories = []
          try:
              keywords_tag = soup.find('meta', {'name': 'keywords'})
              if keywords_tag:
                  tags = [tag.strip() for tag in keywords_tag['content'].split(',')]
          except:
              pass

          try:
              category_tag = soup.find('meta', {'property': 'og:video:tag'})
              if category_tag:
                  categories = [category_tag['content']]
          except:
              pass

          return {
              'title': title,
              'description': description,
              'duration': duration,  # Duration in seconds
              'upload_date': upload_date,
              'view_count': view_count,
              'tags': tags,
              'categories': categories
          }

      except Exception as e:
          print(f"Error getting video info: {str(e)}")
          return {'title': 'Unknown Title', 'description': '', 'duration': 0}
    
    def extract_transcript_from_page(self, video_id: str) -> Optional[List[Dict]]:
        """
        Method 1: Extract transcript by parsing YouTube page for transcript URLs
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            List of transcript segments or None if failed
        """
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            print(f"Trying to extract transcript from page: {url}")
            
            # Add random delay
            time.sleep(random.uniform(1, 3))
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            # Look for transcript/caption URLs in the page source
            page_content = response.text
            
            # Pattern to find timedtext URLs
            timedtext_pattern = r'"captionTracks":\s*\[(.*?)\]'
            match = re.search(timedtext_pattern, page_content)
            
            if not match:
                print("No caption tracks found in page")
                return None
            
            caption_data = match.group(1)
            
            # Extract the first available caption URL
            url_pattern = r'"baseUrl":"([^"]+)"'
            url_match = re.search(url_pattern, caption_data)
            
            if not url_match:
                print("No caption URL found")
                return None
            
            caption_url = url_match.group(1).replace('\\u0026', '&')
            
            print(f"Found caption URL: {caption_url[:100]}...")
            
            # Download the caption XML
            time.sleep(random.uniform(0.5, 1.5))
            caption_response = self.session.get(caption_url, timeout=10)
            caption_response.raise_for_status()
            
            # Parse XML
            root = ET.fromstring(caption_response.content)
            
            transcript = []
            for text_element in root.findall('.//text'):
                start_time = float(text_element.get('start', 0))
                duration = float(text_element.get('dur', 0))
                text_content = text_element.text or ''
                
                # Clean up HTML entities
                text_content = text_content.replace('&amp;', '&')
                text_content = text_content.replace('&lt;', '<')
                text_content = text_content.replace('&gt;', '>')
                text_content = text_content.replace('&quot;', '"')
                text_content = text_content.replace('&#39;', "'")
                
                transcript.append({
                    'start': start_time,
                    'duration': duration,
                    'text': text_content.strip()
                })
            
            if transcript:
                print(f"Successfully extracted {len(transcript)} transcript segments")
                return transcript
            else:
                print("No transcript segments found")
                return None
            
        except Exception as e:
            print(f"Error extracting transcript from page: {str(e)}")
            return None
    
    def extract_transcript_youtube_api_fallback(self, video_id: str) -> Optional[List[Dict]]:
        """
        Method 2: Try the youtube-transcript-api as fallback
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            List of transcript segments or None if failed
        """
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
            
            print("Trying youtube-transcript-api...")
            
            # Try multiple language codes
            languages = ['en', 'en-US', 'en-GB', 'auto']
            
            for lang in languages:
                try:
                    if lang == 'auto':
                        transcript = YouTubeTranscriptApi.get_transcript(video_id)
                    else:
                        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])
                    
                    if transcript:
                        print(f"Successfully got transcript using youtube-transcript-api (lang: {lang})")
                        return transcript
                        
                except NoTranscriptFound:
                    continue
                except Exception as e:
                    print(f"Error with language {lang}: {str(e)}")
                    continue
            
            return None
            
        except ImportError:
            print("youtube-transcript-api not available")
            return None
        except Exception as e:
            print(f"Error with youtube-transcript-api: {str(e)}")
            return None
    
    def extract_transcript_direct_api(self, video_id: str) -> Optional[List[Dict]]:
        """
        Method 3: Direct API approach using YouTube's internal API
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            List of transcript segments or None if failed
        """
        try:
            print("Trying direct API approach...")
            
            # This is a simplified approach - in practice, you might need to
            # reverse engineer more of YouTube's internal API calls
            api_url = f"https://www.youtube.com/api/timedtext?v={video_id}&lang=en&fmt=srv3"
            
            time.sleep(random.uniform(1, 2))
            
            response = self.session.get(api_url, timeout=10)
            
            if response.status_code == 200 and response.content:
                # Try to parse as XML
                try:
                    root = ET.fromstring(response.content)
                    transcript = []
                    
                    for p in root.findall('.//p'):
                        start_time = float(p.get('t', 0)) / 1000  # Convert ms to seconds
                        text_content = ''.join(p.itertext()).strip()
                        
                        if text_content:
                            transcript.append({
                                'start': start_time,
                                'duration': 0,  # Duration not available in this format
                                'text': text_content
                            })
                    
                    if transcript:
                        print(f"Successfully extracted {len(transcript)} segments via direct API")
                        return transcript
                        
                except ET.ParseError:
                    pass
            
            return None
            
        except Exception as e:
            print(f"Error with direct API: {str(e)}")
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
    
    def extract_and_save(self, youtube_url: str) -> Tuple[bool, str, Dict]:
        """
        Main method to extract and save transcript using multiple fallback methods
        
        Args:
            youtube_url: YouTube video URL
            
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
        
        # Try multiple methods to extract transcript
        transcript = None
        methods = [
            ("Page parsing", self.extract_transcript_from_page),
            ("YouTube Transcript API", self.extract_transcript_youtube_api_fallback),
            ("Direct API", self.extract_transcript_direct_api)
        ]
        
        for method_name, method_func in methods:
            print(f"\nTrying method: {method_name}")
            try:
                transcript = method_func(video_id)
                if transcript and len(transcript) > 0:
                    print(f"✓ Success with {method_name}")
                    break
                else:
                    print(f"✗ {method_name} returned no results")
            except Exception as e:
                print(f"✗ {method_name} failed: {str(e)}")
                continue
        
        if not transcript:
            error_msg = "Could not extract transcript using any method. Possible reasons:\n"
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
    print("YouTube Transcript Extractor (Multi-Method)")
    print("=" * 50)
    print("This tool uses multiple methods to extract transcripts:")
    print("1. Direct page parsing")
    print("2. YouTube Transcript API (if available)")
    print("3. Direct API calls")
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
            
            print("\nProcessing...")
            success, message, data = extractor.extract_and_save(youtube_url)
            
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