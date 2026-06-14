import os
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore

def build_knowledge_base():
    # 1. Load the PDFs from your local folder
    print("📚 Loading medical guidelines from knowledge_base...")
    loader = PyPDFDirectoryLoader("knowledge_base")
    documents = loader.load()

    # 2. Chop the text into 500-word segments (with 50-word overlap for context)
    print("✂️ Chunking text into readable segments...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs = text_splitter.split_documents(documents)

    # 3. Download and initialize the local HuggingFace embedding model
    print("🧠 Initializing HuggingFace embedding model...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    # 4. Push the embedded chunks directly to your EKS Qdrant pod
    print("🚀 Pushing vector embeddings to cloud database...")
    url = "http://localhost:6333"
    
    qdrant = QdrantVectorStore.from_documents(
        docs,
        embeddings,
        url=url,
        prefer_grpc=False,
        collection_name="clinical_guidelines"
    )
    print("✅ Knowledge base successfully populated in EKS!")

if __name__ == "__main__":
    build_knowledge_base()