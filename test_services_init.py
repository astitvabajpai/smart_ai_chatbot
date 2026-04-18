import sys
import traceback

try:
    print("1. Testing get_settings...")
    from app.core.config import get_settings
    settings = get_settings()
    print(f"   ✓ Settings loaded")
    
    print("2. Testing DocumentProcessor...")
    from app.services.document_loader import DocumentProcessor
    processor = DocumentProcessor()
    print(f"   ✓ DocumentProcessor initialized")
    
    print("3. Testing VectorStoreService...")
    from app.services.vector_store import VectorStoreService
    vector_store = VectorStoreService()
    print(f"   ✓ VectorStoreService initialized")
    
    print("4. Testing ChatService...")
    from app.services.retriever import HybridRetriever
    from app.services.chat_service import ChatService
    retriever = HybridRetriever(vector_store)
    chat_service = ChatService(retriever)
    print(f"   ✓ ChatService initialized")
    
    print("\n✓ All services initialized successfully!")
    
except Exception as e:
    print(f"\n✗ Error: {type(e).__name__}: {str(e)}")
    print("\nFull traceback:")
    traceback.print_exc()
    sys.exit(1)
