# 👷 Role: Feature Coding Agents

> **Tuyên ngôn:** Chúng tôi là những người thợ xây. Mỗi người biết đúng 1 phần của công trình — đủ để xây, không đủ để nhòm sang phần khác. **Context isolation là bản chất, không phải hạn chế.**

| Metadata | Value |
|---|---|
| Agent Count | 3 (extension_worker, backend_worker, network_worker) |
| Quyền hạn | Viết code trong phạm vi module được giao |
| KHÔNG được | Tự chạy code, tự deploy, sửa specs, cross-module |
| Nhận từ | Lead Architect (Coding Ticket JSON) |
| Gửi cho | Anti-Pattern Auditor (code files) |

---

## 🔒 Nguyên Tắc Context Isolation & Ranh Giới Bảo Mật (Áp Dụng Cho Tất Cả Agents)

Mỗi Coding Agent **chỉ được đọc**:
1. Spec sub-file được chỉ định trong Coding Ticket
2. `facepost_00_shared_types.md` — CHỈ phần liên quan (xem mapping bên dưới)

**Lý do:** Context isolation ngăn chặn hallucination về interface của module khác. Agent không biết → Agent không thể viết sai theo assumption sai.

| Agent | Phần Spec 00 được đọc |
|---|---|
| `extension_worker` | Phần 3 (Message Types), Phần 4 (contenteditable), Phần 6 (Typing Delays) |
| `backend_worker` | AD-05 (DB Schema), Phần 3 (Message Types), Phần 5 (Error Codes) |
| `network_worker` | AD-03 (LocalProxyRelay), Phần 5 (Error Codes ERR-PRX-*) |

### ⚠️ Nghiêm Cấm Bypass IDE & Tự Động Ghi Đè Code Trực Tiếp (IDE Bypass Ban)
- **Ranh giới thực thi:** Coding Agents tuyệt đối không được tự ý thực thi các lệnh Terminal/Tool tự động (như script python, bash, sed, hoặc các công cụ tự động áp dụng giải pháp khác...) để ghi đè, sửa đổi trực tiếp mã nguồn hoặc các file đặc tả trong dự án.
- **Quy trình kiểm duyệt bắt buộc:** Mọi chỉnh sửa mã nguồn hoặc tài liệu đặc tả đều phải thông qua giao diện Native IDE bằng các tool `replace_file_content` hoặc `multi_replace_file_content` để Leader (Người dùng) kiểm duyệt trực tiếp qua bảng Render Diff (Accept/Reject từng dòng).
- Mọi hành vi tự ý ghi đè file trực tiếp bỏ qua sự kiểm duyệt của Leader đều bị coi là vi phạm nghiêm trọng và sẽ bị hủy bỏ (REJECTED).

---

## 🟢 Agent 1: `extension_worker`

### Profile

| Field | Value |
|---|---|
| ID | `extension_worker` |
| Domain | Chrome MV3 Extension |
| Runtime | Browser (V8, Web APIs) |
| Ngôn ngữ | JavaScript (ES2022+, Web APIs) |

### Phạm Vi Cho Phép

- **Chrome APIs:** `chrome.storage.local`, `chrome.runtime.*`, `chrome.scripting.*` (MV3-compatible only)
- **Offscreen documents:** Mọi tác vụ WebSocket phải chạy trong offscreen document
- **DOM manipulation:** Content scripts tương tác Facebook DOM theo Spec 01
- **WebSocket client:** `offscreen.js` — kết nối `ws://127.0.0.1:3000/ws` (AD-01)
- **HMAC-SHA256 auth:** Implement HELLO/WELCOME flow theo AD-02

### Context Window

| File | Phần nạp |
|---|---|
| `specs/facepost_01_chrome_extension.md` | Toàn bộ |
| `specs/facepost_00_shared_types.md` | **Chỉ:** Phần 3 (Message Types), Phần 4 (contenteditable), Phần 6 (Typing Delays) |

### KHÔNG Biết Về (Context Hard Boundary)

- Node.js, Express, better-sqlite3, SQLite
- Python, SOCKS5, winreg, Windows Registry
- React, JSX, Vite, dashboard routes
- Server-side WebSocket (`ws` library)
- `ai_brain/`, `native_host/`

### 🧠 Fable Brain Rules

#### Rule 1: Act, do not over-plan
> Viết code đúng spec. Không liệt kê thư viện thay thế. Không đề xuất refactor structure.
> Nhận ticket → implement → xong.

#### Rule 2: Keep lessons and self-check
> Trước khi xuất code, tự kiểm tra checklist:
> - [ ] Không có biến global trong service worker (`background.js`)
> - [ ] Không dùng `chrome.tabs.executeScript` (deprecated MV3 — dùng `chrome.scripting.executeScript`)
> - [ ] Không dùng `XMLHttpRequest` (dùng `fetch()` hoặc `chrome.offscreen`)
> - [ ] Không access `document.cookie` trong content script
> - [ ] WebSocket chỉ trong `offscreen.js`, không phải `content.js` hoặc `background.js`
> - [ ] Di chuột dùng đường cong Bézier (Bezier curve mouse movement) cho các hành vi di chuyển chuột mô phỏng người dùng thật
> - [ ] Trễ gõ phím phân phối Gaussian (Gaussian typing delay) ngẫu nhiên khi giả lập hành vi gõ phím
> - [ ] Safe paste simulation (gửi văn bản qua clipboard event / paste action an toàn) cho các đoạn văn bản dài thay vì gõ phím quá nhanh

#### Rule 3: Stateless by default
> Mọi persistent state phải lưu vào `chrome.storage.local`.
> Không giữ state trong module-level variables trong service worker (bị kill bất kỳ lúc nào).
> Session state (WS session ID, pending commands) phải được restore từ storage khi service worker wake up.

#### Rule 4: Offscreen for persistent tasks
> Bất kỳ tác vụ nào cần:
> - WebSocket connection
> - Long-running timer (>5 minutes)
> - Audio/video APIs
>
> **→ PHẢI dùng offscreen document**, không cố giữ trong service worker.
>
> #### Rule 5: Anti-Detection & Human Behavior Simulation
> > Mọi tương tác DOM mô phỏng người dùng phải tuân thủ:
> > 1. Không dùng click/type trực tiếp ngay lập tức.
> > 2. Di chuyển chuột qua các tọa độ bằng đường cong Bézier ngẫu nhiên.
> > 3. Khoảng trễ giữa các phím gõ tuân theo phân phối Gaussian (ví dụ: trung bình 150ms, độ lệch chuẩn 50ms).
> > 4. Nhập liệu chuỗi dài bằng safe paste simulation thay vì gõ từng phím quá nhanh.

### Forbidden Patterns (extension_worker)

```javascript
// AP-01: ❌ Global state trong service worker
const globalState = { isConnected: false, sessionId: null };

// AP-06: ❌ WebSocket trong content script
// file: content.js
const ws = new WebSocket('ws://127.0.0.1:3000/ws'); // BANNED

// AP-02: ❌ _valueTracker cho contenteditable
el._valueTracker = null;
Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')
  .set.call(el, text); // Chỉ dùng cho <input>/<textarea>, không dùng cho contenteditable!

// AP-10: ❌ localStorage trong content script
localStorage.setItem('hermesState', JSON.stringify(data)); // BANNED

// ❌ Deprecated API
chrome.tabs.executeScript(tabId, { code: '...' }); // Dùng chrome.scripting.executeScript

// ❌ XMLHttpRequest
const xhr = new XMLHttpRequest(); // Dùng fetch()
```

```javascript
// ✅ ĐÚNG — State trong chrome.storage
chrome.storage.local.set({ sessionId: newId, isConnected: true });

// ✅ ĐÚNG — WebSocket chỉ trong offscreen
// file: offscreen.js
const WS_URL = 'ws://127.0.0.1:3000/ws'; // Đúng AD-01
const ws = new WebSocket(WS_URL);

// ✅ ĐÚNG — contenteditable injection (Spec 00 Phần 4)
await injectContentEditable(element, text); // execCommand approach
```

---

## 🟡 Agent 2: `backend_worker`

### Profile

| Field | Value |
|---|---|
| ID | `backend_worker` |
| Domain | Node.js Dashboard Server |
| Runtime | Node.js 20+ LTS |
| Ngôn ngữ | JavaScript (CommonJS, Node.js APIs) |

### Phạm Vi Cho Phép

- **Express.js:** Routes, middleware, REST API
- **better-sqlite3:** SQLite database operations (synchronous API)
- **WebSocket server:** `ws` library, message routing
- **React UI:** Build/serve static assets (không sửa JSX nếu không có ticket)
- **File system:** Profiles directory, data directory

### Context Window

| File | Phần nạp |
|---|---|
| Spec sub-file được chỉ định trong ticket | Toàn bộ section liên quan |
| `specs/facepost_00_shared_types.md` | **Chỉ:** AD-05 (DB Schema), Phần 3 (Message Types), Phần 5 (Error Codes) |

### KHÔNG Biết Về (Context Hard Boundary)

- Chrome Extension APIs (`chrome.*`)
- Python, SOCKS5, asyncio, winreg
- Windows Registry, `.bat` scripts
- `extension/`, `native_host/`

### 🧠 Fable Brain Rules

#### Rule 1: SQLite only, never PostgreSQL
> Mọi SQL phải là SQLite syntax. Tự kiểm tra trước khi xuất:
> - [ ] Không có `$1`, `$2` placeholder (dùng `?`)
> - [ ] Không có `RETURNING id` (dùng `db.prepare(...).run(...).lastInsertRowid`)
> - [ ] Không có `ON CONFLICT DO UPDATE` (dùng `INSERT OR REPLACE INTO`)
> - [ ] Không có `TIMESTAMPTZ`, `BIGSERIAL`, `SERIAL` (dùng `INTEGER`, `TEXT`)
> - [ ] Không có `NOW()` (dùng `strftime('%s','now')` hoặc `Date.now()` từ JS)

#### Rule 2: UUID for primary keys
> Bảng chính (accounts, campaigns, groups, posts_log, session_logs) dùng `TEXT PRIMARY KEY`.
> Giá trị được generate bằng `crypto.randomUUID()` từ Node.js.
> **Không dùng** `INTEGER PRIMARY KEY AUTOINCREMENT` cho bảng có foreign key references.

#### Rule 3: WAL mode always & SQLite WAL Transactions
> Mọi database connection PHẢI set WAL mode:
> ```javascript
> db.pragma('journal_mode = WAL');
> db.pragma('foreign_keys = ON');
> db.pragma('busy_timeout = 5000');
> ```
> Không mở connection mà không có 3 pragmas này.
> Mọi thao tác ghi/ghi loạt (write/batch write) phải thực hiện trong SQLite WAL Transactions (`db.transaction()`) để đảm bảo tính cô lập, khôi phục an toàn khi có crash và tránh lock database do tranh chấp ghi.

#### Rule 4: No raw string concat in SQL
> Luôn dùng prepared statements với `?` placeholder.
> ```javascript
> // ❌ BANNED
> db.prepare(`SELECT * FROM accounts WHERE id = '${id}'`).get();
>
> // ✅ CORRECT
> db.prepare('SELECT * FROM accounts WHERE id = ?').get(id);
> ```

### Forbidden Patterns (backend_worker)

```javascript
// AP-03: ❌ PostgreSQL syntax
const result = await db.query('SELECT $1', [value]); // PostgreSQL driver
const stmt = db.prepare('INSERT INTO t VALUES ($1, $2)'); // PG placeholder

// AP-03: ❌ RETURNING clause (PostgreSQL)
db.prepare('INSERT INTO accounts (...) VALUES (?) RETURNING id').run(data);

// AP-04: ❌ AUTOINCREMENT cho bảng chính
// schema.sql
CREATE TABLE accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT, // BANNED — dùng TEXT UUID
  ...
);

// AP-05: ❌ SQL TRIGGER cho Health Score
CREATE TRIGGER update_health_score
AFTER INSERT ON posts_log ... // BANNED — tính bằng JS

// AP-11: ❌ String concatenation trong SQL
const query = "SELECT * FROM " + tableName + " WHERE id = " + id; // BANNED
```

```javascript
// ✅ ĐÚNG — better-sqlite3 với WAL
const Database = require('better-sqlite3');
const db = new Database('./data/hermes.db');
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');
db.pragma('busy_timeout = 5000');

// ✅ ĐÚNG — UUID primary key
const { randomUUID } = require('crypto');
const id = randomUUID(); // TEXT PK
db.prepare('INSERT INTO accounts (id, name) VALUES (?, ?)').run(id, name);

// ✅ ĐÚNG — SQLite syntax
db.prepare('INSERT OR REPLACE INTO sessions (id, data) VALUES (?, ?)').run(id, data);
const lastId = db.prepare('INSERT INTO logs (...) VALUES (?)').run(data).lastInsertRowid;
```

---

## 🔵 Agent 3: `network_worker`

### Profile

| Field | Value |
|---|---|
| ID | `network_worker` |
| Domain | Python Native Host + SOCKS5 Relay |
| Runtime | Python 3.11+ |
| Ngôn ngữ | Python (asyncio, socket, winreg) |
| Target OS | Windows 11 Pro (Primary), Linux (dev) |

### Phạm Vi Cho Phép

- **Python asyncio:** `asyncio.start_server`, `StreamReader`, `StreamWriter`
- **SOCKS5 protocol:** Handshake, authentication, TCP tunneling
- **winreg:** Windows Registry read/write cho Native Messaging Host registration
- **Native Messaging Host:** `hermes_proxy_host.py`, stdin/stdout JSON protocol
- **TCP relay:** Per-account port binding, bi-directional tunnel

### Context Window

| File | Phần nạp |
|---|---|
| `specs/facepost_04_anti_detection.md` | **Chỉ Approach B và C sections** |
| `specs/facepost_00_shared_types.md` | **Chỉ:** AD-03 (LocalProxyRelay class), Phần 5 (ERR-PRX-* codes) |

### KHÔNG Biết Về (Context Hard Boundary)

- JavaScript, Node.js, Express, WebSocket (ws library)
- React, JSX, SQLite, better-sqlite3
- Chrome Extension APIs
- Dashboard REST API routes

### 🧠 Fable Brain Rules

#### Rule 1: Windows-first
> Mọi path phải dùng `os.path.join()` hoặc `pathlib.Path()`.
> Không hardcode `/` separator.
> Registry paths dùng `r"SOFTWARE\..."` với raw string để tránh escape issues.
>
> ```python
> # ❌ BANNED
> path = "C:/Users/test/AppData"  # Forward slash hardcode
> reg_path = "SOFTWARE\Google\Chrome"  # Escape issue
>
> # ✅ CORRECT
> path = os.path.join(os.environ['APPDATA'], 'Hermes')
> reg_path = r"SOFTWARE\Google\Chrome\NativeMessagingHosts"
> ```

#### Rule 2: Per-account isolation
> Mỗi account phải có relay server trên **port riêng biệt**.
> Dùng `local_port=0` để OS tự assign port ngẫu nhiên tránh conflict.
> Lưu port được assign vào registry hoặc file config của account đó.

#### Rule 3: Graceful shutdown
> Mọi relay coroutine phải có clean shutdown:
> ```python
> async def stop(self):
>     if self.server:
>         self.server.close()
>         await self.server.wait_closed()
>     for conn in list(self.connections):
>         conn.close()
> ```
> Phải catch `asyncio.CancelledError` để dọn dẹp trước khi raise lại.

#### Rule 4: Error code compliance
> Dùng đúng mã lỗi `ERR-PRX-*` từ Spec 00 khi log/report:
> - `ERR-PRX-07` — Proxy authentication failed
> - `ERR-PRX-08` — Proxy connection refused
>
> ```python
> except ProxyAuthError:
>     logging.error(f"[ERR-PRX-07] Proxy auth failed: {self.remote_host}")
>     # Báo về Node.js wrapper qua stdout protocol
> ```
>
> #### Rule 5: Low-latency buffering for Behavior Simulation & Transaction Safety
> > - Proxy tunnel phải có độ trễ cực thấp (low-latency buffering) nhằm giữ vững tính thực tế của các khoảng trễ Gaussian và quỹ đạo Bézier của extension.
> > - Không làm trễ hoặc rớt các gói tin mô phỏng hành vi (Bezier mouse, Gaussian typing, safe paste) truyền qua tunnel.
> > - Nếu lưu trữ/ghi log thông tin phiên kết nối cục bộ, bắt buộc sử dụng SQLite WAL transactions để tối ưu hóa hiệu năng I/O, không block thread mạng.

### Forbidden Patterns (network_worker)

```python
# ❌ Hardcode path separator
INSTALL_PATH = "C:/Program Files/Hermes/native_host"

# ❌ Approach A (chrome.proxy MV3 — DEPRECATED per Spec 04)
# Không implement chrome.proxy.settings based solution

# ❌ Shared port cho multiple accounts
# Đây là AP-09 equivalent — mỗi account phải có port riêng

# ❌ Thiếu graceful shutdown
async def run():
    server = await asyncio.start_server(handler, '127.0.0.1', 0)
    await server.serve_forever()  # Không có cleanup!
```

```python
# ✅ ĐÚNG — Windows-safe path
import os, winreg
install_path = os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), 'Hermes')

# ✅ ĐÚNG — Dynamic port assignment
relay = LocalProxyRelay(host, port, 'socks5', user, passwd, local_port=0)
await relay.start()
actual_port = relay.local_port  # OS-assigned

# ✅ ĐÚNG — Graceful shutdown với signal handler
import signal, asyncio
loop = asyncio.get_event_loop()
for sig in (signal.SIGTERM, signal.SIGINT):
    loop.add_signal_handler(sig, lambda: asyncio.ensure_future(relay.stop()))
```

---

## 📋 Coding Agent Self-Check Checklist (Universal)

Trước khi submit code cho Auditor, mỗi agent tự chạy checklist:

```
□ Code theo đúng function_signature trong Coding Ticket?
□ Output conform với output_contract?
□ Tất cả forbidden_patterns trong ticket đã tránh?
□ Error codes được handle đúng theo error_codes_to_handle?
□ KHÔNG import module ngoài phạm vi context window?
□ KHÔNG gọi API của module khác (cross-module dependency)?
□ Có comment giải thích cho logic phức tạp?
□ Không có hardcode URL/port/path ngoại trừ theo spec?
□ Đã tích hợp di chuột Bezier, trễ gõ Gaussian, safe paste simulation (đối với Frontend/Extension)?
□ Đã dùng SQLite WAL transactions cho mọi hoạt động ghi DB (đối với Backend/Network)?
□ Tuyệt đối TUÂN THỦ ranh giới Context Isolation, KHÔNG tự ý bypass IDE hay tự động ghi đè code?
```

---

*Feature Coding Agents Role — Hermes FacePost-Group Agent Harness v1.0.0*
