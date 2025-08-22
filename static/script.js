// Global state
let currentUser = null;
let authToken = null;
let currentSessionId = null;
let sessions = [];

// DOM elements
const authScreen = document.getElementById('auth-screen');
const chatScreen = document.getElementById('chat-screen');
const loginForm = document.getElementById('loginForm');
const registerForm = document.getElementById('registerForm');
const userEmail = document.getElementById('userEmail');
const questionInput = document.getElementById('questionInput');
const sendBtn = document.getElementById('sendBtn');
const messagesContainer = document.getElementById('messagesContainer');
const sessionsList = document.getElementById('sessionsList');
const fileInput = document.getElementById('fileInput');
const uploadArea = document.getElementById('uploadArea');
const uploadStatus = document.getElementById('uploadStatus');

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    checkAuthStatus();
    setupEventListeners();
    console.log('🎉 Medical RAG Chatbot loaded!');
});

// Authentication functions
function checkAuthStatus() {
    const token = localStorage.getItem('authToken');
    const user = localStorage.getItem('currentUser');

    if (token && user) {
        authToken = token;
        currentUser = JSON.parse(user);
        showChatInterface();
    } else {
        showAuthInterface();
    }
}

function showAuthInterface() {
    authScreen.style.display = 'flex';
    chatScreen.style.display = 'none';
    console.log('👤 Showing authentication screen');
}

function showChatInterface() {
    authScreen.style.display = 'none';
    chatScreen.style.display = 'flex';
    userEmail.textContent = currentUser.email;
    loadSessions();
    checkIndexStatus();
    console.log('💬 Showing chat interface for:', currentUser.email);
}

function showLogin() {
    document.getElementById('login-form').style.display = 'block';
    document.getElementById('register-form').style.display = 'none';
}

function showRegister() {
    document.getElementById('login-form').style.display = 'none';
    document.getElementById('register-form').style.display = 'block';
}

function logout() {
    localStorage.removeItem('authToken');
    localStorage.removeItem('currentUser');
    authToken = null;
    currentUser = null;
    currentSessionId = null;
    sessions = [];
    showAuthInterface();
    showToast('👋 Logged out successfully!', 'success');
}

// Event listeners
function setupEventListeners() {
    // Auth forms
    loginForm.addEventListener('submit', handleLogin);
    registerForm.addEventListener('submit', handleRegister);

    // Chat input
    questionInput.addEventListener('input', handleInputChange);
    questionInput.addEventListener('keydown', handleKeyPress);

    // File upload
    uploadArea.addEventListener('click', () => fileInput.click());
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    uploadArea.addEventListener('drop', handleFileDrop);
    fileInput.addEventListener('change', handleFileSelect);
}

// Auth handlers
async function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;

    console.log('🔐 Attempting login for:', email);

    try {
        const response = await fetch('/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email, password }),
        });

        const data = await response.json();

        if (response.ok) {
            authToken = data.access_token;
            currentUser = data.user;
            localStorage.setItem('authToken', authToken);
            localStorage.setItem('currentUser', JSON.stringify(currentUser));
            showChatInterface();
            showToast('✅ Login successful!', 'success');
        } else {
            showToast('❌ ' + (data.detail || 'Login failed'), 'error');
        }
    } catch (error) {
        console.error('Login error:', error);
        showToast('🌐 Network error during login', 'error');
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const email = document.getElementById('registerEmail').value;
    const password = document.getElementById('registerPassword').value;

    console.log('📝 Attempting registration for:', email);

    try {
        const response = await fetch('/auth/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email, password }),
        });

        const data = await response.json();

        if (response.ok) {
            authToken = data.access_token;
            currentUser = data.user;
            localStorage.setItem('authToken', authToken);
            localStorage.setItem('currentUser', JSON.stringify(currentUser));
            showChatInterface();
            showToast('🎉 Registration successful!', 'success');
        } else {
            showToast('❌ ' + (data.detail || 'Registration failed'), 'error');
        }
    } catch (error) {
        console.error('Registration error:', error);
        showToast('🌐 Network error during registration', 'error');
    }
}

// Chat functions
function handleInputChange() {
    const hasText = questionInput.value.trim().length > 0;
    sendBtn.disabled = !hasText || !authToken;
}

function handleKeyPress(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (!sendBtn.disabled) {
            sendMessage();
        }
    }
}

async function sendMessage() {
    const question = questionInput.value.trim();
    if (!question || !authToken) return;

    console.log('💬 Sending message:', question);

    // Clear input and disable
    questionInput.value = '';
    sendBtn.disabled = true;

    // Add user message to UI
    addMessage('user', question);

    // Show typing indicator
    const typingElement = addTypingIndicator();

    try {
        const response = await fetch('/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`,
            },
            body: JSON.stringify({
                question: question,
                session_id: currentSessionId,
                top_k: 4,
                provider: 'auto'
            }),
        });

        const data = await response.json();

        // Remove typing indicator
        removeTypingIndicator(typingElement);

        if (response.ok) {
            // Update current session ID
            currentSessionId = data.session_id;

            // Add assistant response
            addMessage('assistant', data.answer, data.citations);

            // Show limit warning if reached
            if (data.limit_reached) {
                showToast('⚠️ Session message limit reached. Start a new session to continue.', 'error');
            }

            // Refresh sessions list
            loadSessions();
        } else {
            addMessage('assistant', `❌ Error: ${data.detail || 'Failed to get response'}`);
            showToast('❌ ' + (data.detail || 'Failed to get response'), 'error');
        }
    } catch (error) {
        console.error('Send message error:', error);
        removeTypingIndicator(typingElement);
        addMessage('assistant', '🌐 Network error occurred. Please try again.');
        showToast('🌐 Network error occurred', 'error');
    }

    // Re-enable input
    handleInputChange();
}

function addMessage(role, content, citations = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = content;

    messageDiv.appendChild(contentDiv);

    // Add citations if available
    if (citations && citations.length > 0) {
        const citationsDiv = document.createElement('div');
        citationsDiv.className = 'citations';

        const citationsTitle = document.createElement('h4');
        citationsTitle.textContent = '📚 Sources:';
        citationsDiv.appendChild(citationsTitle);

        citations.forEach(citation => {
            const citationItem = document.createElement('div');
            citationItem.className = 'citation-item';
            citationItem.textContent = `📄 ${citation.source} (Page ${citation.page}) - Score: ${citation.score.toFixed(3)}`;
            citationsDiv.appendChild(citationItem);
        });

        messageDiv.appendChild(citationsDiv);
    }

    // Remove welcome message if it exists
    const welcomeMessage = messagesContainer.querySelector('.welcome-message');
    if (welcomeMessage) {
        welcomeMessage.remove();
    }

    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function addTypingIndicator() {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'typing-indicator';
    typingDiv.innerHTML = `
        <span>🤖 AI is thinking</span>
        <div class="typing-dots">
            <span></span>
            <span></span>
            <span></span>
        </div>
    `;

    messagesContainer.appendChild(typingDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    return typingDiv;
}

function removeTypingIndicator(element) {
    if (element && element.parentNode) {
        element.parentNode.removeChild(element);
    }
}

// Session management
async function loadSessions() {
    try {
        const response = await fetch('/sessions', {
            headers: {
                'Authorization': `Bearer ${authToken}`,
            },
        });

        if (response.ok) {
            sessions = await response.json();
            renderSessions();
        }
    } catch (error) {
        console.error('Failed to load sessions:', error);
    }
}

function renderSessions() {
    sessionsList.innerHTML = '';

    if (sessions.length === 0) {
        sessionsList.innerHTML = '<div style="text-align: center; color: #718096; padding: 1rem;">No sessions yet</div>';
        return;
    }

    sessions.forEach(session => {
        const sessionDiv = document.createElement('div');
        sessionDiv.className = `session-item ${currentSessionId === session.id ? 'active' : ''}`;
        sessionDiv.onclick = () => loadSession(session.id);

        sessionDiv.innerHTML = `
            <div class="session-title">${session.title}</div>
            <div class="session-time">${new Date(session.updated_at).toLocaleDateString()}</div>
        `;

        sessionsList.appendChild(sessionDiv);
    });
}

async function createNewSession() {
    console.log('➕ Creating new session');

    try {
        const response = await fetch('/sessions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`,
            },
            body: JSON.stringify({ title: 'New chat' }),
        });

        if (response.ok) {
            const newSession = await response.json();
            currentSessionId = newSession.id;

            // Clear messages
            clearMessages();

            // Reload sessions
            loadSessions();
            showToast('✅ New session created!', 'success');
        }
    } catch (error) {
        console.error('Failed to create new session:', error);
        showToast('❌ Failed to create new session', 'error');
    }
}

async function loadSession(sessionId) {
    console.log('📂 Loading session:', sessionId);

    try {
        const response = await fetch(`/sessions/${sessionId}`, {
            headers: {
                'Authorization': `Bearer ${authToken}`,
            },
        });

        if (response.ok) {
            const sessionData = await response.json();
            currentSessionId = sessionId;

            // Clear current messages
            clearMessages();

            // Load session messages
            sessionData.messages.forEach(message => {
                addMessage(message.role, message.content, message.citations);
            });

            // Update UI
            renderSessions();
        }
    } catch (error) {
        console.error('Failed to load session:', error);
        showToast('❌ Failed to load session', 'error');
    }
}

function clearMessages() {
    messagesContainer.innerHTML = `
        <div class="welcome-message">
            <h2>🤖 Welcome to Medical RAG Chatbot</h2>
            <p>Upload PDF documents and ask questions about medical information.</p>
            <p>Your questions will be answered based on the uploaded documents.</p>
        </div>
    `;
}

// File upload functions
function handleDragOver(e) {
    e.preventDefault();
    uploadArea.classList.add('dragover');
}

function handleDragLeave(e) {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
}

function handleFileDrop(e) {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    const files = Array.from(e.dataTransfer.files);
    uploadFiles(files);
}

function handleFileSelect(e) {
    const files = Array.from(e.target.files);
    uploadFiles(files);
}

async function uploadFiles(files) {
    const pdfFiles = files.filter(file => file.type === 'application/pdf');

    if (pdfFiles.length === 0) {
        showToast('❌ Please select PDF files only', 'error');
        return;
    }

    console.log('📄 Uploading', pdfFiles.length, 'PDF files');

    uploadStatus.innerHTML = '<div class="upload-info">📤 Uploading files...</div>';
    uploadArea.classList.add('loading');

    try {
        for (let file of pdfFiles) {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch('/upload', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${authToken}`,
                },
                body: formData,
            });

            const data = await response.json();

            if (response.ok) {
                uploadStatus.innerHTML = `<div class="upload-success">✅ ${file.name} uploaded successfully!</div>`;
            } else {
                uploadStatus.innerHTML = `<div class="upload-error">❌ Failed to upload ${file.name}</div>`;
            }
        }

        // Check index status after upload
        checkIndexStatus();
        showToast(`🎉 ${pdfFiles.length} file(s) uploaded successfully!`, 'success');

    } catch (error) {
        console.error('Upload error:', error);
        uploadStatus.innerHTML = '<div class="upload-error">❌ Upload failed due to network error</div>';
        showToast('❌ Upload failed', 'error');
    } finally {
        uploadArea.classList.remove('loading');
        fileInput.value = ''; // Clear file input
    }
}

async function checkIndexStatus() {
    try {
        const response = await fetch('/health');
        const data = await response.json();

        const indexStatus = document.getElementById('indexStatus');
        if (data.index_exists) {
            indexStatus.textContent = '📚 Knowledge base ready';
            indexStatus.className = 'index-ready';
            sendBtn.disabled = !questionInput.value.trim();
        } else {
            indexStatus.textContent = '⚠️ No documents uploaded yet';
            indexStatus.className = 'index-missing';
            sendBtn.disabled = true;
        }
    } catch (error) {
        console.error('Failed to check index status:', error);
    }
}

// Utility functions
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type}`;
    toast.classList.add('show');

    setTimeout(() => {
        toast.classList.remove('show');
    }, 4000);
}

// Auto-resize textarea
if (questionInput) {
    questionInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 120) + 'px';
    });
}