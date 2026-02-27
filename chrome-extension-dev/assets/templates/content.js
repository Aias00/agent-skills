// Content Script
// Runs on web pages.

console.log("Content script loaded");

const WIDGET_ID = "my-extension-widget";
const DARK_MODE_CLASS = "dark-mode-extension";

async function getSettings() {
  const result = await chrome.storage.local.get(["enabled", "darkMode"]);
  return {
    enabled: result.enabled !== false,
    darkMode: Boolean(result.darkMode)
  };
}

function setDarkMode(enabled) {
  document.documentElement.classList.toggle(DARK_MODE_CLASS, enabled);
  chrome.storage.local.set({ darkMode: enabled });
  return { success: true, darkMode: enabled };
}

function toggleDarkMode() {
  const nextValue = !document.documentElement.classList.contains(DARK_MODE_CLASS);
  return setDarkMode(nextValue);
}

function processSelection(text) {
  const selection = window.getSelection();
  if (!selection || selection.rangeCount === 0) {
    return;
  }

  const range = selection.getRangeAt(0);
  const span = document.createElement("span");
  span.style.backgroundColor = "yellow";
  span.textContent = text;

  range.deleteContents();
  range.insertNode(span);
}

function addExtensionUI() {
  if (document.getElementById(WIDGET_ID)) {
    return;
  }

  const widget = document.createElement("div");
  widget.id = WIDGET_ID;
  widget.style.cssText = `
    position: fixed;
    bottom: 20px;
    right: 20px;
    padding: 12px 16px;
    background: #1a73e8;
    color: white;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    z-index: 999999;
    cursor: pointer;
    font-family: sans-serif;
    font-size: 14px;
  `;
  widget.textContent = "My Extension";
  widget.addEventListener("click", () => {
    chrome.runtime.sendMessage({ action: "widgetClicked" });
  });

  document.body.appendChild(widget);
}

function removeExtensionUI() {
  const widget = document.getElementById(WIDGET_ID);
  if (widget) {
    widget.remove();
  }
}

function applySettings(enabled, darkMode) {
  if (enabled) {
    addExtensionUI();
  } else {
    removeExtensionUI();
  }
  document.documentElement.classList.toggle(DARK_MODE_CLASS, Boolean(darkMode));
  return { success: true };
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log("Message received:", request);

  switch (request.action) {
    case "toggle":
      sendResponse(toggleDarkMode());
      break;

    case "processSelection":
      processSelection(request.text ?? "");
      sendResponse({ success: true });
      break;

    case "applySettings":
      sendResponse(applySettings(request.enabled !== false, request.darkMode));
      break;

    case "ping":
      sendResponse({ status: "alive" });
      break;

    default:
      sendResponse({ error: "Unknown action" });
  }

  return true; // Keep channel open for async response.
});

(async function init() {
  const { enabled, darkMode } = await getSettings();
  applySettings(enabled, darkMode);
})();

chrome.storage.onChanged.addListener((changes, areaName) => {
  if (areaName !== "local") {
    return;
  }

  if (changes.enabled) {
    if (changes.enabled.newValue) {
      addExtensionUI();
    } else {
      removeExtensionUI();
    }
  }

  if (changes.darkMode) {
    document.documentElement.classList.toggle(DARK_MODE_CLASS, Boolean(changes.darkMode.newValue));
  }
});
