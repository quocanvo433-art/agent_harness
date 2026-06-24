# 🔀 Hermes FacePost-Group — Đặc tả kỹ thuật kiến trúc Hybrid Extension (Phân tách phiên bản)

**File:** `facepost_09_hybrid_extension.md`  
**Version:** 2.0.0 (Manual Side Panel Helper Edition)  
**Ngày cập nhật:** 2026-06-18  
**Tài liệu liên quan:** [Đặc tả kỹ thuật Extension Core](./facepost_01_chrome_extension.md)

---

## 🚨 KHUYẾC CÁO CẤU HÌNH VÀ THIẾT KẾ BẮT BUỘC

> [!CAUTION]
> **🚨 Tách biệt cấu hình Manifest:**
> Phiên bản Chrome Web Store (CWS) và phiên bản Ghost (Developer Unpacked) phải sử dụng hai tệp cấu hình `manifest.json` riêng biệt. Nghiêm cấm sử dụng cấu trúc điều kiện logic (if/else) tại runtime để thay đổi quyền hạn. Quy trình kiểm duyệt tĩnh của Google sẽ phân tích trực tiếp tệp manifest tại thời điểm tải lên.

> [!CAUTION]
> **🚨 Định danh Extension ID động:**
> Tránh hardcode Extension ID. Giá trị định danh này thay đổi tùy thuộc vào môi trường thực thi (CWS Production hoặc Developer Unpacked). Phải sử dụng phương thức `chrome.runtime.id` tại runtime để truy xuất ID động.

> [!CAUTION]
> **🚨 Cách ly mã nguồn tự động hóa:**
> Phiên bản CWS (Diplomat) không được phép chứa bất kỳ tham chiếu, hàm thực thi hoặc tài nguyên nào liên quan đến tự động hóa tương tác (ví dụ: `nativeMessaging`, `chrome.scripting.executeScript` với payload tương tác, Bezier mouse simulation, Gaussian delay generator). Quy trình phân tích AST của Google sẽ quét toàn bộ mã nguồn tĩnh và từ chối phê duyệt nếu phát hiện các mẫu này.

> [!CAUTION]
> **🚨 Danh sách thuật ngữ cấm trong phiên bản CWS:**
> Tuyệt đối không sử dụng các từ khóa nhạy cảm trong mã nguồn, chú thích (comment) và mô tả của phiên bản CWS: `bypass`, `bot`, `spam`, `facebook_auto`, `automate`, `crawler`, `bot_simulator`, `facebook_spam`, `spintax`. Quy trình duyệt tự động sử dụng mô hình NLP để quét mã nguồn và từ chối duyệt nếu phát hiện từ khóa thuộc danh mục trên.

---

## Mục Lục

1. [Triết lý thiết kế Hybrid (Phân tách phiên bản)](#1-triết-lý-thiết-kế-hybrid-phân-tách-phiên-bản)
2. [Đặc tả kỹ thuật CWS Diplomat (Side Panel Helper)](#2-đặc-tả-kỹ-thuật-cws-diplomat-side-panel-helper)
3. [Đặc tả kỹ thuật GitHub Ghost (Developer Unpacked Agent)](#3-đặc-tả-kỹ-thuật-github-ghost-developer-unpacked-agent)
4. [Cấu hình Dashboard Server (Phân tuyến định danh thông qua Extension ID)](#4-cấu-hình-dashboard-server-phân-tuyến-định-danh-thông-qua-extension-id)
5. [Cấu trúc thư mục dự án phân nhánh](#5-cấu-trúc-thư-mục-dự-án-phân-nhánh)
6. [Checklist kiểm định trước khi nộp ứng dụng lên Chrome Web Store](#6-checklist-kiểm-định-trước-khi-nộp-ứng-dụng-lên-chrome-web-store)
7. [Bổ sung cấu trúc dữ liệu HELLO handshake](#7-bổ-sung-cấu-trúc-dữ-liệu-hello-handshake)
8. [Bảng mã lỗi hệ thống phân tuyến (Module HYB)](#8-bảng-mã-lỗi-hệ-thống-phân-tuyến-module-hyb)
9. [Phân tích lỗ hổng an ninh và yêu cầu khắc phục](#9-phân-tích-lỗ-hổng-an-ninh-và-yêu-cầu-khắc-phục)

---

## 1. Triết lý thiết kế Hybrid (Phân tách phiên bản)

### 1.1 Phân tích bối cảnh kiểm duyệt
Chính sách kiểm duyệt của Chrome Web Store (CWS) áp đặt các quy định nghiêm ngặt đối với các tiện ích mở rộng có hành vi tự động hóa giao diện (Automation Behavior - tự động mô phỏng click, nhập liệu, điều hướng tuần tự). Tiện ích tích hợp các tính năng này sẽ bị từ chối phê duyệt hoặc đình chỉ tài khoản phát triển.

Để đáp ứng chính sách của CWS đồng thời duy trì khả năng tự động hóa cấp cao cho môi trường phát triển cục bộ, hệ thống được phân tách thành hai phiên bản độc lập với cơ chế hoạt động riêng biệt:

| Tiêu chí | **CWS Diplomat (Store Edition)** | **GitHub Ghost (Developer Edition)** |
|-------|-----------------|-----------------|
| **Mục tiêu phân phối** | Phân phối chính thức trên Chrome Web Store | Phân phối qua GitHub Releases dưới dạng Unpacked |
| **Giao diện & Tương tác** | Tích hợp Chrome Side Panel để hỗ trợ sao chép thủ công | Chạy ẩn không giao diện, tự động tương tác DOM |
| **Quyền hạn hệ thống** | Tối giản (`storage`, `sidePanel`) | Đầy đủ (`scripting`, `nativeMessaging`, `offscreen`, `alarms`...) |
| **Rủi ro kiểm duyệt** | Không có (Hoàn toàn tuân thủ chính sách CWS) | Không áp dụng (Cài đặt thủ công ở chế độ Developer) |

### 1.2 Bảng phân tích phân rã tính năng

| Tính năng | CWS Diplomat (Store Edition) 🤝 | GitHub Ghost (Developer Edition) 👻 | Ghi chú thiết kế |
|-----------|:---:|:---:|---------|
| Side Panel UI | ✅ | ✅ | Hiển thị thông tin quản lý bài đăng |
| Sao chép nội dung thủ công | ✅ | ✅ | Nút Copy hỗ trợ người dùng tự tương tác |
| Đồng bộ dữ liệu thụ động | ✅ | ✅ | Lưu cấu hình, trạng thái phiên qua storage |
| Tự động hóa đăng bài (AgentLoop) | ❌ | ✅ | Tự động tuần tự hóa chiến dịch đăng bài |
| Giao tiếp Python Relay | ❌ | ✅ | Cổng kết nối `nativeMessaging` cấp thấp |
| Patch trạng thái React Fiber | ❌ | ✅ | Can thiệp bộ điều phối trạng thái của Facebook |
| Giả lập chuột Bezier & Phím Gaussian | ❌ | ✅ | Cơ chế chống nhận diện bot tự động |
| Nén DOM & Sinh Fingerprint FNV-1a | ❌ | ✅ | Thu thập snapshot giao diện cho AI Brain |
| WebSocket & Offscreen Document | ❌ | ✅ | Duy trì kết nối persistent WebSocket |
| HMAC-SHA256 Handshake | ❌ | ✅ | Bảo mật xác thực WebSocket |
| **Mức độ rủi ro Store** | 🟢 Không | 🔴 Cao (Chỉ chạy chế độ Developer Unpacked) | |

### 1.3 Cơ chế phân tầng luồng dữ liệu

```
┌─────────────────────────────────────────────────────────────────┐
│                    MÔI TRƯỜNG CHROME WEB STORE                  │
│                  ↓ Cài đặt trực tiếp từ Store                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │        CWS DIPLOMAT — Phiên bản hỗ trợ thủ công         │    │
│  │  • Hoạt động hoàn toàn qua Side Panel (Copy/Paste)      │    │
│  │  • Không chứa mã nguồn tự động hóa hoặc script ẩn       │    │
│  │  • Kết nối Dashboard bằng REST API chế độ Safe Mode     │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│                MÔI TRƯỜNG DEVELOPER UNPACKED                     │
│                  ↓ Cài đặt thủ công chế độ Dev                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │        GITHUB GHOST — Phiên bản tự động hóa cấp cao      │    │
│  │  • Tích hợp đầy đủ tác nhân tự động (Agentic Core)       │    │
│  │  • Sử dụng Offscreen Document duy trì WebSocket          │    │
│  │  • Kết nối Dashboard chế độ Agentic OS (HMAC secured)    │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
          ┌────────────────────────────────────────┐
          │       DASHBOARD (Shared Backend)        │
          │   Phân tuyến luồng lệnh theo ID tiện ích│
          │   wsServer.js điều phối quyền thực thi │
          └────────────────────────────────────────┘
```

---

## 2. Đặc tả kỹ thuật CWS Diplomat (Side Panel Helper)

### 2.1 Cơ chế hoạt động thủ công (Manual Copy/Paste Panel)

Nhằm đảm bảo an toàn tuyệt đối trước các thuật toán kiểm duyệt tĩnh và động của Chrome Web Store, phiên bản Diplomat được thiết kế hoạt động hoàn toàn trong không gian biệt lập thông qua Chrome Side Panel API. Phiên bản này **không sử dụng Content Script** để can thiệp vào trang web Facebook, loại bỏ hoàn toàn khả năng bị đánh giá là "Page Hijacking" hoặc "Automation Bot".

Mọi tương tác được thực thi thủ công bởi người dùng:

#### 2.1.1 Giao diện điều khiển Side Panel
- Tiện ích sử dụng cơ chế hiển thị Side Panel (`chrome.sidePanel`) mở song song với cửa sổ duyệt web khi người dùng nhấp vào biểu tượng tiện ích.
- Giao diện Side Panel hiển thị danh sách các bài viết gợi ý được truy xuất từ Dashboard Server qua REST API.

#### 2.1.2 Sao chép nội dung thủ công (Clipboard Copy Helper)
- Giao diện cung cấp nút bấm **Sao chép nội dung** (Copy Text) và **Sao chép đường dẫn hình ảnh** (Copy Media Link).
- Khi người dùng nhấp nút, tiện ích thực hiện ghi dữ liệu tương ứng vào Clipboard hệ thống thông qua Web Clipboard API (`navigator.clipboard.writeText`).
- Người dùng thực hiện dán (Paste) thủ công nội dung vào khung nhập liệu trên giao diện Facebook và bấm đăng bài.

#### 2.1.3 Quản lý nhóm thủ công (Manual Group Directory)
- Loại bỏ cơ chế đồng bộ tự động danh sách nhóm qua việc lắng nghe sự kiện scroll trang web Facebook.
- Side Panel hiển thị danh mục các nhóm đích do người dùng tự khai báo hoặc cấu hình từ trước trên Dashboard. Cung cấp liên kết nhanh (Quick Link) để người dùng mở nhanh nhóm Facebook tương ứng trong tab mới.

### 2.2 Các tính năng bị loại bỏ hoàn toàn

> [!WARNING]
> Để vượt qua các bộ lọc quét AST (Abstract Syntax Tree) của Google, phiên bản CWS Diplomat phải loại bỏ triệt để các module mã nguồn và thư viện liên quan đến các tính năng sau:

| Tính năng bị loại bỏ | Nguyên nhân phân tích tĩnh |
|-----------|---------------------|
| `nativeMessaging` | Giao tiếp tiến trình con với Local Proxy. Bị đánh giá là phần mềm gián điệp nếu không có giải trình đặc biệt. |
| `chrome.scripting` và Content Scripts | Kỹ thuật chèn script can thiệp DOM Facebook. Bị quét bảo mật cao về đánh cắp dữ liệu người dùng. |
| Giả lập chuột Bezier và bàn phím | Sử dụng synthetic events tạo tương tác giả lập. Bị coi là hành vi tự động hóa độc hại (Bot). |
| WebSocket Persistent | Kết nối WebSocket ngầm liên tục và giữ trạng thái bằng Offscreen Document. Bị nghi ngờ duy trì Botnet. |
| HMAC Signature | Logic mã hóa handshake ngầm với Dashboard Server. |

### 2.3 Thiết lập thông tin CWS (Marketing Pivot)

Nhằm định danh ứng dụng như một công cụ hỗ trợ năng suất cá nhân thông thường:

| Thuộc tính | Phiên bản Ghost (Developer) | Phiên bản Diplomat (CWS Store) |
|--------|----------------|-------------------|
| **Tên hiển thị** | "Hermes OS — Dev Mode" | **"Hermes Content Assistant"** |
| **Mô tả ngắn** | "[DEV ONLY] Full Agentic Extension" | **"Bảng điều khiển Side Panel hỗ trợ quản lý, tổ chức và sao chép nhanh bài viết cá nhân."** |
| **Danh mục** | N/A | **Productivity** (Năng suất) |
| **Hình ảnh đại diện**| Biểu tượng tự động hóa/bánh răng | **Biểu tượng cuốn sổ/ghi chú (Năng suất)** |
| **Ảnh chụp màn hình** | Giao diện điều hành Agent Loop | **Giao diện quản lý danh sách bài viết trên Side Panel** |
| **Từ khóa mô tả** | agent, auto, bot, automation | **save, organize, notes, clipboard, copy** |

### 2.4 manifest.json — Phiên bản CWS (Đặc tả chi tiết)

```json
{
  "manifest_version": 3,
  "name": "Hermes Content Assistant",
  "version": "1.0.0",
  "description": "Bảng điều khiển Side Panel hỗ trợ quản lý, tổ chức và sao chép nhanh bài viết cá nhân.",
  "permissions": ["storage", "sidePanel"],
  "background": {
    "service_worker": "background_safe.js"
  },
  "side_panel": {
    "default_path": "sidepanel.html"
  },
  "icons": {
    "48": "icons/icon48.png",
    "128": "icons/icon128.png"
  }
}
```

### 2.5 Cấu trúc tệp tin phiên bản CWS

```
extension_cws/                  ← Thư mục đóng gói nộp lên Chrome Web Store
├── manifest.json               ← manifest cho bản CWS (Quyền storage và sidePanel)
├── background_safe.js          ← Kích hoạt Side Panel khi nhấp icon
├── sidepanel.html              ← Giao diện Side Panel hiển thị danh sách bài viết
├── sidepanel.js                ← REST API Client, thực hiện Copy-Paste và chuyển hướng tab
└── icons/
    ├── icon48.png              ← Icon chủ đề ghi chú/năng suất
    └── icon128.png
```

#### 2.5.1 background_safe.js — Đặc tả luồng xử lý
```javascript
/**
 * background_safe.js — CWS Diplomat Background Service Worker
 *
 * - Hoàn toàn không trạng thái (Stateless).
 * - Không có AgentLoop, không sử dụng WebSocket hay Offscreen Document.
 * - Nhiệm vụ duy nhất: Cấu hình hành vi kích hoạt Side Panel.
 */

chrome.sidePanel
  .setPanelBehavior({ openPanelOnActionClick: true })
  .catch((error) => console.error("[Background] Lỗi cấu hình Side Panel Behavior:", error));
```

#### 2.5.2 sidepanel.js — Đặc tả luồng xử lý giao diện Side Panel
```javascript
/**
 * sidepanel.js — CWS Diplomat Side Panel Logic
 *
 * - Thực hiện truy vấn REST API đến Dashboard Server để lấy thông tin bài viết.
 * - Quản lý chức năng sao chép nội dung vào clipboard hệ thống.
 * - Chuyển hướng tab hoặc mở liên kết nhóm Facebook thủ công.
 */

const DASHBOARD_API = "http://localhost:3000/api";

document.addEventListener("DOMContentLoaded", () => {
  loadSuggestions();
  setupEventListeners();
});

async function loadSuggestions() {
  try {
    const response = await fetch(`${DASHBOARD_API}/content-suggestions`);
    if (!response.ok) throw new Error("Mất kết nối với Dashboard Server");
    
    const suggestions = await response.json();
    renderSuggestions(suggestions);
  } catch (error) {
    document.getElementById("content-list").innerHTML = 
      `<div class="error-msg">Không thể tải gợi ý bài viết: ${error.message}</div>`;
  }
}

function renderSuggestions(items) {
  const container = document.getElementById("content-list");
  container.innerHTML = "";
  
  items.forEach(item => {
    const card = document.createElement("div");
    card.className = "suggestion-card";
    card.innerHTML = `
      <h4>${escapeHtml(item.title)}</h4>
      <p class="content-preview">${escapeHtml(item.body)}</p>
      <div class="actions">
        <button class="btn-copy-text" data-text="${escapeHtml(item.body)}">Sao chép văn bản</button>
        ${item.mediaUrl ? `<button class="btn-copy-media" data-url="${escapeHtml(item.mediaUrl)}">Sao chép liên kết ảnh</button>` : ""}
        <button class="btn-open-group" data-url="${escapeHtml(item.targetGroupUrl)}">Mở Nhóm</button>
      </div>
    `;
    container.appendChild(card);
  });
}

function setupEventListeners() {
  document.getElementById("content-list").addEventListener("click", async (e) => {
    if (e.target.classList.contains("btn-copy-text")) {
      const text = e.target.getAttribute("data-text");
      await navigator.clipboard.writeText(text);
      showToast("Đã sao chép văn bản bài đăng!");
    }
    
    if (e.target.classList.contains("btn-copy-media")) {
      const mediaUrl = e.target.getAttribute("data-url");
      await navigator.clipboard.writeText(mediaUrl);
      showToast("Đã sao chép liên kết media!");
    }
    
    if (e.target.classList.contains("btn-open-group")) {
      const url = e.target.getAttribute("data-url");
      chrome.tabs.create({ url: url });
    }
  });
}

function escapeHtml(str) {
  return str.replace(/[&<>'"]/g, 
    tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
  );
}

function showToast(message) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.add("visible");
  setTimeout(() => toast.classList.remove("visible"), 2000);
}
```

---

## 3. Đặc tả kỹ thuật GitHub Ghost (Developer Unpacked Agent)

### 3.1 Khả năng tự động hóa toàn phần (Full Agentic)

Bản Ghost giữ nguyên toàn bộ kiến trúc lõi và các quyền hạn đặc biệt để tự động hóa:

| Module lõi | Vai trò kỹ thuật | Đặc tả liên kết |
|--------|-----------|----------------|
| **AgentLoop** | Vòng lặp tự động hóa đăng bài và tự khôi phục khi gặp lỗi (self-healing) | Spec 05 |
| **nativeMessaging** | Giao tiếp Socket qua Local Proxy Client (Python backend) | Spec 01, Section 8 |
| **react_state_patcher** | Can thiệp sâu cấu trúc React Fiber để gán dữ liệu không cần sự kiện UI | Spec 01 |
| **dom_compressor** | Nén cấu trúc DOM và định danh phần tử qua thuật toán băm FNV-1a 32-bit | Spec 01, Section 5 |
| **offscreen.js** | Duy trì kết nối persistent WebSocket thông qua Offscreen Document | Spec 01, Section 3 |
| **human_simulator** | Mô phỏng chuột Bezier tự nhiên và trễ gõ phím phân phối Gaussian | Spec 04 |
| **Checkpoint Detection** | Nhận diện và dừng vòng lặp khi tài khoản Facebook bị khóa bảo mật | Spec 06 |

### 3.2 manifest.json — Phiên bản Ghost (Đặc tả chi tiết)

```json
{
  "manifest_version": 3,
  "name": "Hermes OS — Dev Mode",
  "version": "2.0.0-dev",
  "description": "[DEV ONLY] Full Agentic Extension. Load unpacked only. Do NOT upload to CWS.",
  "permissions": [
    "storage",
    "tabs",
    "activeTab",
    "scripting",
    "nativeMessaging",
    "offscreen",
    "alarms"
  ],
  "host_permissions": [
    "https://www.facebook.com/*",
    "https://*.fb.com/*",
    "http://localhost:3000/*"
  ],
  "background": {
    "service_worker": "background.js",
    "type": "module"
  },
  "content_scripts": [
    {
      "matches": [
        "https://www.facebook.com/*",
        "https://*.fb.com/*"
      ],
      "js": ["content.js"],
      "run_at": "document_idle",
      "all_frames": false
    }
  ],
  "web_accessible_resources": [
    {
      "resources": ["offscreen.html"],
      "matches": ["<all_urls>"]
    }
  ],
  "action": {
    "default_popup": "popup.html",
    "default_icon": {
      "48": "icons/icon48_dev.png",
      "128": "icons/icon128_dev.png"
    }
  },
  "icons": {
    "48": "icons/icon48_dev.png",
    "128": "icons/icon128_dev.png"
  },
  "minimum_chrome_version": "116"
}
```

### 3.3 Khởi tạo bắt tay (HELLO Handshake)

Quy trình bắt tay gửi cấu hình ID động và chế độ thực thi từ Offscreen Document lên Dashboard Server:

```javascript
// offscreen.js — Thực thi trong performHandshake()
// Tham chiếu thêm Spec 01 Section 3.4 và Section 8 để biết giao thức chi tiết

const helloPayload = {
  type: 'HELLO',
  nonce: crypto.randomUUID(),
  timestamp: Date.now(),
  signature: await hmacSha256Hex(authSecret, `${nonce}:${timestamp}`),
  extensionVersion: chrome.runtime.getManifest().version,

  // ── THÔNG TIN PHÂN TUYẾN HYBRID (Spec 09) ─────────────────────
  extension_mode: 'GHOST',               // Xác định chế độ tự động hóa
  extension_id: chrome.runtime.id,       // ID động tại runtime
  // ──────────────────────────────────────────────────────────────
};
ws.send(JSON.stringify(helloPayload));
```

---

## 4. Cấu hình Dashboard Server (Phân tuyến định danh thông qua Extension ID)

### 4.1 Cơ chế phân loại trong `wsServer.js`

Dashboard Server phân loại kết nối dựa trên trường `extension_mode` và kiểm tra chéo chữ ký HMAC với `extension_id` động của phiên bản Ghost.

### 4.2 Triển khai luồng điều phối trên Dashboard (`wsServer.js`)

```javascript
// src/websocket/wsServer.js — Tích hợp sau khi xác thực chữ ký cơ bản

/**
 * handleHybridRouting — Phân quyền kết nối dựa trên chế độ Extension
 *
 * @param {WebSocket} ws        - Kết nối WebSocket hiện hành
 * @param {object}   parsed    - Payload thông điệp HELLO đã phân tách
 */
function handleHybridRouting(ws, parsed) {
  const { account_id, extension_mode, extension_id, hmac } = parsed;
  const mode = extension_mode || 'DIPLOMAT';

  if (mode === 'GHOST') {
    // Thực hiện xác thực HMAC nghiêm ngặt cho chế độ GHOST
    const expectedHmac = computeHMAC(
      account_id + (extension_id || ''),
      config.ws_auth_secret
    );

    if (!hmac || hmac !== expectedHmac) {
      logger.warn(`[WS][HYB] ERR-HYB-01: Sai lệch chữ ký HMAC cho tài khoản=${account_id}`);
      ws.close(4001, 'ERR-HYB-01: HMAC mismatch — Ghost mode denied');
      return;
    }

    // Thiết lập quyền hạn Agentic OS
    ws.agentMode = 'AGENTIC_OS';
    extensionClients.set(account_id, ws);
    ws.accountId = account_id;

    ws.send(JSON.stringify({
      type: 'WELCOME',
      mode: 'AGENTIC_OS',
      features: ['AGENT_LOOP', 'DOM_CONTROL', 'PROXY_RELAY', 'SCREENSHOT'],
      message: 'Ghost Mode activated. Full agentic capabilities enabled.',
    }));

    logger.info(`[WS][HYB] Tiện ích Ghost được đăng ký thành công: account=${account_id}, extId=${extension_id}`);

  } else {
    // Chế độ an toàn (Diplomat)
    ws.agentMode = 'SAFE';
    extensionClients.set(account_id, ws);
    ws.accountId = account_id;

    ws.send(JSON.stringify({
      type: 'WELCOME',
      mode: 'SAFE',
      features: ['GROUP_SYNC', 'CONTENT_WIDGET'],
      message: 'Safe Mode activated. Manual Side Panel support only.',
    }));

    logger.info(`[WS][HYB] Tiện ích Diplomat được đăng ký thành công: account=${account_id}`);
  }
}

/**
 * Điều phối lệnh điều khiển kèm phân quyền chế độ thực thi
 *
 * @param {string} accountId    - Tài khoản đích
 * @param {object} command      - Gói tin lệnh
 * @returns {boolean}           - Trạng thái gửi lệnh thành công
 */
function sendCommandToExtension(accountId, command) {
  const client = extensionClients.get(accountId);

  if (!client || client.readyState !== WebSocket.OPEN) {
    logger.warn(`[WS][HYB] Không tìm thấy kết nối hoạt động cho tài khoản=${accountId}`);
    return false;
  }

  // Danh sách các lệnh tự động hóa bắt buộc phải chạy ở GHOST mode
  const sensitiveCommands = [
    'CLICK_ELEMENT',
    'TYPE_TEXT',
    'SCROLL',
    'NAVIGATE',
    'ATTACH_MEDIA',
    'START_SESSION',
    'AGENT_LOOP_START',
    'AGENT_LOOP_PAUSE',
    'REACT_PATCH',
    'CAPTURE_SCREENSHOT',
    'SEARCH_AND_CLICK',
  ];

  if (sensitiveCommands.includes(command.type) && client.agentMode !== 'AGENTIC_OS') {
    logger.warn(`[WS][HYB] ERR-HYB-02: Bị chặn lệnh nhạy cảm ${command.type} trên phiên bản SAFE (account=${accountId})`);
    return false;
  }

  client.send(JSON.stringify(command));
  return true;
}

function computeHMAC(data, secret) {
  return require('crypto')
    .createHmac('sha256', secret)
    .update(data)
    .digest('hex');
}
```

---

## 5. Cấu trúc thư mục dự án phân nhánh

```
hermes-facepost-group/
├── extension/                          ← 👻 GHOST: Phiên bản chạy chế độ Developer Unpacked
│   ├── manifest.json                   ← Đầy đủ quyền hạn (Spec 09, Section 3.2)
│   ├── background.js                   ← Quản lý vòng đời và offscreen (Spec 01)
│   ├── offscreen.html                  ← Shell cho offscreen document
│   ├── offscreen.js                    ← Persistent WebSocket + HMAC handshake
│   ├── content.js                      ← Content script tự động hóa DOM
│   ├── dom_compressor.js               ← Nén DOM và sinh fingerprint FNV-1a 32-bit
│   ├── react_state_patcher.js          ← Can thiệp sâu React Fiber
│   ├── human_simulator.js              ← Giả lập tương tác Bezier/Gaussian
│   ├── popup.html / popup.js           ← UI cấu hình nâng cao
│   ├── lib/
│   │   └── hmac_sha256.js
│   └── icons/
│       ├── icon48_dev.png
│       └── icon128_dev.png
│
├── extension_cws/                      ← 🤝 DIPLOMAT: Phiên bản phân phối trên Store
│   ├── manifest.json                   ← Cấu hình quyền hạn tối giản (Spec 09, Section 2.4)
│   ├── background_safe.js              ← Cấu hình mở Side Panel
│   ├── sidepanel.html                  ← Khung hiển thị Side Panel
│   ├── sidepanel.js                    ← Hiển thị danh mục bài viết và thực hiện Copy
│   └── icons/
│       ├── icon48.png                  ← Icon ứng dụng năng suất
│       └── icon128.png
│
├── dashboard/                          ← Dashboard Server Node.js (dùng chung)
│   └── src/
│       ├── websocket/
│       │   └── wsServer.js             ← Điều phối và phân tuyến (Spec 09, Section 4.2)
│       └── api/
│           └── routes/
│               └── content.js          ← REST API cấp dữ liệu bài đăng cho Diplomat
```

---

## 6. Checklist kiểm định trước khi nộp ứng dụng lên Chrome Web Store

Tiện ích CWS phải vượt qua 100% các tiêu chí kiểm định sau trước khi tải lên Store:

- [ ] **Cách ly mã nguồn tự động hóa:** Đảm bảo thư mục `extension_cws/` không chứa bất kỳ tệp hoặc thư viện nào như `react_state_patcher.js`, `human_simulator.js`, `dom_compressor.js`.
- [ ] **Lọc từ khóa nhạy cảm:** Quét toàn bộ mã nguồn `extension_cws/` để đảm bảo không tồn tại các từ khóa: `bypass`, `bot`, `crawler`, `automate`, `facebook_auto`.
- [ ] **Độc lập quyền hạn:** Kiểm tra `manifest.json` chỉ chứa quyền `storage` và `sidePanel`. Không có `scripting`, `nativeMessaging` hay `offscreen`.
- [ ] **Loại bỏ console log nhạy cảm:** Không ghi nhận các thông tin cá nhân hoặc thông tin chẩn đoán lỗi hệ thống ra console.
- [ ] **Kiểm thử hành vi tĩnh:** Đảm bảo mã nguồn không thực hiện đánh giá chuỗi động (`eval` hoặc `new Function`).

---

## 7. Bổ sung cấu trúc dữ liệu HELLO handshake (Spec 00)

Cấu trúc interface `HelloMessage` và `WelcomeMessage` được cập nhật tại `facepost_00_shared_types.md`:

```typescript
interface HelloMessage {
  type: 'HELLO';
  nonce: string;
  timestamp: number;
  signature: string;
  extensionVersion: string;
  accountId?: string;

  // Bổ sung phân tầng Hybrid
  extension_mode?: 'GHOST' | 'DIPLOMAT';  // Mặc định là DIPLOMAT
  extension_id?: string;                  // chrome.runtime.id động
  hmac?: string;                          // Chữ ký xác thực phiên bản Ghost
}

interface WelcomeMessage {
  type: 'WELCOME';
  clientType: 'extension' | 'ui';

  // Phản hồi quyền hạn thực thi từ server
  mode?: 'AGENTIC_OS' | 'SAFE';
  features?: string[];  // Danh sách tính năng được cấp phép hoạt động
  message?: string;
}
```

---

## 8. Bảng mã lỗi hệ thống phân tuyến (Module HYB)

| Mã lỗi | Vùng phát sinh | Mô tả lỗi | Biện pháp xử lý của hệ thống |
|------|--------|-------|--------------|
| `ERR-HYB-01` | wsServer.js | Nhận chế độ GHOST nhưng chữ ký HMAC không hợp lệ | Đóng kết nối lập tức bằng `ws.close(4001)`. Log cảnh báo an ninh. |
| `ERR-HYB-02` | wsServer.js | Lệnh tự động hóa gửi tới tiện ích ở chế độ SAFE | Chặn lệnh, ghi log lỗi phân quyền, trả về trạng thái thất bại cho luồng campaign. |
| `ERR-HYB-03` | wsServer.js | Thiếu trường `extension_id` khi thực hiện bắt tay ở chế độ GHOST | Từ chối kết nối, đóng WebSocket bằng code 4001. |
| `ERR-HYB-04` | Side Panel UI| Lỗi kết nối REST API khi tải danh mục bài viết | Hiển thị thông báo mất kết nối trên giao diện Panel, cung cấp nút tải lại thủ công. |

---

## 9. Phân tích lỗ hổng an ninh và yêu cầu khắc phục

### 🔴 LỖ HỔNG CRITICAL

1. **[SEC-09-01] Rò rỉ hành vi tự động hóa trên Store do sử dụng Automation Wrapper:**
   - *Rủi ro:* Thiết kế tích hợp mã nguồn tự động hóa ngầm trong phiên bản CWS và tắt/mở bằng cấu hình động sẽ bị phát hiện bởi công cụ phân tích AST tĩnh của Google. Điều này dẫn đến việc gỡ bỏ ứng dụng và khóa vĩnh viễn tài khoản phát triển.
   - *Biện pháp khắc phục:* Loại bỏ hoàn toàn mã nguồn tự động hóa và cơ chế chèn Content Script trên phiên bản CWS. Tiện ích CWS chỉ chứa giao diện Chrome Side Panel thủ công hỗ trợ sao chép.

2. **[SEC-09-02] Tấn công Replay Attack khi xác thực chữ ký bắt tay tĩnh:**
   - *Rủi ro:* Nếu chữ ký HMAC trong gói tin HELLO được sinh ra từ các tham số tĩnh như `account_id` và `extension_id` mà không có thời gian và nonce động, kẻ tấn công có thể bắt gói tin và phát lại để thiết lập kết nối trái phép.
   - *Biện pháp khắc phục:* Bắt buộc cấu hình chữ ký HMAC kết hợp `nonce` và `timestamp`. Server kiểm tra chênh lệch thời gian tối đa ±30 giây và lưu trữ nonce vào bộ nhớ đệm (Redis/RAM cache) để từ chối các kết nối phát lại.

### 🟠 LỖ HỔNG HIGH

1. **[SEC-09-03] Timing Attack khi so sánh Signature:**
   - *Rủi ro:* Sử dụng toán tử so sánh thông thường (`===` hoặc `!==`) trong Node.js để kiểm tra chữ ký HMAC sẽ thoát sớm ngay khi phát hiện ký tự sai lệch đầu tiên. Điều này cho phép kẻ tấn công đo đạc thời gian phản hồi ở mức mili-giây để dò tìm từng ký tự của chữ ký.
   - *Biện pháp khắc phục:* Bắt buộc sử dụng phương thức so sánh thời gian không đổi `crypto.timingSafeEqual()` của Node.js để đối chiếu chữ ký HMAC.

2. **[SEC-09-04] Rò rỉ định tuyến chéo từ SAFE mode:**
   - *Rủi ro:* Nếu Dashboard Server lưu trạng thái phân quyền thực thi (`agentMode`) ở cấp độ phiên (session/token) thay vì gắn trực tiếp vào thực thể kết nối socket hiện hành, tài khoản chạy ở chế độ SAFE vẫn có thể gửi API thực thi các lệnh tự động hóa sang socket GHOST của tài khoản khác.
   - *Biện pháp khắc phục:* Luôn xác thực thuộc tính `ws.agentMode === 'AGENTIC_OS'` trực tiếp trên đối tượng WebSocket đang xử lý yêu cầu trước khi chuyển tiếp các lệnh nhạy cảm.

---
*Tài liệu đặc tả kiến trúc Hybrid Extension | Version 2.0.0 | Thiết kế bởi Hermes FacePost-Group Design Team*
