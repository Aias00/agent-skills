---
name: chrome-extension-dev
description: Expert Chrome extension development with Manifest V3. Use when creating, building, debugging, or publishing Chrome extensions or browser add-ons. Covers architecture, APIs, security, performance, and best practices. Triggers include Chrome extension, browser extension, browser plugin, Chrome add-on, Manifest V3, content script, background script, extension popup.
---

# Chrome Extension Development

Expert guide for building Chrome extensions using Manifest V3.

## Quick Start

### 1. Create Project Structure

```
my-extension/
├── manifest.json
├── background.js
├── popup/
│   ├── popup.html
│   ├── popup.js
│   └── popup.css
├── content/
│   └── content.js
└── icons/
    └── icon48.png
```

### 2. Basic manifest.json

```json
{
  "manifest_version": 3,
  "name": "My Extension",
  "version": "1.0.0",
  "description": "What your extension does",
  "action": {
    "default_popup": "popup/popup.html",
    "default_icon": {
      "48": "icons/icon48.png"
    }
  },
  "permissions": ["storage", "activeTab"]
}
```

### 3. Load Unpacked

1. Open `chrome://extensions/`
2. Enable "Developer mode" (top right)
3. Click "Load unpacked"
4. Select your extension folder

## Core Components

### Manifest V3

**Required fields**:
- `manifest_version`: 3
- `name`: Extension name
- `version`: Version string (e.g., "1.0.0")

**Key changes from V2**:
- Service workers replace background pages
- No remote code execution
- Enhanced security with CSP
- New permissions model

### Background Service Worker

```javascript
// background.js
chrome.runtime.onInstalled.addListener(() => {
  console.log('Extension installed');
});

chrome.action.onClicked.addListener((tab) => {
  chrome.tabs.sendMessage(tab.id, {action: 'toggle'});
});
```

### Content Scripts

```javascript
// content.js
console.log('Content script loaded');

document.querySelectorAll('a').forEach(link => {
  link.style.color = 'red';
});

// Listen for messages
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'toggle') {
    document.body.classList.toggle('dark-mode');
    sendResponse({success: true});
  }
  return true;
});
```

### Popup UI

```html
<!-- popup/popup.html -->
<!DOCTYPE html>
<html>
<head>
  <style>
    body { width: 300px; padding: 16px; }
    button { width: 100%; padding: 8px; }
  </style>
</head>
<body>
  <h2>My Extension</h2>
  <button id="toggle">Toggle Dark Mode</button>
  <script src="popup.js"></script>
</body>
</html>
```

```javascript
// popup/popup.js
document.getElementById('toggle').addEventListener('click', async () => {
  const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
  await chrome.tabs.sendMessage(tab.id, {action: 'toggle'});
  window.close();
});
```

## Key APIs

### Storage

```javascript
// Save data
await chrome.storage.local.set({key: 'value'});

// Get data
const result = await chrome.storage.local.get(['key']);
console.log(result.key);

// Listen for changes
chrome.storage.onChanged.addListener((changes, areaName) => {
  console.log('Storage changed:', changes);
});
```

### Tabs

```javascript
// Query active tab
const [tab] = await chrome.tabs.query({active: true, currentWindow: true});

// Create new tab
await chrome.tabs.create({url: 'https://example.com'});

// Send message to tab
await chrome.tabs.sendMessage(tab.id, {data: 'hello'});
```

### Messaging

**One-time message**:
```javascript
// Send
const response = await chrome.runtime.sendMessage({action: 'getData'});

// Receive (background.js)
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getData') {
    sendResponse({data: 'Hello from background'});
  }
  return true; // Keep channel open for async
});
```

**Long-lived connection**:
```javascript
// Content script
const port = chrome.runtime.connect({name: 'myPort'});
port.postMessage({message: 'Hello'});
port.onMessage.addListener((msg) => console.log(msg));

// Background
chrome.runtime.onConnect.addListener((port) => {
  port.onMessage.addListener((msg) => {
    port.postMessage({response: 'Hi back'});
  });
});
```

### Context Menus

```javascript
// Create menu
chrome.contextMenus.create({
  id: 'myMenu',
  title: 'My Menu Item',
  contexts: ['selection']
});

// Handle click
chrome.contextMenus.onClicked.addListener((info, tab) => {
  console.log('Selected text:', info.selectionText);
});
```

## Permissions

### Common Permissions

```json
{
  "permissions": [
    "storage",
    "activeTab",
    "tabs",
    "contextMenus",
    "alarms",
    "notifications"
  ],
  "host_permissions": [
    "https://*.example.com/*"
  ]
}
```

### Permission Best Practices

- Use `activeTab` instead of broad host permissions
- Request optional permissions at runtime
- Explain why permissions are needed

```javascript
// Request at runtime
chrome.permissions.request({
  permissions: ['history'],
  origins: ['https://*.example.com/*']
}, (granted) => {
  if (granted) {
    console.log('Permission granted');
  }
});
```

## Security

### Content Security Policy

```json
{
  "content_security_policy": {
    "extension_pages": "script-src 'self'; object-src 'self'"
  }
}
```

### Avoid Inline Scripts

❌ **Don't**:
```html
<button onclick="doSomething()">Click</button>
```

✅ **Do**:
```html
<button id="myButton">Click</button>
<script src="popup.js"></script>
```

```javascript
// popup.js
document.getElementById('myButton').addEventListener('click', doSomething);
```

### Sanitize User Input

```javascript
// Safe
element.textContent = userInput;

// Dangerous - don't use
element.innerHTML = userInput;
```

## Debugging

### Background Service Worker

`chrome://extensions/` → Click "Service Worker" link → DevTools opens

### Content Scripts

Page DevTools → Console (content script logs appear here)

### Popup

Right-click extension icon → "Inspect popup"

### Storage

DevTools → Application → Storage → Chrome Extension Storage

## Common Patterns

See [references/patterns.md](references/patterns.md) for 15+ complete patterns including:
- Page modifier
- Context menu actions
- Dynamic content injection
- Cross-origin API requests
- OAuth authentication
- Keyboard shortcuts
- Badge counter
- Side panel

## Development Workflow

### 1. Plan Extension

- Define core functionality
- Identify required APIs
- Choose components (popup, content script, background)

### 2. Create Structure

Use template from [assets/templates/](assets/templates/)

### 3. Generate Extension Icons

**Don't use placeholder icons!** Generate professional icons based on your extension's functionality.

See [references/icon-generation.md](references/icon-generation.md) for complete guide including:
- AI-powered icon generation
- Design principles for extension icons
- Prompt templates for different extension types
- Icon optimization tips

**Quick example**:
```bash
# Generate icon for a "dark mode" extension
infsh app run falai/flux-dev-lora --input '{
  "prompt": "simple icon of a crescent moon on dark background, minimalist design, clean vector style, app icon, professional, high contrast, centered composition, white moon on dark blue background"
}'
```

### 4. Implement

- Start with manifest.json
- Add background service worker
- Implement content scripts
- Build popup UI

### 5. Test

- Load unpacked extension
- Test on target websites
- Check different scenarios
- Verify permissions

### 6. Package

`chrome://extensions/` → "Pack extension" → Select directory

### 7. Publish

- Pay $5 developer fee
- Upload to Chrome Web Store
- Fill store listing
- Submit for review (1-3 days)

## Performance Tips

### Lazy Loading

```javascript
// Inject only when needed
chrome.action.onClicked.addListener(async (tab) => {
  await chrome.scripting.executeScript({
    target: {tabId: tab.id},
    files: ['content.js']
  });
});
```

### Efficient Storage

- Use `chrome.storage.local` for large data (10MB)
- Use `chrome.storage.sync` for settings (100KB limit)
- Use `chrome.storage.session` for temporary data

### Service Worker Lifecycle

- Service workers wake up on events, then go dormant
- Don't rely on global state
- Use `chrome.storage` for persistence

## Troubleshooting

### Common Issues

**"Could not load extension"**: Check manifest.json syntax

**"Permission denied"**: Verify permissions in manifest

**"Message channel closed"**: Return `true` from message listener for async responses

**Service worker not running**: Check for errors in DevTools Console

**Content script not loading**: Verify `matches` patterns in manifest

## Resources

- **Manifest V3 Reference**: [references/manifest-v3.md](references/manifest-v3.md)
- **API Reference**: [references/api-reference.md](references/api-reference.md)
- **Common Patterns**: [references/patterns.md](references/patterns.md)
- **Icon Generation Guide**: [references/icon-generation.md](references/icon-generation.md) ⭐
- **Templates**: [assets/templates/](assets/templates/)

## When to Use This Skill

Use when:
- Creating new Chrome extensions
- Migrating from Manifest V2 to V3
- Debugging extension issues
- Implementing Chrome APIs
- Publishing to Chrome Web Store
- Optimizing extension performance
- **Generating professional extension icons** ⭐

Always start with clear requirements, choose minimal permissions, generate custom icons, and test thoroughly before publishing.
