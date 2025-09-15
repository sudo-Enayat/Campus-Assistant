from flask import Flask, render_template, request, jsonify, session, Response
from simple_rag import SimpleCampusRAG
import os
from pathlib import Path
import threading
import time
import json

app = Flask(__name__)
app.secret_key = 'your-secret-key'

# Global variables
current_rag = None
current_model = None
sync_status = {'running': False, 'completed': False}

def get_available_models():
    """Get list of available .gguf models"""
    models_folder = Path("models")
    if not models_folder.exists():
        return []
    
    models = []
    for file in models_folder.glob("*.gguf"):
        models.append(file.name)
    return sorted(models)

def load_model_async(model_name):
    """Load model in background thread"""
    global current_rag, current_model
    try:
        model_path = f"models/{model_name}"
        current_rag = SimpleCampusRAG(model_path)
        current_model = model_name
        return True
    except Exception as e:
        print(f"Error loading model: {e}")
        return False

def sync_knowledge_base_async():
    """Sync knowledge base in background thread"""
    global sync_status, current_rag
    sync_status = {'running': True, 'completed': False}
    
    try:
        if current_rag:
            current_rag.build_knowledge_base()
            sync_status = {'running': False, 'completed': True}
        else:
            sync_status = {'running': False, 'completed': False, 'error': 'No model loaded'}
    except Exception as e:
        sync_status = {'running': False, 'completed': False, 'error': str(e)}

@app.route('/')
def index():
    """Main chat interface"""
    return render_template('index.html')

@app.route('/admin')
def admin():
    """Admin panel"""
    if not session.get('admin_logged_in'):
        return render_template('admin.html', login_required=True)
    
    models = get_available_models()
    return render_template('admin.html', 
                         models=models, 
                         current_model=current_model,
                         login_required=False)

@app.route('/admin/login', methods=['POST'])
def admin_login():
    """Simple admin login"""
    password = request.json.get('password', '')
    # Simple password check - change this in production
    if password == 'admin123':
        session['admin_logged_in'] = True
        return jsonify({'success': True})
    return jsonify({'success': False}), 401

@app.route('/admin/logout', methods=['POST'])
def admin_logout():
    """Admin logout"""
    session.pop('admin_logged_in', None)
    return jsonify({'success': True})

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages"""
    global current_rag
    
    if not current_rag:
        return jsonify({'error': 'No model loaded. Please contact admin.'}), 400
    
    data = request.get_json()
    message = data.get('message', '').strip()
    
    if not message:
        return jsonify({'error': 'Empty message'}), 400
    
    try:
        result = current_rag.generate_answer(message)
        return jsonify({
            'response': result['answer'],
            'sources': result['sources'],
            'context_used': result['context_used']
        })
    except Exception as e:
        print(f"Chat error: {e}")
        return jsonify({'error': 'Sorry, I encountered an error processing your request.'}), 500

@app.route('/api/admin/models', methods=['GET'])
def get_models():
    """Get available models"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    models = get_available_models()
    return jsonify({
        'models': models,
        'current_model': current_model
    })

@app.route('/api/admin/load_model', methods=['POST'])
def load_model():
    """Load a specific model"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    model_name = data.get('model_name')
    
    if not model_name:
        return jsonify({'error': 'Model name required'}), 400
    
    # Load model in background thread
    thread = threading.Thread(target=load_model_async, args=(model_name,))
    thread.start()
    
    return jsonify({'success': True, 'message': 'Model loading started...'})

@app.route('/api/admin/model_status', methods=['GET'])
def model_status():
    """Get current model status"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    return jsonify({
        'current_model': current_model,
        'model_loaded': current_rag is not None
    })

@app.route('/api/admin/sync', methods=['POST'])
def sync_knowledge_base():
    """Sync knowledge base"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    global sync_status
    
    if sync_status['running']:
        return jsonify({'error': 'Sync already in progress'}), 400
    
    # Start sync in background thread
    thread = threading.Thread(target=sync_knowledge_base_async)
    thread.start()
    
    return jsonify({'success': True, 'message': 'Sync started'})

@app.route('/api/admin/sync_status', methods=['GET'])
def get_sync_status():
    """Get sync status"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    return jsonify(sync_status)


@app.route('/api/chat/stream', methods=['POST'])
def chat_stream():
    """Handle chat messages with streaming response"""
    global current_rag
    
    if not current_rag:
        return jsonify({'error': 'No model loaded. Please contact admin to load a model first.'}), 400
    
    data = request.get_json()
    message = data.get('message', '').strip()
    
    if not message:
        return jsonify({'error': 'Empty message'}), 400

    def generate():
        try:
            # Phase 1: Query processing
            yield f"data: {json.dumps({'phase': 'thinking', 'message': 'Processing your question...'})}\n\n"
            time.sleep(0.5)
            
            # Convert to English for retrieval only
            english_query = current_rag.rewrite_query(message)
            
            # Phase 2: Searching knowledge base
            yield f"data: {json.dumps({'phase': 'searching', 'message': 'Checking sources...'})}\n\n"
            time.sleep(0.5)
            
            search_results = current_rag.search_knowledge_base(english_query, top_k=3)
            documents = search_results['documents']
            sources = search_results['sources']
            
            # Phase 3: Generating answer
            yield f"data: {json.dumps({'phase': 'answering', 'message': 'Formulating response...'})}\n\n"
            
            
            if not documents:
                # Let Gemma naturally handle "no info" response
                prompt = f"""I don't have information about this topic in my knowledge base. Please respond to this user appropriately:

User asked: {message}

Response:"""
                
                response = current_rag._call_llm(prompt, max_tokens=100, temperature=0.3)
                full_response = response if response else "I don't have information on this topic. Please contact a human for help."
                
                # Stream the fallback response
                words = full_response.split()
                streamed_text = ""
                
                for word in words:
                    streamed_text += word + " "
                    yield f"data: {json.dumps({'phase': 'streaming', 'partial_response': streamed_text.strip()})}\n\n"
                    time.sleep(0.05)
                
                yield f"data: {json.dumps({'phase': 'complete', 'response': full_response, 'sources': [], 'context_used': 0})}\n\n"
                return
            
            # Generate answer with context - use original message, not English query
            context = "\n\n".join(documents)
            unique_sources = list(set(sources))
            
            answer_prompt = f"""You are a helpful campus assistant. Use the context below to answer the user's question.

Context:
{context}

User's question: {message}

Instructions:
- Use only the information from the context above
- If the context doesn't have enough information, say you don't have that information
- replay in user's original language, 
if it's in hindi reply in hindi, if in bengali reply in bengali, english if english, hindlish to hindlish....so on .
Answer:"""
            
            # Generate and stream the response
            full_response = current_rag._call_llm(answer_prompt, max_tokens=300, temperature=0.3)
            
            # Stream response word by word
            words = full_response.split()
            streamed_text = ""
            
            for word in words:
                streamed_text += word + " "
                yield f"data: {json.dumps({'phase': 'streaming', 'partial_response': streamed_text.strip()})}\n\n"
                time.sleep(0.05)
            
            # Send final complete response
            yield f"data: {json.dumps({'phase': 'complete', 'response': full_response, 'sources': unique_sources, 'context_used': len(documents)})}\n\n"
            
        except Exception as e:
            print(f"Chat stream error: {e}")
            yield f"data: {json.dumps({'phase': 'error', 'error': 'Sorry, I encountered an error processing your request.'})}\n\n"

    return Response(generate(), mimetype='text/plain', headers={'Cache-Control': 'no-cache'})



if __name__ == '__main__':
    print("🚀 Starting Campus Chat Server...")
    print("🌐 Access at: http://localhost:5000")
    print("🔧 Admin panel: http://localhost:5000/admin")
    app.run(debug=True, host='0.0.0.0', port=5000)
