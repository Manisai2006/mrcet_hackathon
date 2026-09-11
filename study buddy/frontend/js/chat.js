// Interactive AI Tutor Chat Engine
let currentConversationId = null;

document.addEventListener('DOMContentLoaded', () => {
    // Read conversation ID from URL params if present
    const urlParams = new URLSearchParams(window.location.search);
    const idParam = urlParams.get('id');
    if (idParam) {
        currentConversationId = parseInt(idParam);
    }

    // Set initial profile language preference
    const user = API.getUser();
    if (user && user.profile && user.profile.preferred_language) {
        const langSelect = document.getElementById('languageSelect');
        if (langSelect && !idParam) {
            langSelect.value = user.profile.preferred_language;
        }
    }

    // Load conversation history for sidebar
    loadSidebarHistory();

    // Load user's uploaded documents into select dropdown
    loadDocumentDropdown();

    // If existing conversation, load messages
    if (currentConversationId) {
        loadConversation(currentConversationId);
    }

    // New Chat Button Handler
    const btnNewChat = document.getElementById('btnNewChat');
    if (btnNewChat) {
        btnNewChat.addEventListener('click', () => {
            startNewChat();
        });
    }

    // Mode Selector Handler
    const modeSelect = document.getElementById('tutorModeSelect');
    if (modeSelect) {
        modeSelect.addEventListener('change', (e) => {
            document.getElementById('activeModeBadge').innerText = e.target.value;
        });
    }

    // Sample Prompt Click Handlers
    document.querySelectorAll('.sample-prompt').forEach(btn => {
        btn.addEventListener('click', () => {
            const prompt = btn.getAttribute('data-prompt');
            document.getElementById('chatInput').value = prompt;
            document.getElementById('chatForm').dispatchEvent(new Event('submit'));
        });
    });

    // Chat Form Submission
    const chatForm = document.getElementById('chatForm');
    if (chatForm) {
        chatForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const input = document.getElementById('chatInput');
            const prompt = input.value.trim();
            if (!prompt) return;

            const language = document.getElementById('languageSelect').value;
            const mode = document.getElementById('tutorModeSelect').value;
            const docVal = document.getElementById('documentSelect').value;
            
            let isStrict = false;
            let docId = null;
            if (docVal === 'STRICT_ALL') {
                isStrict = true;
            } else if (docVal) {
                docId = parseInt(docVal);
            }

            // Clear input
            input.value = '';

            // Hide empty state
            const emptyState = document.getElementById('emptyChatState');
            if (emptyState) emptyState.remove();

            // Append Student Bubble
            appendMessage('student', prompt);

            // Show Typing Indicator
            showTypingIndicator();

            try {
                const response = await API.request('/chat', {
                    method: 'POST',
                    body: JSON.stringify({
                        prompt: prompt,
                        conversation_id: currentConversationId,
                        tutor_mode: mode,
                        selected_language: language,
                        selected_document_id: docId,
                        strict_mode: isStrict
                    })
                });

                // Update current conversation ID if newly created
                if (!currentConversationId && response.conversation_id) {
                    currentConversationId = response.conversation_id;
                    history.pushState(null, '', `chat.html?id=${currentConversationId}`);
                    loadSidebarHistory();
                }

                // Append Assistant Bubble
                appendMessage('assistant', response.content);
            } catch (err) {
                showToast(err.message || 'Failed to generate tutor response.', 'error');
                appendMessage('assistant', '⚠️ *Sorry, I ran into an error generating the explanation. Please try asking again!*');
            } finally {
                hideTypingIndicator();
            }
        });
    }
});

function startNewChat() {
    currentConversationId = null;
    history.pushState(null, '', 'chat.html');
    document.getElementById('chatTitle').innerText = 'New Doubt Session';
    const messagesDiv = document.getElementById('chatMessages');
    messagesDiv.innerHTML = `
        <div class="text-center my-auto py-5" id="emptyChatState">
            <div class="fs-1 text-primary mb-3"><i class="fa-solid fa-robot"></i></div>
            <h3 class="fw-bold mb-2">Hello! I am your AI Tutor.</h3>
            <p class="text-secondary max-w-lg mx-auto mb-4">
                Ask any school doubt in <strong>Telugu</strong>, <strong>Hindi</strong>, or <strong>English</strong>. I will guide you step-by-step to help you truly understand!
            </p>
        </div>
    `;
    loadSidebarHistory();
}

async function loadDocumentDropdown() {
    const docSelect = document.getElementById('documentSelect');
    if (!docSelect) return;

    try {
        const documents = await API.request('/documents');
        docSelect.innerHTML = '<option value="">🌐 General AI Knowledge</option>';
        if (documents && documents.length > 0) {
            documents.forEach(doc => {
                docSelect.innerHTML += `<option value="${doc.id}">📄 PDF: ${doc.filename} (${doc.page_count}p)</option>`;
            });
        }

        // Auto-select if doc_id URL parameter present
        const urlParams = new URLSearchParams(window.location.search);
        const docIdParam = urlParams.get('doc_id');
        if (docIdParam) {
            docSelect.value = docIdParam;
        }
    } catch (e) {
        console.error('Failed to load document dropdown options:', e);
    }
}

async function loadSidebarHistory() {
    try {
        const conversations = await API.request('/chat/history');
        const desktopList = document.getElementById('sidebarHistoryList');
        const mobileList = document.getElementById('mobileSidebarHistoryList');

        const html = conversations.map(c => `
            <div class="history-item ${c.id === currentConversationId ? 'active' : ''}" onclick="loadConversation(${c.id})">
                <div class="text-truncate" style="max-width: 190px;">
                    <i class="fa-solid fa-message me-2 small text-primary"></i>${c.title}
                </div>
            </div>
        `).join('');

        if (desktopList) desktopList.innerHTML = html;
        if (mobileList) mobileList.innerHTML = html;
    } catch (e) {
        console.error('Failed to load sidebar history:', e);
    }
}

async function loadConversation(id) {
    currentConversationId = id;
    history.pushState(null, '', `chat.html?id=${id}`);
    
    try {
        const detail = await API.request(`/chat/${id}`);
        document.getElementById('chatTitle').innerText = detail.title;
        document.getElementById('languageSelect').value = detail.selected_language;
        document.getElementById('tutorModeSelect').value = detail.tutor_mode;
        document.getElementById('activeModeBadge').innerText = detail.tutor_mode;

        const messagesDiv = document.getElementById('chatMessages');
        messagesDiv.innerHTML = '';

        detail.messages.forEach(msg => {
            appendMessage(msg.role, msg.content);
        });

        loadSidebarHistory();
    } catch (e) {
        showToast('Failed to load conversation details.', 'error');
    }
}

function appendMessage(role, content) {
    const messagesDiv = document.getElementById('chatMessages');
    const bubble = document.createElement('div');
    bubble.className = `message-bubble ${role === 'student' ? 'message-student' : 'message-assistant'}`;
    
    // Process basic Markdown bold/line breaks for clean rendering
    let formattedText = content
        .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n/g, '<br>');

    const currentLang = document.getElementById('languageSelect') ? document.getElementById('languageSelect').value : 'English';

    bubble.innerHTML = `
        <div class="d-flex align-items-center gap-2 mb-1 opacity-75 small">
            <i class="fa-solid ${role === 'student' ? 'fa-user' : 'fa-graduation-cap'}"></i>
            <span class="fw-bold">${role === 'student' ? 'You' : 'AI Tutor'}</span>
        </div>
        <div>${formattedText}</div>
    `;

    if (role === 'assistant') {
        const actionDiv = document.createElement('div');
        actionDiv.className = 'mt-2 pt-2 border-top border-secondary border-opacity-10 d-flex align-items-center gap-2';
        
        const listenBtn = document.createElement('button');
        listenBtn.className = 'btn btn-outline-primary btn-sm rounded-pill btn-tts-listen py-1 px-3';
        listenBtn.setAttribute('data-lang', currentLang);
        listenBtn.setAttribute('data-raw-text', content);
        listenBtn.setAttribute('aria-label', 'Listen to AI response');
        listenBtn.innerHTML = '<i class="fa-solid fa-volume-high"></i> Listen';
        listenBtn.addEventListener('click', function() {
            if (typeof speakText === 'function') {
                speakText(content, currentLang, listenBtn);
            } else {
                console.error('[TTS] speakText is not defined');
            }
        });
        
        actionDiv.appendChild(listenBtn);
        bubble.appendChild(actionDiv);
    }

    messagesDiv.appendChild(bubble);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    // Trigger auto-speak if enabled
    if (role === 'assistant' && typeof autoSpeakEnabled !== 'undefined' && autoSpeakEnabled) {
        if (typeof speakText === 'function') {
            speakText(content, currentLang);
        }
    }
}

function showTypingIndicator() {
    const messagesDiv = document.getElementById('chatMessages');
    const indicator = document.createElement('div');
    indicator.id = 'activeTypingIndicator';
    indicator.className = 'typing-indicator align-self-start my-2';
    indicator.innerHTML = `
        <span class="me-2">AI is thinking</span>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
    `;
    messagesDiv.appendChild(indicator);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function hideTypingIndicator() {
    const indicator = document.getElementById('activeTypingIndicator');
    if (indicator) indicator.remove();
}
