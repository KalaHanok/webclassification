document.addEventListener('DOMContentLoaded', () => {
  // DOM elements
  const authChoiceDiv = document.getElementById('auth-choice');
  const registrationForm = document.getElementById('registration-form');
  const loginForm = document.getElementById('login-form');
  const messageDiv = document.getElementById('message');
  
  // API endpoints
  const API_BASE = 'http://127.0.0.1:8000/api';
  const REGISTER_URL = `${API_BASE}/register/`;
  const GET_DEVICE_ID_URL = `${API_BASE}/get-device-id/`;

  // Check existing registration
  checkExistingRegistration();

  // Event listeners
  document.getElementById('new-user-btn').addEventListener('click', showRegistrationForm);
  document.getElementById('existing-user-btn').addEventListener('click', showLoginForm);
  document.getElementById('newUserForm').addEventListener('submit', handleRegistration);
  document.getElementById('existingUserForm').addEventListener('submit', handleLogin);

  async function checkExistingRegistration() {
    const { registered, deviceId } = await chrome.storage.local.get(['registered', 'deviceId']);
    if (registered) {
      await notifyBackground(deviceId);
      window.close();
    }
  }

  function showRegistrationForm() {
    authChoiceDiv.classList.add('hidden');
    registrationForm.classList.remove('hidden');
    document.getElementById('deviceId').value = generateUUID();
  }

  function showLoginForm() {
    authChoiceDiv.classList.add('hidden');
    loginForm.classList.remove('hidden');
  }

  async function handleRegistration(e) {
    e.preventDefault();
    
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    const deviceId = document.getElementById('deviceId').value;

    if (password !== confirmPassword) {
      showMessage('Passwords do not match!', 'error');
      return;
    }

    try {
      // Create proper JSON payload
      const payload = {
        username,
        password,
        device_id: deviceId
      };

      await registerUser(payload);
      await storeRegistration(username, deviceId);
      await notifyBackground(deviceId);
      showMessage('Registration successful!', 'success');
      setTimeout(() => window.close(), 1500);
    } catch (error) {
      showMessage(error.message, 'error');
    }
  }

  async function handleLogin(e) {
    e.preventDefault();
    
    const username = document.getElementById('loginUsername').value.trim();
    const password = document.getElementById('loginPassword').value;

    try {
      // Create proper JSON payload
      const payload = {
        username,
        password
      };

      const deviceId = await loginUser(payload);
      await storeRegistration(username, deviceId);
      await notifyBackground(deviceId);
      showMessage('Login successful!', 'success');
      setTimeout(() => window.close(), 1500);
    } catch (error) {
      showMessage(error.message, 'error');
    }
  }

  // Helper functions
  function generateUUID() {
    return crypto.randomUUID();
  }

  function showMessage(text, type) {
    messageDiv.textContent = text;
    messageDiv.className = type;
    messageDiv.classList.remove('hidden');
    setTimeout(() => messageDiv.classList.add('hidden'), 3000);
  }

  async function registerUser(payload) {
    const response = await fetch(REGISTER_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload)
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Registration failed');
    }
  }

  async function loginUser(payload) {
    const response = await fetch(GET_DEVICE_ID_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload)
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Login failed');
    }

    const data = await response.json();
    if (!data.device_id) throw new Error('No device ID received');
    return data.device_id;
  }

  async function storeRegistration(username, deviceId) {
    await chrome.storage.local.set({
      registered: true,
      username,
      deviceId
    });
  }

  async function notifyBackground(deviceId) {
    return new Promise(resolve => {
      chrome.runtime.sendMessage({
        type: 'updateRegistration',
        registered: true,
        deviceId
      }, resolve);
    });
  }
});