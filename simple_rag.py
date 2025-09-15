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
            n_ctx=1024,
            n_threads=6,
            verbose=False,
            n_gpu_layers=0
        )
        print("✅ Model loaded!")
        
        print("🔄 Loading embeddings model...")
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        print("✅ Embeddings loaded!")

        self.chroma_client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.chroma_client.get_or_create_collection(collection_name)

        self.data_folder = Path(data_folder)
        self.data_folder.mkdir(exist_ok=True)

    def _call_llm(self, prompt, max_tokens=256, temperature=0.2, stop=None):
        """Helper method to call LLM"""
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
        """Quick query rewrite for retrieval"""
        # Skip rewriting for simple English queries
        if len(user_query.split()) <= 5 and user_query.encode('utf-8').isascii():
            return user_query
        
        prompt = f"""Convert to English search terms: "{user_query}"

    English:"""

        try:
            response = self._call_llm(prompt, max_tokens=50, temperature=0.0)  
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

    def split_text(self, text, chunk_size=200, overlap=50):
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
        """Generate answer using RAG pipeline - optimized"""
        try:
            # Step 1: Convert query to English for retrieval
            english_query = self.rewrite_query(user_query)
            
            print(f"🔄 Search query: {english_query}")
            
            # Step 2: Search knowledge base - get fewer, more relevant results
            search_results = self.search_knowledge_base(english_query, top_k=2)  # Reduced from 3
            documents = search_results['documents']
            sources = search_results['sources']
            
            # Step 3: Generate answer
            if not documents:
                # Quick fallback - no LLM call needed
                return {
                    'answer': "I don't have information on this topic. Please contact the campus office for help.",
                    'sources': [],
                    'context_used': 0
                }
            
            # Limit context size - only use first 400 characters from documents
            context_parts = []
            total_chars = 0
            for doc in documents:
                if total_chars + len(doc) > 800:  # Limit total context
                    remaining = 400 - total_chars
                    if remaining > 100:  # Only add if meaningful chunk remains
                        context_parts.append(doc[:remaining] + "...")
                    break
                context_parts.append(doc)
                total_chars += len(doc)
            
            context = "\n\n".join(context_parts)
            unique_sources = list(set(sources))
            
            # Shorter, more direct prompt
            answer_prompt = f"""Answer this question using the context provided. Be concise.

    Context: {context}

    Question: {user_query}

    Answer:"""
            
            # Reduced max_tokens for faster generation
            answer = self._call_llm(answer_prompt, max_tokens=150, temperature=0.3)  
            
            return {
                'answer': answer if answer else "I couldn't generate a response.",
                'sources': unique_sources,
                'context_used': len(context_parts)
            }
            
        except Exception as e:
            print(f"Generate answer error: {e}")
            return {
                'answer': "Error processing your question.",
                'sources': [],
                'context_used': 0
            }


    def generate_answer_stream(self, user_query, documents, sources):
        """Generate streaming answer with real token-by-token output"""
        try:
            # Prepare context (limited size for speed)
            context_parts = []
            total_chars = 0
            for doc in documents:
                if total_chars + len(doc) > 600:
                    break
                context_parts.append(doc)
                total_chars += len(doc)
            
            context = "\n\n".join(context_parts)
            unique_sources = list(set(sources))
            
            answer_prompt = f"""Answer concisely using the context:

    Context: {context}

    if context is empty
        reply: "sorry, I don't have that information."

    Question: {user_query}

    Answer:"""
            
            # Real token-by-token streaming from llama-cpp
            full_response = ""
            
            try:
                # Use llama-cpp's streaming capability
                for token in self.llm(
                    answer_prompt,
                    max_tokens=512,
                    temperature=0.0,
                    stream=True,  # This enables real streaming
                    stop=["\n\n", "Question:", "Context:"]
                ):
                    token_text = token['choices'][0]['text']
                    full_response += token_text
                    
                    # Emit each token as it's generated
                    yield {
                        'phase': 'streaming',
                        'partial_response': full_response.strip()
                    }
                
                # Final complete response
                yield {
                    'phase': 'complete',
                    'response': full_response.strip(),
                    'sources': unique_sources,
                    'context_used': len(context_parts)
                }
                
            except Exception as streaming_error:
                print(f"Streaming error, falling back to batch: {streaming_error}")
                # Fallback to non-streaming if streaming fails
                answer = self._call_llm(answer_prompt, max_tokens=120, temperature=0.2)
                
                yield {
                    'phase': 'complete',
                    'response': answer,
                    'sources': unique_sources,
                    'context_used': len(context_parts)
                }
            
        except Exception as e:
            print(f"Generate stream error: {e}")
            yield {
                'phase': 'error',
                'error': 'Error generating response'
            }
