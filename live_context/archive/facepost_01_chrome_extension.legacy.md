# Hermes FacePost-Group — Chrome Extension Spec
## Module: `facepost_01_chrome_extension.md`
**Version:** 2.2.0 (Stateless & Context Guard)
**Date:** 2026-06-18
**Status:** ACTIVE — Replaces v2.1.0

## 🚨 CẢNH BÁO KỸ THUẬT QUAN TRỌNG

### 1. `background.js` (Service Worker Relay)
* 🚨 **Giới hạn vòng đời (Lifecycle Limits):** Service Worker (SW) trong Manifest V3 hoạt động ở chế độ ephemeral (không liên tục). Chrome sẽ giải phóng bộ nhớ và dừng SW sau 30 giây rảnh. Do đó, **nghiêm cấm** khai báo biến trạng thái ở tầng top-level của SW (như `let activeSessions = {}` hoặc `let token;`). 
* 🚀 **Biện pháp xử lý:** Mọi dữ liệu cấu hình hoặc trạng thái bắt buộc phải đọc/ghi trực tiếp qua `chrome.storage.local` hoặc ủy nhiệm hoàn toàn cho `offscreen.js` nắm giữ. SW chỉ đóng vai trò một Stateless Message Relay. Lắng nghe sự kiện `chrome.tabs.onRemoved` để gửi tín hiệu đóng tab về Dashboard.

### 2. `offscreen.js` (Persistent WebSocket Host)
* 🚨 **Duy trì kết nối (Connection Keepalive):** Không khởi tạo kết nối WebSocket theo kiểu phó mặc cho trình duyệt tự duy trì (`new WebSocket(url)` không có kiểm soát). Chrome vẫn có thể đóng băng tab ẩn nếu không có dữ liệu trao đổi liên tục.
* 🚀 **Biện pháp xử lý:** Bắt buộc sử dụng cơ chế **Heartbeat Ping/Pong hai chiều** định kỳ mỗi 10 giây nối trực tiếp với Dashboard Server. Nếu sau 2 chu kỳ (20 giây) không nhận được `PONG`, bắt buộc thực hiện ngắt kết nối chủ động (watchdog disconnect) và thực hiện tái kết nối theo thuật toán lũy thừa (Exponential Backoff) từ 1s đến tối đa 30s.

### 3. `dom_compressor.js` (Semantic DOM Compressor)
* 🚨 **Định danh phần tử (Element Identification):** **Tuyệt đối không** dùng số chỉ mục tuần tự (sequential index) để định danh các phần tử trên giao diện Facebook. Khi React phía Facebook re-render hoặc người dùng cuộn trang xuất hiện thêm phần tử mới, thứ tự index sẽ bị thay đổi hoàn toàn, dẫn đến việc AI Agent tương tác sai phần tử.
* 🚀 **Biện pháp xử lý:** ID định danh (fingerprint) của phần tử bắt buộc phải là một chuỗi băm ổn định (Stable Hash 8 ký tự hex) được sinh ra bằng thuật toán băm FNV-1a 32-bit từ các thuộc tính phi tuần tự: `tag_name + role + aria-label + data-testid + rect` (x, y, width, height). Bổ sung cơ chế chụp ảnh base64/screenshot nếu hệ thống yêu cầu Vision AI.

---

## Mục Lục

1. [Tổng Quan Kiến Trúc](#1-tổng-quan-kiến-trúc)
2. [manifest.json — Cấu hình Manifest V3](#2-manifestjson--cấu-hình-manifest-v3)
3. [Offscreen Document Pattern](#3-offscreen-document-pattern)
4. [background.js — Service Worker Relay](#4-backgroundjs--service-worker-relay)
5. [dom_compressor.js — Fingerprint Hash](#5-dom_compressorjs--fingerprint-hash)
6. [content.js — Message Relay](#6-contentjs--message-relay)
7. [popup.html / popup.js — Giao diện Popup](#7-popuphtml--popupjs--giao-diện-popup)
8. [WebSocket Auth Protocol — Xác thực và bắt tay](#8-websocket-auth-protocol--xác-thực-và-bắt-tay)
9. [Luồng Dữ Liệu Tổng Thể](#9-luồng-dữ-liệu-tổng-thể)
10. [Error Handling & Graceful Degradation](#10-error-handling--graceful-degradation)
11. [Checklist Kiểm Thử](#11-checklist-kiểm-thử)
12. [Facebook Search & Human-like Interactions (Bezier & Gaussian)](#12-facebook-search--human-like-interactions-bezier--gaussian)
13. [Phân tích lỗ hổng an ninh và yêu cầu khắc phục](#13-phân-tích-lỗ-hổng-an-ninh-và-yêu-cầu-khắc-phục)

---

## 1. Tổng Quan Kiến Trúc

### 1.1 Vấn Đề Cốt Lõi MV3 (Audit Findings)

Chrome Extension Manifest V3 áp đặt các ràng buộc bắt buộc:

| Issue ID | Mức độ | Mô tả | Giải pháp |
|----------|--------|-------|-----------|
| **A3** | 🔴 CRITICAL | Service Worker bị Chrome terminate sau **30 giây** không activity → WebSocket đứt, biến global mất | **Offscreen Document API** giữ WebSocket persistent |
| **A4** | 🟠 HIGH | WebSocket không có auth token → bất kỳ process local nào có thể kết nối vào Dashboard | HMAC-SHA256 handshake với shared secret |
| **B1** | 🟠 HIGH | DOM element ID dùng `index` (0, 1, 2...) → race condition khi React re-render thay đổi thứ tự | Fingerprint stable: **FNV-1a 32-bit (8 hex chars)** dựa trên các thuộc tính phi tuần tự và rect tọa độ |
| **C1** | 🟡 LOW | `popup.html` khai báo trong manifest nhưng không có spec | Viết spec popup trạng thái kết nối và cấu hình động |

### 1.2 Sơ Đồ Kiến Trúc Tổng Thể

```
┌─────────────────────────────────────────────────────────────────┐
│                    Chrome Browser Process                        │
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │ content.js   │    │background.js │    │  offscreen.html  │   │
│  │ (Tab Context)│◄──►│(Service Wkr) │◄──►│  offscreen.js    │   │
│  │              │    │  (RELAY ONLY)│    │  [WebSocket Host]│   │
│  └──────┬───────┘    └──────────────┘    └────────┬─────────┘   │
│         │ chrome.runtime.sendMessage               │             │
│  ┌──────▼───────┐                                 │ WebSocket   │
│  │ popup.html   │                                 │ (persistent)│
│  │ (Status UI)  │                                 │             │
│  └──────────────┘                                 │             │
└──────────────────────────────────────────────────-│─────────────┘
                                                     │ ws://localhost:8765/ws
                                         ┌──────────▼─────────────┐
                                         │   Local Dashboard       │
                                         │   (Node.js Server)     │
                                         │   AI Agent Brain       │
                                         └────────────────────────┘
```

---

## 2. manifest.json — Cấu hình Manifest V3

### 2.1 manifest.json Hoàn Chỉnh (Bản Ghost/Unpacked Dev)

```json
{
  "manifest_version": 3,
  "name": "Hermes FacePost-Group",
  "version": "2.2.0",
  "description": "Tự động hóa đăng bài Facebook Group — Hermes AI Agent",
  "permissions": [
    "activeTab",
    "scripting",
    "storage",
    "offscreen",
    "tabs",
    "alarms"
  ],
  "host_permissions": [
    "https://*.facebook.com/*",
    "https://*.fb.com/*"
  ],
  "background": {
    "service_worker": "background.js",
    "type": "module"
  },
  "content_scripts": [
    {
      "matches": [
        "https://*.facebook.com/*",
        "https://*.fb.com/*"
      ],
      "js": ["content.js"],
      "run_at": "document_idle",
      "type": "module"
    }
  ],
  "action": {
    "default_popup": "popup.html",
    "default_icon": {
      "16": "icons/icon16.png",
      "48": "icons/icon48.png",
      "128": "icons/icon128.png"
    },
    "default_title": "Hermes FacePost"
  },
  "web_accessible_resources": [
    {
      "resources": ["offscreen.html"],
      "matches": ["<all_urls>"]
    }
  ],
  "icons": {
    "16": "icons/icon16.png",
    "48": "icons/icon48.png",
    "128": "icons/icon128.png"
  },
  "minimum_chrome_version": "116"
}
```

---

## 3. Offscreen Document Pattern

### 3.1 Vòng đời Offscreen Document

- Tạo bằng `chrome.offscreen.createDocument()`.
- Có ngữ cảnh DOM (document object) → Trình duyệt không giải phóng bộ nhớ như Service Worker.
- WebSocket kết nối và duy trì liên tục trong `offscreen.js`.
- Service Worker đóng vai trò trung gian chuyển tiếp tin nhắn giữa `content.js` và `offscreen.js`.

### 3.2 Thuật Toán Keepalive (Offscreen watchdog)

```pseudocode
OFFSCREEN_KEEPALIVE_ALGORITHM:

CONSTANTS:
  PING_INTERVAL = 10000ms  // Gửi ping mỗi 10s
  WATCHDOG_TIMEOUT = 20000ms // Watchdog 2 chu kỳ (20s)
  RECONNECT_DELAY_BASE = 1000ms
  RECONNECT_DELAY_MAX = 30000ms
  RECONNECT_MULTIPLIER = 2

STATE:
  ws: WebSocket | null = null
  pingTimer: Timer | null = null
  reconnectTimer: Timer | null = null
  reconnectAttempts: int = 0
  isAuthenticated: bool = false
  lastPongTime: timestamp = 0

PROCEDURE connect(serverUrl, authSecret):
  ws = new WebSocket(serverUrl)
  
  ON ws.open:
    reconnectAttempts = 0
    CALL performHandshake(authSecret)
  
  ON ws.message(event):
    IF isAuthenticated:
      msg = JSON.parse(event.data)
      IF msg.type == "PONG":
        lastPongTime = CURRENT_TIMESTAMP()
      ELSE:
        CALL routeMessage(event.data)
    ELSE:
      CALL handleAuthResponse(event.data)
  
  ON ws.close(code, reason):
    isAuthenticated = false
    CALL stopPingLoop()
    CALL scheduleReconnect()
  
  ON ws.error:
    // log error

PROCEDURE startPingLoop():
  lastPongTime = CURRENT_TIMESTAMP()
  pingTimer = setInterval(() => {
    IF ws.readyState == OPEN AND isAuthenticated:
      now = CURRENT_TIMESTAMP()
      // Kiểm tra watchdog 2 chu kỳ không có PONG
      IF now - lastPongTime >= WATCHDOG_TIMEOUT:
        CALL ws.close(4000, "Heartbeat timeout")
        RETURN
      ws.send(JSON.stringify({ type: "PING", ts: now }))
  }, PING_INTERVAL)

PROCEDURE stopPingLoop():
  clearInterval(pingTimer)
  pingTimer = null

PROCEDURE scheduleReconnect():
  delay = MIN(
    RECONNECT_DELAY_BASE * (RECONNECT_MULTIPLIER ^ reconnectAttempts),
    RECONNECT_DELAY_MAX
  )
  reconnectAttempts++
  reconnectTimer = setTimeout(() => connect(serverUrl, authSecret), delay)
```

### 3.3 offscreen.html

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Hermes Offscreen</title>
</head>
<body>
  <script src="offscreen.js" type="module"></script>
</body>
</html>
```

### 3.4 offscreen.js — Thực thi đầy đủ

```javascript
/**
 * offscreen.js — Persistent WebSocket Host
 */

import { hmacSha256Hex } from './lib/hmac_sha256.js';

const DEFAULT_WS_URL = 'ws://127.0.0.1:8765/ws';
let WS_URL = DEFAULT_WS_URL;
const PING_INTERVAL_MS = 10000;
const WATCHDOG_TIMEOUT_MS = 20000;
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;
const RECONNECT_MULTIPLIER = 2;
const HANDSHAKE_TIMEOUT_MS = 5000;

let ws = null;
let pingTimer = null;
let reconnectTimer = null;
let reconnectAttempts = 0;
let isAuthenticated = false;
let authSecret = null;
let pendingHandshakeResolve = null;
let handshakeTimeoutTimer = null;
let lastPongTime = 0;

async function init() {
  const data = await chrome.storage.local.get(['ws_auth_secret', 'wsUrl']);
  if (!data.ws_auth_secret) {
    console.error('[Offscreen] Thiếu khóa bí mật xác thực.');
    notifyBackground({ type: 'WS_STATUS', status: 'NO_SECRET' });
    return;
  }
  authSecret = data.ws_auth_secret;
  if (data.wsUrl) WS_URL = data.wsUrl;
  connect();
}

chrome.runtime.onMessage.addListener((message) => {
  if (message.target === 'offscreen' && message.type === 'RECONNECT') {
    chrome.storage.local.get(['wsUrl', 'ws_auth_secret'], ({ wsUrl, ws_auth_secret }) => {
      if (wsUrl) WS_URL = wsUrl;
      if (ws_auth_secret) authSecret = ws_auth_secret;
      if (ws) ws.close(1000, 'Config changed — reconnecting');
      connect();
    });
  }
});

function connect() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    return;
  }

  console.log(`[Offscreen] Connecting to ${WS_URL}... (attempt ${reconnectAttempts + 1})`);
  ws = new WebSocket(WS_URL);

  ws.addEventListener('open', onOpen);
  ws.addEventListener('message', onMessage);
  ws.addEventListener('close', onClose);
  ws.addEventListener('error', onError);
}

async function onOpen() {
  console.log('[Offscreen] WebSocket connected. Starting handshake...');
  reconnectAttempts = 0;

  try {
    await performHandshake();
    isAuthenticated = true;
    lastPongTime = Date.now();
    console.log('[Offscreen] Auth OK. Starting ping loop.');
    startPingLoop();
    notifyBackground({ type: 'WS_STATUS', status: 'CONNECTED' });
  } catch (err) {
    console.error('[Offscreen] Handshake failed:', err.message);
    ws.close(1008, 'Auth failed');
  }
}

function onMessage(event) {
  let msg;
  try {
    msg = JSON.parse(event.data);
  } catch {
    console.warn('[Offscreen] Non-JSON message received:', event.data);
    return;
  }

  if (!isAuthenticated) {
    handleAuthResponse(msg);
    return;
  }

  if (msg.type === 'PONG') {
    lastPongTime = Date.now();
    return;
  }

  if (msg.type === 'EXTENSION_RELOAD') {
    chrome.runtime.sendMessage({
      source: 'offscreen',
      type: 'TRIGGER_RELOAD',
      reason: msg.reason || 'OTA update applied'
    }).catch(() => {});
    return;
  }

  notifyBackground({ type: 'DASHBOARD_COMMAND', payload: msg });
}

function onClose(event) {
  console.warn(`[Offscreen] WebSocket closed. Code=${event.code}, Reason=${event.reason}`);
  isAuthenticated = false;
  stopPingLoop();
  notifyBackground({ type: 'WS_STATUS', status: 'DISCONNECTED' });
  scheduleReconnect();
}

function onError(event) {
  console.error('[Offscreen] WebSocket error:', event);
}

function performHandshake() {
  return new Promise((resolve, reject) => {
    const nonce = crypto.randomUUID();
    const timestamp = Date.now();

    hmacSha256Hex(authSecret, `${nonce}:${timestamp}`).then(signature => {
      const manifest = chrome.runtime.getManifest();
      const helloMsg = {
        type: 'HELLO',
        nonce,
        timestamp,
        signature,
        extensionVersion: manifest.version || '2.2.0',
        extension_mode: 'GHOST',
        extension_id: chrome.runtime.id
      };

      ws.send(JSON.stringify(helloMsg));

      handshakeTimeoutTimer = setTimeout(() => {
        reject(new Error('Handshake timeout'));
      }, HANDSHAKE_TIMEOUT_MS);

      pendingHandshakeResolve = resolve;
    });
  });
}

function handleAuthResponse(msg) {
  if (msg.type === 'WELCOME') {
    clearTimeout(handshakeTimeoutTimer);
    if (pendingHandshakeResolve) {
      pendingHandshakeResolve();
      pendingHandshakeResolve = null;
    }
  } else if (msg.type === 'AUTH_REJECT') {
    clearTimeout(handshakeTimeoutTimer);
    console.error('[Offscreen] Auth rejected by server:', msg.reason || msg.errorDetail);
    ws.close(1008, 'Auth rejected');
  }
}

function startPingLoop() {
  stopPingLoop();
  pingTimer = setInterval(() => {
    if (ws && ws.readyState === WebSocket.OPEN && isAuthenticated) {
      const now = Date.now();
      if (now - lastPongTime >= WATCHDOG_TIMEOUT_MS) {
        console.warn('[Offscreen] Heartbeat lost. Closing connection.');
        ws.close(4000, 'Heartbeat timeout');
        return;
      }
      ws.send(JSON.stringify({ type: 'PING', ts: now }));
    }
  }, PING_INTERVAL_MS);
}

function stopPingLoop() {
  if (pingTimer) {
    clearInterval(pingTimer);
    pingTimer = null;
  }
}

function scheduleReconnect() {
  if (reconnectTimer) return;

  const delay = Math.min(
    RECONNECT_BASE_MS * Math.pow(RECONNECT_MULTIPLIER, reconnectAttempts),
    RECONNECT_MAX_MS
  );
  reconnectAttempts++;

  console.log(`[Offscreen] Reconnecting in ${delay}ms...`);
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    connect();
  }, delay);
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.target !== 'offscreen') return;

  switch (message.type) {
    case 'SEND_TO_DASHBOARD':
      if (ws && ws.readyState === WebSocket.OPEN && isAuthenticated) {
        ws.send(JSON.stringify(message.payload));
        sendResponse({ success: true });
      } else {
        sendResponse({ success: false, reason: 'WebSocket not ready' });
      }
      break;

    case 'GET_STATUS':
      sendResponse({
        connected: ws?.readyState === WebSocket.OPEN,
        authenticated: isAuthenticated,
        reconnectAttempts
      });
      break;

    default:
      console.warn('[Offscreen] Unknown message type:', message.type);
  }

  return true;
});

function notifyBackground(payload) {
  chrome.runtime.sendMessage({
    source: 'offscreen',
    ...payload
  }).catch(() => {});
}

init();
```

---

## 4. background.js — Service Worker Relay

### 4.1 Cơ chế hoạt động không trạng thái (Stateless)

- Không lưu trữ dữ liệu phiên hoặc tokens trực tiếp trong Service Worker.
- Sử dụng `chrome.storage.local` để lưu trữ biến điều phối ngắn hạn như `isOffscreenCreating` nhằm tránh xung đột tranh chấp (race condition).
- Relay toàn bộ thông điệp giữa các tab và `offscreen.js`.

### 4.2 background.js — Thực thi đầy đủ

```javascript
/**
 * background.js — Service Worker Relay (MV3)
 */

const OFFSCREEN_DOCUMENT_PATH = 'offscreen.html';

chrome.runtime.onInstalled.addListener(async () => {
  await ensureOffscreenDocument();
});

chrome.runtime.onStartup.addListener(async () => {
  await ensureOffscreenDocument();
});

self.addEventListener('activate', async () => {
  await ensureOffscreenDocument();
});

async function ensureOffscreenDocument() {
  const existingContexts = await chrome.runtime.getContexts({
    contextTypes: ['OFFSCREEN_DOCUMENT'],
    documentUrls: [chrome.runtime.getURL(OFFSCREEN_DOCUMENT_PATH)]
  });

  if (existingContexts.length > 0) {
    return;
  }

  const lock = await chrome.storage.local.get(['isOffscreenCreating']);
  if (lock.isOffscreenCreating) {
    return;
  }

  await chrome.storage.local.set({ isOffscreenCreating: true });
  try {
    await chrome.offscreen.createDocument({
      url: OFFSCREEN_DOCUMENT_PATH,
      reasons: ['TESTING'],
      justification: 'Persistent WebSocket connection to Hermes Dashboard'
    });
    console.log('[BG] Offscreen document created.');
  } catch (err) {
    console.error('[BG] Failed to create offscreen document:', err);
  } finally {
    await chrome.storage.local.remove(['isOffscreenCreating']);
  }
}

chrome.tabs.onRemoved.addListener(async (tabId) => {
  await ensureOffscreenDocument();
  chrome.runtime.sendMessage({
    target: 'offscreen',
    type: 'SEND_TO_DASHBOARD',
    payload: {
      type: 'SESSION_EVENT',
      event: 'ERROR',
      errorCode: 'ERR-DOM-02',
      payload: {
        message: `Tab ${tabId} was closed by user or browser`,
        tabId: tabId
      },
      ts: Date.now()
    }
  }).catch(() => {});
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  const source = message.source || 'unknown';

  if (source === 'content') {
    handleContentMessage(message, sender, sendResponse);
    return true;
  }

  if (source === 'offscreen') {
    handleOffscreenMessage(message, sender, sendResponse);
    return true;
  }

  if (source === 'popup') {
    handlePopupMessage(message, sender, sendResponse);
    return true;
  }

  return false;
});

async function handleContentMessage(message, sender, sendResponse) {
  await ensureOffscreenDocument();

  const response = await chrome.runtime.sendMessage({
    target: 'offscreen',
    type: 'SEND_TO_DASHBOARD',
    payload: {
      ...message.payload,
      _meta: {
        tabId: sender.tab?.id,
        url: sender.tab?.url,
        ts: Date.now()
      }
    }
  }).catch(err => ({ success: false, reason: err.message }));

  sendResponse(response);
}

async function handleOffscreenMessage(message, sender, sendResponse) {
  if (message.type === 'WS_STATUS') {
    chrome.runtime.sendMessage({
      source: 'background',
      type: 'WS_STATUS_UPDATE',
      status: message.status
    }).catch(() => {});
    return;
  }

  if (message.type === 'TRIGGER_RELOAD') {
    console.log('[BG] Extension reload triggered:', message.reason);
    await chrome.storage.local.set({
      lastReloadReason: message.reason,
      lastReloadAt: Date.now()
    });
    chrome.runtime.reload();
    return;
  }

  if (message.type === 'DASHBOARD_COMMAND') {
    const cmd = message.payload;
    
    if (cmd.type === 'CAPTURE_SCREENSHOT') {
      try {
        const targetTab = cmd.targetTabId || await getActiveFacebookTabId();
        if (targetTab) {
          const dataUrl = await chrome.tabs.captureVisibleTab(null, { format: 'png' });
          chrome.runtime.sendMessage({
            target: 'offscreen',
            type: 'SEND_TO_DASHBOARD',
            payload: {
              type: 'COMMAND_RESULT',
              commandId: cmd.commandId,
              success: true,
              screenshot: dataUrl,
              executionMs: 100
            }
          });
        }
      } catch (err) {
        chrome.runtime.sendMessage({
          target: 'offscreen',
          type: 'SEND_TO_DASHBOARD',
          payload: {
            type: 'COMMAND_RESULT',
            commandId: cmd.commandId,
            success: false,
            errorCode: 'ERR-DOM-02',
            errorDetail: `Screenshot failed: ${err.message}`,
            executionMs: 100
          }
        });
      }
      return;
    }

    await sendCommandToTab(cmd);
  }
}

async function getActiveFacebookTabId() {
  const [activeTab] = await chrome.tabs.query({
    url: ['https://*.facebook.com/*', 'https://*.fb.com/*'],
    active: true,
    currentWindow: true
  });
  return activeTab?.id || null;
}

async function sendCommandToTab(cmd) {
  if (cmd.targetTabId) {
    chrome.tabs.sendMessage(cmd.targetTabId, {
      source: 'background',
      type: 'EXECUTE_COMMAND',
      command: cmd
    }).catch(err => {
      console.error(`[BG] Failed to send to tab ${cmd.targetTabId}:`, err);
    });
    return;
  }

  const activeTabId = await getActiveFacebookTabId();
  if (activeTabId) {
    chrome.tabs.sendMessage(activeTabId, {
      source: 'background',
      type: 'EXECUTE_COMMAND',
      command: cmd
    }).catch(err => {
      console.warn('[BG] Active Facebook tab unavailable:', err.message);
    });
  } else {
    console.warn('[BG] No active Facebook tab found. Command dropped:', cmd);
  }
}

async function handlePopupMessage(message, sender, sendResponse) {
  if (message.type === 'GET_WS_STATUS') {
    await ensureOffscreenDocument();

    const status = await chrome.runtime.sendMessage({
      target: 'offscreen',
      type: 'GET_STATUS'
    }).catch(() => ({ connected: false, authenticated: false, reconnectAttempts: 0 }));

    sendResponse(status);
  }
}

chrome.alarms.create('keepalive', { periodInMinutes: 0.5 });
chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === 'keepalive') {
    await ensureOffscreenDocument();
  }
});
```

---

## 5. dom_compressor.js — Fingerprint Hash

### 5.1 Thuật toán băm FNV-1a 32-bit cho DOM node
Bảo vệ độ ổn định định danh phần tử trước việc re-render của React:
- Thu thập các trường: `tagName`, `role`, `aria-label`, `data-testid`, và `bounding rect` (x, y, width, height).
- Băm qua thuật toán FNV-1a 32-bit để chuyển thành mã Hex 8 ký tự duy nhất.
- Sử dụng Collision Map để xử lý các phần tử trùng lặp sinh ra cùng mã băm.

```pseudocode
FNV_1A_FINGERPRINT_ALGORITHM:

INPUT: element (DOM Node)
OUTPUT: fingerprint_hex (string, 8 chars)

STEP 1 — Thu thập thuộc tính:
  rect = element.getBoundingClientRect()
  tag = element.tagName.toLowerCase()
  role = element.getAttribute("role") || ""
  aria_label = element.getAttribute("aria-label") || ""
  data_testid = element.getAttribute("data-testid") || ""
  x = Math.round(rect.x)
  y = Math.round(rect.y)
  w = Math.round(rect.width)
  h = Math.round(rect.height)

STEP 2 — Tạo chuỗi thô:
  raw = tag + "|" + role + "|" + aria_label + "|" + data_testid + "|" + x + "|" + y + "|" + w + "|" + h

STEP 3 — Thực thi thuật toán băm FNV-1a (32-bit):
  hash = 2166136261 (FNV offset basis)
  FOR each char in raw:
    hash = hash XOR charCodeAt(char)
    hash = (hash * 16777619) AND 0xFFFFFFFF (FNV prime multiplication)
  fingerprint = hash.toString(16).padStart(8, '0')

STEP 4 — Xử lý xung đột:
  IF fingerprint tồn tại trong map:
    suffix = collision_count[fingerprint]++
    fingerprint = fingerprint + "_" + suffix
```

### 5.2 dom_compressor.js — Thực thi đầy đủ

```javascript
/**
 * dom_compressor.js — DOM Compression Utility with FNV-1a 32-bit hashing
 */

function generateFingerprint(el, collisionMap) {
  const rect = el.getBoundingClientRect();
  const raw = [
    el.tagName?.toLowerCase() || 'unknown',
    el.getAttribute('role') || '',
    el.getAttribute('aria-label') || '',
    el.getAttribute('data-testid') || '',
    Math.round(rect.x),
    Math.round(rect.y),
    Math.round(rect.width),
    Math.round(rect.height),
  ].join('|');

  // FNV-1a 32-bit hash
  let hash = 2166136261;
  for (let i = 0; i < raw.length; i++) {
    hash ^= raw.charCodeAt(i);
    hash = (hash * 16777619) >>> 0;
  }
  const baseHash = hash.toString(16).padStart(8, '0');

  if (!collisionMap) {
    return baseHash;
  }

  const count = collisionMap.get(baseHash) || 0;
  collisionMap.set(baseHash, count + 1);

  return count === 0 ? baseHash : `${baseHash}_${count}`;
}

const INTERACTIVE_SELECTORS = [
  'button',
  'a[href]',
  '[role="button"]',
  '[role="link"]',
  '[role="menuitem"]',
  'input:not([type="hidden"])',
  'textarea',
  '[contenteditable="true"]',
  '[role="textbox"]',
  '[data-testid]',
  '[aria-label]',
  'select',
  '[role="checkbox"]',
  '[role="radio"]',
  '[role="combobox"]',
].join(',');

function compressDOM({ maxElements = 200, visibleOnly = true } = {}) {
  const elements = document.querySelectorAll(INTERACTIVE_SELECTORS);
  const collisionMap = new Map();
  const fingerprintIndex = new Map();
  const snapshot = [];

  for (const el of elements) {
    if (snapshot.length >= maxElements) break;

    if (visibleOnly && !isVisible(el)) continue;

    const rect = el.getBoundingClientRect();
    if (rect.bottom < -500 || rect.top > window.innerHeight + 500) continue;

    const fingerprint = generateFingerprint(el, collisionMap);
    fingerprintIndex.set(fingerprint, el);

    const entry = {
      id: fingerprint,
      tag: el.tagName.toLowerCase(),
      role: el.getAttribute('role') || null,
      ariaLabel: el.getAttribute('aria-label') || null,
      text: (el.innerText || el.textContent || '').trim().slice(0, 80),
      placeholder: el.placeholder || null,
      disabled: el.disabled || el.getAttribute('aria-disabled') === 'true',
      visible: isVisible(el),
      rect: {
        x: Math.round(rect.x),
        y: Math.round(rect.y),
        width: Math.round(rect.width),
        height: Math.round(rect.height)
      },
      href: (() => {
        try { return el.href ? new URL(el.href).pathname : null; } catch { return null; }
      })(),
      src: el.getAttribute('src') || null,
      name: el.getAttribute('name') || null,
      dataTestid: el.getAttribute('data-testid') || null,
      contentEditable: el.isContentEditable || el.getAttribute('contenteditable') === 'true',
      inputType: el.tagName.toLowerCase() === 'input' ? el.type : null
    };

    for (const key of Object.keys(entry)) {
      if (entry[key] === null || entry[key] === undefined) {
        delete entry[key];
      }
    }

    snapshot.push(entry);
  }

  const visibleTexts = snapshot.filter(e => e.visible).map(e => e.text).filter(Boolean);
  const innerTextAgg = visibleTexts.join(' ').slice(0, 2048);

  const visibleButtons = snapshot
    .filter(e => (e.tag === 'button' || e.role === 'button') && e.visible)
    .map(e => e.text)
    .filter(Boolean);

  const visibleInputs = snapshot
    .filter(e => (e.tag === 'input' || e.tag === 'textarea' || e.role === 'textbox' || e.contentEditable) && e.visible)
    .map(e => ({
      id: e.id,
      tag: e.tag,
      role: e.role || '',
      ariaLabel: e.ariaLabel || ''
    }));

  const dialogEl = document.querySelector('div[role="dialog"]');
  const activeModal = (dialogEl && isVisible(dialogEl)) ? (dialogEl.innerText || '').trim().slice(0, 1000) : null;

  const forms = [];
  const formElements = document.querySelectorAll('form');
  for (const formEl of formElements) {
    if (isVisible(formEl)) {
      const formId = generateFingerprint(formEl);
      const fields = [];
      const inputEls = formEl.querySelectorAll('input, textarea, [contenteditable="true"]');
      for (const inputEl of inputEls) {
        if (isVisible(inputEl)) {
          fields.push({
            id: generateFingerprint(inputEl),
            tag: inputEl.tagName.toLowerCase(),
            ariaLabel: inputEl.getAttribute('aria-label') || ''
          });
        }
      }
      forms.push({ id: formId, fields });
    }
  }

  return {
    url: window.location.href,
    title: document.title.slice(0, 100),
    ts: Date.now(),
    page_ready: document.readyState === 'complete',
    scrollY: Math.round(window.scrollY),
    viewportHeight: Math.round(window.innerHeight),
    elementCount: snapshot.length,
    elements: snapshot,
    innerText: innerTextAgg,
    visibleButtons,
    visibleInputs,
    activeModal,
    forms,
    _fingerprintIndex: fingerprintIndex
  };
}

function isVisible(el) {
  if (!el.offsetParent && el.tagName !== 'BODY') return false;
  const style = window.getComputedStyle(el);
  return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
}

function findElementByFingerprint(fingerprint, fingerprintIndex) {
  return fingerprintIndex.get(fingerprint) || null;
}

export { compressDOM, findElementByFingerprint, generateFingerprint };
```

---

## 6. content.js — Message Relay

### 6.1 Cơ chế hoạt động
`content.js` hoạt động tại ngữ cảnh của tab Facebook. Thực hiện:
- Lấy DOM snapshot chuyển về Dashboard qua Service Worker.
- Thực thi các tương tác giả lập người dùng được chỉ định bởi Dashboard.
- Triển khai cơ chế tự bảo vệ context (`Context Guard`) khi extension reload thông qua kết nối Port.

### 6.2 content.js — Thực thi đầy đủ

```javascript
/**
 * content.js — Content Script (Facebook Tab)
 */

import { compressDOM, findElementByFingerprint } from './dom_compressor.js';

const CHAR_DELAY_MIN = 40;
const CHAR_DELAY_MAX = 180;

function gaussianRandom(mean, stdDev) {
  let u = 0, v = 0;
  while (u === 0) u = Math.random();
  while (v === 0) v = Math.random();
  let num = Math.sqrt(-2.0 * Math.log(u)) * Math.cos(2.0 * Math.PI * v);
  num = num * stdDev + mean;
  return num;
}

function charDelayGaussian(mean = 100, stdDev = 30) {
  const delay = gaussianRandom(mean, stdDev);
  return Math.max(CHAR_DELAY_MIN, Math.min(300, Math.round(delay)));
}

let currentSnapshot = null;
let lastSnapshotTs = 0;
const SNAPSHOT_THROTTLE_MS = 500;

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.source !== 'background') return;

  switch (message.type) {
    case 'EXECUTE_COMMAND':
      handleCommand(message.command, sendResponse);
      return true;

    case 'GET_DOM_SNAPSHOT':
      handleGetSnapshot(message, sendResponse);
      return true;

    default:
      console.warn('[Content] Unknown message type:', message.type);
  }
});

async function handleCommand(command, sendResponse) {
  const type = command.type || command.action;
  const elementId = command.elementId || command.targetId;
  const textVal = command.text !== undefined ? command.text : command.value;

  const snapshot = getSnapshot();
  const el = elementId
    ? findElementByFingerprint(elementId, snapshot._fingerprintIndex)
    : null;

  let result = { success: false, errorCode: null, errorDetail: null };
  const startTime = Date.now();

  try {
    switch (type) {
      case 'CLICK_ELEMENT':
      case 'CLICK':
        if (!elementId) {
          result = { success: false, errorCode: 'ERR-DOM-01', errorDetail: 'No elementId provided' };
          break;
        }
        if (!el) {
          result = { success: false, errorCode: 'ERR-DOM-01', errorDetail: `Element not found: ${elementId}` };
          break;
        }
        if (el.disabled || el.getAttribute('aria-disabled') === 'true') {
          result = { success: false, errorCode: 'ERR-DOM-01', errorDetail: `Element is disabled: ${elementId}` };
          break;
        }
        el.click();
        result = { success: true };
        break;

      case 'HUMAN_CLICK':
        if (!elementId) {
          result = { success: false, errorCode: 'ERR-DOM-01', errorDetail: 'No elementId provided' };
          break;
        }
        if (!el) {
          result = { success: false, errorCode: 'ERR-DOM-01', errorDetail: `Element not found: ${elementId}` };
          break;
        }
        await simulateBezierMouseMoveAndClick(el);
        result = { success: true };
        break;

      case 'TYPE_TEXT':
      case 'TYPE':
        if (!elementId) {
          result = { success: false, errorCode: 'ERR-DOM-01', errorDetail: 'No elementId provided' };
          break;
        }
        if (!el) {
          result = { success: false, errorCode: 'ERR-DOM-01', errorDetail: `Element not found: ${elementId}` };
          break;
        }
        if (el.disabled || el.getAttribute('aria-disabled') === 'true') {
          result = { success: false, errorCode: 'ERR-DOM-01', errorDetail: `Element is disabled: ${elementId}` };
          break;
        }
        await smartInject(el, textVal);
        result = { success: true };
        break;

      case 'HUMAN_TYPE':
        if (!elementId) {
          result = { success: false, errorCode: 'ERR-DOM-01', errorDetail: 'No elementId provided' };
          break;
        }
        if (!el) {
          result = { success: false, errorCode: 'ERR-DOM-01', errorDetail: `Element not found: ${elementId}` };
          break;
        }
        await simulateGaussianTyping(el, textVal);
        result = { success: true };
        break;

      case 'FB_SEARCH_GROUP':
        result = await executeFbSearchGroup(command.fb_group_id, command.group_name, command.timeoutMs || 15000, command.commandId);
        break;

      case 'CLEAR':
        if (!el) { result = { success: false, errorCode: 'ERR-DOM-01', errorDetail: `Element not found: ${elementId}` }; break; }
        clearElement(el);
        result = { success: true };
        break;

      case 'SCROLL_INTO_VIEW':
        if (!el) { result = { success: false, errorCode: 'ERR-DOM-01', errorDetail: `Element not found: ${elementId}` }; break; }
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        result = { success: true };
        break;

      case 'SCROLL':
        const targetY = command.scrollY !== undefined ? command.scrollY : 0;
        const scrollBehavior = command.behavior || 'smooth';
        window.scrollTo({ top: targetY, behavior: scrollBehavior });
        result = { success: true };
        break;

      case 'NAVIGATE':
        if (command.url) {
          window.location.href = command.url;
          result = { success: true };
        } else {
          result = { success: false, errorCode: 'ERR-DOM-02', errorDetail: 'No URL provided' };
        }
        break;

      case 'CAPTURE_SNAPSHOT':
      case 'GET_SNAPSHOT':
        const fresh = getSnapshot(true);
        result = {
          success: true,
          snapshot: {
            url: fresh.url,
            title: fresh.title,
            ts: fresh.ts,
            page_ready: fresh.page_ready,
            scrollY: fresh.scrollY,
            viewportHeight: fresh.viewportHeight,
            elementCount: fresh.elementCount,
            elements: fresh.elements,
            innerText: fresh.innerText,
            visibleButtons: fresh.visibleButtons,
            visibleInputs: fresh.visibleInputs,
            activeModal: fresh.activeModal,
            forms: fresh.forms
          }
        };
        break;

      case 'WAIT_FOR_ELEMENT':
        const found = await waitForElement(elementId, command.timeoutMs || 5000);
        result = { success: found, errorCode: found ? null : 'ERR-DOM-01' };
        break;

      default:
        result = { success: false, errorCode: 'ERR-DOM-02', errorDetail: `Unsupported action: ${type}` };
    }
  } catch (err) {
    result = { success: false, errorCode: 'ERR-DOM-02', errorDetail: err.message };
  }

  const executionMs = Date.now() - startTime;
  let responsePayload;

  if (type === 'CAPTURE_SNAPSHOT') {
    responsePayload = {
      type: 'DOM_SNAPSHOT',
      requestId: command.requestId || command.commandId,
      snapshot: result.snapshot || getSnapshot(true)
    };
  } else {
    responsePayload = {
      type: 'COMMAND_RESULT',
      commandId: command.commandId,
      success: result.success,
      errorCode: result.errorCode,
      errorDetail: result.errorDetail,
      executionMs
    };
  }

  await sendResultWithRetry({
    source: 'content',
    payload: responsePayload
  });

  sendResponse(result);
}

async function sendResultWithRetry(message, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      await chrome.runtime.sendMessage(message);
      return;
    } catch (e) {
      console.warn(`[Content] sendMessage attempt ${i + 1} failed:`, e.message);
      if (i < maxRetries - 1) await delay(1000 * (i + 1));
    }
  }
  console.error('[Content] All retries failed. Posting RESULT_FALLBACK to window.');
  window.postMessage({ type: 'RESULT_FALLBACK', ...message }, '*');
}

function getSnapshot(forceRefresh = false) {
  const now = Date.now();
  if (!forceRefresh && currentSnapshot && (now - lastSnapshotTs) < SNAPSHOT_THROTTLE_MS) {
    return currentSnapshot;
  }
  currentSnapshot = compressDOM({ maxElements: 200, visibleOnly: true });
  lastSnapshotTs = now;
  return currentSnapshot;
}

function handleGetSnapshot(message, sendResponse) {
  const snapshot = getSnapshot(message.force);
  sendResponse({
    success: true,
    snapshot: {
      url: snapshot.url,
      title: snapshot.title,
      ts: snapshot.ts,
      page_ready: snapshot.page_ready,
      scrollY: snapshot.scrollY,
      viewportHeight: snapshot.viewportHeight,
      elementCount: snapshot.elementCount,
      elements: snapshot.elements,
      innerText: snapshot.innerText,
      visibleButtons: snapshot.visibleButtons,
      visibleInputs: snapshot.visibleInputs,
      activeModal: snapshot.activeModal,
      forms: snapshot.forms
    }
  });
}

async function injectContentEditable(element, text) {
  element.focus();
  await delay(150);

  document.execCommand('selectAll', false, null);
  document.execCommand('delete', false, null);
  await delay(100);

  for (const char of text) {
    document.execCommand('insertText', false, char);
    await delay(charDelayGaussian(100, 30));
  }
  await delay(200);

  element.dispatchEvent(new Event('input', { bubbles: true }));
  element.dispatchEvent(new Event('change', { bubbles: true }));
  element.dispatchEvent(new InputEvent('input', {
    bubbles: true,
    cancelable: true,
    inputType: 'insertText',
    data: text
  }));
}

function injectInput(element, text) {
  element.focus();
  clearElement(element);

  const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
    element.tagName === 'INPUT' ? window.HTMLInputElement.prototype : window.HTMLTextAreaElement.prototype,
    'value'
  )?.set;

  if (nativeInputValueSetter) {
    nativeInputValueSetter.call(element, text);
  } else {
    element.value = text;
  }
  element.dispatchEvent(new Event('input', { bubbles: true }));
  element.dispatchEvent(new Event('change', { bubbles: true }));
}

async function smartInject(element, text) {
  if (element.isContentEditable || element.getAttribute('contenteditable') === 'true') {
    await injectContentEditable(element, text);
  } else if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
    injectInput(element, text);
  } else {
    console.warn('[Hermes] Unknown element type for inject:', element.tagName);
  }
}

async function simulateBezierMouseMoveAndClick(element) {
  const rect = element.getBoundingClientRect();
  const endX = rect.left + rect.width / 2 + (Math.random() - 0.5) * (rect.width * 0.2);
  const endY = rect.top + rect.height / 2 + (Math.random() - 0.5) * (rect.height * 0.2);

  const startX = window.lastMouseX !== undefined ? window.lastMouseX : Math.random() * window.innerWidth;
  const startY = window.lastMouseY !== undefined ? window.lastMouseY : Math.random() * window.innerHeight;

  const controlX = startX + (endX - startX) * 0.5 + (Math.random() - 0.5) * 200;
  const controlY = startY + (endY - startY) * 0.5 + (Math.random() - 0.5) * 200;

  const steps = 15 + Math.floor(Math.random() * 10);
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    const currentX = (1 - t) * (1 - t) * startX + 2 * (1 - t) * t * controlX + t * t * endX;
    const currentY = (1 - t) * (1 - t) * startY + 2 * (1 - t) * t * controlY + t * t * endY;

    element.dispatchEvent(new MouseEvent('mousemove', {
      bubbles: true,
      cancelable: true,
      clientX: currentX,
      clientY: currentY,
      view: window
    }));

    await delay(charDelayGaussian(15, 5));
  }

  window.lastMouseX = endX;
  window.lastMouseY = endY;

  element.dispatchEvent(new MouseEvent('mouseover', { bubbles: true, cancelable: true, clientX: endX, clientY: endY, view: window }));
  await delay(charDelayGaussian(50, 15));
  element.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, clientX: endX, clientY: endY, view: window }));
  await delay(charDelayGaussian(30, 10));
  element.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, clientX: endX, clientY: endY, view: window }));
  element.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, clientX: endX, clientY: endY, view: window }));
}

async function simulateGaussianTyping(element, text) {
  element.focus();
  await delay(charDelayGaussian(150, 30));

  if (element.isContentEditable || element.getAttribute('contenteditable') === 'true') {
    document.execCommand('selectAll', false, null);
    document.execCommand('delete', false, null);
    await delay(100);

    for (const char of text) {
      document.execCommand('insertText', false, char);
      element.dispatchEvent(new KeyboardEvent('keydown', { key: char, bubbles: true }));
      element.dispatchEvent(new KeyboardEvent('keypress', { key: char, bubbles: true }));
      element.dispatchEvent(new KeyboardEvent('keyup', { key: char, bubbles: true }));
      await delay(charDelayGaussian(100, 35));
    }
  } else {
    clearElement(element);
    let currentVal = '';
    for (const char of text) {
      currentVal += char;
      const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
        element.tagName === 'INPUT' ? window.HTMLInputElement.prototype : window.HTMLTextAreaElement.prototype,
        'value'
      )?.set;
      if (nativeInputValueSetter) {
        nativeInputValueSetter.call(element, currentVal);
      } else {
        element.value = currentVal;
      }
      element.dispatchEvent(new KeyboardEvent('keydown', { key: char, bubbles: true }));
      element.dispatchEvent(new KeyboardEvent('keypress', { key: char, bubbles: true }));
      element.dispatchEvent(new Event('input', { bubbles: true }));
      element.dispatchEvent(new KeyboardEvent('keyup', { key: char, bubbles: true }));
      await delay(charDelayGaussian(100, 35));
    }
    element.dispatchEvent(new Event('change', { bubbles: true }));
  }
}

async function executeFbSearchGroup(fbGroupId, groupName, timeoutMs = 15000, commandId) {
  const startTime = Date.now();
  const query = groupName || fbGroupId;
  if (!query) {
    return {
      success: false,
      errorCode: 'ERR-INVALID-ARGUMENTS',
      errorDetail: 'Neither fb_group_id nor group_name provided for search'
    };
  }

  try {
    const isHome = window.location.pathname === '/' || window.location.pathname === '/home.php';
    let searchInput = document.querySelector('input[placeholder*="Tìm kiếm"], input[aria-label*="Search Facebook"], input[placeholder*="Search Facebook"]');
    
    if (isHome && searchInput) {
      console.log('[Hermes] Found search input on Home. Performing human-like search.');
      await simulateBezierMouseMoveAndClick(searchInput);
      await simulateGaussianTyping(searchInput, query);
      searchInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true }));
      searchInput.dispatchEvent(new KeyboardEvent('keypress', { key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true }));
      searchInput.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true }));
      
      const form = searchInput.closest('form');
      if (form) form.submit();
    } else {
      const searchUrl = `https://www.facebook.com/search/groups/?q=${encodeURIComponent(query)}`;
      console.log(`[Hermes] Fallback navigation to: ${searchUrl}`);
      window.location.href = searchUrl;
    }

    await delay(3000);
    
    const deadline = startTime + timeoutMs;
    let targetElement = null;
    
    while (Date.now() < deadline) {
      const links = Array.from(document.querySelectorAll('a[href*="/groups/"]'));
      
      if (fbGroupId) {
        targetElement = links.find(link => {
          const href = link.getAttribute('href');
          return href.includes(`/groups/${fbGroupId}/`) || href.includes(`/groups/${fbGroupId}?`) || href.endsWith(`/groups/${fbGroupId}`);
        });
      }
      
      if (!targetElement && groupName) {
        const cleanGroupName = groupName.toLowerCase().trim();
        targetElement = links.find(link => {
          const text = link.innerText || link.textContent;
          return text && text.toLowerCase().includes(cleanGroupName);
        });
        
        if (!targetElement) {
          const spanTexts = Array.from(document.querySelectorAll('span, div')).filter(el => {
            const text = el.innerText || el.textContent;
            return text && text.toLowerCase().trim() === cleanGroupName;
          });
          if (spanTexts.length > 0) {
            targetElement = spanTexts[0].closest('a[href*="/groups/"]');
          }
        }
      }
      
      if (targetElement) {
        console.log('[Hermes] Target group found. Simulating click...');
        targetElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
        await delay(500);
        await simulateBezierMouseMoveAndClick(targetElement);
        return { success: true };
      }
      
      await delay(1000);
    }
    
    throw new Error('Group not found in search results within timeout');
  } catch (err) {
    console.error('[Hermes] FB_SEARCH_GROUP failed:', err.message);
    
    const failedPayload = {
      type: 'SEARCH_FAILED',
      commandId: commandId,
      fb_group_id: fbGroupId || null,
      group_name: groupName || null,
      reason: err.message.includes('timeout') ? 'TIMEOUT_EXCEEDED' : 'GROUP_NOT_FOUND',
      url: window.location.href,
      ts: Date.now()
    };
    
    await sendResultWithRetry({
      source: 'content',
      payload: failedPayload
    });
    
    return {
      success: false,
      errorCode: 'ERR-SEARCH-FAILED',
      errorDetail: err.message
    };
  }
}

function clearElement(el) {
  if (el.isContentEditable || el.getAttribute('contenteditable') === 'true') {
    el.innerHTML = '';
    el.dispatchEvent(new InputEvent('input', { bubbles: true }));
  } else {
    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
      window.HTMLInputElement.prototype, 'value'
    )?.set;
    if (nativeInputValueSetter) {
      nativeInputValueSetter.call(el, '');
    } else {
      el.value = '';
    }
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  }
}

async function waitForElement(targetId, timeoutMs) {
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    const snapshot = getSnapshot(true);
    const el = findElementByFingerprint(targetId, snapshot._fingerprintIndex);
    if (el) return true;
    await delay(300);
  }
  return false;
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

window.addEventListener('beforeunload', () => {
  chrome.runtime.sendMessage({
    source: 'content',
    payload: {
      type: 'SESSION_EVENT',
      event: 'ERROR',
      errorCode: 'ERR-DOM-02',
      payload: {
        message: 'Facebook tab unloaded / navigation started',
        url: window.location.href
      },
      ts: Date.now()
    }
  }).catch(() => {});
});

if (document.readyState === 'complete') {
  sendInitialSnapshot();
} else {
  window.addEventListener('load', sendInitialSnapshot);
}

function sendInitialSnapshot() {
  setTimeout(() => {
    const snapshot = getSnapshot(true);
    chrome.runtime.sendMessage({
      source: 'content',
      payload: {
        type: 'PAGE_LOADED',
        snapshot: {
          url: snapshot.url,
          title: snapshot.title,
          ts: snapshot.ts,
          page_ready: snapshot.page_ready,
          scrollY: snapshot.scrollY,
          viewportHeight: snapshot.viewportHeight,
          elementCount: snapshot.elementCount,
          elements: snapshot.elements,
          innerText: snapshot.innerText,
          visibleButtons: snapshot.visibleButtons,
          visibleInputs: snapshot.visibleInputs,
          activeModal: snapshot.activeModal,
          forms: snapshot.forms
        }
      }
    }).catch(() => {});
  }, 1000);
}

let keepAlivePort = null;

function setupContextGuard() {
  try {
    keepAlivePort = chrome.runtime.connect({ name: 'content-keepalive' });
    keepAlivePort.onDisconnect.addListener(() => {
      const error = chrome.runtime.lastError;
      if (error && error.message.includes('Extension context invalidated')) {
        console.warn('[Content] Extension context invalidated. Reloading tab...');
        window.location.reload();
      } else {
        setTimeout(setupContextGuard, 1000);
      }
    });
  } catch (err) {
    console.error('[Content] Cannot connect to extension:', err.message);
    window.location.reload();
  }
}

setupContextGuard();
```

---

## 7. popup.html / popup.js — Giao diện Popup

### 7.1 Giao diện `popup.html`

```html
<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Hermes FacePost</title>
  <link rel="stylesheet" href="popup.css">
</head>
<body>
  <div class="popup-container">
    <div class="popup-header">
      <img src="icons/icon48.png" alt="Hermes" class="logo" />
      <div>
        <h1>Hermes FacePost</h1>
        <span class="version">v2.2.0</span>
      </div>
    </div>

    <div class="status-card" id="statusCard">
      <div class="status-indicator" id="statusDot"></div>
      <div class="status-info">
        <div class="status-label">Dashboard</div>
        <div class="status-text" id="statusText">Đang kiểm tra...</div>
      </div>
    </div>

    <div class="meta-row" id="metaRow" style="display:none;">
      <span id="metaText"></span>
    </div>

    <div class="actions">
      <button id="btnRefresh" class="btn btn-secondary">
        🔄 Refresh
      </button>
      <button id="btnOpenDashboard" class="btn btn-primary">
        🚀 Mở Dashboard
      </button>
    </div>
  </div>

  <script src="popup.js"></script>
</body>
</html>
```

### 7.2 Logic `popup.js`

```javascript
/**
 * popup.js — Popup logic
 */

const DASHBOARD_URL = 'http://localhost:8765';

const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const metaRow = document.getElementById('metaRow');
const metaText = document.getElementById('metaText');
const btnRefresh = document.getElementById('btnRefresh');
const btnOpenDashboard = document.getElementById('btnOpenDashboard');

function renderStatus(status) {
  statusDot.className = 'status-indicator';

  if (!status) {
    statusDot.classList.add('connecting');
    statusText.textContent = 'Đang kiểm tra...';
    metaRow.style.display = 'none';
    return;
  }

  if (status.connected && status.authenticated) {
    statusDot.classList.add('connected');
    statusText.textContent = 'Đã kết nối ✓';
    metaRow.style.display = 'none';
  } else if (status.connected && !status.authenticated) {
    statusDot.classList.add('connecting');
    statusText.textContent = 'Đang xác thực...';
    metaRow.style.display = 'none';
  } else {
    statusDot.classList.add('disconnected');
    statusText.textContent = 'Mất kết nối';
    metaRow.style.display = 'block';
    metaText.textContent = `Đang thử kết nối lại... (lần ${status.reconnectAttempts || 0})`;
  }
}

async function checkStatus() {
  renderStatus(null);

  try {
    const status = await chrome.runtime.sendMessage({
      source: 'popup',
      type: 'GET_WS_STATUS'
    });
    renderStatus(status);
  } catch (err) {
    renderStatus({ connected: false, authenticated: false, reconnectAttempts: 0 });
  }
}

chrome.runtime.onMessage.addListener((message) => {
  if (message.source === 'background' && message.type === 'WS_STATUS_UPDATE') {
    if (message.status === 'CONNECTED') {
      renderStatus({ connected: true, authenticated: true });
    } else if (message.status === 'DISCONNECTED') {
      renderStatus({ connected: false, authenticated: false });
    }
  }
});

btnRefresh.addEventListener('click', () => {
  btnRefresh.disabled = true;
  btnRefresh.textContent = '🔄 ...';
  checkStatus().finally(() => {
    btnRefresh.disabled = false;
    btnRefresh.textContent = '🔄 Refresh';
  });
});

btnOpenDashboard.addEventListener('click', () => {
  chrome.tabs.create({ url: DASHBOARD_URL });
});

checkStatus();
```

---

## 8. WebSocket Auth Protocol — Xác thực và bắt tay

### 8.1 Giao thức bảo mật (Handshake Protocol)

```
CLIENT (offscreen.js)                    SERVER (Dashboard WebSocket)
       │                                        │
       │──── CONNECT ws://localhost:8765/ws ───►│
       │                                        │
       │──── HELLO {                            │
       │       type: "HELLO",                   │
       │       nonce: "uuid-v4",                │
       │       timestamp: 1718000000000,        │
       │       signature: hmac_sha256(          │
       │         secret,                        │
       │         nonce + ":" + timestamp        │
       │       ),                               │
       │       extensionVersion: "2.2.0",       │
       │       extension_mode: "GHOST",         │
       │       extension_id: "ext-id-xxx"       │
       │     }                                 ►│
       │                                        │
       │     Kiểm định phía Server:             │
       │       1. Xác thực HMAC Signature       │
       │       2. Lệch timestamp tối đa ±30s    │
       │       3. Nonce chưa từng xuất hiện     │
       │                                        │
       │◄─── WELCOME { type: "WELCOME",        │
       │               sessionId: "uuid",       │
       │               serverTime: 1718000000100│
       │             }                          │
       │                                        │
       │     [Connection AUTHENTICATED]         │
```

### 8.2 lib/hmac_sha256.js — Thực thi bằng Web Crypto API

```javascript
/**
 * lib/hmac_sha256.js — HMAC-SHA256 Web Crypto API
 */
export async function hmacSha256Hex(secretHex, message) {
  const keyBytes = hexToBytes(secretHex);
  const msgBytes = new TextEncoder().encode(message);

  const cryptoKey = await crypto.subtle.importKey(
    'raw',
    keyBytes,
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );

  const signature = await crypto.subtle.sign('HMAC', cryptoKey, msgBytes);
  return bytesToHex(new Uint8Array(signature));
}

export async function verifyHmacSha256(secretHex, message, signatureHex) {
  const expected = await hmacSha256Hex(secretHex, message);
  return constantTimeEqual(expected, signatureHex);
}

function hexToBytes(hex) {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < bytes.length; i++) {
    bytes[i] = parseInt(hex.substr(i * 2, 2), 16);
  }
  return bytes;
}

function bytesToHex(bytes) {
  return Array.from(bytes)
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
}

function constantTimeEqual(a, b) {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) {
    diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return diff === 0;
}
```

### 8.3 Xác thực phía Node.js Server (wsServer.js)

```javascript
const crypto = require('crypto');
const secret = process.env.HERMES_WS_SECRET;
const seenNonces = new Map();

function validateHandshake(helloMsg) {
  const { nonce, timestamp, signature } = helloMsg;

  const now = Date.now();
  if (Math.abs(now - timestamp) > 30000) {
    return { ok: false, reason: 'Timestamp out of range' };
  }

  if (seenNonces.has(nonce)) {
    return { ok: false, reason: 'Nonce replay detected' };
  }
  seenNonces.set(nonce, timestamp);

  for (const [n, ts] of seenNonces) {
    if (now - ts > 60000) seenNonces.delete(n);
  }

  const secretBytes = Buffer.from(secret, 'hex');
  const expectedSig = crypto
    .createHmac('sha256', secretBytes)
    .update(`${nonce}:${timestamp}`)
    .digest('hex');

  const valid = crypto.timingSafeEqual(
    Buffer.from(signature, 'hex'),
    Buffer.from(expectedSig, 'hex')
  );

  return valid ? { ok: true } : { ok: false, reason: 'Invalid signature' };
}
```

---

## 9. Luồng Dữ Liệu Tổng Thể

### 9.1 Luồng: Dashboard → Thực Thi Lệnh Trên Facebook

```
Dashboard                offscreen.js          background.js         content.js
    │                         │                     │                    │
    │──COMMAND──────────────► │                     │                    │
    │  {type:"EXECUTE",       │                     │                    │
    │   action:"CLICK",       │                     │                    │
    │   targetId:"a3f2c891"}  │                     │                    │
    │                         │                     │                    │
    │                         │──sendMessage──────► │                    │
    │                         │  {type:             │                    │
    │                         │   "DASHBOARD_CMD",  │                    │
    │                         │   payload:{...}}    │                    │
    │                         │                     │──sendMessage─────► │
    │                         │                     │  {type:            │
    │                         │                     │   "EXECUTE_CMD",   │
    │                         │                     │   command:{...}}   │
    │                         │                     │                    │
    │                         │                     │                    │──click el(a3f2c891)
    │                         │                     │                    │
    │                         │                     │ ◄──sendMessage─────│
    │                         │                     │  {type:"CMD_RESULT"│
    │                         │                     │   success:true}    │
    │                         │◄──sendMessage───────│                    │
    │                         │  relay result       │                    │
    │◄─────RESULT─────────────│                     │                    │
    │  {success:true,         │                     │                    │
    │   commandId:"..."}      │                     │                    │
```

---

## 10. Error Handling & Graceful Degradation

### 10.1 Matrix Xử Lý Lỗi

| Sự cố | Cách phát hiện | Phản hồi hệ thống |
|----------|--------|----------|
| Lỗi tạo Offscreen | `createDocument` throw error | Ghi nhận log lỗi, thực hiện kích hoạt lại sau 5 giây. |
| Mất kết nối WebSocket | Sự kiện `onclose` kích hoạt | Khởi chạy thuật toán Exponential Backoff tự động tái kết nối. |
| Xác thực thất bại | Nhận `AUTH_REJECT` | Đóng socket, cập nhật trạng thái ra popup giao diện. |
| Fingerprint DOM đổi | Trả về `null` khi tìm kiếm phần tử | Gửi payload thất bại `{success: false, errorCode: "ERR-DOM-01"}`. |
| Tab Facebook bị tắt | Giao tiếp thông điệp bị crash | Service Worker bắt sự kiện `onRemoved`, gửi báo cáo lỗi về Dashboard. |

---

## 11. Checklist Kiểm Thử

- [ ] **Khởi động & Bắt tay:** Cài đặt Extension, kiểm tra kết nối WebSocket tự động kích hoạt và xác thực thành công (nhận thông điệp `WELCOME`).
- [ ] **Heartbeat & Watchdog:** Ngắt kết nối mạng tạm thời, kiểm tra cơ chế gửi `PING` mỗi 10 giây và tự động đóng socket sau 20 giây mất kết nối (watchdog timeout) để tái kết nối.
- [ ] **Băm FNV-1a ổn định:** Thực hiện re-render trang Facebook, kiểm tra mã băm fingerprint 8 ký tự hex của các nút tương tác không thay đổi.
- [ ] **Mô phỏng tương tác:** Gửi lệnh click và gõ văn bản từ Dashboard, xác nhận các sự kiện chuột Bezier và bàn phím Gaussian kích hoạt đúng thứ tự.

---

## 12. Facebook Search & Human-like Interactions (Bezier & Gaussian)

### 12.1 Thuật Toán Di Chuyển Chuột Bezier
Mọi tương tác click giả lập phải di chuyển qua quỹ đạo cong Bezier bậc hai để tránh bị đánh giá tương tác tự động cơ học:
$$B(t) = (1-t)^2 P_0 + 2(1-t)t P_1 + t^2 P_2 \quad (0 \le t \le 1)$$
Trong đó $P_0$ là điểm bắt đầu, $P_2$ là tọa độ đích, và $P_1$ là điểm điều khiển được gán ngẫu nhiên lệch khỏi đường thẳng nối $P_0, P_2$.

### 12.2 Thuật Toán Gõ Phím Gaussian (Box-Muller Transform)
Tránh các chu kỳ trễ cố định hoặc phân phối đều. Sử dụng thuật toán Box-Muller biến đổi số ngẫu nhiên đều thành phân phối chuẩn Gaussian:
$$Z = \sqrt{-2 \ln U_1} \cos(2\pi U_2)$$
$$Delay = Z \cdot \sigma + \mu$$
Trong đó mean $\mu = 100\text{ms}$, standard deviation $\sigma = 30\text{ms}$. Giá trị trễ được chặn trong khoảng $[40\text{ms}, 300\text{ms}]$.

---

## 13. Phân tích lỗ hổng an ninh và yêu cầu khắc phục

### 🔴 LỖ HỔNG CRITICAL
1. **[SEC-01-01] Thao tác giả lập giao diện bị phát hiện do thiếu cờ `event.isTrusted`:**
   - *Rủi ro:* Sự kiện click và phím sinh bởi Javascript (`dispatchEvent`) luôn mang thuộc tính `isTrusted = false`. Hệ thống phát hiện bot của Facebook (như Akamai Bot Manager) dễ dàng lọc và đánh dấu checkpoint tài khoản khi phát hiện chuỗi tương tác thiếu tin cậy này.
   - *Biện pháp khắc phục:* Chuyển đổi cơ chế tương tác sang sử dụng **Chrome Debugger API** (`chrome.debugger`) gửi lệnh qua giao thức Chrome DevTools Protocol (CDP) (`Input.dispatchMouseEvent` / `Input.dispatchKeyEvent`) để đảm bảo cờ `isTrusted = true`.

### 🟠 LỖ HỔNG HIGH
1. **[SEC-01-02] Rò rỉ thông tin hoặc XSS thông qua việc thiếu kiểm duyệt URL điều hướng:**
   - *Rủi ro:* Lệnh `NAVIGATE` gán trực tiếp URL nhận từ WebSocket vào `window.location.href`. Kẻ tấn công nếu can thiệp được luồng truyền tin có thể gửi mã độc dạng `javascript:...` để chạy script đánh cắp phiên đăng nhập (cookies/tokens).
   - *Biện pháp khắc phục:* Thực hiện kiểm duyệt giao thức của URL thông qua đối tượng `new URL()`. Chỉ cho phép các giao thức an toàn `http:` và `https:`.

---
*Tài liệu đặc tả kiến trúc Extension Core | Version 2.2.0 | Thiết kế bởi Hermes FacePost-Group Design Team*
