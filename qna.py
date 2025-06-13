import os
from groq import Groq
import google.generativeai as genai
from typing import Optional

# Read API keys securely from environment variables
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Initialize clients (fail gracefully if keys are missing)
groq_client = None
gemini_model = None

if GROQ_API_KEY:
    groq_client = Groq(api_key=GROQ_API_KEY)  # Do not expose key in source!
else:
    print("Warning: GROQ_API_KEY not set in environment.")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')
else:
    print("Warning: GEMINI_API_KEY not set in environment.")

def read_transcript(file_path: str) -> str:
    """Read the transcript file content."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return ""

def ask_groq(transcript: str, question: str) -> Optional[str]:
    """Ask a question using Groq API."""
    if not groq_client:
        print("Groq client not initialized. Please set GROQ_API_KEY.")
        return None
    try:
        prompt = f"""
        Here's a transcript:
        ---
        {transcript}
        ---

        Question: {question}

        Please answer the question based on the transcript. If the information isn't directly available in the transcript,
        you can use your general knowledge but please indicate that you're doing so by starting with "Based on general knowledge:"
        """

        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=1024,
        )

        return chat_completion.choices[0].message.content

    except Exception as e:
        print(f"Groq API error: {e}")
        return None

def ask_gemini(transcript: str, question: str) -> Optional[str]:
    """Ask a question using Gemini API as fallback."""
    if not gemini_model:
        print("Gemini model not initialized. Please set GEMINI_API_KEY.")
        return None
    try:
        prompt = f"""
        Here's a transcript:
        ---
        {transcript}
        ---

        Question: {question}

        Please answer the question based on the transcript. If the information isn't directly available in the transcript,
        you can use your general knowledge but please indicate that you're doing so by starting with "Based on general knowledge:"
        """

        response = gemini_model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=1024,
            )
        )

        return response.text

    except Exception as e:
        print(f"Gemini API error: {e}")
        return None

def ask_question_with_fallback(transcript: str, question: str) -> Optional[str]:
    """Ask a question with Gemini as primary and Groq as fallback."""
    print("🔄 Trying Gemini API...")
    
    answer = ask_gemini(transcript, question)
    if answer:
        print("✅ Response from Gemini")
        return answer
    
    print("⚠️  Gemini failed, trying Groq API as fallback...")
    answer = ask_groq(transcript, question)
    if answer:
        print("✅ Response from Groq (fallback)")
        return answer
    
    print("❌ Both APIs failed")
    return None

def test_apis():
    """Test both APIs to ensure they're working."""
    print("Testing API connections...")
    
    try:
        if gemini_model:
            test_response = gemini_model.generate_content("Hello, can you respond with just 'Gemini working'?")
            print("✅ Gemini API: Connected")
        else:
            print("❌ Gemini API: Not initialized")
    except Exception as e:
        print(f"❌ Gemini API: Failed - {e}")
    
    try:
        if groq_client:
            test_response = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": "Hello, can you respond with just 'Groq working'?"}],
                model="llama-3.3-70b-versatile",
                temperature=0.1,
                max_tokens=10,
            )
            print("✅ Groq API: Connected")
        else:
            print("❌ Groq API: Not initialized")
    except Exception as e:
        print(f"❌ Groq API: Failed - {e}")
    
    print()

def main():
    print("=== Transcript Q&A with Dual API Support ===")
    print("Primary: Gemini | Fallback: Groq\n")
    
    test_apis()
    
    file_path = input("Enter the path to your transcript file (txt preferred): ")

    transcript = read_transcript(file_path)
    if not transcript:
        print("Could not read transcript. Please check the file path and try again.")
        return

    print(f"\n✅ Transcript loaded successfully! ({len(transcript)} characters)")
    print("You can now ask questions about the transcript.")
    print("Commands:")
    print("  - Type 'quit' or 'exit' to quit")
    print("  - Type 'test' to test API connections")
    print("  - Type 'switch' to manually choose API (groq/gemini)")
    
    manual_mode = False
    selected_api = None

    while True:
        question = input("\n💭 Enter your question: ")

        if question.lower() in ['quit', 'exit']:
            print("👋 Goodbye!")
            break
        
        if question.lower() == 'test':
            test_apis()
            continue
            
        if question.lower() == 'switch':
            api_choice = input("Choose API (groq/gemini/auto): ").lower()
            if api_choice in ['groq', 'gemini']:
                manual_mode = True
                selected_api = api_choice
                print(f"✅ Switched to {api_choice.upper()} only mode")
            elif api_choice == 'auto':
                manual_mode = False
                print("✅ Switched back to automatic fallback mode")
            else:
                print("❌ Invalid choice. Use 'groq', 'gemini', or 'auto'")
            continue

        if manual_mode:
            if selected_api == 'gemini':
                print("🔄 Using Gemini API (manual mode)...")
                answer = ask_gemini(transcript, question)
            else:
                print("🔄 Using Groq API (manual mode)...")
                answer = ask_groq(transcript, question)
        else:
            answer = ask_question_with_fallback(transcript, question)

        if answer:
            print(f"\n📝 Answer:\n{answer}")
        else:
            print("❌ Sorry, I couldn't generate an answer. Please try again.")

if __name__ == "__main__":
    main()
