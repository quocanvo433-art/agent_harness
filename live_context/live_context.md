# 📖 LIVE CONTEXT - NGỮ CẢNH PHIÊN LÀM VIỆC DỰ ÁN

> ⚡ **CẢNH BÁO CHO AI AGENT:** File này được sinh tự động bởi `live_context_loader.py`. Đọc kỹ và tuân thủ các neo kiến trúc dưới đây.
> **Thời gian cập nhật:** 2026-06-18 09:06:38
> **File đang thao tác:** `extension/popup.css`
> **Tài liệu neo tương ứng:** [Spec 01 - facepost_01_chrome_extension.md](file:////home/newuser/AI_facepostgroup/specs/facepost_01_chrome_extension.md)

---

## I. MỤC TIÊU THIẾT KẾ CỦA PHÂN HỆ VÀ SPEC CHỦ ĐẠO

# Hermes FacePost-Group — Chrome Extension Spec
## Module: `facepost_01_chrome_extension.md`
**Version:** 2.1.0 (Hot-Reload & Context Guard)
**Date:** 2026-06-15
**Status:** ACTIVE — Replaces v1.x (Pre-Audit)

## 🚨 CRITICAL WARNINGS & ANTI-PATTERNS (CHỐNG AI ẢO TƯỞNG)

### 1. `background.js` (Service Worker Relay)
* 🚨 **Cảnh báo đỏ (Lỗi lưu State):** **TUYỆT ĐỐI CẤM** khai báo biến toàn cục (`let token;`, `let activeSessions = {}`, `let isOffscreenCreating = false;`) ở tầng top-level để lưu trạng thái. Service Worker trong Manifest V3 là ephemeral (tạm thời)—Chrome sẽ giải phóng bộ nhớ và "giết" SW sau 30 giây rảnh. Khi SW thức dậy từ một sự kiện mới, toàn bộ biến toàn cục này sẽ bị reset về `undefined`.
* 🚀 **Yêu cầu bắt buộc:** Mọi dữ liệu cấu hình hoặc trạng thái bắt buộc phải đọc/ghi trực tiếp qua `chrome.storage.local` hoặc ủy nhiệm hoàn toàn cho `offscreen.js` nắm giữ. SW chỉ đóng vai trò một Hub chuyển tiếp tin nhắn (Stateless Message Relay). Lắng nghe sự kiện `chrome.tabs.onRemoved` để gửi tín hiệu đóng tab về Dashboard.

### 2. `offscreen.js` (Persistent WebSocket Host)
* 🚨 **Cảnh báo đỏ (Lỗi mất kết nối ngầm):** **CẤM** khởi tạo kết nối WebSocket theo kiểu phó mặc cho trình duyệt tự duy trì (`new WebSocket(url)` không có kiểm soát). Chrome vẫn có thể đóng băng tab ẩn nếu không có dữ liệu trao đổi liên tục.
* 🚀 **Yêu cầu bắt buộc:** Agent bắt buộc phải implement cơ chế **Heartbeat Ping/Pong hai chiều** định kỳ mỗi 10 giây nối trực tiếp với Dashboard Server. Nếu sau 2 chu kỳ (20 giây) không nhận được `PONG`, bắt buộc thực hiện ngắt kết nối chủ động và thực hiện tái kết nối theo thuật toán lũy thừa (Exponential Backoff) từ 1s đến tối đa 30s.

### 3. `dom_compressor.js` (Semantic DOM Compressor)
* 🚨 **Cảnh báo đỏ (Lỗi Race Condition):** **TUYỆT ĐỐI CẤM** dùng số chỉ mục tuần tự (sequential index như `id: 1, 2, 3...`) để định danh các phần tử trên giao diện Facebook. Khi React phía Facebook re-render hoặc người dùng cuộn chuột xuất hiện thêm comment, thứ tự index sẽ bị đảo lộn hoàn toàn, dẫn đến việc AI Agent gõ nhầm nội dung sang ô tìm kiếm hoặc bấm nhầm nút logout.
* 🚀 **Yêu cầu bắt buộc:** ID định danh (fingerprint) của phần tử bắt buộc phải là một chuỗi băm ổn định (Stable Hash 8 ký tự hex) được sinh ra bằng thuật toán băm FNV-1a 32-bit từ các thuộc tính phi tuần tự: `tag_name + role + aria-label + data-testid + rect` (x, y, width, height). Bổ sung cơ chế chụp ảnh base64/screenshot nếu hệ thống yêu cầu Vision AI.

---

## Mục Lục

1. [Tổng Quan Kiến Trúc](#1-tổng-quan-kiến-trúc)
2. [manifest.json — Cập Nhật MV3 Đúng Chuẩn](#2-manifestjson--cập-nhật-mv3-đúng-chuẩn)
3. [Offscreen Document Pattern — Fix A3 CRITICAL](#3-offscreen-document-pattern--fix-a3-critical)
4. [background.js — Service Worker Relay](#4-backgroundjs--service-worker-relay)
5. [dom_compressor.js — Fingerprint Hash Fix A4, B1](#5-dom_compressorjs--fingerprint-hash-fix-b1)
6. [content.js — Message Relay](#6-contentjs--message-relay)
7. [popup.html / popup.js — Fix C1](#7-popuphtml--popupjs--fix-c1)
8. [WebSocket Auth Protocol — Fix A4](#8-websocket-auth-protocol--fix-a4)
9. [Luồng Dữ Liệu Tổng Thể](#9-luồng-dữ-liệu-tổng-thể)
10. [Error Handling & Graceful Degradation](#10-error-handling--graceful-degradation)
11. [Checklist Kiểm Thử](#11-checklist-kiểm-thử)
12. [Facebook Search & Human-like Interactions (Bezier & Gaussian)](#12-facebook-search--human-like-interactions-bezier--gaussian)

---

## 1. Tổng Quan Kiến Trúc

### 1.1 Vấn Đề Cốt Lõi MV3 (Audit Findings)

Chrome Extension Manifest V3 áp đặt các ràng buộc **không thể bỏ qua**:

| Issue ID | Mức độ | Mô tả | Giải pháp |
|----------|--------|-------|-----------|
| **A3** | 🔴 CRITICAL | Service Worker bị Chrome terminate sau **30 giây** không activity → WebSocket đứt, biến global mất | **Offscreen Document API** giữ WebSocket persistent |
| **A4** | 🟠 HIGH | WebSocket không có auth token → bất kỳ process local nào có thể kết nối vào Dashboard | HMAC-SHA256 handshake với shared secret |
| **B1** | 🟠 HIGH | DOM element ID dùng `index` (0, 1, 2...) → race condition khi React re-render thay đổi thứ tự | Fingerprint stable: `SHA1_mini(tag+role+aria-label+innerText)` |
| **C1** | 🟡 LOW | `popup.html` khai báo trong manifest nhưng không có spec | Viết spec popup trạng thái kết nối |

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

> **Key insight:** Service Worker (`background.js`) **không giữ WebSocket**. Nó chỉ là relay trung gian. Toàn bộ WebSocket connection sống trong `offscreen.js` — một context không bao giờ bị Chrome kill chủ động khi có DOM activity.

---

## 2. manifest.json — Cập Nhật MV3 Đúng Chuẩn

### 2.1 Các Thay Đổi So Với v1.x

| Field | v1.x (Sai) | v2.0 (Đúng) | Lý do |
|-------|-----------|-------------|-------|
| `permissions` | `["proxy", "webRequest", ...]` | Bỏ `proxy`, bỏ `webRequest` | MV3 cấm `webRequest` blocking; `proxy` không cần |
| `permissions` | Không có `offscreen` | Thêm `"offscreen"` | Cần để dùng `chrome.offscreen` API |
| `background` | `"persistent": true` hoặc `scripts` array | `"service_worker": "background.js"` | MV3 bắt buộc |
| `offscreen` | Không có | Thêm entry `offscreen.html` | File HTML host cho Offscreen Document |

### 2.2 manifest.json Hoàn Chỉnh

```json
{
  "manifest_version": 3,
  "name": "Hermes FacePost-Group",
  "version": "2.0.0",
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
      "type": "module"  // Chrome 111+ (GAP-01-02: ES Module support)
    }
  ],

  // NOTE GAP-01-02: Nếu cần hỗ trợ Chrome < 111, dùng bundler (esbuild/webpack)
  // để bundle thành single file và bỏ "type": "module" ở trên.

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

> **Lưu ý `minimum_chrome_version: "116"`**: `chrome.offscreen` API chính thức stable từ Chrome 116. Thấp hơn sẽ throw `chrome.offscreen is not defined`.
>
> **GAP-01-02 — ES Module:** `"type": "module"` trong `content_scripts` yêu cầu Chrome ≥ 111. Do `minimum_chrome_version` đã set là `"116"`, điều kiện này đã được thỏa mãn. Nếu hạ minimum xuống dưới 111, phải dùng bundler (esbuild/webpack) thay thế.

### 2.3 File Structure Của Extension

```
hermes-facepost/
├── manifest.json
├── background.js          # Service Worker — relay only
├── offscreen.html         # Offscreen Document HTML shell
├── offscreen.js           # Offscreen Document logic — holds WebSocket
├── content.js             # Content script injected vào Facebook tabs
├── dom_compressor.js      # DOM fingerprint + compress utility
├── popup.html             # Extension popup UI
├── popup.js               # Popup logic
├── popup.css              # Popup styles
├── icons/
│   ├── icon16.png
│   ├── icon48.png
│   └── icon128.png
└── lib/
    └── hmac_sha256.js     # HMAC-SHA256 implementation (pure JS)
```

---

## 3. Offscreen Document Pattern — Fix A3 CRITICAL

### 3.1 Tại Sao Cần Offscreen Document?

**Service Worker Lifecycle Problem:**

```
Timeline:
T=0s   : Chrome khởi động Service Worker (background.js)
T=0s   : SW mở WebSocket tới ws://localhost:8765
T=30s  : Không có event nào → Chrome TERMINATE Service Worker
         ↳ WebSocket connection bị ĐÓNG NGAY LẬP TỨC
         ↳ Mọi biến global (ws, messageQueue, sessionId) = MẤT
T=31s  : Dashboard gửi lệnh → WS broken → timeout
T=31s  : SW wake up (vì có alarm/message) nhưng ws = null
         ↳ Phải reconnect → mất 2-5 giây delay
         ↳ Race condition nếu có lệnh queue
```

**Offscreen Document Solution:**

```
Offscreen Document lifecycle:
- Tạo bằng chrome.offscreen.createDocument()
- Có DOM (document object) → Chrome KHÔNG terminate như SW
- Persistent cho đến khi extension bị disable/uninstall
- WebSocket sống MÃNH MẼ trong offscreen.js

Service Worker role:
- Chỉ là RELAY MESSAGE giữa content.js ↔ offscreen.js
- Nếu SW bị kill → khi wake up lại, offscreen.js vẫn còn kết nối
- SW hỏi "WS status?" → offscreen.js trả lời
```

### 3.2 Thuật Toán Keepalive

```pseudocode
OFFSCREEN_KEEPALIVE_ALGORITHM:

CONSTANTS:
  PING_INTERVAL = 20000ms  // Gửi ping mỗi 20s (dưới ngưỡng 30s kill)
  RECONNECT_DELAY_BASE = 1000ms
  RECONNECT_DELAY_MAX = 30000ms
  RECONNECT_MULTIPLIER = 2

STATE:
  ws: WebSocket | null = null
  pingTimer: Timer | null = null
  reconnectTimer: Timer | null = null
  reconnectAttempts: int = 0
  isAuthenticated: bool = false

PROCEDURE connect(serverUrl, authSecret):
  ws = new WebSocket(serverUrl)
  
  ON ws.open:
    reconnectAttempts = 0
    // Bắt đầu auth handshake ngay
    CALL performHandshake(authSecret)
    // Bắt đầu ping loop
    CALL startPingLoop()
  
  ON ws.message(event):
    IF isAuthenticated:
      CALL routeMessage(event.data)
    ELSE:
      CALL handleAuthResponse(event.data)
  
  ON ws.close(code, reason):
    isAuthenticated = false
    CALL stopPingLoop()
    CALL scheduleReconnect()
  
  ON ws.error:
    // error event luôn đi kèm close event → không cần xử lý riêng

PROCEDURE startPingLoop():
  pingTimer = setInterval(() => {
    IF ws.readyState == OPEN AND isAuthenticated:
      ws.send(JSON.stringify({ type: "PING", ts: Date.now() }))
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

PROCEDURE routeMessage(rawData):
  msg = JSON.parse(rawData)
  IF msg.type == "PONG": RETURN  // heartbeat ok, ignore
  // Relay sang Service Worker → content.js
  chrome.runtime.sendMessage({ source: "offscreen", payload: msg })
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
  <!-- Không cần UI — đây là invisible document -->
  <script src="offscreen.js" type="module"></script>
</body>
</html>
```

### 3.4 offscreen.js — Code Đầy Đủ

```javascript
/**
 * offscreen.js
 * Hermes FacePost-Group — Offscreen Document
 *
 * Đây là module duy nhất giữ WebSocket connection persistent.
 * Service Worker (background.js) KHÔNG giữ WebSocket — chỉ relay messages.
 *
 * Fix: A3 CRITICAL — Service Worker 30s kill problem
 */

import { hmacSha256Hex } from './lib/hmac_sha256.js';

// ─────────────────────────────────────────────
// ─────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────
// GAP-01-01: WS URL đã đổi sang port 8765/ws, hỗ trợ dynamic config
const DEFAULT_WS_URL = 'ws://127.0.0.1:8765/ws';
let WS_URL = DEFAULT_WS_URL; // Được ghi đè từ chrome.storage.local khi init()
const PING_INTERVAL_MS = 10_000;       // 10 giây heartbeat ping
const RECONNECT_BASE_MS = 1_000;
const RECONNECT_MAX_MS = 30_000;
const RECONNECT_MULTIPLIER = 2;
const HANDSHAKE_TIMEOUT_MS = 5_000;

// ─────────────────────────────────────────────
// State
// ─────────────────────────────────────────────
let ws = null;
let pingTimer = null;
let reconnectTimer = null;
let reconnectAttempts = 0;
let isAuthenticated = false;
let authSecret = null;
let pendingHandshakeResolve = null;
let handshakeTimeoutTimer = null;
let lastPongTime = 0;

// ─────────────────────────────────────────────
// Init — Load secret từ storage rồi connect
// ─────────────────────────────────────────────
async function init() {
  // GAP-01-01: Load cả wsUrl (dynamic) lẫn auth secret từ storage
  const data = await chrome.storage.local.get(['ws_auth_secret', 'wsUrl']);
  if (!data.ws_auth_secret) {
    console.error('[Offscreen] Chưa có auth secret. Abort.');
    notifyBackground({ type: 'WS_STATUS', status: 'NO_SECRET' });
    return;
  }
  authSecret = data.ws_auth_secret;
  // Override WS_URL nếu user đã config custom URL
  if (data.wsUrl) WS_URL = data.wsUrl;
  connect();
}

// GAP-01-01: Lắng nghe lệnh RECONNECT khi popup thay đổi config
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

// ─────────────────────────────────────────────
// WebSocket Connection
// ─────────────────────────────────────────────
function connect() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    return; // Đã có kết nối, bỏ qua
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
    lastPongTime = Date.now(); // Khởi tạo lastPongTime khi auth OK
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
    // Chỉ xử lý auth messages khi chưa authenticated
    handleAuthResponse(msg);
    return;
  }

  if (msg.type === 'PONG') {
    lastPongTime = Date.now(); // Cập nhật thời gian nhận PONG cuối cùng
    return; // Heartbeat response — bỏ qua
  }

  // ── Extension Hot-Reload Handler (OTA Update) ──────────────
  // Khi Dashboard gửi lệnh reload extension (sau OTA update),
  // offscreen.js relay lên Service Worker để trigger chrome.runtime.reload().
  if (msg.type === 'EXTENSION_RELOAD') {
    chrome.runtime.sendMessage({
      source: 'offscreen',
      type: 'TRIGGER_RELOAD',
      reason: msg.reason || 'OTA update applied'
    }).catch(() => {});
    return;
  }

  // Relay lệnh từ Dashboard → Service Worker → content.js
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
  // error luôn đi kèm close event — chỉ log
  console.error('[Offscreen] WebSocket error:', event);
}

// ─────────────────────────────────────────────
// Auth Handshake
// ─────────────────────────────────────────────
/**
 * Gửi HELLO với HMAC-SHA256 challenge-response.
 * Protocol chi tiết xem Section 8.
 */
function performHandshake() {
  return new Promise((resolve, reject) => {
    // Tạo nonce ngẫu nhiên
    const nonce = crypto.randomUUID();
    const timestamp = Date.now();

    // Tính HMAC signature
    hmacSha256Hex(authSecret, `${nonce}:${timestamp}`).then(signature => {
      const manifest = chrome.runtime.getManifest();
      const helloMsg = {
        type: 'HELLO',
        nonce,
        timestamp,
        signature,
        extensionVersion: manifest.version || '2.0.0'
      };

      ws.send(JSON.stringify(helloMsg));

      // Timeout nếu server không trả lời
      handshakeTimeoutTimer = setTimeout(() => {
        reject(new Error('Handshake timeout'));
      }, HANDSHAKE_TIMEOUT_MS);

      // Store resolve để dùng trong handleAuthResponse
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
    // pendingHandshakeResolve sẽ không được gọi → Promise reject từ timeout
    console.error('[Offscreen] Auth rejected by server:', msg.reason || msg.errorDetail);
    ws.close(1008, 'Auth rejected');
  }
}

// ─────────────────────────────────────────────
// Ping / Keepalive Loop
// ─────────────────────────────────────────────
function startPingLoop() {
  stopPingLoop(); // Clear bất kỳ timer cũ nào
  pingTimer = setInterval(() => {
    if (ws && ws.readyState === WebSocket.OPEN && isAuthenticated) {
      const now = Date.now();
      // Nếu quá 2 chu kỳ (20s) không nhận được PONG, chủ động ngắt kết nối để reconnect
      if (now - lastPongTime >= PING_INTERVAL_MS * 2) {
        console.warn('[Offscreen] Missed 2 PONGs. Actively closing connection to trigger reconnect.');
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

// ─────────────────────────────────────────────
// Exponential Backoff Reconnect
// ─────────────────────────────────────────────
function scheduleReconnect() {
  if (reconnectTimer) return; // Đã có timer, bỏ qua

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

// ─────────────────────────────────────────────
// Message Handler: Nhận lệnh từ background.js
// ─────────────────────────────────────────────
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

  return true; // Keep message channel open for async sendResponse
});

// ─────────────────────────────────────────────
// Utility: Notify background.js
// ─────────────────────────────────────────────
function notifyBackground(payload) {
  chrome.runtime.sendMessage({
    source: 'offscreen',
    ...payload
  }).catch(() => {
    // Service Worker có thể đang sleep — không có gì để lo
  });
}

// ─────────────────────────────────────────────
// Bootstrap
// ─────────────────────────────────────────────
init();
```

---

## 4. background.js — Service Worker Relay

### 4.1 Vai Trò Và Giới Hạn

**background.js KHÔNG làm:**
- ❌ Giữ WebSocket connection
- ❌ Store state quan trọng trong biến global (sẽ mất khi SW bị kill)
- ❌ Làm bất cứ thứ gì cần persistent memory

**background.js CHỈ làm:**
- ✅ Đảm bảo Offscreen Document đang chạy
- ✅ Relay messages: `content.js ↔ offscreen.js`
- ✅ Relay messages: `popup.js ↔ offscreen.js`
- ✅ Nhận status updates từ `offscreen.js` và broadcast

### 4.2 background.js — Code Đầy Đủ

```javascript
/**
 * background.js
 * Hermes FacePost-Group — Service Worker (MV3)
 *
 * ROLE: Message relay only. No WebSocket. No persistent state.
 *
 * Fix: A3 — Không giữ WebSocket, delegate cho offscreen.js
 */

const OFFSCREEN_DOCUMENT_PATH = 'offscreen.html';

// ─────────────────────────────────────────────
// Startup: Tạo Offscreen Document ngay khi SW khởi động
// ─────────────────────────────────────────────
chrome.runtime.onInstalled.addListener(async () => {
  await ensureOffscreenDocument();
});

chrome.runtime.onStartup.addListener(async () => {
  await ensureOffscreenDocument();
});

// Đảm bảo Offscreen Document sống khi SW wake up
self.addEventListener('activate', async () => {
  await ensureOffscreenDocument();
});

// ─────────────────────────────────────────────
// Ensure Offscreen Document Exists (Stateless)
// ─────────────────────────────────────────────
async function ensureOffscreenDocument() {
  // Kiểm tra xem document đã tồn tại chưa
  const existingContexts = await chrome.runtime.getContexts({
    contextTypes: ['OFFSCREEN_DOCUMENT'],
    documentUrls: [chrome.runtime.getURL(OFFSCREEN_DOCUMENT_PATH)]
  });

  if (existingContexts.length > 0) {
    return; // Đã có — không cần tạo
  }

  // Chống race condition bằng cách dùng chrome.storage.local để lock thay vì biến top-level
  const lock = await chrome.storage.local.get(['isOffscreenCreating']);
  if (lock.isOffscreenCreating) {
    return;
  }

  await chrome.storage.local.set({ isOffscreenCreating: true });
  try {
    await chrome.offscreen.createDocument({
      url: OFFSCREEN_DOCUMENT_PATH,
      // GAP-01-03: 'BLOBS' không hợp lệ cho WS use-case.
      // Chrome 120+: dùng 'WEB_RTC' hoặc 'TESTING'. 'TESTING' là lý do phổ quát nhất.
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

// ─────────────────────────────────────────────
// Lắng nghe sự kiện đóng Tab để báo về Dashboard
// ─────────────────────────────────────────────
chrome.tabs.onRemoved.addListener(async (tabId, removeInfo) => {
  await ensureOffscreenDocument();
  chrome.runtime.sendMessage({
    target: 'offscreen',
    type: 'SEND_TO_DASHBOARD',
    payload: {
      type: 'SESSION_EVENT',
      event: 'ERROR',
      errorCode: 'ERR-DOM-02', // Hoặc code thích hợp báo lỗi điều hướng/tab mất kết nối
      payload: {
        message: `Tab ${tabId} was closed by user or browser`,
        tabId: tabId
      },
      ts: Date.now()
    }
  }).catch(() => {});
});

// ─────────────────────────────────────────────
// Message Router
// ─────────────────────────────────────────────
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  const source = message.source || 'unknown';

  // === Messages từ content.js (Facebook tab) ===
  if (source === 'content') {
    handleContentMessage(message, sender, sendResponse);
    return true;
  }

  // === Messages từ offscreen.js ===
  if (source === 'offscreen') {
    handleOffscreenMessage(message, sender, sendResponse);
    return true;
  }

  // === Messages từ popup.js ===
  if (source === 'popup') {
    handlePopupMessage(message, sender, sendResponse);
    return true;
  }

  return false;
});

// ─────────────────────────────────────────────
// Handler: content.js → offscreen.js → Dashboard
// ─────────────────────────────────────────────
async function handleContentMessage(message, sender, sendResponse) {
  await ensureOffscreenDocument(); // Đảm bảo offscreen alive

  // Relay DOM snapshot hoặc action result tới Dashboard qua offscreen
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

// ─────────────────────────────────────────────
// Handler: offscreen.js → broadcast tới popup & content
// ─────────────────────────────────────────────
async function handleOffscreenMessage(message, sender, sendResponse) {
  if (message.type === 'WS_STATUS') {
    // Broadcast status tới tất cả popup đang mở
    chrome.runtime.sendMessage({
      source: 'background',
      type: 'WS_STATUS_UPDATE',
      status: message.status
    }).catch(() => {}); // Popup có thể không mở
    return;
  }

  // ── Extension Hot-Reload (OTA Update) ──────────────────────
  // Offscreen gửi TRIGGER_RELOAD khi nhận EXTENSION_RELOAD từ Dashboard WS.
  // Service Worker ghi log lý do reload → gọi chrome.runtime.reload().
  if (message.type === 'TRIGGER_RELOAD') {
    console.log('[BG] Extension reload triggered:', message.reason);
    // Ghi log lý do reload vào storage trước khi reload
    await chrome.storage.local.set({
      lastReloadReason: message.reason,
      lastReloadAt: Date.now()
    });
    chrome.runtime.reload();
    return;
  }

  if (message.type === 'DASHBOARD_COMMAND') {
    // GAP-01-05: Thay broadcast bằng targeted routing để tránh race condition
    const cmd = message.payload;
    
    // Bổ sung cơ chế chụp ảnh nếu Dashboard yêu cầu
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
              screenshot: dataUrl, // Trả về base64 screenshot
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

// Helper lấy active Facebook tab ID
async function getActiveFacebookTabId() {
  const [activeTab] = await chrome.tabs.query({
    url: ['https://*.facebook.com/*', 'https://*.fb.com/*'],
    active: true,
    currentWindow: true
  });
  return activeTab?.id || null;
}

// ─────────────────────────────────────────────
// GAP-01-05: Targeted Command Routing (thay thế broadcast)
// ─────────────────────────────────────────────
/**
 * Route lệnh đến tab cụ thể (targetTabId) hoặc active Facebook tab duy nhất.
 * KHÔNG broadcast tới tất cả tabs — tránh race condition khi nhiều tab FB mở.
 */
async function sendCommandToTab(cmd) {
  if (cmd.targetTabId) {
    // Lệnh có target tab cụ thể — gửi trực tiếp
    chrome.tabs.sendMessage(cmd.targetTabId, {
      source: 'background',
      type: 'EXECUTE_COMMAND',
      command: cmd
    }).catch(err => {
      console.error(`[BG] Failed to send to tab ${cmd.targetTabId}:`, err);
    });
    return;
  }

  // Fallback: chỉ gửi tới active Facebook tab trong current window
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

// ─────────────────────────────────────────────
// Handler: popup.js → query status
// ─────────────────────────────────────────────
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

// ─────────────────────────────────────────────
// Alarm để keep SW alive (backup mechanism)
// ─────────────────────────────────────────────
// GAP-01-06: Chrome minimum alarm period là 0.5 phút (30s).
chrome.alarms.create('keepalive', { periodInMinutes: 0.5 });

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === 'keepalive') {
    await ensureOffscreenDocument();
  }
});
```

---

## 5. dom_compressor.js — Fingerprint Hash Fix B1

### 5.1 Vấn Đề Index-Based ID

**Lỗi B1 — Race condition với React re-render:**

```
Scenario:
T=0: Dashboard gửi lệnh "Click element id=2" (index 2 trong list)
T=0: content.js nhận lệnh, chuẩn bị click element[2]
T=0.1: Facebook React re-render (notification arrive, UI update)
T=0.1: Element cũ ở index 2 = gone. Phần tử mới ở index 2 = khác hoàn toàn
T=0.2: content.js click vào element[2] = SAI PHẦN TỬ 🔴

Root cause: ID là số thứ tự trong array → không stable qua re-render
```

### 5.2 Thuật Toán Fingerprint Hash

```pseudocode
FINGERPRINT_ALGORITHM:

INPUT: element (DOM Node)
OUTPUT: fingerprint_hex (string, 8 chars)

STEP 1 — Thu thập attributes ổn định:
  tag = element.tagName.toLowerCase()
  role = element.getAttribute("role") || ""
  aria_label = element.getAttribute("aria-label") || ""
  inner_text = element.innerText?.trim().slice(0, 50) || ""
  data_type = element.getAttribute("data-type") || ""
  href_path = element.href ? new URL(element.href).pathname.slice(0, 30) : ""

STEP 2 — Tạo fingerprint string:
  raw = tag + "|" + role + "|" + aria_label + "|" + inner_text
        + "|" + data_type + "|" + href_path

STEP 3 — Hash bằng SHA1_mini (djb2 variant, 32-bit):
  hash = 5381
  FOR each char in raw:
    hash = ((hash << 5) + hash) + char.charCodeAt(0)
    hash = hash & 0xFFFFFFFF  // Keep 32-bit
  fingerprint = hash.toString(16).padStart(8, '0')

STEP 4 — Handle collision (same fingerprint):
  IF fingerprint đã tồn tại trong elementMap:
    suffix = collision_count[fingerprint]++
    fingerprint = fingerprint + "_" + suffix

RETURN fingerprint

EXAMPLE:
  <button role="button" aria-label="Đăng" ...>Đăng</button>
  raw = "button|button|Đăng|Đăng||"
  fingerprint = "a3f2c891"
```

### 5.3 dom_compressor.js — Code Đầy Đủ

```javascript
/**
 * dom_compressor.js
 * Hermes FacePost-Group — DOM Compression Utility
 *
 * Chuyển DOM snapshot thành định dạng nhỏ gọn cho AI Agent.
 * Dùng FNV-1a 32-bit fingerprint hash ổn định thay vì index.
 *
 * Fix: B1 — Stable element fingerprint (không dùng array index)
 */

// ─────────────────────────────────────────────
// Fingerprint Engine
// ─────────────────────────────────────────────

/**
 * Tạo fingerprint 8-char hex ổn định cho một DOM element.
 * Dựa trên: tag, role, aria-label, data-testid, rect (x, y, width, height)
 * Dùng FNV-1a 32-bit stable hash.
 *
 * @param {Element} el - DOM Element
 * @param {Map<string, number>} [collisionMap] - Track fingerprint collisions
 * @returns {string} - 8-char hex fingerprint
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

  // FNV-1a 32-bit hash → 8-char hex
  let hash = 2166136261;
  for (let i = 0; i < raw.length; i++) {
    hash ^= raw.charCodeAt(i);
    hash = (hash * 16777619) >>> 0;
  }
  const baseHash = hash.toString(16).padStart(8, '0');

  if (!collisionMap) {
    return baseHash;
  }

  // Collision handling: thêm suffix nếu hash đã tồn tại
  const count = collisionMap.get(baseHash) || 0;
  collisionMap.set(baseHash, count + 1);

  return count === 0 ? baseHash : `${baseHash}_${count}`;
}

// ─────────────────────────────────────────────
// Element Selectors — Các phần tử Facebook quan trọng
// ─────────────────────────────────────────────

const INTERACTIVE_SELECTORS = [
  // Buttons & links
  'button',
  'a[href]',
  '[role="button"]',
  '[role="link"]',
  '[role="menuitem"]',

  // Input fields
  'input:not([type="hidden"])',
  'textarea',
  '[contenteditable="true"]',
  '[role="textbox"]',

  // Facebook-specific
  '[data-testid]',
  '[aria-label]',

  // Form controls
  'select',
  '[role="checkbox"]',
  '[role="radio"]',
  '[role="combobox"]',
].join(',');

// ─────────────────────────────────────────────
// DOM Snapshot Builder
// ─────────────────────────────────────────────

/**
 * Snapshot DOM của trang hiện tại thành cấu trúc nhỏ gọn.
 * Mỗi element có fingerprint ID ổn định.
 *
 * @param {object} options
 * @param {number} [options.maxElements=200] - Giới hạn số element
 * @param {boolean} [options.visibleOnly=true] - Chỉ lấy element visible
 * @returns {object} - DOM snapshot
 */
function compressDOM({ maxElements = 200, visibleOnly = true } = {}) {
  const elements = document.querySelectorAll(INTERACTIVE_SELECTORS);
  const collisionMap = new Map();
  const fingerprintIndex = new Map(); // fingerprint → DOM element (for lookup)
  const snapshot = [];

  for (const el of elements) {
    if (snapshot.length >= maxElements) break;

    // Skip hidden elements nếu cần
    if (visibleOnly && !isVisible(el)) continue;

    // Skip elements bên ngoài viewport (quá xa)
    const rect = el.getBoundingClientRect();
    if (rect.bottom < -500 || rect.top > window.innerHeight + 500) continue;

    const fingerprint = generateFingerprint(el, collisionMap);

    // Store mapping để content.js có thể lookup element từ fingerprint
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
      // Extended fields (Spec 00 / Spec 05 derived)
      href: (() => {
        try { return el.href ? new URL(el.href).pathname : null; } catch { return null; }
      })(),
      src: el.getAttribute('src') || null,
      name: el.getAttribute('name') || null,
      dataTestid: el.getAttribute('data-testid') || null,
      contentEditable: el.isContentEditable || el.getAttribute('contenteditable') === 'true',
      inputType: el.tagName.toLowerCase() === 'input' ? el.type : null
    };

    // Loại bỏ null/undefined values để giảm payload size
    for (const key of Object.keys(entry)) {
      if (entry[key] === null || entry[key] === undefined) {
        delete entry[key];
      }
    }

    snapshot.push(entry);
  }

  // --- Derived / Aggregated Fields (Spec 00) ---
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
    // Derived/Aggregated
    innerText: innerTextAgg,
    visibleButtons,
    visibleInputs,
    activeModal,
    forms,
    // fingerprintIndex không serialize — chỉ dùng nội bộ trong content.js
    _fingerprintIndex: fingerprintIndex
  };
}

/**
 * Kiểm tra element có visible không (không phải display:none / visibility:hidden).
 * @param {Element} el
 * @returns {boolean}
 */
function isVisible(el) {
  if (!el.offsetParent && el.tagName !== 'BODY') return false;
  const style = window.getComputedStyle(el);
  return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
}

/**
 * Tìm DOM element từ fingerprint ID.
 * @param {string} fingerprint
 * @param {Map} fingerprintIndex
 * @returns {Element|null}
 */
function findElementByFingerprint(fingerprint, fingerprintIndex) {
  return fingerprintIndex.get(fingerprint) || null;
}

// Export cho content.js
export { compressDOM, findElementByFingerprint, generateFingerprint };
```

---

## 6. content.js — Message Relay

### 6.1 Vai Trò

`content.js` chạy trong context của Facebook tab. Nhiệm vụ:
1. Chụp DOM snapshot và gửi lên Dashboard qua background.js
2. Nhận lệnh từ background.js và thực thi trên DOM
3. Báo cáo kết quả thực thi

### 6.2 content.js — Code Đầy Đủ

```javascript
/**
 * content.js
 * Hermes FacePost-Group — Content Script (Facebook Tab)
 *
 * Chạy trong isolated world của Facebook tab.
 * Giao tiếp với background.js qua chrome.runtime.sendMessage.
 */

import { compressDOM, findElementByFingerprint } from './dom_compressor.js';

// ─────────────────────────────────────────────
// Constants & Configuration (Spec 00 Section 6)
// ─────────────────────────────────────────────
const CHAR_DELAY_MIN = 40;
const CHAR_DELAY_MAX = 180;

// Gaussian random generation using Box-Muller Transform
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

// ─────────────────────────────────────────────
// State
// ─────────────────────────────────────────────
let currentSnapshot = null;   // Snapshot DOM gần nhất
let lastSnapshotTs = 0;
const SNAPSHOT_THROTTLE_MS = 500; // Không chụp nhanh hơn 500ms

// ─────────────────────────────────────────────
// Message Listener — Nhận lệnh từ background.js
// ─────────────────────────────────────────────
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.source !== 'background') return;

  switch (message.type) {
    case 'EXECUTE_COMMAND':
      handleCommand(message.command, sendResponse);
      return true; // Async

    case 'GET_DOM_SNAPSHOT':
      handleGetSnapshot(message, sendResponse);
      return true;

    default:
      console.warn('[Content] Unknown message type:', message.type);
  }
});

// ─────────────────────────────────────────────
// Command Executor (Spec 00 Reconciled)
// ─────────────────────────────────────────────
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
        const fresh = getSnapshot(true); // Force fresh
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

  // Flatten the response payload to match Spec 00
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

  // GAP-01-08: Gửi kết quả với retry nếu SW bị kill giữa chừng
  await sendResultWithRetry({
    source: 'content',
    payload: responsePayload
  });

  sendResponse(result);
}

/**
 * GAP-01-08: Retry sending result về background khi SW có thể đang restart.
 * Exponential backoff 1s → 2s → 3s. Fallback cuối: postMessage cho offscreen document.
 * @param {object} message - Message object để gửi
 * @param {number} maxRetries
 */
async function sendResultWithRetry(message, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      await chrome.runtime.sendMessage(message);
      return; // Thành công
    } catch (e) {
      console.warn(`[Content] sendMessage attempt ${i + 1} failed:`, e.message);
      if (i < maxRetries - 1) await delay(1000 * (i + 1)); // backoff: 1s, 2s
    }
  }
  // Last resort: postMessage vào window để offscreen document listener (nếu có) bắt được
  console.error('[Content] All retries failed. Posting RESULT_FALLBACK to window.');
  window.postMessage({ type: 'RESULT_FALLBACK', ...message }, '*');
}

// ─────────────────────────────────────────────
// DOM Snapshot
// ─────────────────────────────────────────────
function getSnapshot(forceRefresh = false) {
  const now = Date.now();
  if (!forceRefresh && currentSnapshot && (now - lastSnapshotTs) < SNAPSHOT_THROTTLE_MS) {
    return currentSnapshot; // Dùng cache
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

// ─────────────────────────────────────────────
// DOM Action Helpers (Smart Injector - Spec 00 Section 4)
// ─────────────────────────────────────────────

async function injectContentEditable(element, text) {
  element.focus();
  await delay(150); // Đợi focus event propagate

  // Clear existing content
  document.execCommand('selectAll', false, null);
  document.execCommand('delete', false, null);
  await delay(100);

  // Insert text character by character với human delay
  for (const char of text) {
    document.execCommand('insertText', false, char);
    await delay(charDelayGaussian(100, 30));
  }
  await delay(200);

  // Dispatch synthetic events để React reconciler nhận
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
  // Clear trước
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

/**
 * Giả lập đường di chuyển chuột Bezier từ vị trí hiện tại đến phần tử
 * rồi kích hoạt chuỗi sự kiện hover, mousedown, mouseup, click.
 */
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

/**
 * Giả lập gõ phím với trễ Gaussian từng ký tự.
 */
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

/**
 * Thực hiện tìm kiếm và chọn group trên Facebook.
 * Hỗ trợ so khớp fb_group_id hoặc group_name (fallback).
 * Nếu tìm thấy, di chuyển chuột Bezier và click vào kết quả.
 * Nếu thất bại, gửi message SEARCH_FAILED qua WebSocket về Dashboard.
 */
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
    // Thử tương tác UI trên Home page trước
    const isHome = window.location.pathname === '/' || window.location.pathname === '/home.php';
    let searchInput = document.querySelector('input[placeholder*="Tìm kiếm"], input[aria-label*="Search Facebook"], input[placeholder*="Search Facebook"]');
    
    if (isHome && searchInput) {
      console.log('[Hermes] Found search input on Home. Performing human-like search interaction.');
      await simulateBezierMouseMoveAndClick(searchInput);
      await simulateGaussianTyping(searchInput, query);
      searchInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true }));
      searchInput.dispatchEvent(new KeyboardEvent('keypress', { key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true }));
      searchInput.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true }));
      
      const form = searchInput.closest('form');
      if (form) form.submit();
    } else {
      // Fallback: Navigate trực tiếp
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

/**
 * Chờ element với fingerprint ID xuất hiện trong DOM.
 * @param {string} targetId - Fingerprint ID
 * @param {number} timeoutMs
 * @returns {Promise<boolean>}
 */
async function waitForElement(targetId, timeoutMs) {
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    const snapshot = getSnapshot(true); // Force fresh snapshot
    const el = findElementByFingerprint(targetId, snapshot._fingerprintIndex);
    if (el) return true;
    await delay(300);
  }
  return false;
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Gửi tín hiệu đóng tab / unload khi tab sắp đóng hoặc chuyển hướng
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

// ─────────────────────────────────────────────
// Auto-snapshot khi page load xong
// ─────────────────────────────────────────────
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
  }, 1000); // 1s delay để Facebook JS init xong
}

// ── Extension Context Invalidation Handler ──────────────────
// Khi extension reload (OTA update), context bị vô hiệu.
// Content script phải phát hiện và reload tab Facebook để tránh crash.
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
        // Reconnect attempt (Service Worker wake up)
        setTimeout(setupContextGuard, 1000);
      }
    });
  } catch (err) {
    // Extension đã bị unload hoàn toàn
    console.error('[Content] Cannot connect to extension:', err.message);
    window.location.reload();
  }
}

setupContextGuard();
```

---

## 7. popup.html / popup.js — Fix C1

### 7.1 Spec Popup

Popup hiển thị:
1. **Trạng thái kết nối Dashboard**: `Connected ✅` / `Disconnected ❌` / `Connecting... 🟡`
2. **Số lần reconnect** (nếu disconnected)
3. **Nút Refresh** — Force re-check status
4. **Link "Open Dashboard"** — Mở `http://localhost:8765` tab mới

### 7.2 popup.html

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
    <!-- Header -->
    <div class="popup-header">
      <img src="icons/icon48.png" alt="Hermes" class="logo" />
      <div>
        <h1>Hermes FacePost</h1>
        <span class="version">v2.0.0</span>
      </div>
    </div>

    <!-- Status Card -->
    <div class="status-card" id="statusCard">
      <div class="status-indicator" id="statusDot"></div>
      <div class="status-info">
        <div class="status-label">Dashboard</div>
        <div class="status-text" id="statusText">Đang kiểm tra...</div>
      </div>
    </div>

    <!-- Meta info -->
    <div class="meta-row" id="metaRow" style="display:none;">
      <span id="metaText"></span>
    </div>

    <!-- Actions -->
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

### 7.3 popup.css

```css
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  width: 280px;
  min-height: 160px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #0f0f23;
  color: #e2e8f0;
}

.popup-container {
  padding: 16px;
}

.popup-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
  padding-bottom: 12px;
  border-bottom: 1px solid #1e2d4a;
}

.logo {
  width: 32px;
  height: 32px;
  border-radius: 6px;
}

h1 {
  font-size: 14px;
  font-weight: 700;
  color: #60a5fa;
}

.version {
  font-size: 10px;
  color: #475569;
}

/* Status Card */
.status-card {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #1a2035;
  border: 1px solid #2d3a52;
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 10px;
}

.status-indicator {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #475569;
  flex-shrink: 0;
  transition: background 0.3s ease;
}

.status-indicator.connected { background: #22c55e; box-shadow: 0 0 8px #22c55e60; }
.status-indicator.disconnected { background: #ef4444; }
.status-indicator.connecting { background: #f59e0b; animation: pulse 1s infinite; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.status-label {
  font-size: 10px;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.status-text {
  font-size: 13px;
  font-weight: 600;
  color: #e2e8f0;
}

.meta-row {
  font-size: 11px;
  color: #64748b;
  padding: 0 4px;
  margin-bottom: 12px;
}

/* Actions */
.actions {
  display: flex;
  gap: 8px;
}

.btn {
  flex: 1;
  padding: 8px 10px;
  border: none;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-secondary {
  background: #1e2d4a;
  color: #94a3b8;
  border: 1px solid #2d3a52;
}

.btn-secondary:hover {
  background: #243553;
  color: #e2e8f0;
}

.btn-primary {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: white;
}

.btn-primary:hover {
  background: linear-gradient(135deg, #60a5fa, #3b82f6);
  transform: translateY(-1px);
}
```

### 7.4 popup.js

```javascript
/**
 * popup.js
 * Hermes FacePost-Group — Extension Popup
 *
 * Fix: C1 — Popup spec missing
 * GAP-01-04: Dynamic config cho WS URL và Auth Secret
 */

const DASHBOARD_URL = 'http://localhost:8765';

// ─────────────────────────────────────────────
// GAP-01-04: Dynamic Config — Save/Load WS URL & Auth Secret
// ─────────────────────────────────────────────

/**
 * Lưu config vào chrome.storage.local và trigger RECONNECT offscreen.
 * Gọi khi user thay đổi URL/secret trong config form.
 * @param {string} dashboardUrl - ws:// URL (default: ws://127.0.0.1:8765/ws)
 * @param {string} authSecret - Shared secret hex string
 */
async function saveConfig(dashboardUrl, authSecret) {
  await chrome.storage.local.set({
    wsUrl: dashboardUrl || 'ws://127.0.0.1:8765/ws',
    ws_auth_secret: authSecret
  });
  // Thông báo offscreen document reconnect với config mới
  chrome.runtime.sendMessage({ target: 'offscreen', type: 'RECONNECT' }).catch(() => {});
}

/**
 * Load config hiện tại vào form khi popup mở.
 * Auth secret được mask (chỉ hiển thị 8 ký tự đầu).
 */
function loadConfig() {
  chrome.storage.local.get(['wsUrl', 'ws_auth_secret'], ({ wsUrl, ws_auth_secret }) => {
    const wsUrlInput = document.getElementById('ws-url');
    const secretInput = document.getElementById('auth-secret');
    if (wsUrlInput) wsUrlInput.value = wsUrl || 'ws://127.0.0.1:8765/ws';
    if (secretInput && ws_auth_secret) {
      // Mask secret: chỉ hiển thị 8 ký tự đầu + ...
      secretInput.value = ws_auth_secret.slice(0, 8) + '...' + ws_auth_secret.slice(-4);
      secretInput.dataset.masked = 'true'; // Flag để biết giá trị đang bị mask
    }
  });
}

const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const metaRow = document.getElementById('metaRow');
const metaText = document.getElementById('metaText');
const btnRefresh = document.getElementById('btnRefresh');
const btnOpenDashboard = document.getElementById('btnOpenDashboard');

// ─────────────────────────────────────────────
// Update UI theo status
// ─────────────────────────────────────────────
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

// ─────────────────────────────────────────────
// Fetch status từ background.js
// ─────────────────────────────────────────────
async function checkStatus() {
  renderStatus(null); // Loading state

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

// ─────────────────────────────────────────────
// Lắng nghe status updates realtime từ background
// ─────────────────────────────────────────────
chrome.runtime.onMessage.addListener((message) => {
  if (message.source === 'background' && message.type === 'WS_STATUS_UPDATE') {
    if (message.status === 'CONNECTED') {
      renderStatus({ connected: true, authenticated: true });
    } else if (message.status === 'DISCONNECTED') {
      renderStatus({ connected: false, authenticated: false });
    }
  }
});

// ─────────────────────────────────────────────
// Event Listeners
// ─────────────────────────────────────────────
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

// ─────────────────────────────────────────────
// Init
// ─────────────────────────────────────────────
checkStatus();
```

---

## 8. WebSocket Auth Protocol — Fix A4

### 8.1 Tổng Quan Vấn Đề

```
Security Risk A4:
ws://localhost:8765/ws → không có auth
Bất kỳ process trên localhost đều có thể:
  1. Kết nối vào Dashboard WebSocket
  2. Gửi lệnh giả (fake CLICK, TYPE commands)
  3. Nhận snapshot DOM chứa token Facebook, session cookies references

Giải pháp: Shared Secret + HMAC-SHA256 handshake
```

### 8.2 Shared Secret Setup

```pseudocode
SETUP PROCEDURE (one-time, khi extension install):

1. Extension popup/options page tạo secret ngẫu nhiên:
   secret = crypto.getRandomValues(new Uint8Array(32))
   secretHex = toHexString(secret)  // 64-char hex

2. Lưu vào chrome.storage.local:
   chrome.storage.local.set({ ws_auth_secret: secretHex })

3. Hiển thị secretHex cho user copy vào Dashboard config:
   dashboard/.env:
     HERMES_WS_SECRET=<secretHex>

4. Dashboard cũng lưu secret vào config file (KHÔNG đưa lên git).
```

### 8.3 Handshake Protocol

```
CLIENT (offscreen.js)                    SERVER (Dashboard WebSocket)
       |                                        |
       |──── CONNECT ws://localhost:8765/ws ───►|
       |                                        |
       |──── HELLO {                            |
       |       type: "HELLO",                   |
       |       nonce: "uuid-v4",                |  (random UUID, prevent replay)
       |       timestamp: 1718000000000,        |  (Unix ms)
       |       signature: hmac_sha256(          |
       |         secret,                        |
       |         nonce + ":" + timestamp        |
       |       ),                               |
       |       extensionVersion: "2.0.0"        |
       |     }                                 ►|
       |                                        |
       |     Server validates:                  |
       |       1. signature matches             |
       |       2. timestamp within ±30s (clock skew)
       |       3. nonce not seen before (replay protection)
       |                                        |
       |◄─── WELCOME { type: "WELCOME",        |
       |               sessionId: "uuid",       |
       |               serverTime: 1718000000100,|
       |               serverVersion: "1.0.0" }|
       |                                        |
       |     [Connection AUTHENTICATED]         |
       |     [Normal message exchange begins]   |
```

### 8.4 lib/hmac_sha256.js — Web Crypto API Implementation

> **GAP-01-07 — Web Crypto API:** Implementation dùng `crypto.subtle` (Web Crypto API), available trong:
> - ✅ Extension Service Worker (background.js)
> - ✅ Offscreen Document (offscreen.js)
> - ✅ Content Script (content.js)
> - ✅ Popup (popup.js)
>
> **Không cần thư viện third-party** — `crypto.subtle` là built-in API đủ mạnh và được Chrome Extension sandbox chấp nhận.
>
> **Usage:**
> ```javascript
> import { hmacSha256Hex } from './lib/hmac_sha256.js';
> const sig = await hmacSha256Hex(secretHex, `${nonce}:${timestamp}`);
> ```

```javascript
/**
 * lib/hmac_sha256.js
 * HMAC-SHA256 dùng Web Crypto API (GAP-01-07).
 * Available trong tất cả Extension contexts (SW, Offscreen, Content, Popup).
 *
 * @param {string} secret - Hex string secret key
 * @param {string} message - Message to sign
 * @returns {Promise<string>} - HMAC-SHA256 hex string
 */
export async function hmacSha256Hex(secretHex, message) {
  // Convert hex secret to ArrayBuffer
  const keyBytes = hexToBytes(secretHex);
  const msgBytes = new TextEncoder().encode(message);

  // Import key
  const cryptoKey = await crypto.subtle.importKey(
    'raw',
    keyBytes,
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );

  // Sign
  const signature = await crypto.subtle.sign('HMAC', cryptoKey, msgBytes);

  // Convert to hex
  return bytesToHex(new Uint8Array(signature));
}

/**
 * Verify HMAC-SHA256 signature.
 * @param {string} secretHex
 * @param {string} message
 * @param {string} signatureHex
 * @returns {Promise<boolean>}
 */
export async function verifyHmacSha256(secretHex, message, signatureHex) {
  const expected = await hmacSha256Hex(secretHex, message);
  // Constant-time comparison để chống timing attacks
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

### 8.5 Dashboard Server-Side Validation (Node.js Pseudocode)

```javascript
// dashboard/ws_server.js (Node.js side — reference only)

const crypto = require('crypto');
const secret = process.env.HERMES_WS_SECRET; // 64-char hex từ .env
const seenNonces = new Map(); // nonce → timestamp (replay prevention)

function validateHandshake(helloMsg) {
  const { nonce, timestamp, signature } = helloMsg;

  // 1. Kiểm tra timestamp (±30s clock skew tolerance)
  const now = Date.now();
  if (Math.abs(now - timestamp) > 30_000) {
    return { ok: false, reason: 'Timestamp out of range' };
  }

  // 2. Kiểm tra replay attack
  if (seenNonces.has(nonce)) {
    return { ok: false, reason: 'Nonce replay detected' };
  }
  seenNonces.set(nonce, timestamp);

  // Cleanup nonces cũ hơn 1 phút
  for (const [n, ts] of seenNonces) {
    if (now - ts > 60_000) seenNonces.delete(n);
  }

  // 3. Verify HMAC-SHA256
  const secretBytes = Buffer.from(secret, 'hex');
  const expectedSig = crypto
    .createHmac('sha256', secretBytes)
    .update(`${nonce}:${timestamp}`)
    .digest('hex');

  const valid = crypto.timingSafeEqual(
    Buffer.from(signature, 'hex'),
    Buffer.from(expectedSig, 'hex')
  );

  return valid
    ? { ok: true }
    : { ok: false, reason: 'Invalid signature' };
}

wss.on('connection', (ws) => {
  ws.isAuthenticated = false;

  ws.on('message', (raw) => {
    const msg = JSON.parse(raw);

    if (!ws.isAuthenticated) {
      if (msg.type === 'HELLO') {
        const result = validateHandshake(msg);
        if (result.ok) {
          ws.isAuthenticated = true;
          ws.send(JSON.stringify({
            type: 'WELCOME',
            status: 'OK',
            sessionId: crypto.randomUUID()
          }));
        } else {
          ws.send(JSON.stringify({ type: 'AUTH_REJECT', reason: result.reason }));
          ws.close(1008, 'Auth failed');
        }
      }
      return; // Bỏ qua mọi message khác khi chưa auth
    }

    // Process authenticated messages...
    handleMessage(ws, msg);
  });
});
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

### 9.2 Luồng: Facebook DOM → AI Agent Brain

```
content.js              background.js         offscreen.js           Dashboard
    │                         │                    │                     │
    │ Page load / mutation     │                    │                     │
    │──sendMessage──────────► │                    │                     │
    │  {type:"PAGE_LOADED",   │                    │                     │
    │   snapshot:{elements:   │                    │                     │
    │     [{id:"a3f2c891",    │                    │                     │
    │       tag:"button",     │                    │                     │
    │       text:"Đăng"}]}}   │                    │                     │
    │                         │──sendMessage─────► │                     │
    │                         │  relay to offscreen│                     │
    │                         │                    │──ws.send───────────►│
    │                         │                    │  JSON snapshot      │
    │                         │                    │                     │──AI parse DOM
```

---

## 10. Error Handling & Graceful Degradation

### 10.1 Matrix Xử Lý Lỗi

| Scenario | Detect | Response |
|----------|--------|----------|
| `offscreen.js` không tạo được | `chrome.offscreen.createDocument()` throw | Log error, retry sau 5s |
| WebSocket server không chạy | `ws.onerror` + `ws.onclose` | Exponential backoff reconnect |
| Auth handshake fail | Server gửi `AUTH_REJECT` | Close WS, báo user qua popup |
| Auth secret chưa setup | `chrome.storage.local.get` trả `undefined` | Báo "NO_SECRET" qua popup |
| Element fingerprint không tìm thấy | `findElementByFingerprint` trả `null` | Trả `{success:false, error:"Element not found"}` |
| Tab bị close khi đang thực thi | `chrome.tabs.sendMessage` throw | Log, skip command |
| Dashboard gửi `timestamp` quá cũ | Server validation fail | `AUTH_REJECT` với reason |
| Tìm kiếm Group thất bại | Group không tìm thấy hoặc timeout | Gửi `SEARCH_FAILED` WebSocket, trả `{success:false, error:...}` |

### 10.2 Popup Error States

```
Trạng thái popup.html theo lỗi:

❌ NO_SECRET:
  statusText = "Chưa cài đặt secret key"
  metaText = "Vào Options để thiết lập"

❌ AUTH_REJECTED:
  statusText = "Xác thực thất bại"
  metaText = "Kiểm tra HERMES_WS_SECRET trong Dashboard"

🟡 CONNECTING:
  statusText = "Đang kết nối..."
  [pulsing animation]

❌ DISCONNECTED (retry):
  statusText = "Mất kết nối"
  metaText = "Thử lại lần 3... (chờ 8s)"

✅ CONNECTED:
  statusText = "Đã kết nối ✓"
```

---

## 11. Checklist Kiểm Thử

### 11.1 Test Cases Cơ Bản

| ID | Test | Expected | Priority |
|----|------|----------|----------|
| T01 | Install extension → mở popup | Hiện "Connecting..." → "Đã kết nối" (nếu Dashboard chạy) | P0 |
| T02 | Dashboard không chạy → popup | "Mất kết nối" + retry count tăng | P0 |
| T03 | Mở Facebook tab → snapshot gửi lên Dashboard | Dashboard nhận `PAGE_LOADED` event | P0 |
| T04 | Dashboard gửi `CLICK` với fingerprint ID | Element được click đúng | P0 |
| T05 | Facebook React re-render → resend command với old ID | Command fail gracefully với "Element not found" | P1 |
| T06 | SW bị Chrome kill (simulate: chrome://serviceworker-internals → Stop) | Offscreen giữ WS alive, SW wake up → relay tiếp tục | P0 |
| T07 | Sai secret key → HELLO | `AUTH_REJECT` → popup "Xác thực thất bại" | P1 |
| T08 | Replay attack: gửi lại HELLO cũ | Server reject "Nonce replay" | P2 |
| T09 | Timestamp cách hiện tại >30s | Server reject "Timestamp out of range" | P2 |
| T10 | TYPE command với 500 ký tự | Text nhập đúng vào contenteditable, React state updated | P1 |

### 11.2 Validate Chrome Version

```bash
# Kiểm tra Chrome version >= 116
google-chrome --version
# Cần: Google Chrome 116.0.xxxx.xx trở lên
```

### 11.3 Validate Extension Load

```
chrome://extensions/ → Load unpacked → chọn thư mục hermes-facepost/
Kiểm tra:
  ✅ Không có lỗi trong "Errors" section
  ✅ Service worker "Active" (background.js)
  ✅ chrome://serviceworker-internals/ hiện Offscreen document
  ✅ Popup mở được
```

---

## Appendix: Changelog

| Version | Date | Changes |
|---------|------|---------|
| 2.3.0 | 2026-06-16 | **Hot-Reload & Context Guard** — Extension hot-reload qua WS `EXTENSION_RELOAD` → `TRIGGER_RELOAD` → `chrome.runtime.reload()`, Content script context invalidation guard (`keepAlivePort` + `onDisconnect`), Section 12.6 OTA flow diagram |
| 2.2.0 | 2026-06-16 | **Search & Anti-Detection Upgrade** — Thêm thuật toán di chuyển chuột Bezier, trễ gõ Gaussian (Box-Muller), logic tương tác ô Search FB Home và khớp nhóm qua `fb_group_id`/`group_name`, WebSocket `SEARCH_FAILED` message |
| 2.1.0 | 2026-06-15 | **Post-Audit Patch (Kimi+Qwen)** — GAP-01-01 (WS port 8765/ws + dynamic config), GAP-01-02 (ES Module content_scripts), GAP-01-03 (Offscreen reason TESTING), GAP-01-04 (Popup config form), GAP-01-05 (Targeted tab routing), GAP-01-06 (Alarm min 0.5), GAP-01-07 (hmac_sha256 Web Crypto doc), GAP-01-08 (sendResultWithRetry), Typing delay 40-180ms |
| 2.0.0 | 2026-06-15 | **Rewrite hoàn toàn** — Fix A3 (Offscreen), A4 (Auth), B1 (Fingerprint), C1 (Popup) |
| 1.x.x | — | Legacy — Deprecated. Xem `tmp/archive/facepost_01_v1.legacy.md` |

---

## 12. Facebook Search & Human-like Interaction Specs

### 12.1 Thuật Toán Di Chuyển Chuột Bezier (Anti-Bot Detection)
Nhằm tránh cơ chế phát hiện bot bằng click cơ học tức thời, mọi tương tác click trong Extension phải chuyển qua `simulateBezierMouseMoveAndClick`.
* **Đường Cong Bezier Bậc Hai (Quadratic Bezier):**
  $$B(t) = (1-t)^2 P_0 + 2(1-t)t P_1 + t^2 P_2 \quad (0 \le t \le 1)$$
  Trong đó $P_0$ là tọa độ bắt đầu, $P_2$ là tọa độ đích, $P_1$ là điểm điều khiển được tính ngẫu nhiên nằm giữa hai điểm để tạo độ cong tự nhiên.
* **Chuỗi sự kiện (Mouse Event Cascade):**
  Gồm `mousemove` phát liên tiếp dọc đường cong, theo sau bởi trễ chuẩn, rồi `mouseover`, `mousedown`, `mouseup`, và cuối cùng là `click`.

### 12.2 Thuật Toán Gõ Phím Gaussian (Normal Distribution Delay)
Tránh trễ gõ ngẫu nhiên đều (Uniform Random) vì nó để lại dấu vết phi tự nhiên trong dữ liệu của Facebook.
* **Box-Muller Transform:**
  Sinh số ngẫu nhiên phân phối chuẩn $N(\mu, \sigma^2)$ từ hai số ngẫu nhiên đều $U_1, U_2 \in (0, 1)$:
  $$Z = \sqrt{-2 \ln U_1} \cos(2\pi U_2)$$
  $$Delay = Z \cdot \sigma + \mu$$
  Trong đó mean $\mu = 100\text{ms}$ và standard deviation $\sigma = 30\text{ms}$. Trễ được kẹp trong khoảng $[40\text{ms}, 300\text{ms}]$.

### 12.3 Quy Trình Tương Tác Ô Search Facebook Home
1. **Định Vị Ô Search:** Content script quét tìm phần tử input qua selector:
   `input[placeholder*="Tìm kiếm"], input[aria-label*="Search Facebook"]`
2. **Focus & Nhập Liệu:** Di chuyển chuột Bezier đến input, click để kích hoạt focus, sau đó dùng trễ Gaussian để gõ từ khóa.
3. **Kích Hoạt Tìm Kiếm:** Phát sự kiện phím `Enter` (keyCode 13) và gửi form submit để gửi truy vấn.
4. **Cơ Chế Điều Hướng Dự Phòng (Navigation Fallback):** Nếu không tìm thấy input hoặc không thể tương tác UI, thực hiện redirect trực tiếp sang URL:
   `https://www.facebook.com/search/groups/?q=encodeURIComponent(query)`

### 12.4 Quy Trình Quét Kết Quả và Khớp Group
Khi trang kết quả tải xong, content script định vị danh sách group:
* **Khớp theo `fb_group_id`:** Quét các thẻ `<a>` có liên kết chứa `/groups/{fb_group_id}/`.
* **Khớp theo `group_name` (Dự phòng):** Nếu không cung cấp ID hoặc so khớp ID thất bại, duyệt text hiển thị của các thẻ kết quả. So khớp không phân biệt hoa thường và bỏ ký tự thừa với `group_name`.
* **Điều hướng:** Click Bezier vào phần tử khớp.

### 12.5 Giao Thức WebSocket Báo Lỗi `SEARCH_FAILED`
Nếu vượt quá timeout (mặc định 15s) mà không tìm thấy group khớp hoặc không hoàn thành quy trình, gửi payload WebSocket sau về Dashboard qua `offscreen.js`:
```json
{
  "type": "SEARCH_FAILED",
  "commandId": "cmd-uuid-xxx",
  "fb_group_id": "1234567890",
  "group_name": "Cộng Đồng AI Việt Nam",
  "reason": "GROUP_NOT_FOUND", // Hoặc "TIMEOUT_EXCEEDED", "NO_SEARCH_INPUT"
  "url": "https://www.facebook.com/search/groups/?q=...",
  "ts": 1718000000000
}
```

### 12.6 Extension Hot-Reload (OTA Update Flow)

Khi Dashboard áp dụng bản cập nhật OTA (`autoUpdater.js` — Spec 03):

1. Dashboard gửi WebSocket message `{ type: 'EXTENSION_RELOAD', reason: 'OTA v2.1.0' }` tới tất cả extensions.
2. `offscreen.js` nhận → relay `TRIGGER_RELOAD` lên `background.js`.
3. `background.js` ghi log lý do + timestamp vào `chrome.storage.local` → gọi `chrome.runtime.reload()`.
4. Chrome unload toàn bộ extension contexts → Service Worker + Offscreen + Content scripts đều bị terminate.
5. Chrome tự reload extension từ thư mục unpacked (đã giải nén mã mới).
6. Offscreen Document tự tạo lại → WebSocket reconnect tự động.
7. Content script cũ phát hiện context invalidated (qua `onDisconnect` keepAlivePort) → reload tab Facebook.
8. Content script mới inject vào tab đã reload → hoạt động bình thường.

**Sơ đồ:**

```
Dashboard autoUpdater.js
  │ WS: EXTENSION_RELOAD
  ▼
offscreen.js → TRIGGER_RELOAD → background.js
  │                                    │
  │                          chrome.runtime.reload()
  │                                    │
  ▼                                    ▼
Content.js detectDisconnect      Extension reloaded
  │                                    │
  window.location.reload()       New offscreen.js connects
```

> **Lưu ý:** Sau khi reload, `lastReloadReason` và `lastReloadAt` được lưu trong `chrome.storage.local` để popup có thể hiển thị lý do reload gần nhất cho user.

---

## Cảnh báo An ninh & Lỗ hổng Kiến trúc

### 🔴 LỖ HỔNG CRITICAL
1. **[FINDING-03] Thao tác giả lập chuột/phím bị chặn bởi `event.isTrusted`:**
   - *Rủi ro:* Tất cả các sự kiện chuột/phím giả lập bằng JS (`dispatchEvent(new MouseEvent(...))`) trong Content Script đều bị gán `event.isTrusted = false`. Hệ thống chống bot của Facebook (như Akamai Bot Manager hoặc JS cục bộ của FB) sẽ chặn hoặc gắn cờ checkpoint tài khoản ngay lập tức khi phát hiện thao tác không đáng tin cậy này.
   - *Yêu cầu Remediation:* Bắt buộc sử dụng **Chrome Debugger API** (`chrome.debugger`) để gửi các sự kiện di chuột, click và nhấn phím cấp thấp thông qua giao thức Chrome DevTools Protocol (CDP) (`Input.dispatchMouseEvent`, `Input.dispatchKeyEvent`). Điều này đảm bảo `event.isTrusted = true`.
2. **[FINDING-01] Mất kết nối vĩnh viễn khi Offscreen bị Chrome đóng ngầm:**
   - *Rủi ro:* Trình duyệt Chrome có quyền tắt ngầm Offscreen Document khi máy khách thiếu tài nguyên (Low Memory). Nếu Offscreen bị đóng, WebSocket sập. Nếu lúc này Service Worker (SW) đang ở trạng thái ngủ (idle sau 30 giây), hệ thống sẽ mất kết nối vĩnh viễn với Dashboard.
   - *Yêu cầu Remediation:* Di chuyển toàn bộ WebSocket Connection trực tiếp vào Service Worker. Kể từ Chrome 116+, các hoạt động truyền nhận WebSocket trong SW sẽ tự động reset bộ đếm idle timer của SW giúp giữ luồng chạy ngầm ổn định.

### 🟠 LỖ HỔNG HIGH
1. **[FINDING-04] Lỗ hổng DOM-based XSS qua lệnh `NAVIGATE`:**
   - *Rủi ro:* Lệnh `NAVIGATE` nhận URL trực tiếp từ WebSocket và gán thẳng vào `window.location.href` mà không qua validate. Kẻ tấn công trung gian hoặc chiếm quyền Dashboard có thể gửi chuỗi `javascript:` độc hại để chạy script trong Main World của Facebook nhằm đánh cắp cookies/tokens.
   - *Yêu cầu Remediation:* Validate và lọc kĩ URL nhận được, chỉ cho phép giao thức `http:` và `https:` thông qua đối tượng `new URL()`.
2. **[FINDING-02] Từ chối duyệt ứng dụng trên Chrome Web Store do lạm dụng lý do `TESTING`:**
   - *Rủi ro:* Sử dụng lý do `TESTING` cho offscreen document sẽ bị đội ngũ kiểm duyệt của Google từ chối phê duyệt (Rejection) khi submit extension lên CWS.
   - *Yêu cầu Remediation:* Nếu bắt buộc dùng offscreen, hãy thay đổi lý do thành `DOM_SCRAPING` hoặc `DOM_PARSER` kèm theo giải trình (`justification`) hướng tới trải nghiệm người dùng cụ thể.
3. **[FINDING-05] Phân tích Entropy hành vi phát hiện đường cong Bezier và Box-Muller hoàn hảo:**
   - *Rủi ro:* Thuật toán Bezier và Box-Muller tạo ra các đường di chuyển chuột mượt mà hoàn hảo và phân phối trễ gõ phím quá đều về mặt toán học. Sự thiếu ngẫu nhiên thực tế (micro-tremors, typos, khoảng nghỉ suy nghĩ) sẽ bị hệ thống phân tích hành vi của Facebook nhận diện là bot.
   - *Yêu cầu Remediation:* Bổ sung nhiễu ngẫu nhiên (jitter) dọc đường Bezier, mô phỏng lỗi gõ phím (typos) với tỷ lệ thấp rồi gõ Backspace sửa lại, và thêm khoảng dừng nhận thức khi chuyển đổi giữa các input fields.

---

*Tài liệu này được tạo bởi Hermes Design System. Mọi thay đổi phải qua code review và cập nhật changelog.*


---

## II. NGUYÊN TẮC VẬN HÀNH BẮT BUỘC TRONG PHIÊN
1. Phải tham chiếu chính xác các hàm và biến được mô tả trong tài liệu Spec này.
2. Không tự ý thay đổi giao thức truyền tin (ví dụ: đổi schema websocket) mà không cập nhật tài liệu thiết kế.
3. Chú ý các nguyên tắc tối ưu hóa SQLite (WAL mode) khi thay đổi logic DB.
