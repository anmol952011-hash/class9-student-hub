
const $ = (id) => document.getElementById(id);

function showError(elId, msg) {
    const el = $(elId);
    el.textContent = msg;
    el.classList.remove('hidden');
}

function hideError(elId) {
    $(elId).classList.add('hidden');
}


async function checkAuth() {
    try {
        const res = await fetch('/api/me');
        const data = await res.json();
        if (data.logged_in) {
            $('email-display').textContent = data.email;
            $('user-info').classList.remove('hidden');
            $('guest-buttons').classList.add('hidden');
        } else {
            $('user-info').classList.add('hidden');
            $('guest-buttons').classList.remove('hidden');
        }
    } catch (e) {
        console.error("Auth check failed:", e);
    }
}
checkAuth();


function openModal(id) { $(id).classList.remove('hidden'); }
function closeModal(id) { $(id).classList.add('hidden'); }


document.querySelectorAll('[data-close]').forEach(btn => {
    btn.addEventListener('click', () => closeModal(btn.dataset.close));
});


document.querySelectorAll('[data-open]').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        if (link.dataset.close) closeModal(link.dataset.close);
        openModal(link.dataset.open);
    });
});


document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) overlay.classList.add('hidden');
    });
});


$('btn-show-login').addEventListener('click', () => {
    hideError('login-error');
    openModal('login-modal');
});
$('btn-show-signup').addEventListener('click', () => {
    hideError('signup-error');
    openModal('signup-modal');
});


$('btn-login-submit').addEventListener('click', async () => {
    hideError('login-error');
    const email = $('login-email').value.trim();
    const password = $('login-password').value;

    if (!email || !password) {
        return showError('login-error', 'Please fill in both fields.');
    }

    const btn = $('btn-login-submit');
    btn.disabled = true;
    btn.textContent = 'Logging in...';

    try {
        const res = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (res.ok) {
            closeModal('login-modal');
            $('login-email').value = '';
            $('login-password').value = '';
            await checkAuth();
        } else {
            showError('login-error', data.error || 'Login failed.');
        }
    } catch (e) {
        showError('login-error', 'Network error. Try again.');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Login';
    }
});
$('btn-signup-submit').addEventListener('click', async () => {
    hideError('signup-error');
    const email = $('signup-email').value.trim();
    const password = $('signup-password').value;

    if (!email || !password) {
        return showError('signup-error', 'Please fill in both fields.');
    }

    const btn = $('btn-signup-submit');
    btn.disabled = true;
    btn.textContent = 'Creating account...';

    try {
        const res = await fetch('/api/signup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (res.ok) {
            closeModal('signup-modal');
            $('signup-email').value = '';
            $('signup-password').value = '';
            await checkAuth();
        } else {
            showError('signup-error', data.error || 'Signup failed.');
        }
    } catch (e) {
        showError('signup-error', 'Network error. Try again.');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Sign Up';
    }
});

$('btn-logout').addEventListener('click', async () => {
    await fetch('/api/logout', { method: 'POST' });
    await checkAuth();
});

$('btn-summarize').addEventListener('click', async () => {
    const text = $('summary-input').value;
    const outputDiv = $('summary-output');
    const btn = $('btn-summarize');

    if (!text || text.trim().length < 20) {
        return alert("Please paste at least a paragraph of text.");
    }

    outputDiv.classList.remove('hidden');
    outputDiv.textContent = "⏳ Generating summary, please wait...";
    btn.disabled = true;

    try {
        const res = await fetch('/api/summarize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });
        const data = await res.json();
        outputDiv.textContent = res.ok ? data.result : "Error: " + (data.error || "Unknown");
    } catch (e) {
        outputDiv.textContent = "Network error. Please try again.";
    } finally {
        btn.disabled = false;
    }
});

$('btn-mocktest').addEventListener('click', async () => {
    const topic = $('mocktest-input').value;
    const outputDiv = $('mocktest-output');
    const btn = $('btn-mocktest');

    if (!topic) return alert("Please enter a topic.");

    outputDiv.classList.remove('hidden');
    outputDiv.textContent = "⏳ Generating mock test...";
    btn.disabled = true;

    try {
        const res = await fetch('/api/mocktest', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic })
        });
        const data = await res.json();
        outputDiv.textContent = res.ok ? data.result : "Error: " + (data.error || "Unknown");
    } catch (e) {
        outputDiv.textContent = "Network error. Please try again.";
    } finally {
        btn.disabled = false;
    }
});

$('btn-ask').addEventListener('click', async () => {
    const question = $('question-input').value;
    const outputDiv = $('question-output');
    const btn = $('btn-ask');

    if (!question) return alert("Please type a question.");

    outputDiv.classList.remove('hidden');
    outputDiv.textContent = "⏳ Thinking...";
    btn.disabled = true;

    try {
        const res = await fetch('/api/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question })
        });
        const data = await res.json();
        outputDiv.textContent = res.ok ? data.result : "Error: " + (data.error || "Unknown");
    } catch (e) {
        outputDiv.textContent = "Network error. Please try again.";
    } finally {
        btn.disabled = false;
    }
});

$('question-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') $('btn-ask').click();
});

$('fab-ask').addEventListener('click', () => {
    openModal('fab-modal');
    $('fab-input').focus();
});

function appendChat(text, cls) {
    const msg = document.createElement('div');
    msg.className = `chat-msg ${cls}`;
    msg.textContent = text;
    $('fab-chat').appendChild(msg);
    $('fab-chat').scrollTop = $('fab-chat').scrollHeight;
    return msg;
}

async function sendFabQuestion() {
    const input = $('fab-input');
    const question = input.value.trim();
    if (!question) return;

    appendChat(question, 'user');
    input.value = '';
    const thinking = appendChat("Thinking...", 'ai thinking');

    try {
        const res = await fetch('/api/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question })
        });
        const data = await res.json();
        thinking.classList.remove('thinking');
        thinking.textContent = res.ok ? data.result : "Error: " + (data.error || "Unknown");
    } catch (e) {
        thinking.classList.remove('thinking');
        thinking.textContent = "Network error. Please try again.";
    }
}

$('fab-send').addEventListener('click', sendFabQuestion);
$('fab-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendFabQuestion();
});