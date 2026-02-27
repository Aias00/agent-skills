# Common Chrome Extension Patterns

## Pattern 1: Page Modifier

Modify content on specific websites.

**manifest.json**:
```json
{
  "content_scripts": [{
    "matches": ["https://example.com/*"],
    "js": ["content.js"],
    "css": ["content.css"]
  }]
}
```

**content.js**:
```javascript
// Modify page content
document.querySelectorAll('a').forEach(link => {
  link.style.color = 'red';
});

// Add custom elements
const banner = document.createElement('div');
banner.id = 'my-banner';
banner.textContent = 'Extension is active';
document.body.insertBefore(banner, document.body.firstChild);
```

## Pattern 2: Popup with Options

Extension with popup UI and settings.

**manifest.json**:
```json
{
  "action": {
    "default_popup": "popup.html"
  },
  "options_ui": {
    "page": "options.html",
    "open_in_tab": false
  },
  "permissions": ["storage"]
}
```

**popup.html**:
```html
<!DOCTYPE html>
<html>
<head>
  <style>
    body { width: 300px; padding: 10px; }
  </style>
</head>
<body>
  <h2>Extension Popup</h2>
  <button id="action">Do Action</button>
  <script src="popup.js"></script>
</body>
</html>
```

**popup.js**:
```javascript
document.getElementById('action').addEventListener('click', async () => {
  const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
  chrome.tabs.sendMessage(tab.id, {action: 'toggle'});
  window.close();
});
```

## Pattern 3: Context Menu Action

Add item to right-click menu.

**manifest.json**:
```json
{
  "permissions": ["contextMenus", "activeTab"]
}
```

**background.js**:
```javascript
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'search-selection',
    title: 'Search for "%s"',
    contexts: ['selection']
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === 'search-selection') {
    const query = encodeURIComponent(info.selectionText);
    chrome.tabs.create({url: `https://google.com/search?q=${query}`});
  }
});
```

## Pattern 4: Background Data Processing

Process data in background and notify user.

**manifest.json**:
```json
{
  "background": {
    "service_worker": "background.js"
  },
  "permissions": ["storage", "alarms", "notifications"]
}
```

**background.js**:
```javascript
// Periodic check
chrome.alarms.create('check-data', {periodInMinutes: 30});

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === 'check-data') {
    const response = await fetch('https://api.example.com/data');
    const data = await response.json();
    
    const {lastCount} = await chrome.storage.local.get('lastCount');
    if (data.count !== lastCount) {
      chrome.notifications.create({
        type: 'basic',
        iconUrl: 'icons/icon48.png',
        title: 'New Data Available',
        message: `Count changed to ${data.count}`
      });
      chrome.storage.local.set({lastCount: data.count});
    }
  }
});
```

## Pattern 5: Content Script ↔ Background Messaging

Two-way communication between components.

**content.js**:
```javascript
// Request data from background
chrome.runtime.sendMessage({action: 'getUserData'}, (response) => {
  console.log('User data:', response.userData);
});

// Listen for messages from background
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'updatePage') {
    document.body.style.backgroundColor = request.color;
    sendResponse({success: true});
  }
  return true;
});
```

**background.js**:
```javascript
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getUserData') {
    chrome.storage.local.get('userData', (result) => {
      sendResponse({userData: result.userData});
    });
    return true; // Async response
  }
});

// Send message to active tab
chrome.tabs.query({active: true, currentWindow: true}, ([tab]) => {
  chrome.tabs.sendMessage(tab.id, {
    action: 'updatePage',
    color: '#f0f0f0'
  });
});
```

## Pattern 6: Dynamic Content Script Injection

Inject scripts only when needed.

**manifest.json**:
```json
{
  "permissions": ["activeTab", "scripting"]
}
```

**background.js**:
```javascript
chrome.action.onClicked.addListener(async (tab) => {
  // Check if already injected
  try {
    await chrome.tabs.sendMessage(tab.id, {action: 'ping'});
    console.log('Already injected');
  } catch (e) {
    // Not injected, inject now
    await chrome.scripting.executeScript({
      target: {tabId: tab.id},
      files: ['content.js']
    });
    await chrome.scripting.insertCSS({
      target: {tabId: tab.id},
      files: ['content.css']
    });
  }
});
```

## Pattern 7: Cross-Origin API Requests

Fetch data from APIs and display in popup.

**manifest.json**:
```json
{
  "host_permissions": ["https://api.example.com/*"]
}
```

**popup.js**:
```javascript
async function fetchData() {
  const response = await fetch('https://api.example.com/data');
  const data = await response.json();
  displayData(data);
}

function displayData(data) {
  const container = document.getElementById('data-container');
  container.innerHTML = `<p>${data.message}</p>`;
}

// Load on popup open
fetchData();
```

## Pattern 8: User Authentication (OAuth)

Authenticate user with external service.

**manifest.json**:
```json
{
  "permissions": ["identity"],
  "oauth2": {
    "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
    "scopes": ["https://www.googleapis.com/auth/userinfo.email"]
  }
}
```

**background.js**:
```javascript
function getAuthToken() {
  return new Promise((resolve) => {
    chrome.identity.getAuthToken({interactive: true}, resolve);
  });
}

async function fetchUserInfo() {
  const token = await getAuthToken();
  const response = await fetch('https://www.googleapis.com/oauth2/v2/userinfo', {
    headers: {Authorization: `Bearer ${token}`}
  });
  return response.json();
}

// Remove cached token on logout
chrome.identity.removeCachedAuthToken({token: oldToken}, () => {
  console.log('Token removed');
});
```

## Pattern 9: Keyboard Shortcuts

Define and handle keyboard commands.

**manifest.json**:
```json
{
  "commands": {
    "toggle-feature": {
      "suggested_key": {
        "default": "Ctrl+Shift+Y",
        "mac": "Command+Shift+Y"
      },
      "description": "Toggle feature"
    },
    "_execute_action": {
      "suggested_key": {
        "default": "Ctrl+Shift+E"
      }
    }
  }
}
```

**background.js**:
```javascript
chrome.commands.onCommand.addListener((command) => {
  if (command === 'toggle-feature') {
    // Toggle feature
    console.log('Feature toggled');
  }
});
```

## Pattern 10: Badge Counter

Show notification count on extension icon.

**background.js**:
```javascript
async function updateBadge() {
  const data = await fetchData();
  const count = data.unreadCount;
  
  if (count > 0) {
    chrome.action.setBadgeText({text: count.toString()});
    chrome.action.setBadgeBackgroundColor({color: '#FF0000'});
  } else {
    chrome.action.setBadgeText({text: ''});
  }
}

// Update periodically
chrome.alarms.create('update-badge', {periodInMinutes: 1});
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'update-badge') {
    updateBadge();
  }
});
```

## Pattern 11: Side Panel Extension

Use the new side panel UI.

**manifest.json**:
```json
{
  "side_panel": {
    "default_path": "sidepanel.html"
  },
  "permissions": ["sidePanel"]
}
```

**background.js**:
```javascript
chrome.action.onClicked.addListener((tab) => {
  chrome.sidePanel.open({windowId: tab.windowId});
});

// Or open on specific pages
chrome.sidePanel.setPanelBehavior({openPanelOnActionClick: true});
```

**sidepanel.html**:
```html
<!DOCTYPE html>
<html>
<head>
  <style>
    body { width: 400px; padding: 16px; }
  </style>
</head>
<body>
  <h2>Side Panel</h2>
  <div id="content">Loading...</div>
  <script src="sidepanel.js"></script>
</body>
</html>
```

## Pattern 12: Save Page State

Store page data for later use.

**content.js**:
```javascript
function savePageState() {
  const state = {
    scrollPosition: window.scrollY,
    text: document.getSelection().toString(),
    timestamp: Date.now()
  };
  chrome.storage.local.set({[`state_${window.location.href}`]: state});
}

function restorePageState() {
  chrome.storage.local.get(`state_${window.location.href}`, (result) => {
    const state = result[`state_${window.location.href}`];
    if (state) {
      window.scrollTo(0, state.scrollPosition);
    }
  });
}

window.addEventListener('scroll', savePageState);
window.addEventListener('load', restorePageState);
```

## Pattern 13: Dark Mode Toggle

Toggle page between light and dark mode.

**manifest.json**:
```json
{
  "action": {
    "default_popup": "popup.html"
  },
  "permissions": ["activeTab", "scripting"]
}
```

**popup.js**:
```javascript
document.getElementById('toggle-dark').addEventListener('click', async () => {
  const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
  chrome.scripting.executeScript({
    target: {tabId: tab.id},
    func: toggleDarkMode
  });
});

function toggleDarkMode() {
  document.body.classList.toggle('dark-mode-extension');
  const isDark = document.body.classList.contains('dark-mode-extension');
  chrome.storage.local.set({darkMode: isDark});
}
```

**content.css**:
```css
.dark-mode-extension {
  background-color: #1a1a1a !important;
  color: #e0e0e0 !important;
}

.dark-mode-extension * {
  background-color: inherit !important;
  color: inherit !important;
}
```

## Pattern 14: Intercept and Modify Requests

Monitor or block specific requests.

**manifest.json**:
```json
{
  "permissions": ["webRequest", "webRequestAuthProvider"],
  "host_permissions": ["https://*.example.com/*"]
}
```

**background.js**:
```javascript
chrome.webRequest.onBeforeRequest.addListener(
  (details) => {
    console.log('Request to:', details.url);
    if (details.url.includes('/block-me')) {
      return {cancel: true}; // Block request
    }
  },
  {urls: ['<all_urls>']},
  ['blocking']
);

chrome.webRequest.onCompleted.addListener(
  (details) => {
    console.log('Request completed:', details.url, details.statusCode);
  },
  {urls: ['<all_urls>']}
);
```

## Pattern 15: Omnibox Search

Add custom search to address bar.

**manifest.json**:
```json
{
  "omnibox": {
    "keyword": "mysearch"
  }
}
```

**background.js**:
```javascript
chrome.omnibox.onInputChanged.addListener((text, suggest) => {
  suggest([
    {content: 'suggestion1', description: 'First suggestion'},
    {content: 'suggestion2', description: 'Second suggestion'}
  ]);
});

chrome.omnibox.onInputEntered.addListener((text) => {
  chrome.tabs.create({url: `https://example.com/search?q=${text}`});
});
```
