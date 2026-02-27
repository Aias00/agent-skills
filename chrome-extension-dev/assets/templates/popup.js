// Popup JavaScript
// Runs when popup is opened.

console.log("Popup loaded");

function showStatus(message, isError = false) {
  const statusEl = document.getElementById("status");
  statusEl.textContent = message;
  statusEl.className = "status" + (isError ? " error" : "");
  statusEl.style.display = "block";

  setTimeout(() => {
    statusEl.style.display = "none";
  }, 3000);
}

async function getActiveTabId() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) {
    throw new Error("No active tab available");
  }
  return tab.id;
}

async function ensureContentScript(tabId) {
  try {
    await chrome.tabs.sendMessage(tabId, { action: "ping" });
    return;
  } catch (error) {
    await chrome.scripting.insertCSS({
      target: { tabId },
      files: ["content.css"]
    });
    await chrome.scripting.executeScript({
      target: { tabId },
      files: ["content.js"]
    });
  }
}

async function loadSettings() {
  const result = await chrome.storage.local.get(["enabled", "darkMode"]);
  document.getElementById("chk-enabled").checked = result.enabled ?? true;
  document.getElementById("chk-darkmode").checked = result.darkMode ?? false;
}

async function saveSettings() {
  const enabled = document.getElementById("chk-enabled").checked;
  const darkMode = document.getElementById("chk-darkmode").checked;

  await chrome.storage.local.set({ enabled, darkMode });

  try {
    const tabId = await getActiveTabId();
    await ensureContentScript(tabId);
    await chrome.tabs.sendMessage(tabId, {
      action: "applySettings",
      enabled,
      darkMode
    });
  } catch (error) {
    console.log("Unable to apply settings to active tab:", error);
  }

  showStatus("Settings saved!");
}

async function toggleFeature() {
  try {
    const tabId = await getActiveTabId();
    await ensureContentScript(tabId);
    const response = await chrome.tabs.sendMessage(tabId, { action: "toggle" });
    showStatus(response.success ? "Feature toggled!" : "Failed to toggle", !response.success);
  } catch (error) {
    showStatus("Error toggling feature: " + error.message, true);
  }
}

async function injectScript() {
  try {
    const tabId = await getActiveTabId();
    await ensureContentScript(tabId);
    showStatus("Script ready on active tab");
  } catch (error) {
    showStatus("Error injecting script: " + error.message, true);
  }
}

async function saveData() {
  const data = document.getElementById("input-data").value;
  await chrome.storage.local.set({ userData: data });
  showStatus("Data saved!");
  document.getElementById("input-data").value = "";
}

async function loadData() {
  const result = await chrome.storage.local.get(["userData"]);
  if (result.userData) {
    document.getElementById("input-data").value = result.userData;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  loadSettings();
  loadData();

  document.getElementById("btn-toggle").addEventListener("click", toggleFeature);
  document.getElementById("btn-inject").addEventListener("click", injectScript);
  document.getElementById("btn-save").addEventListener("click", saveData);

  document.getElementById("chk-enabled").addEventListener("change", saveSettings);
  document.getElementById("chk-darkmode").addEventListener("change", saveSettings);
});
