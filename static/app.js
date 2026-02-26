const API = 'http://localhost:8000';
let token = localStorage.getItem('token');

if (token) {
    document.getElementById('loggedOutNav').style.display = 'none';
    document.getElementById('loggedInNav').style.display = 'block';
    showSection('payment');
}

function showMessage(msg, isError = false) {
    const div = document.getElementById('message');
    div.className = 'message ' + (isError ? 'error' : 'success');
    div.textContent = msg;
    setTimeout(() => div.textContent = '', 3000);
}

function showSection(section) {
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.getElementById(section).classList.add('active');
    if (section === 'transactions') loadTransactions();
}

async function register() {
    const email = document.getElementById('regEmail').value;
    const password = document.getElementById('regPassword').value;
    
    try {
        const res = await fetch(`${API}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        
        if (res.ok) {
            showMessage('Registration successful! Please login.');
            showSection('login');
        } else {
            showMessage(data.detail, true);
        }
    } catch (err) {
        showMessage('Error: ' + err.message, true);
    }
}

async function login() {
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    
    try {
        const res = await fetch(`${API}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        
        if (res.ok) {
            token = data.access_token;
            localStorage.setItem('token', token);
            document.getElementById('loggedOutNav').style.display = 'none';
            document.getElementById('loggedInNav').style.display = 'block';
            showMessage('Login successful!');
            showSection('payment');
        } else {
            showMessage(data.detail, true);
        }
    } catch (err) {
        showMessage('Error: ' + err.message, true);
    }
}

async function makePayment() {
    const amount = parseFloat(document.getElementById('amount').value);
    const currency = document.getElementById('currency').value;
    const merchant_id = document.getElementById('merchantId').value;
    const idempotency_key = Date.now() + '-' + Math.random();
    
    try {
        const res = await fetch(`${API}/payment`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ amount, currency, merchant_id, idempotency_key })
        });
        const data = await res.json();
        
        if (res.ok) {
            showMessage('Payment successful!');
            document.getElementById('amount').value = '';
            document.getElementById('currency').value = '';
            document.getElementById('merchantId').value = '';
        } else {
            showMessage(data.detail, true);
        }
    } catch (err) {
        showMessage('Error: ' + err.message, true);
    }
}

async function loadTransactions() {
    try {
        const res = await fetch(`${API}/transactions`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();
        
        if (res.ok) {
            const list = document.getElementById('transactionList');
            if (data.transactions.length === 0) {
                list.innerHTML = '<p>No transactions yet.</p>';
            } else {
                list.innerHTML = data.transactions.map(t => `
                    <div style="border: 1px solid #ddd; padding: 10px; margin: 10px 0;">
                        <strong>Amount:</strong> ${t.amount} ${t.currency}<br>
                        <strong>Merchant:</strong> ${t.merchant_id}<br>
                        <strong>Date:</strong> ${new Date(t.created_at).toLocaleString()}
                    </div>
                `).join('');
            }
        } else {
            showMessage('Failed to load transactions', true);
        }
    } catch (err) {
        showMessage('Error: ' + err.message, true);
    }
}

function logout() {
    localStorage.removeItem('token');
    token = null;
    document.getElementById('loggedOutNav').style.display = 'block';
    document.getElementById('loggedInNav').style.display = 'none';
    showMessage('Logged out successfully');
    showSection('register');
}
