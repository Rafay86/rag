const apiBase = (window.location.hostname === 'localhost') ? 'http://localhost:8080' : '';

// DOM Elements
const chatForm = document.getElementById('chat-form');
const messageInput = document.getElementById('message-input');
const chatWindow = document.getElementById('chat-window');
const sessionEl = document.getElementById('session-id');
const resetSessionBtn = document.getElementById('reset-session');
const fileInput = document.getElementById('file-upload');
const uploadBtn = document.getElementById('upload-btn');
const uploadStatus = document.getElementById('upload-status');
const documentList = document.getElementById('document-list');

// Session Management
function makeSessionId() {
  return 'sess-' + ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
    (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
  );
}

let sessionId = localStorage.getItem('saama_session_id');
if (!sessionId) {
  sessionId = makeSessionId();
  localStorage.setItem('saama_session_id', sessionId);
}
sessionEl.textContent = sessionId.substring(0, 12) + '...';

resetSessionBtn.addEventListener('click', () => {
  sessionId = makeSessionId();
  localStorage.setItem('saama_session_id', sessionId);
  sessionEl.textContent = sessionId.substring(0, 12) + '...';
  chatWindow.innerHTML = ''; // Clear chat
  appendSystemMessage('New session started.');
});

// Chat Logic
function appendMessage(text, who='bot', highlightedContexts = []) {
  const el = document.createElement('div');
  el.className = 'message ' + (who === 'user' ? 'user' : 'bot');
  el.innerText = text;
  
  if (who === 'bot' && Array.isArray(highlightedContexts) && highlightedContexts.length) {
    const meta = document.createElement('div');
    meta.className = 'meta';
    meta.innerText = `${highlightedContexts.length} references found. `;
    
    const toggleBtn = document.createElement('button');
    toggleBtn.className = 'context-toggle';
    toggleBtn.textContent = 'Show details';
    
    const list = document.createElement('div');
    list.className = 'context-list';
    list.style.display = 'none';

    highlightedContexts.forEach((ctx) => {
      const item = document.createElement('div');
      item.className = 'context-item';
      
      const header = document.createElement('div');
      header.className = 'context-header';
      header.innerText = `${ctx.source || 'Unknown Source'} (Page ${ctx.page || '?'})`;
      
      const body = document.createElement('div');
      body.className = 'context-body';
      body.innerText = ctx.context_text || '';
      
      item.appendChild(header);
      item.appendChild(body);
      list.appendChild(item);
    });

    toggleBtn.addEventListener('click', () => {
      const isHidden = list.style.display === 'none';
      list.style.display = isHidden ? 'flex' : 'none';
      toggleBtn.textContent = isHidden ? 'Hide details' : 'Show details';
    });

    meta.appendChild(toggleBtn);
    el.appendChild(meta);
    el.appendChild(list);
  }

  chatWindow.appendChild(el);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

function appendSystemMessage(text) {
  const el = document.createElement('div');
  el.className = 'message bot';
  el.style.opacity = '0.8';
  el.style.fontStyle = 'italic';
  el.innerText = text;
  chatWindow.appendChild(el);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

async function postQuestion(question) {
  appendMessage(question, 'user');

  const payload = {
    session_id: sessionId,
    question: question,
    history: [] 
  };

  // Add temporary loading indicator
  const loadingId = 'loading-' + Date.now();
  const loadingEl = document.createElement('div');
  loadingEl.id = loadingId;
  loadingEl.className = 'message bot';
  loadingEl.innerText = 'Thinking...';
  chatWindow.appendChild(loadingEl);
  chatWindow.scrollTop = chatWindow.scrollHeight;

  try {
    const res = await fetch(`${apiBase}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    document.getElementById(loadingId).remove();

    if (!res.ok) {
      const err = await res.text();
      appendSystemMessage('Error: ' + err);
      return;
    }

    const data = await res.json();
    const answer = data.answer || data;
    const contexts = data.highlighted_contexts || [];

    appendMessage(answer, 'bot', contexts);
  } catch (err) {
    document.getElementById(loadingId)?.remove();
    appendSystemMessage('Network error: ' + (err.message || err));
  }
}

chatForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const text = messageInput.value.trim();
  if (!text) return;
  messageInput.value = '';
  postQuestion(text);
});

// File Upload Logic
fileInput.addEventListener('change', () => {
  if (fileInput.files.length > 0) {
    uploadBtn.disabled = false;
    document.querySelector('.file-label span').innerText = `${fileInput.files.length} file(s) selected`;
  } else {
    uploadBtn.disabled = true;
    document.querySelector('.file-label span').innerText = 'Choose files...';
  }
});

uploadBtn.addEventListener('click', async () => {
  const files = fileInput.files;
  if (!files.length) return;

  const formData = new FormData();
  for (let i = 0; i < files.length; i++) {
    formData.append('file', files[i]);
  }

  uploadBtn.disabled = true;
  uploadBtn.innerText = 'Uploading...';
  uploadStatus.innerText = '';

  try {
    const res = await fetch(`${apiBase}/upload-doc`, {
      method: 'POST',
      body: formData
    });

    const result = await res.json();

    if (res.ok) {
      uploadStatus.innerText = `Uploaded ${result.summary.success} file(s).`;
      uploadStatus.className = 'status-success';
      fetchDocuments(); // Refresh list
      fileInput.value = '';
      document.querySelector('.file-label span').innerText = 'Choose files...';
    } else {
      uploadStatus.innerText = 'Upload failed.';
      uploadStatus.className = 'status-error';
    }
  } catch (err) {
    uploadStatus.innerText = 'Error: ' + err.message;
    uploadStatus.className = 'status-error';
  } finally {
    uploadBtn.disabled = true; // Reset state
    uploadBtn.innerText = 'Upload';
  }
});

// Document Listing Logic
async function fetchDocuments() {
  try {
    const res = await fetch(`${apiBase}/list-docs`);
    if (!res.ok) return;
    
    const docs = await res.json();
    renderDocumentList(docs);
  } catch (err) {
    console.error('Failed to fetch documents:', err);
  }
}

function renderDocumentList(docs) {
  documentList.innerHTML = '';
  
  if (!docs || docs.length === 0) {
    documentList.innerHTML = '<div class="empty-state">No documents indexed.</div>';
    return;
  }

  docs.forEach(doc => {
    const item = document.createElement('div');
    item.className = 'doc-item';
    
    const name = document.createElement('span');
    name.className = 'doc-name';
    name.innerText = doc.filename;
    name.title = doc.filename;
    
    item.appendChild(name);
    documentList.appendChild(item);
  });
}

// Initial Load
fetchDocuments();