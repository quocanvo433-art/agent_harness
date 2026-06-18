# 🚫 Anti-Pattern Registry — Hermes FacePost-Group

> **Tuyên ngôn:** Tài liệu này là Hiến pháp chất lượng của dự án. Mọi dòng code vi phạm các Anti-Pattern được định nghĩa dưới đây sẽ bị hệ thống kiểm duyệt tĩnh và Auditor Agent REJECT ngay lập tức.

# 📋 Bảng Tổng Hợp 32 Anti-Patterns

| ID | Severity | Module | Anti-Pattern Name | Detection Hint | Spec Reference |
|---|---|---|---|---|---|
| **AP-01** | `CRITICAL` | Extension | Global state trong `background.js` | Khai báo `let`/`var`/`const` lưu trạng thái ở root level | [facepost_01_chrome_extension.md](file:///home/newuser/AI_facepostgroup/specs/facepost_01_chrome_extension.md) |
| **AP-02** | `CRITICAL` | Extension | `_valueTracker` cho contenteditable div | Gán trực tiếp `element._valueTracker` hoặc `innerText` | [facepost_01_chrome_extension.md](file:///home/newuser/AI_facepostgroup/specs/facepost_01_chrome_extension.md) |
| **AP-03** | `CRITICAL` | DB / Backend | PostgreSQL syntax trong SQLite | Dùng `$1`, `$2`, `RETURNING`, `TIMESTAMPTZ`, `BIGSERIAL` | [facepost_00_shared_types.md](file:///home/newuser/AI_facepostgroup/specs/facepost_00_shared_types.md) |
| **AP-04** | `CRITICAL` | DB / Backend | `INTEGER PRIMARY KEY AUTOINCREMENT` | Khai báo `AUTOINCREMENT` trong SQLite table schema | [facepost_00_shared_types.md](file:///home/newuser/AI_facepostgroup/specs/facepost_00_shared_types.md) |
| **AP-05** | `CRITICAL` | DB / Backend | SQL TRIGGER cho Health Score | Viết trigger tự động update điểm sức khỏe tài khoản | [facepost_03_dashboard_app.md](file:///home/newuser/AI_facepostgroup/specs/facepost_03_dashboard_app.md) |
| **AP-06** | `CRITICAL` | Extension | `new WebSocket` trong `content.js` | Khởi tạo kết nối WebSocket trực tiếp từ content script | [facepost_01_chrome_extension.md](file:///home/newuser/AI_facepostgroup/specs/facepost_01_chrome_extension.md) |
| **AP-07** | `CRITICAL` | UI / AI Brain | Raw system prompt trên UI | Hardcode system prompt hướng dẫn AI ở phía Client/UI | [facepost_02_ai_agent_brain.md](file:///home/newuser/AI_facepostgroup/specs/facepost_02_ai_agent_brain.md) |
| **AP-08** | `CRITICAL` | UI | `ws.onmessage` trong component con | Đăng ký trực tiếp sự kiện WebSocket trong React component | [facepost_07_dashboard_ui.md](file:///home/newuser/AI_facepostgroup/specs/facepost_07_dashboard_ui.md) |
| **AP-09** | `HIGH` | Extension | `chrome.proxy.settings` (Approach A) | Gọi trực tiếp API thiết lập proxy của Chrome Extension | [facepost_04_anti_detection.md](file:///home/newuser/AI_facepostgroup/specs/facepost_04_anti_detection.md) |
| **AP-10** | `HIGH` | Extension | `localStorage` trong content script | Đọc/Ghi dữ liệu cấu hình qua `localStorage` ở content | [facepost_01_chrome_extension.md](file:///home/newuser/AI_facepostgroup/specs/facepost_01_chrome_extension.md) |
| **AP-11** | `HIGH` | DB / Backend | String concat trong SQL query | Nối chuỗi biến trực tiếp vào chuỗi chuẩn bị SQL | [facepost_00_shared_types.md](file:///home/newuser/AI_facepostgroup/specs/facepost_00_shared_types.md) |
| **AP-12** | `HIGH` | AI Brain | LLM output không qua `HumanessHarness` | Trả về nội dung AI tạo ra trực tiếp mà không chấm điểm | [facepost_08_content_engine.md](file:///home/newuser/AI_facepostgroup/specs/facepost_08_content_engine.md) |
| **AP-13** | `MEDIUM` | Extension | WS reconnect không có exponential backoff | Sử dụng khoảng thời gian reconnect cố định hoặc lặp vô hạn | [facepost_01_chrome_extension.md](file:///home/newuser/AI_facepostgroup/specs/facepost_01_chrome_extension.md) |
| **AP-14** | `MEDIUM` | UI | AI reply box không giới hạn chiều cao | Hộp thoại hiển thị text của AI không set max-height | [facepost_07_dashboard_ui.md](file:///home/newuser/AI_facepostgroup/specs/facepost_07_dashboard_ui.md) |
| **AP-15** | `LOW` | Extension | CSS selector hardcode của Facebook | Dùng các class động của FB làm selector chính | [facepost_06_checkpoint_handler.md](file:///home/newuser/AI_facepostgroup/specs/facepost_06_checkpoint_handler.md) |
| **AP-16** | `LOW` | UI | Fetch keywords trong render loop | Gọi API tải từ khóa trực tiếp trong component render body | [facepost_08_content_engine.md](file:///home/newuser/AI_facepostgroup/specs/facepost_08_content_engine.md) |
| **AP-17** | `HIGH` | Agent Loop / Extension | CẤM điều hướng trực tiếp bằng URL (Direct Navigation) liên tục đối với các tài khoản mới hoặc tài khoản có độ Trust thấp | Dò tìm xem code có liên tục gọi lệnh `NAVIGATE` hoặc `chrome.tabs.update` trực tiếp tới URL của Facebook Groups mà không thông qua luồng Search-and-Click hay không. | [facepost_04_anti_detection.md](file:///home/newuser/AI_facepostgroup/specs/facepost_04_anti_detection.md), [facepost_05_agent_loop.md](file:///home/newuser/AI_facepostgroup/specs/facepost_05_agent_loop.md) |
| **AP-18** | `CRITICAL` | Security / Event Loop | Unsanitized Dynamic RegEx Creation | Khởi tạo `new RegExp()` trực tiếp từ biến đầu vào mà không qua sanitizer | [facepost_08_content_engine.md](file:///home/newuser/AI_facepostgroup/specs/facepost_08_content_engine.md) |
| **AP-19** | `CRITICAL` | Desktop / Electron | Direct WebContents Leak in Electron | Chuyển tiếp trực tiếp IPC event từ Preload Script sang Renderer process | [facepost_10_desktop_packaging.md](file:///home/newuser/AI_facepostgroup/specs/facepost_10_desktop_packaging.md) |
| **AP-20** | `CRITICAL` | Backend / Database | Raw DB Imports on UI | Import các module database (`better-sqlite3`, `pg`) trực tiếp trên file frontend `.jsx` | [facepost_07_dashboard_ui.md](file:///home/newuser/AI_facepostgroup/specs/facepost_07_dashboard_ui.md) |
| **AP-21** | `HIGH` | Stealth / Chrome | WebRTC IP Leakage Exposure | Không tắt UDP non-proxied cho WebRTC trong cấu hình Chrome | [facepost_04_anti_detection.md](file:///home/newuser/AI_facepostgroup/specs/facepost_04_anti_detection.md) |
| **AP-22** | `HIGH` | Stealth / Network | SOCKS5 DNS Leakage | Sử dụng proxy dạng `socks5://` thay vì `socks5h://` gây rò rỉ DNS ở local | [facepost_04_anti_detection.md](file:///home/newuser/AI_facepostgroup/specs/facepost_04_anti_detection.md) |
| **AP-23** | `HIGH` | Stealth / WebSocket | Static Signature for WebSocket Hello | Gói tin HELLO WebSocket được gửi bằng payload JSON tĩnh, không đổi qua các phiên | [facepost_00_shared_types.md](file:///home/newuser/AI_facepostgroup/specs/facepost_00_shared_types.md) |
| **AP-24** | `HIGH` | Stealth / Automation | Non-Stealthy Object Protocol Override | Ghi đè các hàm API trình duyệt bằng cách gán biến trần, làm lệch prototype chain | [facepost_04_anti_detection.md](file:///home/newuser/AI_facepostgroup/specs/facepost_04_anti_detection.md) |
| **CE-UI-01** | `CRITICAL` | UI / Content Engine | Rò rỉ thông tin đăng nhập DB / Network Credentials trên Frontend | Nhúng trực tiếp connection string hoặc API Key / JWT Secret trong mã nguồn UI | [facepost_07_dashboard_ui.md](file:///home/newuser/AI_facepostgroup/specs/facepost_07_dashboard_ui.md) |
| **CE-UI-02** | `HIGH` | UI / Content Engine | Rò rỉ dữ liệu qua Log Console ở môi trường Production | Log Cookie, token, cấu hình nhạy cảm ra console | [facepost_07_dashboard_ui.md](file:///home/newuser/AI_facepostgroup/specs/facepost_07_dashboard_ui.md) |
| **CE-UI-03** | `HIGH` | UI / Content Engine | Rò rỉ kết nối mạng do không giải phóng Listener | EventSource/WebSocket/setInterval không được dọn dẹp khi unmount | [facepost_07_dashboard_ui.md](file:///home/newuser/AI_facepostgroup/specs/facepost_07_dashboard_ui.md) |
| **CE-UI-04** | `CRITICAL` | UI / Content Engine | Đọc ghi DB trực tiếp từ UI components | Import module database (SQLite/Postgres client) trực tiếp trên file frontend | [facepost_07_dashboard_ui.md](file:///home/newuser/AI_facepostgroup/specs/facepost_07_dashboard_ui.md) |
| **AP-25** | `CRITICAL` | Security / Secrets | Rò rỉ khóa bí mật và thiếu tệp `.gitignore` | Commit `.env` chứa API Key/Secret, thiếu hoặc không cấu hình `.gitignore` | [facepost_rules_of_project.md](file:///home/newuser/AI_facepostgroup/facepost_rules_of_project.md) |

---

## 🔍 Mô Tả Chi Tiết 18 Anti-Patterns Nghiêm Trọng (CRITICAL & HIGH)

### AP-01: Global state trong `background.js` (CRITICAL)

* **Tại sao bị cấm (Why is it banned?):**
  Trình duyệt Chrome chạy Manifest V3 sử dụng Service Worker làm nền tảng cho `background.js`. Service Worker có cơ chế Event-driven và sẽ bị tắt (terminate) bất kỳ lúc nào bởi trình duyệt khi không có hoạt động để tối ưu bộ nhớ RAM. Do đó, tất cả các biến toàn cục (global variables) lưu trong bộ nhớ RAM của Service Worker sẽ bị xóa sạch. Nếu lưu trữ trạng thái kết nối, phiên làm việc hoặc thông tin tài khoản tại đây, Extension sẽ mất trạng thái khi khởi động lại Service Worker.
* **Code ví dụ sai (Bad code snippet):**
  ```javascript
  // background.js - Khai báo biến global lưu trạng thái
  let wsConnection = null;
  let activeSession = { username: "", token: "" };
  let isPosting = false;

  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'START_POST') {
      isPosting = true; // Sẽ bị mất khi Service Worker bị tắt và bật lại sau đó
    }
  });
  ```
* **Code ví dụ đúng (Good code snippet):**
  ```javascript
  // background.js - Sử dụng chrome.storage để lưu trữ trạng thái bền vững
  chrome.runtime.onMessage.addListener(async (message, sender, sendResponse) => {
    if (message.type === 'START_POST') {
      await chrome.storage.local.set({ isPosting: true });
    }
  });

  // Khi cần lấy trạng thái
  async function checkPostingStatus() {
    const result = await chrome.storage.local.get('isPosting');
    return result.isPosting || false;
  }
  ```
* **Cách dò tìm / Detection Hint:**
  Sử dụng công cụ `grep` tìm kiếm các khai báo biến ở ngoài cùng của file `background.js` mà không được lưu/nạp từ storage:
  ```bash
  grep -n '^let \|^var ' background.js | grep -v 'function\|class\|=>'
  ```
* **Spec Reference:** [facepost_01_chrome_extension.md §Section-2.1](file:///home/newuser/AI_facepostgroup/specs/facepost_01_chrome_extension.md)

---

### AP-02: `_valueTracker` cho contenteditable div (CRITICAL)

* **Tại sao bị cấm (Why is it banned?):**
  Trang web Facebook được xây dựng hoàn toàn bằng thư viện React. Khi mô phỏng việc điền nội dung vào khung soạn thảo bài viết (thường là thẻ `div` có thuộc tính `contenteditable="true"`), việc gán trực tiếp `innerText` hoặc cố gắng hack thuộc tính nội bộ React bằng `_valueTracker` sẽ không trigger được cơ chế đồng bộ State của React. Điều này dẫn đến giao diện hiển thị văn bản nhưng React State vẫn rỗng, làm cho nút "Đăng" (Publish) bị vô hiệu hóa hoặc gây lỗi crash cây component của React.
* **Code ví dụ sai (Bad code snippet):**
  ```javascript
  // Cố gắng can thiệp trực tiếp vào thuộc tính của phần tử DOM
  const editor = document.querySelector('div[contenteditable="true"]');
  editor.innerText = "Nội dung bài viết mẫu";
  if (editor._valueTracker) {
    editor._valueTracker.setValue("Nội dung bài viết mẫu");
  }
  ```
* **Code ví dụ đúng (Good code snippet):**
  ```javascript
  // Sử dụng mô phỏng hành vi gõ phím thông qua Selection và Dispatch Events chuẩn
  const editor = document.querySelector('div[contenteditable="true"]');
  editor.focus();
  
  // Xóa nội dung cũ bằng Range
  const selection = window.getSelection();
  const range = document.createRange();
  range.selectNodeContents(editor);
  selection.removeAllRanges();
  selection.addRange(range);
  document.execCommand('delete', false, null);

  // Chèn nội dung bằng execCommand để React ghi nhận thay đổi tự nhiên
  document.execCommand('insertText', false, "Nội dung bài viết mẫu");
  
  // Phát các sự kiện cần thiết để kích hoạt cập nhật React State
  editor.dispatchEvent(new Event('input', { bubbles: true }));
  editor.dispatchEvent(new Event('change', { bubbles: true }));
  ```
* **Cách dò tìm / Detection Hint:**
  Tìm kiếm các từ khóa can thiệp trực tiếp vào value tracker hoặc innerText trên khung soạn thảo:
  ```bash
  grep -n '_valueTracker\|innerText.*=' content.js
  ```
* **Spec Reference:** [facepost_01_chrome_extension.md §Section-2.2](file:///home/newuser/AI_facepostgroup/specs/facepost_01_chrome_extension.md)

---

### AP-03: PostgreSQL syntax trong SQLite (CRITICAL)

* **Tại sao bị cấm (Why is it banned?):**
  Hệ thống Dashboard cục bộ chạy trên cơ sở dữ liệu SQLite để đảm bảo tính gọn nhẹ, di động và dễ triển khai trên máy khách. SQLite không tương thích với một số cú pháp đặc trưng của PostgreSQL như placeholder dạng số (`$1`, `$2`), các kiểu dữ liệu nâng cao (`TIMESTAMPTZ`, `BIGSERIAL`), hoặc mệnh đề trả về dữ liệu nhanh `RETURNING` (chỉ được hỗ trợ hạn chế ở các phiên bản SQLite rất mới). Viết cú pháp PostgreSQL sẽ làm crash ứng dụng ngay lập tức.
* **Code ví dụ sai (Bad code snippet):**
  ```javascript
  // Sử dụng placeholder kiểu PostgreSQL ($1, $2) và TIMESTAMPTZ
  const query = `INSERT INTO logs (level, message, created_at) VALUES ($1, $2, CURRENT_TIMESTAMP)`;
  db.prepare(query).run('info', 'Hệ thống khởi động');
  ```
* **Code ví dụ đúng (Good code snippet):**
  ```javascript
  // Sử dụng placeholder chuẩn của SQLite (?) và kiểu TEXT/INTEGER cho thời gian
  const query = `INSERT INTO logs (level, message, created_at) VALUES (?, ?, datetime('now'))`;
  db.prepare(query).run('info', 'Hệ thống khởi động');
  ```
* **Cách dò tìm / Detection Hint:**
  Kiểm tra các chuỗi truy vấn SQL chứa ký tự placeholders của Postgres hoặc các từ khóa kiểu dữ liệu Postgres:
  ```bash
  grep -rn '\$1\|\$2\|RETURNING\|TIMESTAMPTZ\|BIGSERIAL\|ON CONFLICT DO UPDATE' src/
  ```
* **Spec Reference:** [facepost_00_shared_types.md §AD-05](file:///home/newuser/AI_facepostgroup/specs/facepost_00_shared_types.md)

---

### AP-04: `INTEGER PRIMARY KEY AUTOINCREMENT` (CRITICAL)

* **Tại sao bị cấm (Why is it banned?):**
  Trong SQLite, khi khai báo một cột là `INTEGER PRIMARY KEY AUTOINCREMENT`, SQLite bắt buộc phải tạo và cập nhật một bảng hệ thống nội bộ tên là `sqlite_sequence` để theo dõi giá trị ID lớn nhất từng được tạo. Việc này tạo ra overhead ghi đĩa không cần thiết, làm giảm hiệu năng ghi dữ liệu đi đáng kể. SQLite mặc định tự động tăng (auto-increment) cho bất kỳ cột nào khai báo là `INTEGER PRIMARY KEY` bằng cách tự lấy ID lớn nhất hiện tại cộng 1 mà không cần bảng phụ. Chỉ dùng `AUTOINCREMENT` khi có yêu cầu nghiêm ngặt cấm tái sử dụng ID cũ đã bị xóa.
* **Code ví dụ sai (Bad code snippet):**
  ```sql
  -- Bảng log ghi nhận với tần suất ghi lớn nhưng dùng AUTOINCREMENT
  CREATE TABLE system_logs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      message TEXT,
      timestamp INTEGER
  );
  ```
* **Code ví dụ đúng (Good code snippet):**
  ```sql
  -- Tối ưu hóa SQLite bằng cách bỏ AUTOINCREMENT
  CREATE TABLE system_logs (
      id INTEGER PRIMARY KEY,
      message TEXT,
      timestamp INTEGER
  );
  ```
* **Cách dò tìm / Detection Hint:**
  Tìm kiếm từ khóa `AUTOINCREMENT` trong các tệp tin SQL hoặc cấu hình Schema:
  ```bash
  grep -in 'AUTOINCREMENT' src/
  ```
* **Spec Reference:** [facepost_00_shared_types.md §AD-05](file:///home/newuser/AI_facepostgroup/specs/facepost_00_shared_types.md)

---

### AP-05: SQL TRIGGER cho Health Score (CRITICAL)

* **Tại sao bị cấm (Why is it banned?):**
  Việc cài đặt logic tính toán điểm sức khỏe (Health Score) của tài khoản Facebook bằng SQL triggers trực tiếp trong cơ sở dữ liệu làm phân mảnh logic nghiệp vụ (business logic) của hệ thống. Logic này cực kỳ khó bảo trì, khó viết unit test, và gây chậm trễ cho luồng ghi của SQLite vốn là cơ sở dữ liệu single-writer. Điểm sức khỏe phải được tính toán linh hoạt bằng mã nguồn Dashboard (Node.js) hoặc AI Brain trước khi ghi vào cơ sở dữ liệu.
* **Code ví dụ sai (Bad code snippet):**
  ```sql
  -- Viết trigger trực tiếp trong cơ sở dữ liệu
  CREATE TRIGGER update_account_health AFTER INSERT ON account_events
  BEGIN
      UPDATE accounts 
      SET health_score = health_score - 10 
      WHERE id = NEW.account_id AND NEW.event_type = 'CHECKPOINT';
  END;
  ```
* **Code ví dụ đúng (Good code snippet):**
  ```javascript
  // Thực hiện tính toán trong Service Layer của Backend Dashboard
  async function logAccountEvent(accountId, eventType) {
    await db.transaction(async (tx) => {
      // 1. Insert event log
      await tx.prepare('INSERT INTO account_events (account_id, event_type) VALUES (?, ?)')
              .run(accountId, eventType);
      
      // 2. Tính toán điểm mới trong mã nguồn ứng dụng
      if (eventType === 'CHECKPOINT') {
        const account = await tx.prepare('SELECT health_score FROM accounts WHERE id = ?').get(accountId);
        const newScore = Math.max(0, account.health_score - 10);
        
        await tx.prepare('UPDATE accounts SET health_score = ? WHERE id = ?')
                .run(newScore, accountId);
      }
    });
  }
  ```
* **Cách dò tìm / Detection Hint:**
  Tìm kiếm lệnh tạo trigger liên quan đến điểm sức khỏe:
  ```bash
  grep -rn 'CREATE TRIGGER.*health' src/
  ```
* **Spec Reference:** [facepost_03_dashboard_app.md §Section-3.1](file:///home/newuser/AI_facepostgroup/specs/facepost_03_dashboard_app.md)

---

### AP-06: `new WebSocket` trong `content.js` (CRITICAL)

* **Tại sao bị cấm (Why is it banned?):**
  Content scripts được nhúng trực tiếp và chạy trong môi trường bảo mật của trang web mục tiêu (Facebook.com). Nếu khởi tạo kết nối WebSocket trực tiếp từ content script đến Dashboard cục bộ, trình duyệt sẽ chặn kết nối ngay lập tức do vi phạm chính sách bảo mật CSP (Content Security Policy) nghiêm ngặt của Facebook. Đồng thời, việc mở socket này làm tăng nguy cơ bị Facebook quét phát hiện (anti-bot detection). Toàn bộ kết nối WebSocket phải được quản lý tập trung ở Service Worker (`background.js`) hoặc Offscreen Document, sau đó truyền dữ liệu về `content.js` bằng cơ chế gửi tin nhắn nội bộ `chrome.runtime`.
* **Code ví dụ sai (Bad code snippet):**
  ```javascript
  // content.js - Kết nối WebSocket trực tiếp từ trang Facebook
  const socket = new WebSocket('ws://localhost:3000/control');
  socket.onmessage = (event) => {
    const command = JSON.parse(event.data);
    executeCommand(command);
  };
  ```
* **Code ví dụ đúng (Good code snippet):**
  ```javascript
  // content.js - Nhận lệnh thông qua tin nhắn nội bộ của Extension
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'EXECUTE_COMMAND') {
      executeCommand(message.command);
      sendResponse({ status: 'EXECUTED' });
    }
    return true;
  });
  ```
* **Cách dò tìm / Detection Hint:**
  Tìm kiếm việc khởi tạo WebSocket trong thư mục extension, loại trừ `background.js` hoặc `offscreen.js`:
  ```bash
  grep -n 'new WebSocket' extension/content*.js
  ```
* **Spec Reference:** [facepost_01_chrome_extension.md §Section-2.2](file:///home/newuser/AI_facepostgroup/specs/facepost_01_chrome_extension.md)

---

### AP-07: Raw system prompt trên UI (CRITICAL)

* **Tại sao bị cấm (Why is it banned?):**
  System Prompt chứa các chỉ dẫn cốt lõi điều phối hành vi của AI Agent (ví dụ: cách viết bài giả dạng Gen Z, cách lách kiểm duyệt Facebook). Nếu hiển thị trực tiếp System Prompt trên giao diện người dùng (UI Dashboard) hoặc hardcode ở phía Client-side bundle, người dùng hoặc kẻ xấu có thể dễ dàng lấy cắp tài sản trí tuệ (IP) hoặc thực hiện các cuộc tấn công Prompt Injection để phá hoại AI. System prompt phải được lưu trữ bảo mật ở Dashboard Backend và chỉ gửi yêu cầu sinh nội dung qua API Endpoint bí mật.
* **Code ví dụ sai (Bad code snippet):**
  ```javascript
  // dashboard/components/PromptEditor.jsx - Lộ raw prompt trên client
  const SYSTEM_PROMPT = "Bạn là chuyên gia marketing thế hệ Z, viết bài bằng tiếng Việt...";
  
  export function PromptPanel() {
    return <textarea defaultValue={SYSTEM_PROMPT} className="w-full h-40" />;
  }
  ```
* **Code ví dụ đúng (Good code snippet):**
  ```javascript
  // dashboard/components/PromptEditor.jsx - Client chỉ gửi tham số nghiệp vụ
  export function PromptPanel() {
    const handleGenerate = async (topic) => {
      const response = await fetch('/api/posts/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic, style: 'GenZ' })
      });
      const data = await response.json();
      showGeneratedText(data.content);
    };
  }
  ```
* **Cách dò tìm / Detection Hint:**
  Tìm kiếm các khối văn bản chỉ dẫn AI dài dòng trong mã nguồn React/UI:
  ```bash
  grep -rn 'You are an AI\|Bạn là một AI' dashboard/src/
  ```
* **Spec Reference:** [facepost_02_ai_agent_brain.md §Section-1.2](file:///home/newuser/AI_facepostgroup/specs/facepost_02_ai_agent_brain.md)

---

### AP-08: `ws.onmessage` trong component con (CRITICAL)

* **Tại sao bị cấm (Why is it banned?):**
  Đăng ký sự kiện lắng nghe tin nhắn WebSocket (`ws.onmessage`) trực tiếp bên trong các React component con rất dễ gây ra hiện tượng rò rỉ bộ nhớ (memory leaks) khi component re-render hoặc unmount mà không dọn dẹp listener. Đồng thời, đăng ký trùng lặp listener sẽ làm lặp tin nhắn xử lý hoặc crash giao diện. WebSocket cần được quản lý tập trung ở một Singleton Service hoặc React Context Provider, component con chỉ lắng nghe qua state hoặc hooks.
* **Code ví dụ sai (Bad code snippet):**
  ```javascript
  // ChildComponent.jsx - Đăng ký listener trực tiếp
  export function ChildComponent() {
    useEffect(() => {
      window.globalSocket.onmessage = (e) => {
        const data = JSON.parse(e.data);
        console.log("Nhận tin nhắn:", data);
      };
    }, []); // Gây đè listener toàn cục và rò rỉ bộ nhớ
  }
  ```
* **Code ví dụ đúng (Good code snippet):**
  ```javascript
  // WebSocketProvider.jsx - Quản lý tập trung qua React Context
  const WSContext = createContext(null);

  export function WSProvider({ children }) {
    const [lastMessage, setLastMessage] = useState(null);
    useEffect(() => {
      const ws = new WebSocket(WS_URL);
      ws.onmessage = (e) => setLastMessage(JSON.parse(e.data));
      return () => ws.close();
    }, []);
    return <WSContext.Provider value={lastMessage}>{children}</WSContext.Provider>;
  }

  // Component con chỉ đọc từ Context
  export function ChildComponent() {
    const lastMsg = useContext(WSContext);
    // Xử lý dữ liệu tin nhắn...
  }
  ```
* **Cách dò tìm / Detection Hint:**
  Tìm kiếm thuộc tính `onmessage` hoặc `addEventListener` của socket trong các file React component:
  ```bash
  grep -rn 'onmessage\|addEventListener.*message' dashboard/src/
  ```
* **Spec Reference:** [facepost_07_dashboard_ui.md §Section-2.1](file:///home/newuser/AI_facepostgroup/specs/facepost_07_dashboard_ui.md)

---

### AP-09: `chrome.proxy.settings` (Approach A) (HIGH)

* **Tại sao bị cấm (Why is it banned?):**
  Sử dụng API `chrome.proxy.settings` để cấu hình Proxy trực tiếp trên Extension (Approach A) làm thay đổi proxy toàn cục của toàn bộ trình duyệt Chrome. Điều này làm lộ lưu lượng mạng của tất cả các tab khác (rò rỉ thông tin), dễ gây lỗi xác thực proxy (authentication popup) và dễ bị Facebook phát hiện do sự thiếu nhất quán trong fingerprinting. Dự án Hermes bắt buộc sử dụng **Approach B (Local Proxy Relay)**: cấu hình Extension trỏ về Local Python Host ở cổng `8086`, để Python Host tự quản lý luồng proxy sạch và ẩn danh.
* **Code ví dụ sai (Bad code snippet):**
  ```javascript
  // background.js - Set proxy trực tiếp qua API của Chrome
  chrome.proxy.settings.set({
    value: {
      mode: "fixed_servers",
      rules: { singleProxy: { scheme: "http", host: "192.168.1.100", port: 1080 } }
    },
    scope: "regular"
  });
  ```
* **Code ví dụ đúng (Good code snippet):**
  ```javascript
  // Chạy Native Python Host điều phối proxy cục bộ ở 127.0.0.1:8086
  // Extension chỉ gửi lệnh cấu hình proxy hiện tại cho Python Host qua HTTP/WS
  async function updateProxyRoute(proxyIp, proxyPort, auth) {
    await fetch('http://127.0.0.1:8086/configure_proxy', {
      method: 'POST',
      body: JSON.stringify({ ip: proxyIp, port: proxyPort, auth })
    });
  }
  ```
* **Cách dò tìm / Detection Hint:**
  Tìm kiếm từ khóa `chrome.proxy.settings` trong toàn bộ mã nguồn của extension:
  ```bash
  grep -rn 'chrome.proxy.settings' extension/
  ```
* **Spec Reference:** [facepost_04_anti_detection.md §Section-1.2](file:///home/newuser/AI_facepostgroup/specs/facepost_04_anti_detection.md)

---

### AP-10: `localStorage` trong content script (HIGH)

* **Tại sao bị cấm (Why is it banned?):**
  `localStorage` trong content script chia sẻ chung không gian lưu trữ và namespace với chính trang web đang chạy (Facebook.com). Nếu lưu trữ thông tin nhạy cảm của hệ thống như access token, API key, auth secret hoặc cấu hình lệnh tại đây, các đoạn mã thu thập dữ liệu (telemetry) của Facebook hoàn toàn có thể đọc và lấy cắp các thông tin này để khóa tài khoản hoặc phá hủy hệ thống. Phải sử dụng `chrome.storage.local` vốn được bảo mật và cách ly hoàn toàn với website.
* **Code ví dụ sai (Bad code snippet):**
  ```javascript
  // content.js - Lưu trữ auth token của dashboard vào localStorage
  localStorage.setItem('hermes_token', 'secret_token_123');
  ```
* **Code ví dụ đúng (Good code snippet):**
  ```javascript
  // content.js - Lưu trữ vào chrome storage cách ly
  chrome.storage.local.set({ 'hermes_token': 'secret_token_123' }, () => {
    console.log('Token đã được lưu an toàn');
  });
  ```
* **Cách dò tìm / Detection Hint:**
  Quét tìm từ khóa `localStorage` trong các tệp tin content script:
  ```bash
  grep -n 'localStorage' extension/content*.js
  ```
* **Spec Reference:** [facepost_01_chrome_extension.md §Section-2.3](file:///home/newuser/AI_facepostgroup/specs/facepost_01_chrome_extension.md)

---

### AP-11: String concat trong SQL query (HIGH)

* **Tại sao bị cấm (Why is it banned?):**
  Nối chuỗi trực tiếp các tham số đầu vào của người dùng hoặc các nguồn dữ liệu bên ngoài để tạo câu lệnh SQL là nguyên nhân cốt lõi gây ra lỗi bảo mật SQL Injection cực kỳ nghiêm trọng. Đối với SQLite cục bộ, việc này có thể dẫn đến việc xóa sạch dữ liệu hoặc chèn mã độc vào DB cấu hình. Luôn luôn phải sử dụng Prepared Statement với các ký tự thay thế `?` hoặc đặt tên biến.
* **Code ví dụ sai (Bad code snippet):**
  ```javascript
  // Ghép chuỗi trực tiếp tạo truy vấn nguy hiểm
  const username = getRawInput();
  const query = `SELECT * FROM accounts WHERE username = '${username}'`;
  const user = db.prepare(query).get();
  ```
* **Code ví dụ đúng (Good code snippet):**
  ```javascript
  // Sử dụng Prepared Statement an toàn
  const username = getRawInput();
  const query = `SELECT * FROM accounts WHERE username = ?`;
  const user = db.prepare(query).get(username);
  ```
* **Cách dò tìm / Detection Hint:**
  Kiểm tra các lệnh `prepare` hoặc thực thi SQL có chứa phép cộng chuỗi hoặc biến template literals:
  ```bash
  grep -rn 'prepare(.*+.*)\|prepare(.*`.*${.*}.*`)' src/
  ```
* **Spec Reference:** [facepost_00_shared_types.md §Section-5](file:///home/newuser/AI_facepostgroup/specs/facepost_00_shared_types.md)

---

### AP-12: LLM output không qua `HumanessHarness` (HIGH)

* **Tại sao bị cấm (Why is it banned?):**
  Các bài viết do AI (LLM) tự động tạo ra thường mang đặc điểm hành văn rất đặc trưng như: sử dụng danh sách liệt kê, câu từ quá trang trọng, mở đầu và kết bài mang tính rập khuôn, hoặc dùng các từ ngữ sáo rỗng. Nếu đăng trực tiếp các nội dung này lên Facebook, thuật toán kiểm duyệt nội dung của Facebook sẽ nhận diện ngay lập tức đây là tài khoản spam/bot tự động và khóa tài khoản (checkpoint). Tất cả nội dung sinh ra phải được chạy qua `HumanessHarness` để đánh giá tính tự nhiên, độ đa dạng độ dài câu, từ lóng và viết lại nếu không đạt điểm chuẩn.
* **Code ví dụ sai (Bad code snippet):**
  ```javascript
  // Lấy thẳng nội dung AI trả về để điền vào form đăng bài
  const generatedText = await llm.generateText(prompt);
  await page.type('div[contenteditable="true"]', generatedText);
  ```
* **Code ví dụ đúng (Good code snippet):**
  ```javascript
  // Chạy qua bộ kiểm tra Humanness trước khi đăng
  const generatedText = await llm.generateText(prompt);
  const auditResult = HumannessHarness.verify(generatedText);
  
  if (auditResult.scorePercent < 80) {
    // Yêu cầu LLM viết lại kèm gợi ý chỉnh sửa lỗi hành văn AI
    const refinedText = await llm.regenerateText(generatedText, auditResult.warnings);
    await page.type('div[contenteditable="true"]', refinedText);
  } else {
    await page.type('div[contenteditable="true"]', generatedText);
  }
  ```
* **Cách dò tìm / Detection Hint:**
  Kiểm tra các nơi gọi API sinh nội dung bài đăng mà thiếu hàm `verify` hoặc gọi tới `HumanessHarness`:
  ```bash
  grep -rn 'generate.*Text' src/ | grep -v 'HumanessHarness'
  ```
* **Spec Reference:** [facepost_08_content_engine.md §Section-4.1](file:///home/newuser/AI_facepostgroup/specs/facepost_08_content_engine.md)

---

### AP-17: CẤM điều hướng trực tiếp bằng URL (Direct Navigation) liên tục đối với các tài khoản mới hoặc tài khoản có độ Trust thấp (HIGH)

* **Tại sao bị cấm (Why is it banned?):**
  Việc liên tục nhảy thẳng tới các URL cụ thể (như link trực tiếp của Facebook Groups) bằng các câu lệnh điều hướng trực tiếp (`NAVIGATE` hoặc `chrome.tabs.update`) tạo ra một vết signature bot cực kỳ rõ ràng đối với hệ thống giám sát của Facebook. Người dùng thực tế luôn có các hành vi chuyển tiếp tự nhiên (như tìm kiếm tên group trên thanh Search, click vào kết quả, hoặc đi qua Newsfeed). Đối với các tài khoản mới lập hoặc tài khoản có độ tin cậy (Trust) thấp, hành vi điều hướng trực tiếp lặp đi lặp lại sẽ lập tức kích hoạt hệ thống phát hiện bot và dẫn đến checkpoint hoặc khóa tài khoản nhanh chóng.
* **Code ví dụ sai (Bad code snippet):**
  ```javascript
  // Thực hiện điều hướng trực tiếp liên tục tới các link Group
  const groups = [
    "https://www.facebook.com/groups/group1",
    "https://www.facebook.com/groups/group2",
    "https://www.facebook.com/groups/group3"
  ];

  for (const url of groups) {
    // Gọi trực tiếp API điều hướng của extension hoặc công cụ tự động hóa
    await chrome.tabs.update(tabId, { url: url });
    await delay(5000);
    await postToGroup();
  }
  ```
* **Code ví dụ đúng (Good code snippet):**
  ```javascript
  // Mô phỏng hành vi tự nhiên bằng cách tìm kiếm và click (Search-and-Click)
  async function navigateToGroupViaSearch(groupName, groupId) {
    // 1. Đi tới trang chủ hoặc trang tìm kiếm chung
    await chrome.tabs.update(tabId, { url: "https://www.facebook.com/search/groups/?q=" + encodeURIComponent(groupName) });
    await waitForElement('input[type="search"]');
    
    // 2. Mô phỏng cuộn trang và tìm element chứa link Group có ID khớp
    const groupLinkSelector = `a[href*="/groups/${groupId}/"]`;
    await waitForElement(groupLinkSelector);
    
    // 3. Thực hiện click tự nhiên vào link nhóm từ kết quả tìm kiếm
    const groupLinkElement = document.querySelector(groupLinkSelector);
    groupLinkElement.scrollIntoView({ behavior: 'smooth' });
    await delayRandom(1000, 3000);
    groupLinkElement.click();
  }
  ```
* **Cách dò tìm / Detection Hint:**
  Dò tìm xem code có liên tục gọi lệnh `NAVIGATE` hoặc `chrome.tabs.update` trực tiếp tới URL của Facebook Groups mà không thông qua luồng Search-and-Click hay không:
  ```bash
  grep -rn 'chrome.tabs.update\|NAVIGATE' extension/src/
  ```
* **Spec Reference:** [facepost_04_anti_detection.md](file:///home/newuser/AI_facepostgroup/specs/facepost_04_anti_detection.md), [facepost_05_agent_loop.md](file:///home/newuser/AI_facepostgroup/specs/facepost_05_agent_loop.md)

---

### CE-UI-01: Rò rỉ thông tin đăng nhập DB / Network Credentials trên Frontend (CRITICAL)

* **Tại sao bị cấm (Why is it banned?):**
  Nhúng trực tiếp thông tin xác thực (credentials) như chuỗi kết nối cơ sở dữ liệu (PostgreSQL/SQLite path), API keys, JWT secrets, hoặc admin passwords trên mã nguồn giao diện (Frontend React/Vite) làm lộ các thông tin này ra client-side build bundle. Bất kỳ ai truy cập Dashboard UI đều có thể inspect code và đánh cắp thông tin xác thực để trực tiếp thao túng DB hoặc gọi API phá hoại hệ thống.
* **Code ví dụ sai (Incorrect code snippet):**
  ```javascript
  // dashboard/src/services/api.js
  // Khai báo trực tiếp API key hoặc kết nối DB ở frontend
  const API_KEY = "hermes_secret_jwt_token_987654321";
  const DB_CONNECTION_STRING = "postgresql://postgres:mysecretpassword@127.0.0.1:5432/hermes";

  export async function fetchStats() {
    return fetch(`${DB_CONNECTION_STRING}/stats`, {
      headers: { 'Authorization': `Bearer ${API_KEY}` }
    }).then(res => res.json());
  }
  ```
* **Code ví dụ đúng (Correct code snippet):**
  ```javascript
  // dashboard/src/services/api.js
  // Gọi qua API Gateway/Backend Proxy an toàn
  export async function fetchStats() {
    // API endpoint của Dashboard Backend (đứng sau reverse proxy có auth session)
    return fetch('/api/dashboard/stats')
      .then(res => {
        if (!res.ok) throw new Error("Unauthorized");
        return res.json();
      });
  }
  ```
* **Cách dò tìm / Detection Hint:**
  Kiểm tra mã nguồn UI xem có chứa các biến cứng API_KEY, DB_CONNECTION_STRING hoặc các chuỗi nhạy cảm:
  ```bash
  grep -rn 'postgresql:\/\/\|mongodb:\/\/\|API_KEY\s*=\s*["\']' dashboard/src/
  ```
* **Spec Reference:** [facepost_07_dashboard_ui.md §Section-4.2](file:///home/newuser/AI_facepostgroup/specs/facepost_07_dashboard_ui.md)

---

### CE-UI-02: Rò rỉ dữ liệu qua Log Console ở môi trường Production (HIGH)

* **Tại sao bị cấm (Why is it banned?):**
  Việc ghi nhật ký (logging) các thông tin nhạy cảm của người dùng (như Cookie tài khoản Facebook, Token, dữ liệu bài đăng chưa kiểm duyệt) ra trình duyệt Client (Developer Console) trên môi trường production làm lộ dữ liệu cho bên thứ ba (qua các extension độc hại hoặc truy cập vật lý). Dashboard UI bắt buộc phải loại bỏ hoặc filter toàn bộ console.log nhạy cảm trước khi deploy.
* **Code ví dụ sai (Incorrect code snippet):**
  ```javascript
  // dashboard/src/components/AccountManager.jsx
  function handleAccountSelect(account) {
    // Log thẳng cookie hoặc token của tài khoản Facebook ra console
    console.log("Selected account cookie:", account.cookie);
    console.debug("Full network auth payload:", account.networkPayload);
    setSelected(account);
  }
  ```
* **Code ví dụ đúng (Correct code snippet):**
  ```javascript
  // dashboard/src/components/AccountManager.jsx
  import { logger } from '../utils/logger';

  function handleAccountSelect(account) {
    // Sử dụng logger wrapper tự động ẩn thông tin nhạy cảm và tắt log ở production
    logger.info("Selected account ID: " + account.id);
    setSelected(account);
  }
  ```
* **Cách dò tìm / Detection Hint:**
  Kiểm tra xem có sử dụng `console.log` hoặc `console.debug` in trực tiếp các object nhạy cảm:
  ```bash
  grep -rn 'console\.log(.*cookie\|.*token\|.*payload)' dashboard/src/
  ```
* **Spec Reference:** [facepost_07_dashboard_ui.md §Section-4.3](file:///home/newuser/AI_facepostgroup/specs/facepost_07_dashboard_ui.md)

---

### CE-UI-03: Rò rỉ kết nối mạng do không giải phóng Listener/Subscription (HIGH)

* **Tại sao bị cấm (Why is it banned?):**
  Trong UI Content Engine, khi kết nối tới luồng stream (EventSource/Server-Sent Events) hoặc WebSocket để theo dõi tiến độ sinh bài viết, nếu không giải phóng (cleanup) kết nối này khi component unmount, kết nối mạng sẽ vẫn tiếp tục duy trì ngầm. Điều này gây rò rỉ cổng kết nối, quá tải RAM trên client và tràn socket descriptor trên backend khi người dùng điều hướng qua lại giữa các trang.
* **Code ví dụ sai (Incorrect code snippet):**
  ```javascript
  // dashboard/src/components/ContentGenerator.jsx
  export function ContentGenerator() {
    useEffect(() => {
      // Đăng ký luồng stream nhưng không dọn dẹp khi unmount
      const eventSource = new EventSource('/api/content/stream');
      eventSource.onmessage = (event) => {
        updateGenerationProgress(JSON.parse(event.data));
      };
    }, []); 
  }
  ```
* **Code ví dụ đúng (Correct code snippet):**
  ```javascript
  // dashboard/src/components/ContentGenerator.jsx
  export function ContentGenerator() {
    useEffect(() => {
      const eventSource = new EventSource('/api/content/stream');
      eventSource.onmessage = (event) => {
        updateGenerationProgress(JSON.parse(event.data));
      };

      // Trả về hàm dọn dẹp (cleanup function) bắt buộc để đóng kết nối
      return () => {
        eventSource.close();
      };
    }, []); 
  }
  ```
* **Cách dò tìm / Detection Hint:**
  Tìm các useEffect chứa EventSource, WebSocket, hoặc setInterval mà thiếu khối return dọn dẹp:
  ```bash
  grep -rn 'new EventSource\|new WebSocket' dashboard/src/
  ```
* **Spec Reference:** [facepost_07_dashboard_ui.md §Section-2.3](file:///home/newuser/AI_facepostgroup/specs/facepost_07_dashboard_ui.md)

---

### CE-UI-04: Đọc ghi DB trực tiếp từ UI components (CRITICAL)

* **Tại sao bị cấm (Why is it banned?):**
  Mã nguồn chạy trên Browser không thể và không được phép giao tiếp trực tiếp với cơ sở dữ liệu (SQLite, Postgres). Việc import trực tiếp các module DB client (như `better-sqlite3`, `pg`, `sequelize`) vào React components sẽ làm lộ hoàn toàn schema, thông tin kết nối và làm lỗi quá trình build frontend (do các thư viện Node native c++ bindings không tương thích với môi trường Browser). Toàn bộ thao tác đọc/ghi dữ liệu từ UI phải đi qua REST API / GraphQL API của Dashboard Backend.
* **Code ví dụ sai (Incorrect code snippet):**
  ```javascript
  // dashboard/src/components/Stats.jsx
  // Import trực tiếp DB connection của backend vào React Component
  import db from '../../../backend/database/sqlite_connection';

  export function StatsPanel() {
    // Thực thi câu lệnh SQL trực tiếp trên frontend
    const totalPosts = db.prepare('SELECT COUNT(*) as count FROM posts').get().count;
    return <div>Total Posts: {totalPosts}</div>;
  }
  ```
* **Code ví dụ đúng (Correct code snippet):**
  ```javascript
  // dashboard/src/components/Stats.jsx
  import { useEffect, useState } from 'react';

  export function StatsPanel() {
    const [totalPosts, setTotalPosts] = useState(0);
    
    useEffect(() => {
      // Đọc dữ liệu thông qua API endpoint bảo mật
      fetch('/api/stats/posts-count')
        .then(res => res.json())
        .then(data => setTotalPosts(data.count));
    }, []);

    return <div>Total Posts: {totalPosts}</div>;
  }
  ```
* **Cách dò tìm / Detection Hint:**
  Kiểm tra việc import các module backend hoặc database trực tiếp vào các component UI:
  ```bash
  grep -rn 'import.*from.*\/backend\/database' dashboard/src/
  ```
* **Spec Reference:** [facepost_07_dashboard_ui.md §Section-3.3](file:///home/newuser/AI_facepostgroup/specs/facepost_07_dashboard_ui.md)

---

### AP-18: Unsanitized Dynamic RegEx Creation (CRITICAL)

* **Tại sao bị cấm (Why is it banned?):**
  Khởi tạo biểu thức chính quy động (`new RegExp(variable)`) trực tiếp từ dữ liệu lóng hoặc input do người dùng nhập vào mà không chạy qua hàm escape/sanitize sẽ mở ra lỗ hổng bảo mật nghiêm trọng. Trình duyệt hoặc Backend Node.js có thể bị treo cứng hoàn toàn Event Loop do hiện tượng Catastrophic Backtracking (RegEx DoS / ReDoS) khi gặp các chuỗi input được thiết kế độc hại.
* **Code ví dụ sai (Bad code snippet):**
  ```javascript
  const userInput = getRawInput(); // Gây lỗi ReDoS treo CPU nếu nhập "((a+)+)+"
  const regex = new RegExp(userInput);
  const isMatch = regex.test(messageContent);
  ```
* **Code ví dụ đúng (Good code snippet):**
  ```javascript
  // Sử dụng hàm escape RegExp chuẩn trước khi khởi tạo
  function escapeRegExp(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }
  const userInput = getRawInput();
  const regex = new RegExp(escapeRegExp(userInput));
  const isMatch = regex.test(messageContent);
  ```
* **Cách dò tìm / Detection Hint (AST):**
  AST Selector check node `NewExpression` có `callee.name === 'RegExp'` và đối số đầu tiên không phải là một chuỗi literal tĩnh.
* **Spec Reference:** [facepost_08_content_engine.md](file:///home/newuser/AI_facepostgroup/specs/facepost_08_content_engine.md)

---

### AP-19: Direct WebContents Leak in Electron (CRITICAL)

* **Tại sao bị cấm (Why is it banned?):**
  Trong ứng dụng Electron Desktop, việc chuyển tiếp trực tiếp đối tượng `event` thô của IPC hoặc lộ trực tiếp đối tượng `WebContents` từ Preload Script sang Renderer process sẽ triệt tiêu ranh giới an toàn của IPC. Kẻ tấn công nếu hack được giao diện (Renderer) có thể lợi dụng đối tượng rò rỉ này để thực thi mã độc từ xa (RCE) trên hệ điều hành của người dùng.
* **Code ví dụ sai (Bad code snippet):**
  ```javascript
  // preload.js - Rò rỉ đối tượng send thô
  contextBridge.exposeInMainWorld('electronAPI', {
    sendRaw: (channel, data) => ipcRenderer.send(channel, data) // Cho phép renderer gửi kênh bất kỳ
  });
  ```
* **Code ví dụ đúng (Good code snippet):**
  ```javascript
  // preload.js - Chỉ expose các hàm nghiệp vụ cụ thể và an toàn
  contextBridge.exposeInMainWorld('electronAPI', {
    toggleStatus: (status) => ipcRenderer.send('toggle-status', status)
  });
  ```
* **Cách dò tìm / Detection Hint (AST):**
  AST Selector phát hiện trong `preload.js` có expose hàm cho phép gọi `ipcRenderer.send` hoặc `ipcRenderer.invoke` với đối số kênh (channel) là một biến động thay vì chuỗi tĩnh.
* **Spec Reference:** [facepost_10_desktop_packaging.md](file:///home/newuser/AI_facepostgroup/specs/facepost_10_desktop_packaging.md)

---

### AP-20: Raw DB Imports on UI (CRITICAL)

* **Tại sao bị cấm (Why is it banned?):**
  Import trực tiếp các module database (`better-sqlite3`, `pg`, `sequelize`) trong các file frontend React (`.jsx` / `.tsx`) sẽ làm lộ hoàn toàn schema, thông tin kết nối và làm lỗi quá trình đóng gói tài nguyên UI (vì các thư viện native c++ bindings không tương thích với browser). Toàn bộ thao tác đọc/ghi dữ liệu từ UI phải đi qua REST API của Dashboard Backend.
* **Code ví dụ sai (Bad code snippet):**
  ```javascript
  // Stats.jsx
  import db from '../../../backend/database/sqlite_connection'; // CRITICAL VIOLATION
  export function StatsPanel() {
    const total = db.prepare('SELECT COUNT(*) as count FROM posts').get().count;
    return <div>Total: {total}</div>;
  }
  ```
* **Code ví dụ đúng (Good code snippet):**
  ```javascript
  // Stats.jsx
  import { useEffect, useState } from 'react';
  export function StatsPanel() {
    const [total, setTotal] = useState(0);
    useEffect(() => {
      fetch('/api/stats/posts-count')
        .then(res => res.json())
        .then(data => setTotal(data.count));
    }, []);
    return <div>Total: {total}</div>;
  }
  ```
* **Cách dò tìm / Detection Hint (AST):**
  AST Selector phát hiện câu lệnh `ImportDeclaration` chứa `source.value` khớp với các thư viện database như `better-sqlite3`, `pg`, `sequelize` hoặc liên kết trực tiếp tới file kết nối database backend trong thư mục frontend.
* **Spec Reference:** [facepost_07_dashboard_ui.md](file:///home/newuser/AI_facepostgroup/specs/facepost_07_dashboard_ui.md)

---

### AP-21: WebRTC IP Leakage Exposure (HIGH)

* **Tại sao bị cấm (Why is it banned?):**
  Mặc định, trình duyệt Chrome cho phép các kết nối WebRTC truy vấn địa chỉ IP cục bộ (local LAN IP) và IP mạng thật của card mạng thông qua các giao thức STUN/TURN, bỏ qua mọi cấu hình proxy của extension. Facebook sử dụng kỹ thuật này để quét địa chỉ IP thật đằng sau proxy của bot. Nếu thiếu cấu hình tắt UDP non-proxied cho WebRTC trong launch options của Chrome, hệ thống sẽ bị rò rỉ IP thật và tài khoản bị gắn cờ spam.
* **Code ví dụ sai (Bad code snippet):**
  ```javascript
  // chrome_launcher.js - Khởi chạy Chrome thô không cấu hình WebRTC
  const browser = await puppeteer.launch({
    args: ['--proxy-server=http://127.0.0.1:8086']
  });
  ```
* **Code ví dụ đúng (Good code snippet):**
  ```javascript
  // chrome_launcher.js - Thêm cờ ép WebRTC đi qua proxy
  const browser = await puppeteer.launch({
    args: [
      '--proxy-server=http://127.0.0.1:8086',
      '--force-webrtc-ip-handling-policy=disable_non_proxied_udp'
    ]
  });
  ```
* **Cách dò tìm / Detection Hint (AST):**
  AST Selector tìm kiếm các lệnh khởi chạy Puppeteer/Selenium (`puppeteer.launch` hoặc `new Builder()`), xác thực xem trong mảng `args` hoặc `options` có chứa chuỗi `--force-webrtc-ip-handling-policy=disable_non_proxied_udp` hay không.
* **Spec Reference:** [facepost_04_anti_detection.md](file:///home/newuser/AI_facepostgroup/specs/facepost_04_anti_detection.md)

---

### AP-22: SOCKS5 DNS Leakage (HIGH)

* **Tại sao bị cấm (Why is it banned?):**
  Sử dụng tiền tố proxy SOCKS5 ở dạng tĩnh `socks5://` sẽ làm rò rỉ luồng phân giải DNS (DNS Leak). Lúc này, trình duyệt sẽ tự phân giải địa chỉ tên miền bằng máy chủ DNS của mạng Internet cục bộ (local ISP), sau đó mới đẩy lưu lượng TCP qua proxy SOCKS5. Facebook sẽ đối chiếu quốc gia của DNS server với quốc gia của IP Proxy, nếu lệch nhau (ví dụ: DNS ở Việt Nam nhưng IP Proxy ở Mỹ), tài khoản sẽ bị khóa ngay lập tức. Bắt buộc phải chuyển hóa thành `socks5h://` để ép toàn bộ luồng phân giải DNS sang đầu xa của Proxy.
* **Code ví dụ sai (Bad code snippet):**
  ```javascript
  // Cấu hình proxy rò rỉ DNS
  const proxyUrl = "socks5://proxyuser:proxypass@192.168.1.100:1080";
  ```
* **Code ví dụ đúng (Good code snippet):**
  ```javascript
  // Sử dụng socks5h:// để phân giải DNS tại đầu xa của proxy
  const proxyUrl = "socks5h://proxyuser:proxypass@192.168.1.100:1080";
  ```
* **Cách dò tìm / Detection Hint (AST):**
  AST Selector kiểm tra các chuỗi cấu hình mạng hoặc proxy URL xem có chứa tiền tố `socks5://` thay vì `socks5h://`.
* **Spec Reference:** [facepost_04_anti_detection.md](file:///home/newuser/AI_facepostgroup/specs/facepost_04_anti_detection.md)

---

### AP-23: Static Signature for WebSocket Hello (HIGH)

* **Tại sao bị cấm (Why is it banned?):**
  Gửi gói tin bắt tay chào mừng (`HELLO`/`HANDSHAKE`) của WebSocket từ Extension lên Dashboard bằng một cấu trúc JSON tĩnh không đổi qua các phiên tạo ra vết signature mạng rất dễ nhận diện. Kẻ tấn công hoặc WAF Facebook có thể dễ dàng chặn đứng kết nối bằng cách so khớp cấu trúc byte của JSON. Bắt buộc phải inject `nonce` ngẫu nhiên, `timestamp` động và sắp xếp ngẫu nhiên thứ tự các key trong JSON payload.
* **Code ví dụ sai (Bad code snippet):**
  ```javascript
  // background.js - Gửi tin nhắn tĩnh rập khuôn
  const helloPayload = {
    type: "HELLO",
    version: "2.0.0",
    client_id: "hermes_ext_client"
  };
  ws.send(JSON.stringify(helloPayload));
  ```
* **Code ví dụ đúng (Good code snippet):**
  ```javascript
  // background.js - Thêm salt động và ngẫu nhiên hóa
  const helloPayload = {
    type: "HELLO",
    version: "2.0.0",
    client_id: "hermes_ext_client",
    timestamp: Date.now(),
    nonce: Math.random().toString(36).substring(7)
  };
  ws.send(JSON.stringify(helloPayload));
  ```
* **Cách dò tìm / Detection Hint (AST):**
  AST Selector kiểm tra các câu lệnh gửi tin nhắn WebSocket chào mừng xem payload có chứa các biến thời gian hoặc nonce động hay không.
* **Spec Reference:** [facepost_00_shared_types.md](file:///home/newuser/AI_facepostgroup/specs/facepost_00_shared_types.md)

---

### AP-24: Non-Stealthy Object Protocol Override (HIGH)

* **Tại sao bị cấm (Why is it banned?):**
  Ghi đè trực tiếp các thuộc tính tự động hóa của trình duyệt (như `navigator.webdriver = false`) bằng phép gán trần sẽ làm lệch chuỗi prototype chain. Các script bảo mật WAF cấp cao của Facebook sẽ kiểm tra hàm `navigator.webdriver.toString()` hoặc kiểm tra thuộc tính getter. Nếu phát hiện bị ghi đè thô sơ, nó sẽ phát hiện ra bot ngay. Bắt buộc phải sử dụng các cờ native từ Chrome Launch options (`--disable-blink-features=AutomationControlled`).
* **Code ví dụ sai (Bad code snippet):**
  ```javascript
  // content.js - Ghi đè thô sơ bị phát hiện ngay lập tức
  Object.defineProperty(navigator, 'webdriver', {
    get: () => false
  });
  ```
* **Code ví dụ đúng (Good code snippet):**
  ```javascript
  // chrome_launcher.js - Sử dụng cấu hình native khởi chạy
  const browser = await puppeteer.launch({
    args: ['--disable-blink-features=AutomationControlled']
  });
  ```
* **Cách dò tìm / Detection Hint (AST):**
  AST Selector check trong content script xem có chứa việc gán đè thuộc tính `navigator.webdriver` hoặc `navigator.languages`.
* **Spec Reference:** [facepost_04_anti_detection.md](file:///home/newuser/AI_facepostgroup/specs/facepost_04_anti_detection.md)

---

### AP-25: Rò rỉ khóa bí mật và thiếu tệp `.gitignore` (CRITICAL)

* **Tại sao bị cấm (Why is it banned?):**
  Lưu trữ thông tin xác thực nhạy cảm (như Facebook API keys, App Secrets, DB connection string, proxy password) trực tiếp trong file `.env` và vô tình commit file này lên Git repository công khai/nội bộ hoặc thiếu tệp `.gitignore` chuẩn sẽ dẫn đến nguy cơ rò rỉ thông tin nghiêm trọng. Kẻ xấu có thể quét (scan) mã nguồn trên Git để lấy cắp tài nguyên, tài khoản Facebook, hoặc tấn công trực tiếp vào cơ sở dữ liệu của hệ thống Dashboard. Do đó, `.env` chứa credentials thật tuyệt đối không được đưa lên Git control.
* **Code ví dụ sai (Bad code snippet):**
  Mã nguồn commit trực tiếp file `.env` chứa credentials thật:
  ```env
  # .env - Chứa API keys thật và bị track bởi Git
  DATABASE_URL="postgresql://postgres:my-secret-password@localhost:5432/facepost"
  FACEBOOK_APP_SECRET="9abc7816ef871b6238b1d98a2"
  DEEPSEEK_API_KEY="sk-abcd1234efgh5678"
  ```
  Hoặc trong source code hardcode key:
  ```javascript
  const apiKey = "sk-abcd1234efgh5678"; // Hardcoded secret
  ```
* **Code ví dụ đúng (Good code snippet):**
  1. Chỉ commit `.env.example` chứa các biến rỗng:
  ```env
  # .env.example - Mẫu cấu hình không chứa giá trị thật
  DATABASE_URL=""
  FACEBOOK_APP_SECRET=""
  DEEPSEEK_API_KEY=""
  ```
  2. Cấu hình `.gitignore` đầy đủ tại thư mục gốc của dự án:
  ```git
  # .gitignore
  .env
  .env.local
  .env.development.local
  .env.test.local
  .env.production.local
  *.pem
  *.key
  node_modules/
  dist/
  build/
  *.log
  logs/
  data/*.db
  data/*.db-*
  ChromeTestProfile/
  tmp/
  .opus/
  ```
  3. Load cấu hình qua process.env thay vì hardcode:
  ```javascript
  const apiKey = process.env.DEEPSEEK_API_KEY;
  ```
* **Cách dò tìm / Detection Hint:**
  Kiểm tra danh sách tệp tin đang trong staging area của Git trước khi commit để chặn đứng file `.env` thật hoặc các file chứa thông tin nhạy cảm:
  ```bash
  # Tìm các file cấu hình env bị commit nhầm
  git diff --cached --name-only | grep '.env'

  # Quét mã nguồn tìm các khóa API bị hardcode
  grep -rn 'sk-\|password=\|secret=' src/
  ```
* **Spec Reference:** [facepost_rules_of_project.md §Section-6](file:///home/newuser/AI_facepostgroup/facepost_rules_of_project.md)

---

## 💡 Các Anti-Patterns Mức Độ Trung Bình & Thấp (AP-13 đến AP-16)

### AP-13: WS reconnect không có exponential backoff (MEDIUM)
* **Mô tả:** Khi kết nối WebSocket bị đứt, nếu thiết lập kết nối lại với khoảng thời gian cố định ngắn (ví dụ mỗi 1 giây) sẽ gây nghẽn mạng và quá tải Dashboard backend (reconnection storm).
* **Code đúng:** Sử dụng exponential backoff (nhân đôi delay sau mỗi lần thử) cộng thêm khoảng thời gian ngẫu nhiên (jitter).
* **Spec Ref:** [facepost_01_chrome_extension.md](file:///home/newuser/AI_facepostgroup/specs/facepost_01_chrome_extension.md)

### AP-14: AI reply box không giới hạn chiều cao (MEDIUM)
* **Mô tả:** Hộp thoại hiển thị câu trả lời hoặc log của AI trên Dashboard UI nếu không giới hạn chiều cao sẽ đẩy các thành phần UI khác xuống dưới khi nội dung quá dài, làm vỡ bố cục giao diện.
* **Code đúng:** Thêm thuộc tính CSS `max-height` (ví dụ `max-h-96`) kèm theo `overflow-y-auto` cho khung hiển thị.
* **Spec Ref:** [facepost_07_dashboard_ui.md](file:///home/newuser/AI_facepostgroup/specs/facepost_07_dashboard_ui.md)

### AP-15: CSS selector hardcode của Facebook (LOW)
* **Mô tả:** Facebook mã hóa tên class (obfuscated class) động và thay đổi liên tục. Hardcode class như `.x1n2onr6` sẽ làm hỏng chức năng tự động hóa khi Facebook cập nhật phiên bản mới.
* **Code đúng:** Ưu tiên sử dụng các thuộc tính tĩnh không đổi như `data-testid`, `aria-label` hoặc cấu trúc DOM cha con tương đối.
* **Spec Ref:** [facepost_06_checkpoint_handler.md](file:///home/newuser/AI_facepostgroup/specs/facepost_06_checkpoint_handler.md)

### AP-16: Fetch keywords trong render loop (LOW)
* **Mô tả:** Gọi trực tiếp hàm fetch keywords của AI Engine bên trong luồng render (render loop) của React component sẽ kích hoạt vòng lặp gọi API vô hạn, làm tràn bộ nhớ và treo trình duyệt.
* **Code đúng:** Bọc lời gọi API vào trong hook `useEffect` với mảng phụ thuộc (dependency array) trống hoặc có biến điều khiển hợp lý.
* **Spec Ref:** [facepost_08_content_engine.md](file:///home/newuser/AI_facepostgroup/specs/facepost_08_content_engine.md)

---

*Anti-Pattern Registry — Hermes FacePost-Group Agent Harness v1.0.0*
