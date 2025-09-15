document.addEventListener('DOMContentLoaded', function() {
    const messageInput = document.getElementById('messageInput');
    const sendButton = document.getElementById('sendButton');
    const chatMessages = document.getElementById('chatMessages');
    
    // Admin elements
    const adminPassword = document.getElementById('adminPassword');
    const loginButton = document.getElementById('loginButton');
    const modelSelect = document.getElementById('modelSelect');
    const loadModelBtn = document.getElementById('loadModelBtn');
    const syncBtn = document.getElementById('syncBtn');

    // Chat functionality
    if (sendButton && messageInput) {
        sendButton.addEventListener('click', sendMessage);
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }

    // Admin functionality (unchanged)
    if (loginButton && adminPassword) {
        loginButton.addEventListener('click', adminLogin);
        adminPassword.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                adminLogin();
            }
        });
    }

    if (modelSelect) {
        modelSelect.addEventListener('change', function() {
            if (loadModelBtn) {
                loadModelBtn.disabled = !this.value;
            }
        });
    }

    if (loadModelBtn) {
        loadModelBtn.addEventListener('click', loadModel);
    }

    if (syncBtn) {
        syncBtn.addEventListener('click', syncKnowledgeBase);
        setInterval(checkSyncStatus, 2000);
    }

    function sendMessage() {
        const message = messageInput.value.trim();
        if (!message) return;

        // Add user message to chat
        addMessage(message, 'user');
        messageInput.value = '';
        sendButton.disabled = true;

        // Start streaming chat
        startStreamingChat(message);
    }

    function startStreamingChat(message) {
        let statusElement = null;
        let responseElement = null;
        let currentResponse = '';

        // Create EventSource for streaming
        fetch('/api/chat/stream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: message })
        })
        .then(response => {
            const reader = response.body.getReader();
            
            function readStream() {
                return reader.read().then(({ done, value }) => {
                    if (done) {
                        sendButton.disabled = false;
                        if (statusElement) {
                            statusElement.remove();
                        }
                        return;
                    }

                    const chunk = new TextDecoder().decode(value);
                    const lines = chunk.split('\n');
                    
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                handleStreamData(data);
                            } catch (e) {
                                console.error('Parse error:', e);
                            }
                        }
                    }

                    return readStream();
                });
            }

            return readStream();
        })
        .catch(error => {
            console.error('Streaming error:', error);
            if (statusElement) {
                statusElement.remove();
            }
            addMessage('Connection error. Please try again.', 'bot');
            sendButton.disabled = false;
        });

        function handleStreamData(data) {
            switch (data.phase) {
                case 'thinking':
                    statusElement = addAnimatedStatus('🤔 Processing your question...', 'thinking');
                    break;
                    
                case 'searching':
                    if (statusElement) {
                        updateAnimatedStatus(statusElement, '🔍 Checking sources...', 'searching');
                    }
                    break;
                    
                case 'answering':
                    if (statusElement) {
                        updateAnimatedStatus(statusElement, '✍️ Formulating response...', 'answering');
                    }
                    break;
                    
                case 'streaming':
                    if (statusElement) {
                        statusElement.remove();
                        statusElement = null;
                    }
                    
                    if (!responseElement) {
                        responseElement = addStreamingMessage('', 'bot');
                    }
                    
                    updateStreamingMessage(responseElement, data.partial_response);
                    break;
                    
                case 'complete':
                    if (statusElement) {
                        statusElement.remove();
                    }
                    
                    if (responseElement) {
                        finalizeStreamingMessage(responseElement, data.response, data.sources);
                    } else {
                        // Fallback if no streaming occurred
                        let response = data.response;
                        if (data.sources && data.sources.length > 0) {
                            response += '\n\n📚 Sources: ' + data.sources.join(', ');
                        }
                        addMessage(response, 'bot');
                    }
                    
                    sendButton.disabled = false;
                    break;
                    
                case 'error':
                    if (statusElement) {
                        statusElement.remove();
                    }
                    addMessage(data.error, 'bot');
                    sendButton.disabled = false;
                    break;
            }
        }
    }

    function addAnimatedStatus(text, phase) {
        const statusDiv = document.createElement('div');
        statusDiv.className = `message bot-message status-message ${phase}`;
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar bot-avatar';
        avatar.innerHTML = '<i class="fas fa-robot"></i>';
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        const bubble = document.createElement('div');
        bubble.className = 'message-bubble bot-bubble status-bubble';
        bubble.innerHTML = `${text} <span class="wave-animation">⚡</span>`;
        
        messageContent.appendChild(bubble);
        statusDiv.appendChild(avatar);
        statusDiv.appendChild(messageContent);
        
        chatMessages.appendChild(statusDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        return statusDiv;
    }

    function updateAnimatedStatus(element, text, phase) {
        const bubble = element.querySelector('.message-bubble');
        bubble.innerHTML = `${text} <span class="wave-animation">⚡</span>`;
        element.className = `message bot-message status-message ${phase}`;
    }

    function addStreamingMessage(content, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message streaming-message`;

        const avatar = document.createElement('div');
        avatar.className = `message-avatar ${sender}-avatar`;
        avatar.innerHTML = sender === 'bot' ? '<i class="fas fa-robot"></i>' : '<i class="fas fa-user"></i>';

        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';

        const bubble = document.createElement('div');
        bubble.className = `message-bubble ${sender}-bubble`;
        bubble.style.whiteSpace = 'pre-wrap';
        bubble.textContent = content;

        messageContent.appendChild(bubble);
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(messageContent);

        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        return messageDiv;
    }

    function updateStreamingMessage(element, content) {
        const bubble = element.querySelector('.message-bubble');
        bubble.textContent = content;
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function finalizeStreamingMessage(element, finalContent, sources) {
        const bubble = element.querySelector('.message-bubble');
        let content = finalContent;
        
        if (sources && sources.length > 0) {
            content += '\n\n📚 Sources: ' + sources.join(', ');
        }
        
        bubble.textContent = content;
        element.classList.remove('streaming-message');
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function addMessage(content, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;

        const avatar = document.createElement('div');
        avatar.className = `message-avatar ${sender}-avatar`;
        avatar.innerHTML = sender === 'bot' ? '<i class="fas fa-robot"></i>' : '<i class="fas fa-user"></i>';

        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';

        const bubble = document.createElement('div');
        bubble.className = `message-bubble ${sender}-bubble`;
        bubble.style.whiteSpace = 'pre-wrap';
        bubble.textContent = content;

        messageContent.appendChild(bubble);

        if (sender === 'user') {
            messageDiv.appendChild(messageContent);
            messageDiv.appendChild(avatar);
        } else {
            messageDiv.appendChild(avatar);
            messageDiv.appendChild(messageContent);
        }

        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Admin functions (unchanged from before)
    function adminLogin() {
        const password = adminPassword.value;
        
        fetch('/admin/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ password: password })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                location.reload();
            } else {
                alert('Invalid password');
                adminPassword.value = '';
            }
        })
        .catch(error => {
            alert('Login error');
        });
    }

    function loadModel() {
        const modelName = modelSelect.value;
        if (!modelName) return;

        loadModelBtn.disabled = true;
        loadModelBtn.innerHTML = '<i class="fas fa-spinner spinning"></i> Loading...';

        fetch('/api/admin/load_model', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ model_name: modelName })
        })
        .then(response => response.json())
        .then(data => {
            updateModelStatus(data.success ? 'Loading model...' : data.error, data.success ? 'info' : 'error');
            
            if (data.success) {
                const checkInterval = setInterval(() => {
                    fetch('/api/admin/model_status')
                        .then(response => response.json())
                        .then(statusData => {
                            if (statusData.model_loaded && statusData.current_model === modelName) {
                                updateModelStatus(`Model "${modelName}" loaded successfully!`, 'success');
                                clearInterval(checkInterval);
                            }
                        });
                }, 2000);
            }
        })
        .catch(error => {
            updateModelStatus('Error loading model', 'error');
        })
        .finally(() => {
            loadModelBtn.disabled = false;
            loadModelBtn.innerHTML = '<i class="fas fa-download"></i> Load Model';
        });
    }

    function syncKnowledgeBase() {
        syncBtn.disabled = true;
        syncBtn.className = 'sync-btn syncing';
        syncBtn.innerHTML = '<i class="fas fa-sync-alt spinning"></i> Syncing...';

        fetch('/api/admin/sync', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateSyncStatus('Sync started...', 'info');
            } else {
                updateSyncStatus(data.error, 'error');
                resetSyncButton();
            }
        })
        .catch(error => {
            updateSyncStatus('Sync error', 'error');
            resetSyncButton();
        });
    }

    function checkSyncStatus() {
        if (!syncBtn || syncBtn.disabled === false) return;

        fetch('/api/admin/sync_status')
            .then(response => response.json())
            .then(data => {
                if (data.running) {
                    return;
                } else if (data.completed) {
                    syncBtn.className = 'sync-btn completed';
                    syncBtn.innerHTML = '<i class="fas fa-check"></i> Sync Complete';
                    updateSyncStatus('Knowledge base synced successfully!', 'success');
                    
                    setTimeout(() => {
                        resetSyncButton();
                    }, 3000);
                } else if (data.error) {
                    updateSyncStatus('Sync failed: ' + data.error, 'error');
                    resetSyncButton();
                }
            })
            .catch(error => {
                // Don't show error for status checks
            });
    }

    function resetSyncButton() {
        if (syncBtn) {
            syncBtn.disabled = false;
            syncBtn.className = 'sync-btn';
            syncBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Sync Documents';
        }
    }

    function updateModelStatus(message, type) {
        const statusDiv = document.getElementById('modelStatus');
        if (statusDiv) {
            statusDiv.textContent = message;
            statusDiv.className = `status-display ${type}`;
        }
    }

    function updateSyncStatus(message, type) {
        const statusDiv = document.getElementById('syncStatus');
        if (statusDiv) {
            statusDiv.textContent = message;
            statusDiv.className = `status-display ${type}`;
        }
    }
});
