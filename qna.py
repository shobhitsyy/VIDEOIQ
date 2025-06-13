from groq import Groq
import google.generativeai as genai
from typing import Optional
import time

# Initialize clients
groq_client = Groq(
    api_key="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",  # Replace with your Groq API key
)

# Configure Gemini
genai.configure(api_key="AIzaSyCwQq8ipQkIJrV9gy_D1xeZSfok_lyJ6t0")  # Replace with your Gemini API key
gemini_model = genai.GenerativeModel('gemini-1.5-flash')

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
    
    # Try Gemini first
    answer = ask_gemini(transcript, question)
    if answer:
        print("✅ Response from Gemini")
        return answer
    
    # If Gemini fails, try Groq
    print("⚠️  Gemini failed, trying Groq API as fallback...")
    answer = ask_groq(transcript, question)
    if answer:
        print("✅ Response from Groq (fallback)")
        return answer
    
    # If both fail
    print("❌ Both APIs failed")
    return None

def test_apis():
    """Test both APIs to ensure they're working."""
    print("Testing API connections...")
    
    # Test Gemini first (now primary)
    try:
        test_response = gemini_model.generate_content("Hello, can you respond with just 'Gemini working'?")
        print("✅ Gemini API: Connected")
    except Exception as e:
        print(f"❌ Gemini API: Failed - {e}")
    
    # Test Groq second (now fallback)
    try:
        test_response = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": "Hello, can you respond with just 'Groq working'?"}],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            max_tokens=10,
        )
        print("✅ Groq API: Connected")
    except Exception as e:
        print(f"❌ Groq API: Failed - {e}")
    
    print()

def main():
    print("=== Transcript Q&A with Dual API Support ===")
    print("Primary: Gemini | Fallback: Groq\n")
    
    # Test API connections
    test_apis()
    
    # Get the transcript file path
    file_path = input("Enter the path to your transcript file (txt preferred): ")

    # Read the transcript
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

    # Question-answering loop
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

        # Process the question
        if manual_mode:
            if selected_api == 'gemini':
                print("🔄 Using Gemini API (manual mode)...")
                answer = ask_gemini(transcript, question)
            else:  # groq
                print("🔄 Using Groq API (manual mode)...")
                answer = ask_groq(transcript, question)
        else:
            # Use automatic fallback
            answer = ask_question_with_fallback(transcript, question)

        if answer:
            print(f"\n📝 Answer:\n{answer}")
        else:
            print("❌ Sorry, I couldn't generate an answer. Please try again.")

if __name__ == "__main__":
    main()
