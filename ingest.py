import os
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore

def build_knowledge_base():
    print("📚 Loading medical guidelines from knowledge_base...")
    loader = PyPDFDirectoryLoader("knowledge_base")
    documents = loader.load()

    print("✂️ Chunking text into readable segments...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs = text_splitter.split_documents(documents)

    print("🧠 Initializing OpenAI embedding model...")
    # This now perfectly matches your FastAPI backend (1536 dimensions)
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    print("🚀 Pushing vector embeddings to cloud database...")
    url = "http://localhost:6333"
    
    qdrant = QdrantVectorStore.from_documents(
        docs,
        embeddings,
        url=url,
        prefer_grpc=False,
        collection_name="clinical_guidelines_v2" # Updated name!
    )
    print("✅ Knowledge base successfully populated with OpenAI vectors!")

if __name__ == "__main__":
    build_knowledge_base()