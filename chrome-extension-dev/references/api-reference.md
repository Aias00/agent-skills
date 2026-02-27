# Chrome Extension API Quick Reference

## Storage API

### Methods

```javascript
// Store data
chrome.storage.local.set({key: value}, () => {
  console.log('Saved');
});

// Get data
chrome.storage.local.get(['key1', 'key2'], (result) => {
  console.log(result.key1, result.key2);
});

// Get all data
chrome.storage.local.get(null, (result) => {
  console.log(result);
});

// Remove data
chrome.storage.local.remove(['key'], () => {
  console.log('Removed');
});

// Clear all
chrome.storage.local.clear(() => {
  console.log('Cleared');
});

// Get storage info
chrome.storage.local.getBytesInUse(['key'], (bytesInUse) => {
  console.log(`Using ${bytesInUse} bytes`);
});
```

### Events

```javascript
chrome.storage.onChanged.addListener((changes, areaName) => {
  console.log('Changes in', areaName);
  for (let [key, {oldValue, newValue}] of Object.entries(changes)) {
    console.log(`${key}: ${oldValue} -> ${newValue}`);
  }
});
```

## Tabs API

### Create

```javascript
chrome.tabs.create({
  url: 'https://example.com',
  active: true,
  index: 0,
  windowId: windowId
}, (tab) => {
  console.log('Created tab:', tab.id);
});
```

### Query

```javascript
chrome.tabs.query({
  active: true,
  currentWindow: true,
  url: 'https://example.com/*'
}, (tabs) => {
  tabs.forEach(tab => console.log(tab.id, tab.url));
});
```

### Update

```javascript
chrome.tabs.update(tabId, {
  url: 'https://example.com',
  active: true,
  muted: true
}, (tab) => {
  console.log('Updated');
});
```

### Remove

```javascript
chrome.tabs.remove(tabId, () => {
  console.log('Tab closed');
});
```

### Events

```javascript
chrome.tabs.onCreated.addListener((tab) => {});
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete') {
    console.log('Tab loaded:', tab.url);
  }
});
chrome.tabs.onRemoved.addListener((tabId, removeInfo) => {});
chrome.tabs.onActivated.addListener((activeInfo) => {});
```

### Execute Script

```javascript
chrome.scripting.executeScript({
  target: {tabId: tabId},
  files: ['content.js']
});

chrome.scripting.executeScript({
  target: {tabId: tabId},
  func: () => {
    document.body.style.backgroundColor = 'red';
  }
});
```

## Runtime API

### Messaging

**One-time message**:

```javascript
// Send from content script
chrome.runtime.sendMessage({action: 'getData'}, (response) => {
  console.log('Response:', response);
});

// Listen in background
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getData') {
    sendResponse({data: 'Hello'});
  }
  return true; // Keep channel open for async response
});
```

**Long-lived connection**:

```javascript
// Content script
const port = chrome.runtime.connect({name: 'knockknock'});
port.postMessage({joke: 'Knock knock'});
port.onMessage.addListener((msg) => {
  console.log('Received:', msg);
});

// Background
chrome.runtime.onConnect.addListener((port) => {
  port.onMessage.addListener((msg) => {
    if (msg.joke === 'Knock knock') {
      port.postMessage({question: "Who's there?"});
    }
  });
});
```

### Open Options Page

```javascript
chrome.runtime.openOptionsPage();
```

### Get Extension Info

```javascript
const manifest = chrome.runtime.getManifest();
console.log(manifest.name, manifest.version);

const url = chrome.runtime.getURL('images/icon.png');
```

### Install/Update Events

```javascript
chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === 'install') {
    console.log('First install');
  } else if (details.reason === 'update') {
    console.log('Updated from', details.previousVersion);
  }
});
```

## Context Menus API

### Create

```javascript
chrome.contextMenus.create({
  id: 'my-menu',
  title: 'My Menu Item',
  contexts: ['selection', 'image', 'link', 'page']
});
```

**Contexts**:
- `all`
- `page`
- `selection`
- `link`
- `editable`
- `image`
- `video`
- `audio`
- `frame`

### Events

```javascript
chrome.contextMenus.onClicked.addListener((info, tab) => {
  console.log('Clicked:', info.menuItemId);
  console.log('Selection:', info.selectionText);
  console.log('Link URL:', info.linkUrl);
  console.log('Image URL:', info.srcUrl);
});
```

### Update/Remove

```javascript
chrome.contextMenus.update('my-menu', {
  title: 'New Title'
});

chrome.contextMenus.remove('my-menu');
chrome.contextMenus.removeAll();
```

## Bookmarks API

### Create

```javascript
chrome.bookmarks.create({
  parentId: '1',
  title: 'My Bookmark',
  url: 'https://example.com'
}, (bookmark) => {
  console.log('Created:', bookmark.id);
});
```

### Get/Query

```javascript
chrome.bookmarks.getTree((bookmarkTreeNodes) => {
  // Recursive tree
});

chrome.bookmarks.search({title: 'My'}, (results) => {
  console.log(results);
});
```

### Events

```javascript
chrome.bookmarks.onCreated.addListener((id, bookmark) => {});
chrome.bookmarks.onRemoved.addListener((id, removeInfo) => {});
chrome.bookmarks.onChanged.addListener((id, changeInfo) => {});
```

## Alarms API

### Create

```javascript
chrome.alarms.create('alarm-name', {
  delayInMinutes: 1,
  periodInMinutes: 5
});
```

### Get/Clear

```javascript
chrome.alarms.get('alarm-name', (alarm) => {
  console.log(alarm);
});

chrome.alarms.clear('alarm-name');
chrome.alarms.clearAll();
```

### Event

```javascript
chrome.alarms.onAlarm.addListener((alarm) => {
  console.log('Alarm triggered:', alarm.name);
});
```

## Notifications API

### Create

```javascript
chrome.notifications.create('id', {
  type: 'basic',
  iconUrl: 'icons/icon48.png',
  title: 'Notification Title',
  message: 'Notification message',
  buttons: [
    {title: 'Button 1'},
    {title: 'Button 2'}
  ]
});
```

### Events

```javascript
chrome.notifications.onClicked.addListener((notificationId) => {});
chrome.notifications.onButtonClicked.addListener((notificationId, buttonIndex) => {});
chrome.notifications.onClosed.addListener((notificationId, byUser) => {});
```

## Web Navigation API

### Events

```javascript
chrome.webNavigation.onCompleted.addListener((details) => {
  console.log('Page loaded:', details.url);
}, {url: [{hostEquals: 'example.com'}]});

chrome.webNavigation.onHistoryStateUpdated.addListener((details) => {
  console.log('URL changed without reload:', details.url);
});
```

## Action API (Toolbar Button)

### Set Icon/Title

```javascript
chrome.action.setIcon({
  tabId: tabId,
  path: 'icons/icon-active.png'
});

chrome.action.setTitle({
  tabId: tabId,
  title: 'New Title'
});
```

### Badge

```javascript
chrome.action.setBadgeText({text: 'NEW'});
chrome.action.setBadgeBackgroundColor({color: '#FF0000'});
chrome.action.setBadgeTextColor({color: '#FFFFFF'});
```

### Event

```javascript
chrome.action.onClicked.addListener((tab) => {
  // No popup defined, this triggers
  console.log('Icon clicked');
});
```

## Commands API (Keyboard Shortcuts)

### Get All

```javascript
chrome.commands.getAll((commands) => {
  commands.forEach(cmd => console.log(cmd.name, cmd.shortcut));
});
```

### Event

```javascript
chrome.commands.onCommand.addListener((command) => {
  console.log('Command triggered:', command);
});
```

## Permissions API

### Request

```javascript
chrome.permissions.request({
  permissions: ['history'],
  origins: ['https://*.example.com/*']
}, (granted) => {
  console.log('Permission granted:', granted);
});
```

### Check/Remove

```javascript
chrome.permissions.contains({
  permissions: ['history']
}, (hasPermission) => {
  console.log('Has permission:', hasPermission);
});

chrome.permissions.remove({
  permissions: ['history']
}, (removed) => {
  console.log('Permission removed:', removed);
});
```

## Windows API

### Create/Get

```javascript
chrome.windows.create({
  url: 'https://example.com',
  type: 'popup',
  state: 'maximized'
});

chrome.windows.getCurrent((window) => {
  console.log('Current window:', window.id);
});
```

### Events

```javascript
chrome.windows.onCreated.addListener((window) => {});
chrome.windows.onRemoved.addListener((windowId) => {});
chrome.windows.onFocusChanged.addListener((windowId) => {});
```

## Side Panel API

### Open

```javascript
chrome.sidePanel.open({windowId: windowId});
```

### Set Behavior

```javascript
chrome.sidePanel.setPanelBehavior({openPanelOnActionClick: true});
```

## Scripting API

### Insert CSS

```javascript
chrome.scripting.insertCSS({
  target: {tabId: tabId},
  files: ['content.css']
});
```

### Remove CSS

```javascript
chrome.scripting.removeCSS({
  target: {tabId: tabId},
  files: ['content.css']
});
```

## Identity API

### Get Auth Token

```javascript
chrome.identity.getAuthToken({interactive: true}, (token) => {
  console.log('Access token:', token);
});
```

### Launch Web Auth Flow

```javascript
chrome.identity.launchWebAuthFlow({
  url: 'https://accounts.google.com/o/oauth2/v2/auth?...',
  interactive: true
}, (redirectUrl) => {
  console.log('Redirect URL:', redirectUrl);
});
```
