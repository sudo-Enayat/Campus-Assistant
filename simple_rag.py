import chromadb
from sentence_transformers import SentenceTransformer
from llama_cpp import Llama
import os, json, re
from pathlib import Path

class SimpleCampusRAG:
    def __init__(self, model_path, data_folder="data", persist_dir="./chroma_db", collection_name="campus_docs"):
        print("🔄 Loading Gemma model...")
        self.llm = Llama(
            model_path=model_path,
            n_ctx=2048,
            n_threads=4,
            verbose=False
        )
        print("✅ Gemma loaded!")
        
        print("🔄 Loading embeddings model...")
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        print("✅ Embeddings loaded!")

        self.chroma_client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.chroma_client.get_or_create_collection(collection_name)

        self.data_folder = Path(data_folder)
        self.data_folder.mkdir(exist_ok=True)

    def _call_llm(self, prompt, max_tokens=256, temperature=0.0, stop=None):
        """Helper method to call Gemma LLM"""
        try:
            resp = self.llm(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop or []
            )
            # Clean up the response - remove leading/trailing whitespace, dots, newlines
            result = resp["choices"][0]["text"].strip()
            
            # Remove leading punctuation and newlines
            while result and result[0] in '.,:;!\n\r\t ':
                result = result[1:].strip()
                
            return result
            
        except Exception as e:
            print(f"LLM call error: {e}")
            return ""

    def rewrite_query(self, user_query):
        """Rewrite query to English for better retrieval (documents are English-only)"""
        prompt = f"""Please convert this query to clear, well-formed English for document search purposes. Fix any spelling/grammar and expand abbreviations:

Original query: "{user_query}"

English search query:"""

        try:
            response = self._call_llm(prompt, max_tokens=100, temperature=0.1)
            return response.strip() if response.strip() else user_query
        except Exception as e:
            print(f"Query rewrite error: {e}")
            return user_query

    def search_knowledge_base(self, english_query, top_k=3):
        """Search for relevant documents using English query"""
        try:
            if self.collection.count() == 0:
                print("⚠️ Knowledge base is empty!")
                return {'documents': [], 'sources': []}
            
            query_embedding = self.embedding_model.encode([english_query])
            
            results = self.collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=top_k
            )
            
            documents = []
            sources = []
            
            if results and 'documents' in results and len(results['documents']) > 0:
                doc_list = results['documents'][0]
                meta_list = results['metadatas'][0]
                
                for doc, meta in zip(doc_list, meta_list):
                    documents.append(doc)
                    sources.append(meta.get('filename', 'Unknown'))
            
            return {
                'documents': documents,
                'sources': sources
            }
            
        except Exception as e:
            print(f"Search error: {e}")
            return {'documents': [], 'sources': []}

    def split_text(self, text, chunk_size=500, overlap=50):
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            if end < len(text):
                last_period = text.rfind(".", start, end)
                if last_period > start + chunk_size // 2:
                    end = last_period + 1
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start = max(end - overlap, end)
            if start >= len(text):
                break
        return chunks

    def build_knowledge_base(self):
        print("🔄 Loading documents...")
        documents, metadatas, ids = [], [], []
        doc_id = 0
        
        for file_path in self.data_folder.glob("**/*"):
            if file_path.is_file() and file_path.suffix.lower() in [".txt", ".md"]:
                try:
                    content = file_path.read_text(encoding="utf-8")
                    chunks = self.split_text(content)
                    
                    for i, chunk in enumerate(chunks):
                        documents.append(chunk)
                        metadatas.append({
                            "source": str(file_path), 
                            "filename": file_path.name, 
                            "chunk_id": i
                        })
                        ids.append(f"doc_{doc_id}_{i}")
                    
                    print(f"✅ Processed {file_path.name} ({len(chunks)} chunks)")
                    doc_id += 1
                    
                except Exception as e:
                    print(f"❌ Error processing {file_path}: {e}")

        if not documents:
            print("⚠️ No documents found to index.")
            return

        print(f"📄 Found {len(documents)} document chunks")
        print("🔄 Creating embeddings...")
        
        embeddings = self.embedding_model.encode(documents)
        
        try:
            self.chroma_client.delete_collection(self.collection.name)
            self.collection = self.chroma_client.create_collection(self.collection.name)
        except:
            pass
        
        self.collection.add(
            embeddings=embeddings.tolist(),
            documents=documents,
            metadatas=metadatas,
            ids=ids,
        )
        print("✅ Knowledge base built successfully!")

    def generate_answer(self, user_query):
        """Generate answer using RAG pipeline - let Gemma handle language naturally"""
        try:
            # Step 1: Convert query to English for retrieval (since docs are English)
            english_query = self.rewrite_query(user_query)
            
            print(f"🔄 Original: {user_query}")
            print(f"🔄 Search query: {english_query}")
            
            # Step 2: Search knowledge base using English query
            search_results = self.search_knowledge_base(english_query, top_k=3)
            documents = search_results['documents']
            sources = search_results['sources']
            
            # Step 3: Generate answer using original query + English context
            if not documents:
                # Let Gemma naturally respond to "no info" in user's language
                prompt = f"""I don't have information about this topic in my knowledge base. Please respond to this user appropriately:

User asked: {user_query}

Response:"""
                
                answer = self._call_llm(prompt, max_tokens=100, temperature=0.3)
                return {
                    'answer': answer if answer else "I don't have information on this topic. Please contact a human for help.",
                    'sources': [],
                    'context_used': 0
                }
            
            # Use English context but original user query - let Gemma match the language naturally
            context = "\n\n".join(documents)
            unique_sources = list(set(sources))
            
            answer_prompt = f"""You are a helpful campus assistant. Use the context below to answer the user's question.

Context:
{context}

User's question: {user_query}

Instructions:
- Use only the information from the context above
- If the context doesn't have enough information, say you don't have that information
- Be helpful and concise
- reply in user's original language

Answer:"""
            
            answer = self._call_llm(answer_prompt, max_tokens=300, temperature=0.3)
            
            return {
                'answer': answer if answer else "I couldn't generate a response.",
                'sources': unique_sources,
                'context_used': len(documents)
            }
            
        except Exception as e:
            print(f"Generate answer error: {e}")
            return {
                'answer': "I encountered an error while processing your question. Please try again.",
                'sources': [],
                'context_used': 0
            }
