# Hermes FacePost-Group — Spec 06: Checkpoint & 2FA Handler Specification
**Priority:** D1 HIGH  
**Status:** NEW SPEC — Production Implementation Ready  
**Version:** 2.1.0  
**Updated:** 2026-06-18  
**Audit Ref:** C3, C4 — Missing checkpoint flow + Missing error taxonomy  

---

## 1. Tổng Quan Kỹ Thuật

Tài liệu này đặc tả cơ chế nhận diện, phân loại và xử lý các trạng thái khóa tạm thời (Checkpoint) và yêu cầu xác thực hai lớp (2FA) của mạng xã hội Facebook. Mục tiêu cốt lõi của đặc tả này là giải quyết triệt để lỗi treo phiên làm việc (Session Hangs) và tiến trình chạy ngầm không tự giải phóng (Zombie Processes) khi tài khoản gặp sự cố bảo mật.

### 1.1. Nguyên Nhân Sự Cố
* Trạng thái tài khoản trong cơ sở dữ liệu được đánh dấu là `CHECKPOINT` nhưng thiếu luồng xử lý và giải phóng tài nguyên hệ thống tương ứng.
* Các tiến trình Chrome chạy ngầm không được tắt đúng cách khi gặp checkpoint, làm tiêu hao tài nguyên RAM/CPU và chặn hàng đợi (Queue Block).

### 1.2. Mục Tiêu Thiết Kế
* **Định danh chính xác:** Phát hiện checkpoint tức thời thông qua phân tích cấu trúc DOM (DOM snapshot) kết hợp phân tích trực quan (Visual check qua OCR/Multimodal).
* **Xử lý bất đồng bộ thích nghi:** Phân loại checkpoint để lựa chọn giải pháp: Tự động giải quyết (Auto-Dismiss/Auto-Solve), Đưa vào chế độ ngủ và cô lập (Sleep & Hibernate), hoặc Chuyển tiếp phê duyệt thủ công (Manual Intervention Escalation).
* **Giải phóng tài nguyên tuyệt đối:** Ngắt tiến trình Chrome ngay khi gặp checkpoint khó để tránh bị khóa vĩnh viễn và giải phóng slot xử lý cho worker khác.

---

## Mục Lục

1. [Phân Loại Checkpoint Facebook (Taxonomy CHK-01 -> CHK-08)](#2-phân-loại-checkpoint-facebook-taxonomy-chk-01---chk-08)
2. [Giải Pháp Chụp Ảnh OCR và Phân Tích Trực Quan (Visual Check & Multimodal)](#3-giải-pháp-chụp-ảnh-ocr-và-phân-tích-trực-quan-visual-check--multimodal)
3. [Cấu Trúc Module CheckpointDetector](#4-cấu-trúc-module-checkpointdetector)
4. [Tự Động Xử Lý Checkpoint (Automated Handling)](#5-tự-động-xử-lý-checkpoint-automated-handling)
5. [Cơ Chế Phê Duyệt Đa Tầng (Multi-Tiered Escalation Gateway)](#6-cơ-chế-phê-duyệt-đa-tầng-multi-tiered-escalation-gateway)
6. [Hệ Thống Mã Lỗi (Error Code Taxonomy)](#7-hệ-thống-mã-lỗi-error-code-taxonomy)
7. [Hệ Thống Đánh Giá Sức Khỏe Tài Khoản (Account Health Score System)](#8-hệ-thống-đánh-giá-sức-khỏe-tài-khoản-account-health-score-system)
8. [Chế Độ Giãn Cách Thích Nghi (Adaptive Rate Limiting)](#9-chế-độ-giãn-cách-thích-nghi-adaptive-rate-limiting)
9. [Cấu Trúc Cơ Sở Dữ Liệu SQLite (Database Extensions)](#10-cấu-trúc-cơ-sở-dữ-liệu-sqlite-database-extensions)
10. [Tích Hợp Phiên Làm Việc (Session FSM Integration)](#11-tích-hợp-phiên-làm-việc-session-fsm-integration)

---

## 2. Phân Loại Checkpoint Facebook (Taxonomy CHK-01 -> CHK-08)

Facebook triển khai nhiều dạng xác minh danh tính khác nhau dựa trên mức độ rủi ro hành vi được ghi nhận. Dưới đây là phân loại chi tiết 8 loại checkpoint:

| Mã Số | Tên Checkpoint | Phương Án Xử Lý | Mức Độ Nghiêm Trọng | Thời Gian Xử Lý Trung Bình |
|-------|----------------|-----------------|---------------------|----------------------------|
| **CHK-01** | Phone Number Verification (OTP SMS) | Thủ công (Awaiting Manual) | Nguy cấp (CRITICAL) | 5–30 phút |
| **CHK-02** | Photo Identity Verification (Bạn bè) | Thủ công (Awaiting Manual) | Nguy cấp (CRITICAL) | 10–60 phút |
| **CHK-03** | Trusted Contacts Verification | Thủ công (Awaiting Manual) | Cao (HIGH) | 10–60 phút |
| **CHK-04** | Video Selfie Verification | Thủ công (Awaiting Manual) | Nguy cấp (CRITICAL) | 30+ phút |
| **CHK-05** | CAPTCHA (hCaptcha / Text CAPTCHA) | Tự động hóa một phần (OCR) | Cao (HIGH) | 1–5 phút |
| **CHK-06** | Confirm It's You (Xác nhận hành vi) | Thủ công (Awaiting Manual) | Trung bình (MEDIUM) | 5–15 phút |
| **CHK-07** | Account Temporarily Locked (Tạm khóa) | Tự động thích nghi (Auto-Cooldown)| Trung bình (MEDIUM) | 1–24 giờ |
| **CHK-08** | Content Policy Violation Warning | Tự động dismiss (Auto-Dismiss) | Thấp (LOW) | Tức thời (Immediate) |

### 2.1. CHK-01: Phone Number Verification (OTP SMS)
* **Mô tả:** Facebook yêu cầu nhập mã xác nhận gửi về số điện thoại liên kết hoặc mã xác thực ứng dụng (Authenticator App).
* **Dấu hiệu nhận biết (DOM Fingerprint):**
  - Text: `"Nhập mã xác nhận"` / `"Enter confirmation code"`, `"Chúng tôi đã gửi mã"` / `"We sent a code"`, `"Resend code"`.
  - Selectors: `input[name="approvals_code"]`, `input[autocomplete="one-time-code"]`, `form[action*="checkpoint/verify"]`.
  - URL: `/checkpoint/`, `/login/checkpoint/`, `/security/checkpoint/`.

### 2.2. CHK-02: Photo Identity Verification (Xác minh hình ảnh bạn bè)
* **Mô tả:** Facebook hiển thị các bức ảnh của bạn bè trong danh sách và yêu cầu tài khoản lựa chọn chính xác tên của họ.
* **Dấu hiệu nhận biết (DOM Fingerprint):**
  - Text: `"Xác nhận danh tính"` / `"Confirm your identity"`, `"Ai trong ảnh này?"` / `"Who is in this photo?"`, `"Select a name"`.
  - Selectors: `div[data-testid*="identity"]`, `img[data-testid*="checkpoint-photo"]`, `ul[role="listbox"]`.

### 2.3. CHK-03: Trusted Contacts Verification
* **Mô tả:** Yêu cầu liên hệ với các liên hệ tin cậy đã thiết lập từ trước để lấy mã bảo mật phục hồi.
* **Dấu hiệu nhận biết (DOM Fingerprint):**
  - Text: `"Trusted contacts"` / `"Danh bạ đáng tin"`, `"Contact your friends"`, `"recovery code"`.
  - Selectors: `div[data-module-role*="trusted"]`, `a[href*="trusted_contact"]`.

### 2.4. CHK-04: Video Selfie Verification
* **Mô tả:** Yêu cầu người dùng quay video chuyển động khuôn mặt trực tiếp bằng camera thiết bị.
* **Dấu hiệu nhận biết (DOM Fingerprint):**
  - Text: `"Video selfie"`, `"record a short video"`, `"xác minh khuôn mặt"`.
  - Selectors: `video[data-testid*="selfie"]`, `button[data-testid*="start-recording"]`.

### 2.5. CHK-05: CAPTCHA (hCaptcha / Text CAPTCHA)
* **Mô tả:** Xuất hiện thử thách phân biệt robot dạng hCaptcha hoặc hình ảnh ký tự viết mờ.
* **Dấu hiệu nhận biết (DOM Fingerprint):**
  - Text: `"I'm not a robot"` / `"Tôi không phải robot"`, `"Verify you're human"`.
  - Selectors: `iframe[src*="hcaptcha.com"]`, `div.h-captcha`, `input[name*="captcha"]`, `img[alt*="captcha"]`.

### 2.6. CHK-06: "Confirm It's You" (Behavioral Check)
* **Mô tả:** Yêu cầu xác minh thiết bị hoặc địa điểm đăng nhập lạ so với lịch sử tương tác trước đó.
* **Dấu hiệu nhận biết (DOM Fingerprint):**
  - Text: `"Xác nhận đây là bạn"` / `"Confirm it's you"`, `"Was this you?"`, `"Thiết bị mới"`.
  - Selectors: `button[value*="approve"]`, `form[action*="login_approvals"]`.

### 2.7. CHK-07: Account Temporarily Locked (Tạm thời vô hiệu hóa)
* **Mô tả:** Facebook tạm khóa tài khoản trong thời gian xác định do nghi ngờ spam hoặc hoạt động bất thường.
* **Dấu hiệu nhận biết (DOM Fingerprint):**
  - Text: `"Tài khoản bị tạm khóa"` / `"Account temporarily locked"`, `"Try again later"`, `"bị tạm thời vô hiệu hóa"`.
  - Selectors: `div[class*="lockout"]`, `div[role="main"] > div > div:has(h2:contains("locked"))`.
  - Regular Expression trích xuất thời gian cooldown: `/(\d+)\s*(giờ|hour|phút|minute|ngày|day)/i`.

### 2.8. CHK-08: Content Policy Violation Warning
* **Mô tả:** Hiển thị cảnh báo vi phạm Tiêu chuẩn cộng đồng về nội dung đăng tải. Yêu cầu người dùng xác nhận đã đọc cảnh báo để tiếp tục sử dụng.
* **Dấu hiệu nhận biết (DOM Fingerprint):**
  - Text: `"Vi phạm Tiêu chuẩn cộng đồng"` / `"Community Standards violation"`, `"Tôi hiểu"` / `"I understand"`, `"Đồng ý"`.
  - Selectors: `div[data-testid*="policy-warning"]`, `button[value="ok"]`, `button[value="dismiss"]`.

---

## 3. Giải Pháp Chụp Ảnh OCR và Phân Tích Trực Quan (Visual Check & Multimodal)

Khi Facebook áp dụng cơ chế xáo trộn mã nguồn HTML và mã hóa CSS ngẫu nhiên để chống cào thông tin, việc phát hiện chỉ dựa trên cấu trúc DOM tĩnh sẽ không đạt độ tin cậy tuyệt đối. Hệ thống triển khai thêm **Engine Kiểm Tra Trực Quan (Visual Check Engine)** thông qua chụp ảnh màn hình và xử lý đa phương thức (OCR / Multimodal).

```
                             [Phiên làm việc nghi ngờ checkpoint]
                                              │
                                     [Chụp Ảnh Màn Hình]
                                              │
                     ┌────────────────────────┴────────────────────────┐
                     ▼                                                 ▼
             [Xử lý OCR cục bộ]                           [Gửi Lên AI Multimodal Vision]
         (Tesseract / Cloud OCR API)                         (Gemini 1.5 Flash API)
                     │                                                 │
       Trích xuất từ khóa thô trong ảnh                      Phân tích giao diện trực quan 
                     │                                                 │
                     ▼                                                 ▼
        Phân loại Checkpoint ID (CHK)                      - Trả về cấu trúc Checkpoint ID
                     │                                     - Tọa độ Bounding Box của nút bấm 
                     │                                     - Phương án tự phục hồi (Self-Healing)
                     │                                                 │
                     └────────────────────────┬────────────────────────┘
                                              ▼
                             [Ra quyết định xử lý trong FSM]
```

### 3.1. Chức Năng Chụp Ảnh Màn Hình (Screenshot Capture)
Khi tiến hành thao tác trên trang web hoặc khi gặp lỗi DOM (`ERR-DOM-01`), hệ thống sẽ gọi phương thức chụp ảnh màn hình thông qua CDP (Chrome DevTools Protocol) hoặc Puppeteer API:
```javascript
async function captureVisualContext(pageDriver, accountId) {
  const screenshotBuffer = await pageDriver.screenshot({
    type: 'png',
    fullPage: false // Chỉ chụp khung nhìn viewport hiện tại
  });
  const tempPath = path.join(__dirname, '..', 'tmp', `screenshot_${accountId}_${Date.now()}.png`);
  await fs.promises.writeFile(tempPath, screenshotBuffer);
  return tempPath;
}
```

### 3.2. Module Nhận Diện Ký Tự Quang Học (OCR Engine)
OCR Engine chịu trách nhiệm trích xuất nhanh các khối văn bản xuất hiện trên hình ảnh màn hình nhằm bổ trợ thông tin cho `CheckpointDetector`.
* **Cơ chế hoạt động:** Sử dụng thư viện OCR cục bộ (Tesseract.js hoặc thư viện hệ thống tương đương) hoặc gọi Cloud Vision API để phân tích vùng ảnh.
* **Nhận diện từ khóa:** Tìm kiếm các từ khóa tiếng Việt, tiếng Anh và ngôn ngữ thiết lập của trình duyệt liên quan đến checkpoint để tính toán trọng số quyết định.

### 3.3. Module Phân Tích Đa Phương Thức (Multimodal Vision Analyzer)
Khi cấu trúc DOM bị xáo trộn hoặc ẩn (shadow DOM), hệ thống gửi ảnh chụp màn hình kèm theo mã HTML tối giản (minified DOM) tới mô hình AI Multimodal Vision (ví dụ: Gemini 1.5 Flash) để thực hiện chẩn đoán trực quan.
* **Cấu trúc dữ liệu gửi lên:**
  - `image`: Ảnh chụp màn hình định dạng PNG hoặc JPEG (base64).
  - `context`: Đường dẫn URL hiện tại, lịch sử hành động trước đó, mã tài khoản.
* **Định dạng dữ liệu trả về từ AI Vision (JSON):**
```json
{
  "checkpointDetected": true,
  "checkpointType": "CHK_PHONE_OTP",
  "confidence": 0.95,
  "actionRequired": "manual_input",
  "visualElements": [
    {
      "elementName": "otp_input_field",
      "description": "Ô nhập mã OTP SMS",
      "coordinates": { "x": 450, "y": 320 },
      "boundingBox": { "top": 310, "left": 400, "bottom": 330, "right": 500 }
    },
    {
      "elementName": "submit_button",
      "description": "Nút bấm gửi mã tiếp tục",
      "coordinates": { "x": 450, "y": 380 },
      "boundingBox": { "top": 370, "left": 410, "bottom": 390, "right": 490 }
    }
  ]
}
```

### 3.4. Logic Tự Phục Hồi (Self-Healing Recovery Logic)
Dựa trên phản hồi từ AI Multimodal Vision:
* **Tự động nhấp chuột theo tọa độ:** Nếu hệ thống không tìm thấy selector DOM hợp lệ của các nút bấm hành động (ví dụ: Nút "Tiếp tục" hoặc nút "Bỏ qua"), hệ thống sẽ sử dụng tọa độ trung tâm `(x, y)` từ trường `coordinates` trong kết quả visual check. Trình điều khiển sẽ gọi hàm giả lập chuột Bezier để di chuyển và nhấp chuột chính xác vào tọa độ vật lý đó trên viewport.
* **Giải quyết CAPTCHA bằng OCR:** Khi phát hiện ảnh CAPTCHA (CHK-05), hệ thống sẽ tự động crop vùng ảnh chứa CAPTCHA dựa trên bounding box do AI Vision phân tích ➔ gửi vùng ảnh đã crop tới module OCR để giải mã ký tự ➔ điền kết quả vào ô nhập liệu tương ứng ➔ bấm nút tiếp tục.

---

## 4. Cấu Trúc Module CheckpointDetector

`CheckpointDetector` sử dụng cơ chế **Weighted Scoring Engine** (Tính điểm trọng số) kết hợp với kết quả từ cấu trúc DOM và Visual Check để đưa ra phân loại chính xác, tránh việc hardcode selectors dễ bị vô hiệu hóa khi Facebook thay đổi cấu trúc mã nguồn.

### 4.1. Quy Tắc Tính Điểm Trọng Số (Weighted Scoring Engine)
Mỗi loại checkpoint định nghĩa một bộ luật (rules) với trọng số (weight) tương ứng:
$$\text{Score} = \sum (\text{Rule Weight} \times \text{Match Status})$$
$$\text{Confidence} = \min\left(1.0, \frac{\text{Score}}{\text{Max Score}}\right)$$
Trạng thái Checkpoint được xác định khi chỉ số `Confidence` vượt qua ngưỡng `CONFIDENCE_THRESHOLD = 0.60`.

### 4.2. Triển Khai Chi Tiết `checkpoint_detector.js`

```javascript
// checkpoint_detector.js
'use strict';

const CONFIDENCE_THRESHOLD = 0.60;
const CHECKPOINT_URL_PATTERNS = [
  /facebook\.com\/checkpoint/i,
  /facebook\.com\/login\/checkpoint/i,
  /facebook\.com\/security\/checkpoint/i,
  /facebook\.com\/login\/approvals/i,
];

const CHECKPOINT_RULES = {
  CHK_PHONE_OTP: {
    maxScore: 10,
    threshold: 0.65,
    canAutoHandle: false,
    rules: [
      { type: 'selector', selector: 'input[name="approvals_code"]', weight: 4 },
      { type: 'selector', selector: 'input[autocomplete="one-time-code"]', weight: 3 },
      { type: 'text', patterns: ['nhập mã xác nhận', 'enter confirmation code', 'we sent a code', 'chúng tôi đã gửi mã'], weight: 2 },
      { type: 'text', patterns: ['gửi lại mã', 'resend code', 'resend sms'], weight: 1 },
      { type: 'url', patterns: [/checkpoint\/verify/i, /login_approvals/i], weight: 2 },
      { type: 'selector', selector: 'form[action*="checkpoint/verify"]', weight: 3 },
    ]
  },
  CHK_PHOTO_IDENTITY: {
    maxScore: 10,
    threshold: 0.60,
    canAutoHandle: false,
    rules: [
      { type: 'text', patterns: ['xác nhận danh tính', 'confirm your identity', 'who is in this photo', 'ai trong ảnh này'], weight: 4 },
      { type: 'selector', selector: 'ul[role="listbox"]', weight: 2 },
      { type: 'selector', selector: 'img[data-testid*="checkpoint"]', weight: 2 },
      { type: 'text', patterns: ['nhận dạng', 'tagged photo', 'identify'], weight: 2 },
      { type: 'url', patterns: [/identity_check/i, /photo_verify/i], weight: 3 },
    ]
  },
  CHK_TRUSTED_CONTACTS: {
    maxScore: 10,
    threshold: 0.65,
    canAutoHandle: false,
    rules: [
      { type: 'text', patterns: ['trusted contacts', 'danh bạ đáng tin', 'liên hệ bạn bè', 'recovery code', 'mã khôi phục'], weight: 4 },
      { type: 'selector', selector: 'a[href*="trusted_contact"]', weight: 4 },
      { type: 'url', patterns: [/trusted_contact_checkpoint/i], weight: 4 },
    ]
  },
  CHK_VIDEO_SELFIE: {
    maxScore: 10,
    threshold: 0.60,
    canAutoHandle: false,
    rules: [
      { type: 'text', patterns: ['video selfie', 'quay video', 'record a short video', 'xác minh khuôn mặt', 'face verification'], weight: 5 },
      { type: 'selector', selector: 'button[data-testid*="start-recording"]', weight: 4 },
      { type: 'selector', selector: 'video[data-testid*="selfie"]', weight: 4 },
    ]
  },
  CHK_CAPTCHA: {
    maxScore: 10,
    threshold: 0.55,
    canAutoHandle: true,
    rules: [
      { type: 'selector', selector: 'iframe[src*="hcaptcha.com"]', weight: 5 },
      { type: 'selector', selector: 'div.h-captcha', weight: 4 },
      { type: 'selector', selector: 'input[name*="captcha"]', weight: 3 },
      { type: 'text', patterns: ["i'm not a robot", "tôi không phải robot", "verify you're human"], weight: 3 },
    ]
  },
  CHK_BEHAVIORAL: {
    maxScore: 10,
    threshold: 0.60,
    canAutoHandle: false,
    rules: [
      { type: 'text', patterns: ['xác nhận đây là bạn', 'confirm it\'s you', 'was this you', 'đây có phải bạn không', 'thiết bị mới'], weight: 4 },
      { type: 'selector', selector: 'button[value*="approve"]', weight: 3 },
      { type: 'url', patterns: [/login_approvals/i, /two_step_verification/i], weight: 3 },
    ]
  },
  CHK_COOLDOWN: {
    maxScore: 10,
    threshold: 0.55,
    canAutoHandle: true,
    rules: [
      { type: 'text', patterns: ['tài khoản bị tạm khóa', 'account temporarily locked', 'temporarily disabled', 'bị tạm thời vô hiệu hóa'], weight: 5 },
      { type: 'text', patterns: ['thử lại sau', 'try again later', 'thử lại vào'], weight: 3 },
      { type: 'text', patterns: ['24 hours', '48 hours', '7 days', '24 giờ', '48 giờ', '7 ngày'], weight: 2 },
      { type: 'regex', pattern: /(\d+)\s*(giờ|hour|phút|minute|ngày|day)\s*(nữa|left|remaining)/i, weight: 4 },
    ]
  },
  CHK_POLICY_WARNING: {
    maxScore: 10,
    threshold: 0.55,
    canAutoHandle: true,
    rules: [
      { type: 'text', patterns: ['vi phạm tiêu chuẩn cộng đồng', 'community standards violation', 'nội dung của bạn đã bị gỡ', 'your content was removed'], weight: 4 },
      { type: 'text', patterns: ['tôi hiểu', 'i understand', 'đồng ý', 'ok', 'tìm hiểu thêm'], weight: 2 },
      { type: 'selector', selector: 'div[data-testid*="policy-warning"]', weight: 3 },
      { type: 'selector', selector: 'button[value="ok"], button[value="dismiss"]', weight: 3 },
    ]
  }
};

function parseCooldownSeconds(textContent) {
  let totalSeconds = 0;
  const patterns = [
    { regex: /(\d+)\s*(ngày|ngay|day|days)/gi, multiplier: 86400 },
    { regex: /(\d+)\s*(giờ|gio|tiếng|hour|hours|hrs|hr)/gi, multiplier: 3600 },
    { regex: /(\d+)\s*(phút|phut|minute|minutes|min|mins)/gi, multiplier: 60 },
  ];

  for (const { regex, multiplier } of patterns) {
    regex.lastIndex = 0;
    let match;
    while ((match = regex.exec(textContent)) !== null) {
      totalSeconds += parseInt(match[1]) * multiplier;
    }
  }

  return totalSeconds > 0 ? totalSeconds : 86400; // Fallback mặc định 24 giờ
}

function matchSelectorInElements(selector, elements) {
  const inputNameMatch = selector.match(/input\[name=["']([^"']+)["']\]/);
  if (inputNameMatch) {
    return elements.some(e => e.tag === 'input' && e.name === inputNameMatch[1]);
  }

  const testIdContains = selector.match(/\[data-testid\*=["']([^"']+)["']\]/);
  if (testIdContains) {
    return elements.some(e => e.dataTestid?.includes(testIdContains[1]));
  }

  const iframeSrc = selector.match(/iframe\[src\*=["']([^"']+)["']\]/);
  if (iframeSrc) {
    return elements.some(e => e.tag === 'iframe' && e.src?.includes(iframeSrc[1]));
  }

  const btnValueExact = selector.match(/button\[value=["']([^"']+)["']\]/);
  if (btnValueExact) {
    return elements.some(e => e.tag === 'button' && e.value === btnValueExact[1]);
  }

  const formAction = selector.match(/form\[action\*=["']([^"']+)["']\]/);
  if (formAction) {
    return elements.some(e => e.tag === 'form' && e.action?.includes(formAction[1]));
  }

  return elements.some(e =>
    (e.ariaLabel || '').toLowerCase().includes(selector.toLowerCase()) ||
    (e.text || '').toLowerCase().includes(selector.toLowerCase())
  );
}

function scoreCheckpointType(type, rules, domSnapshot) {
  const textContent = [
    domSnapshot.innerText || '',
    domSnapshot.textContent || '',
    domSnapshot.title || '',
    ...(domSnapshot.elements || []).map(e => e.text || e.ariaLabel || '').filter(Boolean)
  ].join(' ').toLowerCase();

  const url = (domSnapshot.url || '').toLowerCase();
  const elements = domSnapshot.elements || [];
  let score = 0;

  for (const rule of rules) {
    let hit = false;
    switch (rule.type) {
      case 'text':
        hit = rule.patterns.some(p => textContent.includes(p.toLowerCase()));
        break;
      case 'selector':
        hit = matchSelectorInElements(rule.selector, elements);
        break;
      case 'url':
        hit = rule.patterns.some(p => p.test ? p.test(url) : url.includes(p.toLowerCase()));
        break;
      case 'regex':
        try {
          const re = rule.pattern instanceof RegExp ? rule.pattern : new RegExp(rule.pattern, 'i');
          hit = re.test(textContent);
        } catch (e) {
          hit = false;
        }
        break;
      default:
        break;
    }
    if (hit) score += rule.weight;
  }
  return score;
}

function detect(domSnapshot) {
  const now = Date.now();
  const isCheckpointUrl = CHECKPOINT_URL_PATTERNS.some(p => p.test(domSnapshot.url || ''));

  let bestType = null;
  let bestConfidence = 0;
  let bestCanAutoHandle = false;

  for (const [type, config] of Object.entries(CHECKPOINT_RULES)) {
    const score = scoreCheckpointType(type, config.rules, domSnapshot);
    const confidence = Math.min(score / config.maxScore, 1.0);

    if (confidence >= config.threshold && confidence > bestConfidence) {
      bestType = type;
      bestConfidence = confidence;
      bestCanAutoHandle = config.canAutoHandle;
    }
  }

  if (isCheckpointUrl && bestType && bestConfidence < 0.9) {
    bestConfidence = Math.min(bestConfidence + 0.15, 1.0);
  }

  if (!bestType || bestConfidence < CONFIDENCE_THRESHOLD) {
    return {
      detected: false,
      type: null,
      confidence: bestConfidence,
      canAutoHandle: false,
      metadata: { timestamp: now, url: domSnapshot.url }
    };
  }

  const metadata = {
    timestamp: now,
    url: domSnapshot.url,
    warningText: domSnapshot.innerText || domSnapshot.textContent || ''
  };

  if (bestType === 'CHK_COOLDOWN') {
    metadata.cooldownSeconds = parseCooldownSeconds(metadata.warningText);
  }

  return {
    detected: true,
    type: bestType,
    confidence: bestConfidence,
    canAutoHandle: bestCanAutoHandle,
    metadata
  };
}

if (typeof module !== 'undefined') {
  module.exports = { detect, parseCooldownSeconds, matchSelectorInElements, CHECKPOINT_RULES };
}
```

---

## 5. Tự Động Xử Lý Checkpoint (Automated Handling)

### 5.1. Auto-Handler cho CHK_COOLDOWN (Tạm khóa tài khoản)

```javascript
async function handleCooldown(accountId, detectionResult, db) {
  const { cooldownSeconds } = detectionResult.metadata;
  const cooldownUntil = new Date(Date.now() + cooldownSeconds * 1000);
  const cooldownUntilStr = cooldownUntil.toISOString();

  // Cập nhật trạng thái tài khoản vào SQLite
  db.prepare(`
    UPDATE accounts 
    SET 
      status = 'COOLDOWN',
      cooldown_until = ?,
      last_checkpoint_at = datetime('now'),
      checkpoint_count_7d = checkpoint_count_7d + 1
    WHERE id = ?
  `).run(cooldownUntilStr, accountId);

  // Log sự kiện
  db.prepare(`
    INSERT INTO account_events (account_id, event_type, event_data, created_at)
    VALUES (?, 'CHECKPOINT_COOLDOWN', ?, datetime('now'))
  `).run(accountId, JSON.stringify({
    cooldown_seconds: cooldownSeconds,
    cooldown_until: cooldownUntilStr
  }));

  updateHealthScore(accountId, db);

  return {
    action: 'RELEASE_WORKER',
    retryAfter: cooldownUntil,
    message: `Account ${accountId} entered cooldown for ${Math.round(cooldownSeconds/3600)}h`
  };
}
```

### 5.2. Auto-Handler cho CHK_POLICY_WARNING (Cảnh báo vi phạm chính sách)

```javascript
class CheckpointAutoHandler {
  constructor({ wsServer, pageDriver = null }) {
    this.wsServer = wsServer;
    this.pageDriver = pageDriver;
  }

  async clickElement(accountId, selector) {
    if (this.pageDriver) {
      await this.pageDriver.click(selector);
    } else if (this.wsServer) {
      await this.wsServer.sendToExtension(accountId, {
        type: 'CLICK_ELEMENT',
        payload: { selector }
      });
      return this.wsServer.waitForResult(accountId, 'COMMAND_RESULT', 10000);
    } else {
      throw new Error('ERR_NO_PAGE_DRIVER: No driver available for DOM interaction');
    }
  }

  async handlePolicyWarning(accountId, detectionResult) {
    const fallbackSelectors = [
      'button[value="ok"]',
      'button[value="dismiss"]',
      'button[aria-label*="Tôi hiểu"]',
      'button[aria-label*="Đồng ý"]',
      'button[aria-label*="OK"]',
    ];
    
    let clicked = false;
    for (const sel of fallbackSelectors) {
      try {
        await this.clickElement(accountId, sel);
        clicked = true;
        break;
      } catch (_) {
        // Tiếp tục thử selector dự phòng tiếp theo
      }
    }

    if (!clicked) {
      return { success: false, reason: 'Dismiss button not found' };
    }

    return {
      success: true,
      action: 'RESUME_WITH_DELAY',
      additionalDelayMs: 5 * 60 * 1000,
      message: `Policy warning dismissed for account ${accountId}`
    };
  }
}
```

---

## 6. Cơ Chế Phê Duyệt Đa Tầng (Multi-Tiered Escalation Gateway)

Để kiểm soát hành vi và ngăn chặn rủi ro hư hỏng tài khoản hàng loạt, hệ thống định nghĩa quy trình phân tầng xử lý 3 cấp độ (3-Tier Approval Gateway):

### 6.1. Thiết Kế 3 Tầng Phân Quyền
1. **TIER 1: Tự phục hồi tự động (Auto-Solve)**
   - *Điều kiện kích hoạt:* Các lỗi cấu trúc nhẹ (`ERR-DOM-01/02`), CAPTCHA hỗ trợ giải mã bằng OCR, hoặc lỗi tràn hạn ngạch khóa API của một mô hình đơn lẻ.
   - *Hành động:* Hệ thống tự động thực thi cơ chế thử lại (retry) với thuật toán giãn trễ số mũ (exponential backoff) tối đa 3 lần.
2. **TIER 2: Leo thang lên Trình quản lý AI (AI Leader)**
   - *Điều kiện kích hoạt:* Phát hiện vòng lặp vô hạn (FSM Deadlock), cạn kiệt toàn bộ khóa API dịch vụ, hoặc lỗi kết nối SQLite tạm thời.
   - *Hành động:* Gửi thông tin chẩn đoán lên IDE Agent để chạy quy trình tự khắc phục (giải phóng dung lượng RAM, khởi động lại tiến trình mồ côi, phục hồi cơ sở dữ liệu từ file backup gần nhất).
3. **TIER 3: Cổng phê duyệt từ Con người (Human Approval)**
   - *Điều kiện kích hoạt:* Checkpoint bảo mật nặng (`CHK_PHONE_OTP`, `CHK_VIDEO_SELFIE`, `CHK_PHOTO_IDENTITY`), hoặc nghi ngờ có sự tấn công/can thiệp mã nguồn không an toàn.
   - *Hành động:*
     - Lập tức ngắt kết nối tiến trình Chrome của tài khoản đó (Kill Chrome Process) để cách ly. Ghi nhận trạng thái `HIBERNATE_AWAITING_MANUAL`.
     - Phát cảnh báo khẩn cấp lên giao diện điều khiển (Dashboard UI) qua WebSocket.
     - Hiển thị màn hình tương tác yêu cầu quản trị viên can thiệp: Nhập OTP, giải câu hỏi bạn bè, hoặc chụp selfie khuôn mặt.

### 6.2. Thiết Kế Sleep & Hibernate và Bão Checkpoint (Checkpoint Storm)
Khi tài khoản gặp checkpoint khó đòi hỏi can thiệp từ người dùng:
1. **Sleep & Hibernate:** Hệ thống **bắt buộc** ngắt ngay tiến trình Chrome để bảo vệ tài khoản khỏi bị quét checkpoint liên tiếp (gây khóa vĩnh viễn), giải phóng luồng chạy cho hàng đợi, và lưu giữ URL checkpoint trong database.
2. **Bão Checkpoint (Checkpoint Storm Protection):** Khi người dùng hoàn thành giải quyết checkpoint thủ công thông qua nút "Xử lý Checkpoint" trên Dashboard, hệ thống **bắt buộc** đưa tài khoản vào trạng thái cooldown kéo dài từ **12 đến 24 giờ** (sinh thời gian ngẫu nhiên). Đồng thời ngắt tiếp Chrome process để tránh việc vừa giải checkpoint xong đã thực hiện tương tác ngay lập tức, một hành vi dễ bị Facebook đánh dấu spam.

---

## 7. Hệ Thống Mã Lỗi (Error Code Taxonomy)

Hệ thống phân cấp lỗi rõ ràng để Session FSM đưa ra quyết định phục hồi chuẩn xác:

| Mã Lỗi | Tên Lỗi | Mô Tả Kỹ Thuật | Mức Độ | Phương Án Khắc Phục (Retry Strategy) |
|--------|---------|----------------|--------|--------------------------------------|
| **ERR-DOM-01** | Element Not Found | Không tìm thấy selector trong cấu trúc DOM | Thấp (RECOVERABLE) | Thử lại 3 lần, giãn cách 2 giây. Nếu thất bại, ghi nhận log và chuyển qua hành động tiếp theo. |
| **ERR-DOM-02** | DOM Snapshot Empty | Snapshot DOM trả về giá trị rỗng hoặc timeout | Thấp (RECOVERABLE) | Tải lại trang (Reload), thử lại tối đa 2 lần. |
| **ERR-NET-02** | WS Disconnected | Mất kết nối WebSocket tới Extension | Thấp (RECOVERABLE) | Tự động kết nối lại theo chu kỳ số mũ: 1s, 2s, 4s, 8s,... |
| **ERR-PRX-07** | Proxy Auth Failed | Lỗi xác thực tài khoản Proxy (407) | Nghiêm trọng (FATAL) | Đánh dấu proxy lỗi, chuyển sang cấu hình proxy dự phòng. |
| **ERR-PRX-08** | Proxy Conn Refused | Proxy từ chối kết nối | Thấp (RECOVERABLE) | Tự động luân chuyển proxy khác trong danh sách. |
| **ERR-CHK-09** | Hard Checkpoint | Phát hiện checkpoint khó (OTP, selfie, hình ảnh) | Nghiêm trọng (FATAL) | Tạm dừng phiên, kích hoạt chế độ Sleep & Hibernate, cảnh báo người dùng can thiệp. |
| **ERR-CHK-12** | Account Locked | Phát hiện trạng thái tạm khóa tài khoản (cooldown)| Thấp (RECOVERABLE) | Parse thời gian cooldown từ giao diện, lên lịch chạy lại sau. |
| **ERR-SYS-16** | DB Write Failed | Không ghi được dữ liệu vào tệp SQLite | Nghiêm trọng (FATAL) | Thử lại 3 lần. Nếu không thành công, lưu sự kiện vào RAM buffer và phát tín hiệu cảnh báo hệ thống. |

---

## 8. Hệ Thống Đánh Giá Sức Khỏe Tài Khoản (Account Health Score System)

Chỉ số sức khỏe tài khoản (`health_score`) nằm trong khoảng `[0, 100]` được tính toán động thông qua JavaScript callback để quyết định tần suất và giới hạn hoạt động.

### 8.1. Các Yếu Tố Điều Chỉnh Điểm Sức Khỏe
* Điểm khởi đầu mặc định: `100`
* Mỗi sự kiện checkpoint gặp phải trong 7 ngày gần nhất: `-10` điểm (giới hạn trừ tối đa `-40`).
* Mỗi sự kiện cooldown trong 30 ngày: `-5` điểm.
* Mỗi cảnh báo vi phạm chính sách nội dung (Policy warning) trong 30 ngày: `-3` điểm.
* Mỗi bài đăng thành công: `+2` điểm (giới hạn cộng tối đa `+30`).
* Mỗi khoảng nghỉ an toàn (Adequate rest >= 5 phút) trong 24 giờ: `+1` điểm (tối đa `+10`).
* Hoạt động ổn định liên tục không phát sinh lỗi mỗi 72 giờ: `+5` điểm (tối đa `+20`).
* Trạng thái tài khoản DIE/LOCKED/BANNED: Đặt ngay về `0` điểm.

### 8.2. Ngưỡng Hành Động (Thresholds)
* **`Score < 20`**: Tự động vô hiệu hóa hoạt động của tài khoản (Set `auto_disabled = 1`), ghi lý do tự động khóa và gửi cảnh báo tới quản trị viên.
* **`Score từ 20 đến 40`**: Nhân đôi thời gian giãn cách tối thiểu giữa các bài đăng (`2x delay`).
* **`Score từ 70 đến 100`**: Tài khoản hoạt động ổn định, có thể rút ngắn thời gian giãn cách xuống còn `0.8x`.

### 8.3. Triển Khai JavaScript Callback `health_score.js`

Hệ thống loại bỏ hoàn toàn các cơ chế SQL triggers chạy ngầm trong SQLite để tránh xung đột luồng và khóa tệp tin cơ sở dữ liệu. Tất cả các tính toán được thực thi thông qua module JavaScript đồng bộ:

```javascript
// health_score.js
'use strict';

function calculateHealthScore(accountId, db) {
  const account = db.prepare('SELECT * FROM accounts WHERE id = ?').get(accountId);
  if (!account) return 0;

  if (['DIE', 'LOCKED', 'BANNED'].includes(account.status)) return 0;
  if (account.status === 'CHECKPOINT') return 20;

  let score = 100;

  // Trừ điểm checkpoint 7 ngày qua
  const checkpoints7d = db.prepare(`
    SELECT COUNT(*) as cnt FROM account_events
    WHERE account_id = ?
      AND event_type LIKE 'CHECKPOINT_%'
      AND created_at > datetime('now', '-7 days')
  `).get(accountId)?.cnt || 0;
  score -= Math.min(checkpoints7d * 10, 40);

  // Trừ điểm cooldown 30 ngày qua
  const cooldownEvents = db.prepare(`
    SELECT COUNT(*) as cnt FROM account_events
    WHERE account_id = ? AND event_type = 'CHECKPOINT_COOLDOWN'
      AND created_at > datetime('now', '-30 days')
  `).get(accountId)?.cnt || 0;
  score -= Math.min(cooldownEvents * 5, 20);

  // Trừ điểm Policy warning
  const policyWarnings = db.prepare(`
    SELECT COUNT(*) as cnt FROM account_events
    WHERE account_id = ? AND event_type = 'POLICY_WARNING'
      AND created_at > datetime('now', '-30 days')
  `).get(accountId)?.cnt || 0;
  score -= Math.min(policyWarnings * 3, 15);

  // Cộng điểm đăng bài thành công
  const successPosts = db.prepare(`
    SELECT COUNT(*) as cnt FROM posting_logs
    WHERE account_id = ? AND event_type = 'POST_SUCCESS'
  `).get(accountId)?.cnt || 0;
  score += Math.min(successPosts * 2, 30);

  // Cộng điểm khoảng nghỉ đủ
  const adequateRests = db.prepare(`
    SELECT COUNT(*) as cnt FROM post_intervals
    WHERE account_id = ? AND interval_minutes >= 5
      AND posted_at > datetime('now', '-24 hours')
  `).get(accountId)?.cnt || 0;
  score += Math.min(adequateRests, 10);

  // Cộng điểm hoạt động ổn định liên tục
  const lastIssue = db.prepare(`
    SELECT MAX(created_at) as ts FROM account_events
    WHERE account_id = ? AND event_type NOT LIKE 'POST_%'
  `).get(accountId)?.ts;
  if (lastIssue) {
    const hoursSince = (Date.now() - new Date(lastIssue).getTime()) / 3600000;
    const bonus72h = Math.min(Math.floor(hoursSince / 72) * 5, 20);
    score += bonus72h;
  }

  if (account.auto_disabled) score -= 30;

  return Math.max(0, Math.min(100, Math.round(score)));
}

function updateHealthScore(accountId, db) {
  const newScore = calculateHealthScore(accountId, db);
  const account = db.prepare('SELECT health_score, auto_disabled FROM accounts WHERE id = ?').get(accountId);
  if (!account) return;

  db.prepare('UPDATE accounts SET health_score = ? WHERE id = ?').run(newScore, accountId);

  // Kích hoạt auto-disable nếu sức khỏe dưới ngưỡng
  if (newScore < 20 && !account.auto_disabled) {
    db.prepare(`
      UPDATE accounts
      SET auto_disabled = 1,
          auto_disabled_reason = 'Health score fell below threshold 20',
          auto_disabled_at = datetime('now')
      WHERE id = ?
    `).run(accountId);

    db.prepare(`
      INSERT INTO account_events (account_id, event_type, event_data, severity, created_at)
      VALUES (?, 'AUTO_DISABLED', ?, 'FATAL', datetime('now'))
    `).run(accountId, JSON.stringify({ health_score: newScore, threshold: 20 }));
  }

  return newScore;
}

module.exports = { calculateHealthScore, updateHealthScore };
```

---

## 9. Chế Độ Giãn Cách Thích Nghi (Adaptive Rate Limiting)

Hệ thống tính toán thời gian trễ động dựa trên chỉ số nhân phạt tích lũy (`penalty_multiplier`) của từng tài khoản.

### 9.1. Công Thức Tính Thời Gian Giãn Cách
$$\text{Delay} = \text{Base Delay} \times (0.8 + \text{random}() \times 0.7) \times \text{Penalty Multiplier}$$
* **Base Delay:** Mặc định là 300 giây (5 phút).
* **Penalty Multiplier:** Khởi điểm từ `1.0`. Cộng thêm `0.5` cho mỗi lần gặp checkpoint trong vòng 24 giờ qua (Tối đa `4.0`). Giá trị này sẽ tự động reset về `1.0` nếu tài khoản không gặp sự cố trong vòng 72 giờ liên tục.
* **Giới hạn thời gian trễ:** Clamping trong khoảng từ `300 giây` (5 phút) đến `3600 giây` (1 giờ).

### 9.2. Khung Giờ Đăng Bài An Toàn
Facebook thường quét tự động theo lô vào các khung giờ cụ thể. Thuật toán lên lịch (Scheduler) sẽ tránh đăng bài vào các giờ cao điểm kiểm duyệt:
* **Khung giờ nguy hiểm cao:** `00:00 - 06:00` (Hệ thống Facebook thực thi các tác vụ bảo trì và quét spam tự động).
* **Khung giờ nguy hiểm trung bình:** `12:00 - 13:00` (Khung giờ lượng người dùng truy cập cao, các mô hình học máy phát hiện spam của Facebook hoạt động với công suất cao nhất).
* **Khung giờ an toàn đề xuất:** `07:00 - 11:30` và `14:00 - 21:00`.

---

## 10. Cấu Trúc Cơ Sở Dữ Liệu SQLite (Database Extensions)

Bổ sung các bảng ghi nhận sự kiện và các cột trạng thái vào cơ sở dữ liệu SQLite:

```sql
-- Thêm các cột quản lý trạng thái checkpoint vào bảng accounts
ALTER TABLE accounts ADD COLUMN cooldown_until TEXT DEFAULT NULL;
ALTER TABLE accounts ADD COLUMN checkpoint_count_7d INTEGER DEFAULT 0;
ALTER TABLE accounts ADD COLUMN health_score REAL DEFAULT 100.0;
ALTER TABLE accounts ADD COLUMN auto_disabled INTEGER DEFAULT 0;
ALTER TABLE accounts ADD COLUMN auto_disabled_reason TEXT DEFAULT NULL;
ALTER TABLE accounts ADD COLUMN auto_disabled_at TEXT DEFAULT NULL;
ALTER TABLE accounts ADD COLUMN penalty_multiplier REAL DEFAULT 1.0;
ALTER TABLE accounts ADD COLUMN last_checkpoint_at TEXT DEFAULT NULL;
ALTER TABLE accounts ADD COLUMN checkpoint_metadata TEXT DEFAULT NULL;

-- Bảng lưu trữ lịch sử sự kiện bảo mật tài khoản
CREATE TABLE IF NOT EXISTS account_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id INTEGER NOT NULL,
  event_type TEXT NOT NULL,
  event_data TEXT DEFAULT '{}',
  error_code TEXT,
  severity TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_account_events_account_id ON account_events(account_id);
CREATE INDEX IF NOT EXISTS idx_account_events_type ON account_events(event_type);
CREATE INDEX IF NOT EXISTS idx_account_events_created_at ON account_events(created_at);

-- Bảng ghi nhận khoảng cách đăng bài để tính toán health score
CREATE TABLE IF NOT EXISTS post_intervals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id INTEGER NOT NULL,
  group_id INTEGER,
  posted_at TEXT NOT NULL,
  interval_minutes REAL,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_post_intervals_account_id ON post_intervals(account_id);
CREATE INDEX IF NOT EXISTS idx_post_intervals_posted_at ON post_intervals(posted_at);
```

---

## 11. Tích Hợp Phiên Làm Việc (Session FSM Integration)

Quy trình tích hợp logic phát hiện checkpoint trực quan (Visual check) và xử lý Sleep & Hibernate vào vòng lặp hữu hạn của máy trạng thái Session (Session FSM):

```javascript
// session_fsm.js
const { updateHealthScore } = require('./health_score');
const { detect } = require('./checkpoint_detector');

function insertAccountEvent(db, { accountId, eventType, eventData, errorCode, severity }) {
  db.prepare(`
    INSERT INTO account_events (account_id, event_type, event_data, error_code, severity, created_at)
    VALUES (?, ?, ?, ?, ?, datetime('now'))
  `).run(accountId, eventType, eventData || '{}', errorCode || null, severity || 'INFO');

  // Kích hoạt callback cập nhật điểm số sức khỏe tức thời
  updateHealthScore(accountId, db);
}

async function runSessionStep(session, pageDriver, db) {
  // 1. Lấy thông tin DOM snapshot dạng JSON từ trình duyệt
  const domSnapshot = await pageDriver.getDomSnapshot();
  
  // 2. Thực hiện quét cấu trúc DOM thô để tìm dấu hiệu checkpoint
  let checkResult = detect(domSnapshot);

  // 3. Nếu nghi ngờ có checkpoint nhưng độ tin cậy thấp, kích hoạt Visual Check
  if (checkResult.detected && checkResult.confidence < 0.85) {
    console.log(`[SessionFSM] Low confidence (${checkResult.confidence}) detected. Activating Visual Check...`);
    const screenshotPath = await captureVisualContext(pageDriver, session.accountId);
    
    // Gọi API AI Multimodal Vision để chẩn đoán trực quan hình ảnh
    const visualDiagnosis = await callMultimodalVisionAPI(screenshotPath, domSnapshot);
    if (visualDiagnosis.checkpointDetected) {
      checkResult = {
        detected: true,
        type: visualDiagnosis.checkpointType,
        confidence: visualDiagnosis.confidence,
        canAutoHandle: visualDiagnosis.checkpointType === 'CHK_POLICY_WARNING',
        metadata: {
          url: domSnapshot.url,
          timestamp: Date.now(),
          visualElements: visualDiagnosis.visualElements
        }
      };
    }
  }

  if (!checkResult.detected) {
    return { continue: true };
  }

  // Phân loại mã lỗi
  const errorCodeMap = {
    CHK_PHONE_OTP: 'ERR-CHK-09',
    CHK_CAPTCHA: 'ERR-CHK-10',
    CHK_PHOTO_IDENTITY: 'ERR-CHK-11',
    CHK_COOLDOWN: 'ERR-CHK-12',
    CHK_TRUSTED_CONTACTS: 'ERR-CHK-09',
    CHK_VIDEO_SELFIE: 'ERR-CHK-09',
    CHK_BEHAVIORAL: 'ERR-CHK-09',
    CHK_POLICY_WARNING: 'ERR-ACT-15',
  };

  const errorCode = errorCodeMap[checkResult.type] || 'ERR-CHK-09';
  const severity = checkResult.type === 'CHK_POLICY_WARNING' ? 'RECOVERABLE' : 'FATAL';

  // Lưu thông tin sự kiện và cập nhật metadata vào accounts
  db.prepare(`
    UPDATE accounts 
    SET checkpoint_metadata = ? 
    WHERE id = ?
  `).run(JSON.stringify(checkResult.metadata), session.accountId);

  insertAccountEvent(db, {
    accountId: session.accountId,
    eventType: checkResult.type,
    eventData: JSON.stringify(checkResult.metadata),
    errorCode,
    severity
  });

  // Xử lý tự động đối với các lỗi nhẹ
  if (checkResult.canAutoHandle) {
    if (checkResult.type === 'CHK_COOLDOWN') {
      await handleCooldown(session.accountId, checkResult, db);
      return { continue: false, reason: 'COOLDOWN' };
    }
    if (checkResult.type === 'CHK_POLICY_WARNING') {
      const handler = new CheckpointAutoHandler({ pageDriver });
      await handler.handlePolicyWarning(session.accountId, checkResult);
      return { continue: true, additionalDelayMs: 5 * 60 * 1000 };
    }
  }

  // ─── CHẾ ĐỘ SLEEP & HIBERNATE CHO CHECKPOINT NGHIÊM TRỌNG ───
  const hardCheckpoints = ['CHK_PHONE_OTP', 'CHK_VIDEO_SELFIE', 'CHK_PHOTO_IDENTITY', 'CHK_TRUSTED_CONTACTS', 'CHK_BEHAVIORAL'];
  
  if (hardCheckpoints.includes(checkResult.type)) {
    console.log(`[Hibernate] Hard checkpoint detected (${checkResult.type}). Activating Sleep & Hibernate.`);
    
    // Ngắt kết nối tiến trình Chrome ngay lập tức để bảo vệ phiên làm việc và giải phóng luồng
    await pageDriver.killChromeProcess(session.accountId);
    
    db.prepare(`
      UPDATE accounts 
      SET status = 'HIBERNATE_AWAITING_MANUAL'
      WHERE id = ?
    `).run(session.accountId);

    // Gửi tín hiệu WebSocket cảnh báo tới Dashboard UI
    await broadcastCheckpointAlert(session, checkResult);

    return { 
      continue: false, 
      reason: 'HIBERNATE_AWAITING_MANUAL',
      message: `Chrome process killed. Session hibernation active for account ${session.accountId}.`
    };
  }

  // Các trường hợp khác đưa về trạng thái chờ xử lý truyền thống
  db.prepare(`UPDATE accounts SET status = 'AWAITING_MANUAL' WHERE id = ?`).run(session.accountId);
  await broadcastCheckpointAlert(session, checkResult);

  return { continue: false, reason: 'AWAITING_MANUAL' };
}
```

### 11.1. Cổng Phục Hồi Lại Tiến Trình (Re-spawn & Recovery Protocol)
Khi quản trị viên click vào nút "Xử lý Checkpoint" trên giao diện điều khiển (Dashboard):
1. Gửi request POST tới `/api/checkpoint/respawn`.
2. Hệ thống gọi phương thức để khởi chạy lại Chrome: `await pageDriver.spawnChromeProcess(accountId)`.
3. Tự động phục hồi lại chính xác địa chỉ IP của proxy được sử dụng trước đó (Sticky IP) và các cấu hình Device Fingerprint để tránh bị Facebook quét nghi ngờ thiết bị mới.
4. Trình duyệt tự động mở tab điều hướng tới URL checkpoint đã ghi nhận trong `checkpoint_metadata`.
5. Người dùng tương tác trực tiếp giải quyết thử thách bảo mật trên giao diện headless/headed.
6. Khi hoàn tất, người dùng xác nhận trên giao diện. Hệ thống sẽ kích hoạt **Logic bảo vệ chống Bão Checkpoint** (Enforce Checkpoint Storm Cooldown 12-24h), ghi nhận thời gian cooldown vào SQLite, và thực hiện ngắt (kill) Chrome process ngay lập tức để đưa tài khoản vào trạng thái nghỉ dưỡng sức khỏe.

---

*Document Version: 2.1.0 | Specification for visual checkpoint handling | Author: Spec Team*
