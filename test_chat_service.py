from app.services.retriever import HybridRetriever
from app.services.vector_store import VectorStoreService
from app.services.chat_service import ChatService

try:
    print("Initializing services...")
    vector_store = VectorStoreService()
    retriever = HybridRetriever(vector_store)
    chat_service = ChatService(retriever)
    
    print("✓ ChatService initialized!")
    
    # Test answer method
    print("\nTesting answer method...")
    response = chat_service.answer(
        user_id="test_user",
        question="What is AI?",
        chat_history=[],
        top_k=5
    )
    
    print(f"✓ Chat response received!")
    print(f"  Answer: {response.answer[:100]}")
    print(f"  Sources: {response.sources}")
    
except Exception as e:
    import traceback
    print(f"✗ Error: {type(e).__name__}")
    print(f"  Message: {str(e)}")
    print("\nFull traceback:")
    traceback.print_exc()
