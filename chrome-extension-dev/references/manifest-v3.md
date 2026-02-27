# Manifest V3 Complete Reference

## Overview

Manifest V3 is the current extension platform, replacing V2. Key changes:

- Service workers replace background pages
- Remote code execution removed
- Enhanced security with CSP
- New APIs and permissions model

## Required Fields

```json
{
  "manifest_version": 3,
  "name": "Extension Name",
  "version": "1.0.0",
  "description": "What your extension does"
}
```

## Optional Metadata

```json
{
  "short_name": "Short Name",
  "author": "Your Name",
  "homepage_url": "https://example.com",
  "version_name": "1.0 beta"
}
```

## Icons

```json
{
  "icons": {
    "16": "icons/icon16.png",
    "32": "icons/icon32.png",
    "48": "icons/icon48.png",
    "128": "icons/icon128.png"
  }
}
```

**Requirements**:
- PNG format recommended
- 128x128 required for Chrome Web Store
- Sizes: 16, 32, 48, 128 (all optional but recommended)

## Action (Browser/Page Action)

```json
{
  "action": {
    "default_icon": {
      "16": "icons/icon16.png",
      "48": "icons/icon48.png"
    },
    "default_title": "Click me",
    "default_popup": "popup.html",
    "theme_icons": [{
      "light": "icons/light.png",
      "dark": "icons/dark.png",
      "size": 16
    }]
  }
}
```

## Background (Service Worker)

```json
{
  "background": {
    "service_worker": "background.js",
    "type": "module"
  }
}
```

**Key Differences from V2**:
- No DOM access
- No XMLHttpRequest (use fetch)
- No synchronous APIs
- Lifecycle: wake up, run, go dormant
- Use `chrome.alarms` for periodic tasks

## Content Scripts

### Static Declaration

```json
{
  "content_scripts": [{
    "matches": ["https://*.example.com/*"],
    "exclude_matches": ["https://example.com/excluded/*"],
    "js": ["content.js"],
    "css": ["content.css"],
    "run_at": "document_idle",
    "all_frames": false,
    "match_origin_as_fallback": true,
    "world": "ISOLATED"
  }]
}
```

### Run_at Options

- `"document_start"` - Before DOM is loaded
- `"document_end"` - After DOM, before subresources
- `"document_idle"` - After window.onload (default)

### World Options

- `"ISOLATED"` - Separate JavaScript world (default)
- `"MAIN"` - Same world as page JavaScript

## Permissions

### Host Permissions

```json
{
  "host_permissions": [
    "https://*.example.com/*",
    "https://api.example.com/*",
    "<all_urls>"
  ]
}
```

### API Permissions

```json
{
  "permissions": [
    "storage",
    "tabs",
    "activeTab",
    "contextMenus",
    "alarms",
    "notifications",
    "bookmarks",
    "history",
    "identity",
    "webRequest"
  ]
}
```

### Optional Permissions

```json
{
  "optional_permissions": [
    "history",
    "bookmarks"
  ],
  "optional_host_permissions": [
    "https://*.example.com/*"
  ]
}
```

**Request at Runtime**:
```javascript
chrome.permissions.request({
  permissions: ['history'],
  origins: ['https://*.example.com/*']
}, (granted) => {
  console.log('Permission granted:', granted);
});
```

## Web Accessible Resources

```json
{
  "web_accessible_resources": [{
    "resources": ["images/*.png", "scripts/*.js"],
    "matches": ["https://example.com/*"]
  }]
}
```

## Commands (Keyboard Shortcuts)

```json
{
  "commands": {
    "_execute_action": {
      "suggested_key": {
        "default": "Ctrl+Shift+Y",
        "mac": "Command+Shift+Y"
      },
      "description": "Open extension popup"
    },
    "custom-command": {
      "suggested_key": {
        "default": "Ctrl+Shift+Z"
      },
      "description": "Custom action"
    }
  }
}
```

## Context Menus

```json
{
  "permissions": ["contextMenus"]
}
```

```javascript
chrome.contextMenus.create({
  id: 'my-menu',
  title: 'My Menu',
  contexts: ['selection', 'image', 'link']
});
```

## Options Page

```json
{
  "options_page": "options.html"
}
```

### Embedded Options

```json
{
  "options_ui": {
    "page": "options.html",
    "open_in_tab": false
  }
}
```

## Side Panel

```json
{
  "side_panel": {
    "default_path": "sidepanel.html"
  },
  "permissions": ["sidePanel"]
}
```

## Content Security Policy

```json
{
  "content_security_policy": {
    "extension_pages": "script-src 'self'; object-src 'self'",
    "sandbox": "sandbox allow-scripts; script-src 'self'"
  }
}
```

## Sandboxed Pages

```json
{
  "sandbox": {
    "pages": ["sandbox.html"]
  }
}
```

**Use Cases**:
- Running untrusted HTML/CSS
- Using libraries that require eval()
- Displaying user-generated content

## Cross-Origin Resource Sharing (CORS)

```json
{
  "host_permissions": ["https://api.example.com/*"]
}
```

Background service worker can make cross-origin fetch requests.

## Web Navigation

```json
{
  "permissions": ["webNavigation"]
}
```

```javascript
chrome.webNavigation.onCompleted.addListener((details) => {
  console.log('Page loaded:', details.url);
});
```

## Declarative Content

```json
{
  "permissions": ["declarativeContent"]
}
```

```javascript
chrome.runtime.onInstalled.addListener(() => {
  chrome.declarativeContent.onPageChanged.removeRules(undefined, () => {
    chrome.declarativeContent.onPageChanged.addRules([{
      conditions: [
        new chrome.declarativeContent.PageStateMatcher({
          pageUrl: {hostEquals: 'example.com'},
        })
      ],
      actions: [new chrome.declarativeContent.ShowPageAction()]
    }]);
  });
});
```

## Storage

```json
{
  "permissions": ["storage"]
}
```

**Types**:
- `chrome.storage.local` - 10MB default, unlimited with permission
- `chrome.storage.sync` - 100KB total, synced across devices
- `chrome.storage.session` - In-memory only (V3+)

## Alarms

```json
{
  "permissions": ["alarms"]
}
```

```javascript
chrome.alarms.create('myAlarm', {delayInMinutes: 1});
chrome.alarms.onAlarm.addListener((alarm) => {
  console.log('Alarm:', alarm.name);
});
```

## Identity (OAuth)

```json
{
  "permissions": ["identity"],
  "oauth2": {
    "client_id": "YOUR_CLIENT_ID",
    "scopes": ["https://www.googleapis.com/auth/userinfo.email"]
  }
}
```

## Common Manifest Examples

### Minimal Extension

```json
{
  "manifest_version": 3,
  "name": "Minimal Extension",
  "version": "1.0",
  "action": {
    "default_popup": "popup.html"
  }
}
```

### Content Script Only

```json
{
  "manifest_version": 3,
  "name": "Content Script Extension",
  "version": "1.0",
  "content_scripts": [{
    "matches": ["https://example.com/*"],
    "js": ["content.js"]
  }]
}
```

### Full Featured

```json
{
  "manifest_version": 3,
  "name": "Full Featured Extension",
  "version": "1.0",
  "description": "A complete extension",
  "permissions": ["storage", "activeTab", "contextMenus"],
  "host_permissions": ["https://*.example.com/*"],
  "background": {
    "service_worker": "background.js"
  },
  "action": {
    "default_popup": "popup.html"
  },
  "options_ui": {
    "page": "options.html",
    "open_in_tab": false
  },
  "content_scripts": [{
    "matches": ["https://*.example.com/*"],
    "js": ["content.js"]
  }],
  "commands": {
    "_execute_action": {
      "suggested_key": {"default": "Ctrl+Shift+E"}
    }
  }
}
```

## Validation

Use the [manifest validator](https://github.com/GoogleChrome/chrome-extensions-samples/tree/main/tools/manifest-validator) to check your manifest.
