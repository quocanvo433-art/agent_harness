# 🔍 BÁO CÁO PHÂN TÍCH KHUYẾT ĐIỂM CỦA AGENT HARNESS (ARCHITECTURAL DEFICIENCIES)

> **Mục tiêu:** Giải thích lý do vì sao `agent_harness` (môi trường kiểm thử QA tự động) báo PASS các cổng kiểm duyệt (QA Gates) nhưng sản phẩm thực tế lại gặp hàng loạt lỗi giao tiếp (Handshake), vòng đời kết nối và các tính năng "bình hoa di động".
> **Ngày thực hiện:** 2026-06-28
> **Người thực hiện:** Lead Architect Agent & Antigravity AI Coding Assistant

---

## 🛑 TỔNG QUAN: VÌ SAO HARNESS BỊ "QUA MẶT"?

Qua rà soát chi tiết luồng chạy của `agent_harness/local_e2e_runner.js` và các checklist trong `qa_agent.md`, nguyên nhân cốt lõi khiến Backend và Extension đầy lỗi nhưng vẫn vượt qua khâu kiểm thử tự động là do **Harness kiểm thử bằng các đối tượng giả lập (Mocking) quá mức, bỏ qua việc tích hợp môi trường thực tế (Real-world Integration)**. 

Dưới đây là **6 khuyết điểm chí mạng** của `agent_harness`:

---

### 1. Trình chạy E2E bỏ qua Trình duyệt Chrome và Extension thực tế (Mock Connection Bypass)
*   **Mô tả khuyết điểm:** 
    Trong file `local_e2e_runner.js`, để kiểm tra kết nối WebSocket và bắt tay (Handshake), bộ chạy E2E **không hề khởi chạy Google Chrome thực tế để nạp Extension**, mà thay vào đó tự viết một script Node.js client giả lập (`const WebSocket = require('ws')`) để kết nối trực tiếp đến server.
*   **Hậu quả:** 
    *   **Bỏ sót lỗi tải Extension:** Do không chạy Chrome thật để test kết nối, Harness hoàn toàn không phát hiện ra việc Chrome chặn load extension chưa đóng gói từ thư mục `Temp` (lỗi EPERM/Silent Block).
    *   **Bỏ sót lỗi code môi trường Browser:** Client test viết bằng Node.js có sẵn thư viện `crypto` và môi trường hoàn chỉnh, chạy thẳng tắp. Nó không hề chạy qua file `offscreen.js` và `background.js` thực tế vốn bị lỗi đứt gãy do `chrome.storage.local` rỗng (`accountId` trống) và lỗi tự hủy của Offscreen Document.
    *   **Kết quả:** Test runner báo `WELCOME` thành công (PASS), trong khi trên máy người dùng, Extension nằm im 100% (Offline).

---

### 2. Sự "Ưu Ái" Môi Trường trong Test Runner (Dynamic Port Mocking)
*   **Mô tả khuyết điểm:** 
    Bộ chạy E2E tự động đọc cổng kết nối thực tế từ file `active_port.json` do backend tạo ra rồi truyền trực tiếp cho client giả lập để connect.
*   **Hậu quả:** 
    Nó không phát hiện ra lỗi rằng trong file `offscreen.js` chạy thực tế trên Chrome, **cổng kết nối WebSocket đang bị hardcode cứng là 8765** (`ws://127.0.0.1:8765/ws`). Khi Backend chạy trên cổng động khác (ví dụ: do 8765 bị bận), client giả lập vẫn chạy được (vì đọc từ file JSON), nhưng Extension thật thì kết nối thất bại hoàn toàn.

---

### 3. Thiếu khâu Kiểm tra Trạng thái Sống (Target Verification) của Extension
*   **Mô tả khuyết điểm:** 
    Harness sử dụng Puppeteer để kết nối với Electron GUI (cổng 9223) và kiểm tra click các Tab trên UI, nhưng không sử dụng Puppeteer để kết nối với Chrome test (cổng 9222) nhằm quét danh sách các Target (`browser.targets()`).
*   **Hậu quả:** 
    Nếu Harness quét danh sách Target trên Chrome, nó sẽ lập tức phát hiện ra lỗi `Service worker target not found` hoặc `Offscreen document target not found`. Việc thiếu kiểm định sự hiện diện của các tiến trình nền của Extension khiến ứng dụng bị coi là hoạt động bình thường dù nhân xử lý đã chết.

---

### 4. Bỏ qua Schema Validation ở Runtime (Lệch pha Đặc tả vs Code)
*   **Mô tả khuyết điểm:** 
    Mặc dù `specs/schemas/` định nghĩa rất nhiều cấu trúc tin nhắn chặt chẽ (như `hello.schema.json`), Backend thực tế (`wsServer.js`) lại không hề nhúng bộ kiểm định Ajv để kiểm tra cấu trúc tin nhắn nhận được từ client.
*   **Hậu quả:** 
    Các Coding Agent tự do viết code truyền nhận dữ liệu phẳng hoàn toàn, bỏ qua cấu trúc phức tạp trong schema. Vì test runner cũng gửi tin nhắn phẳng để khớp với code Backend, hệ thống báo PASS, nhưng để lại sự lệch pha nghiêm trọng giữa tài liệu thiết kế (Constitution/Spec) và mã nguồn thực tế.

---

### 5. Chấp nhận "Trạng thái Logic" thay vì "Kết quả Thao tác DOM thật"
*   **Mô tả khuyết điểm:** 
    Trong các QA Gate dành cho FSM loop (Tuần 4 - QA-04), bộ test chỉ kiểm tra xem FSM có chuyển dịch qua lại giữa các trạng thái `Home -> Search -> Click -> Post` hay không bằng cách giả lập kết quả trả về của các hàm.
*   **Hậu quả:** 
    Nó không xác minh xem các hàm click, điền text có thực sự tương tác trúng các phần tử DOM trên trang Facebook thật hay không. Điều này cho phép các Coding Agent viết code rỗng (Stub/Mock với `setTimeout` hoặc trả về kết quả thành công giả định) để vượt qua bài test một cách dễ dàng, biến các tính năng FSM trở thành "bình hoa di động".

---

### 6. Tác dụng phụ của việc Cô lập Ngữ cảnh quá mức (Context Isolation)
*   **Mô tả khuyết điểm:** 
    Hệ thống Swarm phân chia Coding Agent thành các tác tử chuyên biệt, bị cô lập ngữ cảnh (Agent viết Extension không biết gì về Backend, Agent viết Backend chỉ code theo API của mình).
*   **Hậu quả:** 
    Khi không có một "Tác tử Tích hợp" (Integration Agent) chịu trách nhiệm kiểm tra sự ăn khớp giữa các mảnh ghép, các giả định sai lệch (ví dụ: Backend đổi cấu trúc API, Extension vẫn gọi theo cấu trúc cũ) không được phát hiện cho đến khi ráp nối thực tế trên máy người dùng.

---

## 🛠️ ĐỀ XUẤT CẢI TIẾN AGENT HARNESS (ACTION ITEMS)

Để biến `agent_harness` thành một hệ thống chốt chặn chất lượng thực chất, cần bổ sung các cơ chế sau:

1.  **Sửa đổi `local_e2e_runner.js` để test Chrome thật:**
    Thay vì dùng Node mock client, buộc runner phải khởi chạy Chrome thông qua `chrome_launcher.js`, đợi Extension kết nối thật vào WebSocket, rồi mới tiến hành assert trạng thái `ws_connected === 1` của account trong Database.
2.  **Thực thi kiểm định Target:**
    Thêm bước quét `browser.targets()` trong test runner để đảm bảo `service_worker` và `offscreen_document` của Extension đang chạy và không phát sinh lỗi (exception) trong console log.
3.  **Kích hoạt Strict Schema Validation ở Backend:**
    Nhúng Ajv validate toàn bộ tin nhắn WS và API request nhận được để bắt lỗi lập trình lệch pha spec ngay lập tức.
4.  **Viết Test Case tương tác DOM thật:**
    Sử dụng JSDOM nạp các HTML fixture của Facebook thực tế, chạy Content Script thật để kiểm tra độ chính xác của selector và Bezier mouse click.
