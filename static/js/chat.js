var chatStudentId = '';
var chatSessionId = '';
var isWaiting = false;

function getEl(id) { return document.getElementById(id); }

function chatMessages() { return getEl('chatMessages'); }
function chatEmpty() { return getEl('chatEmpty'); }
function messageInput() { return getEl('messageInput'); }
function sendBtn() { return getEl('sendBtn'); }
function topicChips() { return getEl('topicChips'); }

function initChat(studentId, sessionId) {
    chatStudentId = studentId;
    if (sessionId) {
        chatSessionId = sessionId;
        loadHistory(sessionId);
    }
}

function loadHistory(sessionId) {
    fetch('/student/session/' + sessionId + '/messages')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.messages && data.messages.length > 0) {
                var empty = chatEmpty();
                var chips = topicChips();
                if (empty) empty.style.display = 'none';
                if (chips) chips.style.display = 'none';
                data.messages.forEach(function(msg) {
                    appendMessage(msg.role, msg.content);
                });
                scrollToBottom();
            }
        })
        .catch(function(e) { console.error('Failed to load history:', e); });
}

function appendMessage(role, content) {
    var empty = chatEmpty();
    var chips = topicChips();
    if (empty) empty.style.display = 'none';
    if (chips) chips.style.display = 'none';

    var container = chatMessages();
    if (!container) return;

    var div = document.createElement('div');
    div.className = 'message message-' + role;
    div.innerHTML = '<div class="message-bubble">' + formatContent(content) + '</div>';
    container.appendChild(div);
    renderMathInElement(div);
}

function appendTyping() {
    var container = chatMessages();
    if (!container) return;
    var div = document.createElement('div');
    div.className = 'message message-assistant';
    div.id = 'typingIndicator';
    div.innerHTML = '<div class="message-bubble typing-indicator"><div class="typing-dots"><span></span><span></span><span></span></div></div>';
    container.appendChild(div);
    scrollToBottom();
}

function removeTyping() {
    var el = getEl('typingIndicator');
    if (el) el.remove();
}

function formatContent(content) {
    // Split content into text parts and SVG blocks
    // Match ```svg blocks, or ``` blocks containing <svg tag
    var parts = [];
    var lastIndex = 0;
    var regex = /```(?:svg)?\s*\n?([\s\S]*?)```/g;
    var match;

    while ((match = regex.exec(content)) !== null) {
        // Text before this match → escape
        if (match.index > lastIndex) {
            parts.push({ type: 'text', html: escapeHtml(content.substring(lastIndex, match.index)) });
        }
        var code = match[1].trim();
        // Only treat as SVG if it contains <svg tag
        if (/<svg[\s\S]*<\/svg>/i.test(code)) {
            var safe = code.replace(/<script[\s\S]*?<\/script>/gi, '');
            parts.push({ type: 'svg', html: '<div class="svg-diagram">' + safe + '</div>' });
        } else {
            // Regular code block
            parts.push({ type: 'text', html: '<pre><code>' + escapeHtml(code) + '</code></pre>' });
        }
        lastIndex = match.index + match[0].length;
    }
    // Remaining text
    if (lastIndex < content.length) {
        parts.push({ type: 'text', html: escapeHtml(content.substring(lastIndex)) });
    }

    return parts.map(function(p) { return p.html; }).join('');
}

function escapeHtml(text) {
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/`([^`]+)`/g, '<code>$1</code>');
}

function sendMessage() {
    if (isWaiting) return;
    var input = messageInput();
    var btn = sendBtn();
    if (!input || !btn) return;

    var text = input.value.trim();
    if (!text) return;

    isWaiting = true;
    btn.disabled = true;
    input.value = '';

    appendMessage('user', text);
    appendTyping();
    scrollToBottom();

    fetch('/student/chat/' + chatStudentId + '/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            message: text,
            session_id: chatSessionId
        })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        removeTyping();
        if (data.error) {
            appendMessage('assistant', '抱歉，出现了一个错误：' + data.error);
        } else {
            appendMessage('assistant', data.response);
            if (!chatSessionId && data.session_id) {
                chatSessionId = data.session_id;
            }
        }
        scrollToBottom();
        isWaiting = false;
        btn.disabled = false;
        input.focus();
    })
    .catch(function(e) {
        removeTyping();
        appendMessage('assistant', '抱歉，连接出现了问题，请稍后重试。');
        console.error('Chat error:', e);
        isWaiting = false;
        btn.disabled = false;
        input.focus();
    });
}

function sendQuickMessage(text) {
    var input = messageInput();
    if (input) {
        input.value = text;
    }
    sendMessage();
}

function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

function scrollToBottom() {
    var container = chatMessages();
    if (container) {
        container.scrollTop = container.scrollHeight;
    }
}

// Set up event listeners when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    var input = messageInput();
    if (input) {
        input.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 120) + 'px';
        });
    }
});
