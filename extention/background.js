const WHITELISTED_DOMAINS = [
  'google.com',
  'yahoo.com',
  'bing.com',
  'duckduckgo.com'
];

// Initialize extension state
let deviceId = null;
let isRegistered = false;

// Check if URL is whitelisted
function isWhitelisted(url) {
  return WHITELISTED_DOMAINS.some(domain => url.includes(domain));
}

// Initialize extension
chrome.runtime.onInstalled.addListener(async () => {
  const storage = await chrome.storage.local.get(['registered', 'deviceId']);
  console.log('Storage data:', storage);
  isRegistered = storage.registered || false;
  deviceId = storage.deviceId || null;
});

// Handle content classification
async function classifyContent(url, text) {

  console.log('isRegistered:', isRegistered);
  console.log('deviceId:', deviceId);
  if (!isRegistered || isWhitelisted(url)) {
    return { block: false };
  }

  try {
    const response = await fetch('http://127.0.0.1:8000/api/classify/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        domain:url,
        text_content:text,
        device_id: deviceId
      })
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Classification failed:', error);
    return { block: false }; // Fail open
  }
}

// Message handling
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  switch (request.type) {
    case 'classifyContent':
      classifyContent(request.url, request.text)
        .then(result => sendResponse(result))
        .catch(error => {
          console.error('Classification error:', error);
          sendResponse({ block: false });
        });
      return true; // Keep message channel open

    case 'updateRegistration':
      isRegistered = request.registered;
      deviceId = request.deviceId;
      sendResponse({ success: true });
      break;

    default:
      console.warn('Unknown message type:', request.type);
      sendResponse({ error: 'Unknown message type' });
  }
});