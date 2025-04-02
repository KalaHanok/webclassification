// Capture page text content
function extractText() {
  // Remove script and style elements
  const elementsToRemove = document.querySelectorAll('script, style, noscript, iframe');
  elementsToRemove.forEach(el => el.remove());
  
  // Get all text content
  return document.body.innerText || '';
}

// Check if URL is from a search engine
const SEARCH_ENGINES = [
  'google.com/search',
  'bing.com/search',
  'duckduckgo.com/',
  'yahoo.com/search'
];

function isSearchEngine(url) {
  return SEARCH_ENGINES.some(domain => url.includes(domain));
}

// Block page with styled content
async function blockPage() {
  const blockedHTML = await fetch(chrome.runtime.getURL('blocked.html'))
    .then(response => response.text());
  
  document.documentElement.innerHTML = `
    <head>
      <meta charset="UTF-8">
      <title>Content Blocked</title>
      <link rel="stylesheet" href="${chrome.runtime.getURL('blocked.css')}">
    </head>
    <body>
      ${blockedHTML}
    </body>
  `;
  window.stop();
}

// Check if we should block the page
async function checkPage() {
  const url = window.location.href;
  
  // Skip search engine result pages
  if (isSearchEngine(url)) {
    return;
  }

  const text = extractText();
  const response = await chrome.runtime.sendMessage({
    action: 'checkContent',
    type: 'classifyContent',
    url,
    text
  });
  
  if (response.block) {
    await blockPage();
  }
}

// Run check when DOM starts loading
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', checkPage);
} else {
  checkPage();
}