// Background Service Worker
// Runs independently of any web page.

console.log("Background service worker started");

// Initialize defaults and one-time platform resources.
chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === "install") {
    console.log("Extension installed for the first time");
    chrome.storage.local.set({
      enabled: true,
      darkMode: false,
      userData: "",
      data: null
    });
  } else if (details.reason === "update") {
    console.log("Extension updated from", details.previousVersion);
  }

  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create(
      {
        id: "my-extension-menu",
        title: "My Extension Action",
        contexts: ["selection"]
      },
      () => {
        if (chrome.runtime.lastError) {
          console.log("Failed to create context menu:", chrome.runtime.lastError.message);
        }
      }
    );
  });

  chrome.alarms.create("checkData", { periodInMinutes: 30 });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== "my-extension-menu" || !tab?.id) {
    return;
  }

  try {
    await chrome.tabs.sendMessage(tab.id, {
      action: "processSelection",
      text: info.selectionText ?? ""
    });
  } catch (error) {
    console.log("Unable to message content script:", error);
  }
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "checkData") {
    console.log("Periodic check running");
  }
});

// Listen for messages from content scripts or popup.
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log("Message received:", request);

  switch (request.action) {
    case "getData":
      chrome.storage.local.get(["data"], (result) => {
        sendResponse({ data: result.data ?? null });
      });
      return true; // Keep channel open for async response.

    case "saveData":
      chrome.storage.local.set({ data: request.data }, () => {
        sendResponse({ success: true });
      });
      return true;

    case "widgetClicked":
      sendResponse({ success: true });
      return false;

    default:
      sendResponse({ error: "Unknown action" });
      return false;
  }
});
