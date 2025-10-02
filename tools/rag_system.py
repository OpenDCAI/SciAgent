# rag_system.py
import json
import os
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings # Updated import
from langchain_community.vectorstores import Chroma # Updated import
from langchain.schema import Document
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

# Read the API key from environment variables
API_KEY = os.getenv("API_KEY")

class CPAssistant:
    """
    RAG System, configured to use OpenRouter's API with a powerful model.
    """
    def __init__(self):
        self.embeddings = None
        self.vectorstore = None
        self.llm = None
        self.qa_chain = None
        
    def setup_embeddings(self):
        """Initializes the model to convert text into vectors (embeddings)."""
        print("Setting up embeddings (sentence-transformers)...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}
        )
        print("Embeddings ready!")
        
    def load_documents(self):
        """Loads and processes documents from the V2.0 JSON structure."""
        print("Loading documents (V2.0)...")
        documents = []
        # --- Load Algorithms from JSON files ---
        algo_dir = Path("data/algorithms")
        if algo_dir.exists():
            for file_path in algo_dir.glob("*.json"):
                with open(file_path, 'r', encoding='utf-8') as f: data = json.load(f)
                content = f"""
[Algorithm Title]: {data.get('title', '')}, [Aliases]: {', '.join(data.get('aliases', []))}
[Summary]: {data.get('summary', '')}
[Theory]: {data.get('theory', '')}
[Implementations]:
"""
                for impl in data.get('implementations', []): content += f"--- Implementation ({impl.get('name', 'Unnamed')}) ---\n```cpp\n{impl.get('code', '')}\n```\n"
                for problem in data.get('example_problems', []): content += f"--- Problem: {problem.get('id', 'Unknown')} ---\nDescription: {problem.get('description', '')}\n"
                doc = Document(page_content=content, metadata={"source": file_path.name, "type": "algorithm", "title": data.get('title', '')})
                documents.append(doc)
        
        # --- Load Templates from C++ files ---
        template_dir = Path("data/templates")
        if template_dir.exists():
            for file_path in template_dir.glob("*.cpp"):
                with open(file_path, 'r', encoding='utf-8') as f: page_content = f.read()
                documents.append(Document(page_content=page_content, metadata={"source": file_path.name, "type": "template"}))

        print(f"Loaded {len(documents)} documents")
        return documents
    
    def create_vectorstore(self, documents):
        """Creates the vector database from the processed documents."""
        print("Creating vector store...")
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)
        split_docs = text_splitter.split_documents(documents)
        self.vectorstore = Chroma.from_documents(documents=split_docs, embedding=self.embeddings, persist_directory="vectorstore")
        print(f"Vector store created successfully with {len(split_docs)} chunks!")
        
    def setup_llm(self, rag_tool_model):
        """Initializes the LLM using OpenRouter's API with a timeout."""
        print("Setting up LLM...")
        api_key = os.environ.get("API_KEY")
        self.llm = ChatOpenAI(
            model=rag_tool_model, 
            temperature=0.1,
            api_key=api_key,
            base_url=os.environ.get("API_BASE", "https://openrouter.ai/api/v1"),
            request_timeout=30, # Added timeout to prevent infinite hangs
            default_headers={
                "HTTP-Referer": "http://localhost:3000",
                "X-Title": "ICPC AI Assistant",
            },
        )
        print("LLM ready!")
        
    def create_qa_chain(self):
        """Creates the QA chain with an optimized prompt."""
        prompt_template = """
You are a world-class competitive programmer and algorithm expert. Use the provided CONTEXT to answer the QUESTION with extreme detail and accuracy.

CONTEXT:
{context}

QUESTION: {question}

INSTRUCTIONS:
- Provide a detailed theoretical explanation based on the context.
- If the context contains C++ code, present the full, correct, and runnable code.
- Mention any common pitfalls or important variations if they are in the context.

DETAILED C++ FOCUSED ANSWER:
"""
        PROMPT = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
        
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.vectorstore.as_retriever(search_kwargs={"k": 3}),
            chain_type_kwargs={"prompt": PROMPT},
            return_source_documents=True
        )
        print("QA Chain (C++) ready!")
    
    def initialize(self, rag_tool_model):
        """Initializes the entire RAG system."""
        print("Initializing CP Assistant...")
        if not Path("vectorstore").exists() or not os.listdir("vectorstore"):
            self.setup_embeddings()
            documents = self.load_documents()
            self.create_vectorstore(documents)
        else:
            print("Vector store already exists, loading...")
            self.setup_embeddings()
            self.vectorstore = Chroma(persist_directory="vectorstore", embedding_function=self.embeddings)
        
        self.setup_llm(rag_tool_model)
        self.create_qa_chain()
        print("CP Assistant is ready!")
    
    def ask(self, question: str) -> dict:
        """Sends a question to the system and returns the answer."""
        if not self.qa_chain:
            print("System not initialized!")
            return {}
        try:
            result = self.qa_chain.invoke(question)
            return {"result": result["result"]}
        except Exception as e:
            print(f"Error querying AI: {e}")
            return {}

if __name__ == "__main__":
    # Run this file directly to build the vectorstore or for testing
    assistant = CPAssistant()
    assistant.initialize()
    print("\n--- Test Mode ---")
    question = "Explain Disjoint Set Union (DSU) and its optimizations."
    print(f"Test query: {question}")
    response = assistant.ask(question)
    print("\nTest Response:\n", response.get("result", "No response."))