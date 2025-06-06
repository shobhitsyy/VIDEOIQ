from dotenv import load_dotenv
load_dotenv()
from groq import Groq
from typing import Optional

# Initialize Groq client
client = Groq(
    api_key="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",  # Replace with your Groq API key
)

def read_transcript(file_path: str) -> str:
    """Read the transcript file content."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return ""

def ask_question(transcript: str, question: str) -> Optional[str]:
    """Ask a question about the transcript using Groq."""
    try:
        # Create a prompt that includes both the transcript and the instruction
        prompt = f"""
        Here's a transcript:
        ---
        {transcript}
        ---
        
        Question: {question}
        
        Please answer the question based on the transcript. If the information isn't directly available in the transcript, 
        you can use your general knowledge but please indicate that you're doing so by starting with "Based on general knowledge:"
        """
        
        # Generate response using Groq
        chat_completion = client.chat.completions.create(
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
        
        # Extract the response
        return chat_completion.choices[0].message.content

    except Exception as e:
        print(f"Error generating response: {e}")
        return None

def main():
    # Get the transcript file path
    file_path = input("Enter the path to your transcript file (txt preferred): ")
    
    # Read the transcript
    transcript = read_transcript(file_path)
    if not transcript:
        print("Could not read transcript. Please check the file path and try again.")
        return
    
    print("\nTranscript loaded successfully! You can now ask questions.")
    print("Type 'quit' to exit.")
    
    # Question-answering loop
    while True:
        question = input("\nEnter your question: ")
        
        if question.lower() == 'quit':
            print("Goodbye!")
            break
            
        answer = ask_question(transcript, question)
        if answer:
            print("\nAnswer:", answer)
        else:
            print("Sorry, I couldn't generate an answer. Please try again.")

if __name__ == "__main__":
    main()