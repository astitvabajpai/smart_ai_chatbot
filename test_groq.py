from app.core.config import get_settings
from langchain_groq import ChatGroq

try:
    settings = get_settings()
    print(f"Groq API Key set: {bool(settings.groq_api_key)}")
    print(f"Groq Model: {settings.groq_model}")
    
    llm = ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0.2,
        streaming=False,
    )
    
    # Test with a simple message
    response = llm.invoke([{"role": "user", "content": "What is 2+2?"}])
    print(f"✓ Groq API working!")
    print(f"Response: {response.content[:100]}")
except Exception as e:
    import traceback
    print(f"✗ Groq API Error: {type(e).__name__}")
    print(f"  Message: {str(e)}")
    traceback.print_exc()
