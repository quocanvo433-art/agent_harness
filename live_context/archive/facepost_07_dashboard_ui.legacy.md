# 📊 Hermes FacePost-Group — Đặc Tả Thiết Kế Giao Diện Dashboard (Spec 07)

**Version:** 2.1.0 (Post-Audit)
**Status:** ACTIVE
**Updated:** 2026-06-16

Tài liệu này đặc tả chi tiết giao diện người dùng (UI/UX) của Dashboard điều phối và quản lý chiến dịch Hermes FacePost-Group. Thiết kế hướng tới trải nghiệm "Futuristic Clean / Cyber-Office" trực quan, to rõ, nịnh mắt, màu trung tính pha neon sáng và hỗ trợ truyền tải trạng thái hoạt động theo thời gian thực (Live-stream/Real-time reporting).

---

## 🎨 1. Ngôn Ngữ Thiết Kế (Design Language)

Hệ thống sử dụng các mảng màu nền trung tính cực kỳ dịu mắt, kết hợp với các dải màu neon rực rỡ để nhấn mạnh trạng thái "sống" (Live) của các AI Agent và phân biệt các cảnh báo lỗi.

### 1.1 Màu sắc chủ đạo (Color Palette)
- **Nền tổng thể (Base Palette):** Sử dụng các tone màu Slate/Zinc (Xám đá/Xám kẽm) từ nhạt đến đậm làm nền. Tránh dùng màu đen thuần túy để không bị tối và mỏi mắt.
  - Nền ứng dụng chính: `bg-zinc-950` (#09090b)
  - Nền các Card/Component: `bg-zinc-900/30` hoặc `bg-zinc-900/40` với hiệu ứng `backdrop-blur-md`
  - Viền cấu trúc: `border-zinc-800`
- **Dải màu Neon nhấn mạnh trạng thái (Accent Neon Palette):**
  - 🟢 **Emerald Green (Xanh lục bảo):** `#10b981`. Thể hiện trạng thái `SUCCESS` hoặc tài khoản có điểm sức khỏe tốt (`HP >= 70`).
  - 🔵 **Electric Cyan (Xanh neon hoàng gia):** `#06b6d4`. Thể hiện trạng thái `AI_THINK` (AI đang suy luận phân tích DOM).
  - 🟣 **Electric Blue (Xanh lam neon):** `#3b82f6`. Thể hiện trạng thái `ACTING` hoặc `WAIT_ACTION_RESULT` (Đang tương tác DOM hoặc chờ kết quả).
  - 🟡 **Safety Amber (Vàng hổ phách):** `#f59e0b`. Thể hiện trạng thái `WAIT` / `RETRY` hoặc Cảnh báo cần chú ý.
  - 🔴 **Crimson Red (Đỏ thẫm):** `#f43f5e`. Thể hiện trạng thái `CHECKPOINT_DETECTED`, `FAILED` hoặc Lỗi hệ thống.
  - 🟠 **Safety Orange (Cam cảnh báo):** `#f97316`. Thể hiện trạng thái `SEARCH_FAILED` (Lỗi không tìm thấy nhóm hoặc lỗi tìm kiếm khác), cần nổi bật để thu hút chú ý của user để xử lý thủ công.

### 1.2 Hiệu ứng thị giác (UX Feel)
- **Glassmorphism:** Sử dụng nền mờ đục nhẹ (`backdrop-blur-md`), viền mỏng sắc nét (`border border-zinc-800/80`) và đổ bóng đổ chìm sâu để tạo chiều sâu giao diện.
- **Micro-Animations:**
  - Hiệu ứng thở phát sáng (`pulse-glow`) xung quanh viền các Card khi AI đang suy nghĩ.
  - Biểu tượng chấm trạng thái nhấp nháy (`animate-ping`) khi luồng đăng đang hoạt động.
  - Hiệu ứng di chuột (hover transition) mượt mà làm sáng nhẹ nền card và nổi bật viền.
- **Typography:** Font chữ không chân to rõ ràng (`font-sans` như Inter, Outfit), font chữ đơn cách (`font-mono`) cho logs, thông số kỹ thuật và terminal.

---

## 🏛️ 2. Bố Cục Tổng Thể (Dashboard Layout Framework)

Giao diện được chia thành 3 phân vùng chính cố định trên một màn hình view (Không cuộn trang tổng thể, chỉ cuộn nội dung riêng trong từng phân vùng).

```
+------------------------------------------------------------------------------------+
|  [Logo] HERMES-OS  |  Global Stats: 5 Active Agents | 120 Posts Today | [Status Bar] |
+---------------------+--------------------------------------------------------------+
|                     |                                                              |
|                     |  MAIN VIEW: CONSOLE LIVE-STREAM & REPORTING                  |
|  SIDEBAR            |  +--------------------------------------------------------+  |
|  - OverView (Live)  |  | [Component 1: LiveAgentGrid]                           |  |
|  - Campaigns        |  | Thẻ Worker to rõ, nhấp nháy theo State Machine         |  |
|  - Accounts & Proxy |  +--------------------------------------------------------+  |
|                     |  | [Component 2: AccountHealthAnalytics]                  |  |
|                     |  | Biểu đồ cột + Vòng tròn Gauge điểm sức khỏe            |  |
|                     |  +--------------------------------------------------------+  |
|                     |                                                              |
+---------------------+--------------------------------------------------------------+
| [Component 3: RealtimeLogTerminal] -> Dòng log SSE chảy liên tục nhảy chữ màu neon  |
+------------------------------------------------------------------------------------+
```

- **Header:** Cố định ở đỉnh màn hình (chiều cao 64px), hiển thị logo dự án, trạng thái chung của socket server, tổng số Agent đang hoạt động và số bài viết đăng thành công trong ngày.
- **Sidebar:** Chiều rộng cố định 260px ở bên trái, chứa menu chuyển đổi giữa các tab: Live Console, Campaigns, Accounts & Proxy, **⚙️ Settings** (gồm sub-tab: 🔑 API Keys, 🛡️ Sao lưu, 💻 Hệ thống), và tab **☕ Ủng hộ Cà Phê (Donate)**.
- **Main View Area:** Phần hiển thị nội dung chính bên phải, chiếm phần còn lại của màn hình, tự động co giãn.
- **Realtime Log Terminal:** Cố định ở đáy màn hình (chiều cao 220px), cuộn tự động hiển thị dòng chảy nhật ký hệ thống.

---

## 📦 3. Các React Components Cốt Lõi (Mã Mẫu & Đặc Tả)

### 3.1 Component `<LiveAgentGrid />` & `<AgentCard />`
Đây là linh hồn của Dashboard, thực hiện việc stream trạng thái và hành động tương tác DOM của AI Agent theo thời gian thực từ WebSocket server.

#### Layout Wireframe
```
+--------------------------------------------+
| 👤 ACCOUNT: Nguyen Van A    [ Score: 85 ]  |  <-- Avatar, Tên profile, Điểm HP
| Proxy: 127.0.0.1:8001 | Group: J2TEAM      |  <-- Cấu hình proxy & Group hiện tại
| +----------------------------------------+ |
| | STATE: ● AI_THINK                      | |  <-- State Machine badge (Neon Cyan)
| +----------------------------------------+ |
| [🤖 Brain]: Đang đọc DOM nén, nhận diện  | |  <-- Action description box
|  nút "Viết bài" để tạo hành động click...| |
| ---------------------------------------- |
| Stats: 🟢 14 Đăng | 🔴 0 Lỗi | ⏱️ 45s       |  <-- Metrics chân trang
+--------------------------------------------+
```

#### React Component Specification
```jsx
import React, { memo } from 'react';

// Sử dụng React.memo để chặn re-render không cần thiết nếu dữ liệu session không đổi
const AgentCard = memo(({ session }) => {
  const { accountId, accountName, proxy, currentGroup, currentState, lastActionDesc, metrics, healthScore } = session;

  // Bản đồ màu sắc và hiệu ứng phát sáng tương ứng với FSM State
  const stateThemeMap = {
    'INIT': 'border-zinc-800 text-zinc-500 bg-zinc-900/10',
    'NAVIGATING': 'border-blue-500/30 text-blue-400 shadow-[0_0_10px_rgba(59,130,246,0.1)]',
    'OBSERVING': 'border-zinc-700 text-zinc-300',
    'AI_THINK': 'border-cyan-500/50 text-cyan-400 shadow-[0_0_15px_rgba(6,182,212,0.15)] animate-pulse',
    'ACTING': 'border-blue-500/50 text-blue-400 shadow-[0_0_15px_rgba(59,130,246,0.15)]',
    'WAIT_ACTION_RESULT': 'border-amber-500/30 text-amber-400',
    'VERIFYING': 'border-purple-500/40 text-purple-400',
    'SUCCESS': 'border-emerald-500/50 text-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.1)]',
    'CHECKPOINT_DETECTED': 'border-rose-500 text-rose-400 shadow-[0_0_20px_rgba(244,63,94,0.2)] bg-rose-950/10 animate-pulse',
    'SEARCH_FAILED': 'border-orange-500 text-orange-400 shadow-[0_0_20px_rgba(249,115,22,0.2)] bg-orange-950/10 animate-pulse',
    'FAILED': 'border-zinc-800 text-zinc-600 bg-zinc-950/20'
  };

  const currentTheme = stateThemeMap[currentState] || 'border-zinc-800 text-zinc-400';

  const getHealthColor = (score) => {
    if (score >= 70) return 'text-emerald-400 border-emerald-500/30';
    if (score >= 40) return 'text-amber-400 border-amber-500/30';
    return 'text-rose-400 border-rose-500/30 animate-pulse';
  };

  return (
    <div className={`p-6 border rounded-2xl bg-zinc-900/30 backdrop-blur-md transition-all duration-300 flex flex-col justify-between h-[280px] ${currentTheme}`}>
      <div>
        {/* Header card: Account Name & Health Score */}
        <div className="flex justify-between items-start mb-2">
          <div>
            <h3 className="text-lg font-bold text-zinc-100 tracking-tight">{accountName}</h3>
            <p className="text-xs text-zinc-500 font-mono mt-0.5">🌐 Proxy: {proxy || 'Direct'}</p>
          </div>
          <div className="text-right">
            <span className={`text-xs font-mono font-bold px-2.5 py-1 bg-zinc-950 rounded-md border ${getHealthColor(healthScore)}`}>
              HP: {healthScore}
            </span>
          </div>
        </div>

        <p className="text-xs text-zinc-400 font-medium mb-3">
          📍 Đang tương tác: <span className="text-zinc-200 font-semibold">{currentGroup || 'Chưa chạy'}</span>
        </p>

        {/* Trạng thái FSM của Agent Loop */}
        <div className="mb-3">
          <div className="text-[10px] font-bold uppercase tracking-wider text-zinc-500 mb-1">Trạng thái FSM</div>
          <div className="flex items-center text-sm font-mono font-bold tracking-wide">
            <span className="w-2 h-2 rounded-full bg-current mr-2 animate-ping" />
            {currentState}
          </div>
        </div>
      </div>

      {/* Dòng text mô tả chi tiết hành vi AI đang thực hiện */}
      <div>
        <div className="w-full bg-black/40 border border-zinc-800/80 rounded-xl p-3 min-h-[64px] flex items-center mb-3">
          <p className="text-xs font-mono text-zinc-300 leading-relaxed w-full break-words line-clamp-2">
            <span className="text-zinc-600 mr-1.5">&gt;</span>
            {lastActionDesc || 'Đang chờ điều hành phân bổ tác vụ...'}
          </p>
        </div>

        {/* Chân card: Thống kê mini */}
        <div className="flex justify-between items-center pt-2 border-t border-zinc-800/60 text-[11px] font-mono text-zinc-500">
          <div>🟢 <span className="text-zinc-300 font-bold">{metrics.successCount}</span> Đăng</div>
          <div>🔴 <span className="text-zinc-300 font-bold">{metrics.failedCount}</span> Lỗi</div>
          <div className="text-zinc-400">⏱️ {metrics.elapsedTime}s</div>
        </div>
      </div>
    </div>
  );
});

export default AgentCard;
```

---

### 3.2 Component `<AccountHealthGauge />`
Gauge báo cáo hiệu năng tích hợp chỉ số thích nghi. Đồng hồ hiển thị điểm số sức khỏe tài khoản, hỗ trợ trực quan hóa mức độ rủi ro của từng Facebook profile.

#### React Component Specification
```jsx
import React from 'react';

const AccountHealthGauge = ({ score }) => {
  // Tính toán chu vi hình tròn cho dashoffset
  const radius = 50;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  const getGaugeColors = (score) => {
    if (score >= 70) return { stroke: '#10b981', bg: 'bg-emerald-500/10', text: 'text-emerald-400', label: 'HEALTHY' };
    if (score >= 40) return { stroke: '#f59e0b', bg: 'bg-amber-500/10', text: 'text-amber-400', label: 'WARMED / DELAY X2' };
    return { stroke: '#f43f5e', bg: 'bg-rose-500/10', text: 'text-rose-400 animate-pulse', label: 'CRITICAL / STOP' };
  };

  const theme = getGaugeColors(score);

  return (
    <div className="flex flex-col items-center p-6 border border-zinc-800 rounded-2xl bg-zinc-900/20 backdrop-blur-md w-[220px]">
      <div className="relative flex items-center justify-center w-32 h-32">
        <svg className="transform -rotate-90 w-full h-full">
          {/* Vòng nền xám */}
          <circle
            cx="64"
            cy="64"
            r={radius}
            stroke="#27272a"
            strokeWidth="8"
            fill="transparent"
          />
          {/* Vòng màu chỉ số sức khỏe */}
          <circle
            cx="64"
            cy="64"
            r={radius}
            stroke={theme.stroke}
            strokeWidth="8"
            fill="transparent"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            className="transition-all duration-500 ease-out"
          />
        </svg>
        <div className="absolute flex flex-col items-center justify-center">
          <span className="text-3xl font-extrabold text-white tracking-tight">{score}</span>
          <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest mt-0.5">SCORE</span>
        </div>
      </div>
      <div className={`mt-4 px-3 py-1 rounded-full text-[10px] font-extrabold tracking-wider border border-zinc-800 ${theme.bg} ${theme.text}`}>
        {theme.label}
      </div>
    </div>
  );
};

export default AccountHealthGauge;
```

### 3.3 Component `<EmergencyEscalationGateway />`
Component thông báo khẩn cấp (Overlay Modal) khi hệ thống phát hiện các lỗi rủi ro bảo mật, deadlock hoặc checkpoint nặng (Tier 3 Escalation). Cung cấp hành lang tương tác và phê duyệt bắt buộc cho Người dùng để chống ảo giác tự trị của AI.

#### Layout Wireframe
```
+------------------------------------------------------------+
| 🚨 HÀNH LANG PHÊ DUYỆT KHẨN CẤP (TIER 3)                   |
+------------------------------------------------------------+
| Loại sự cố: [ RỦI RO BẢO MẬT - ERR-ESC-21 ]                |
| Nick ảnh hưởng: [ Nick A (ID: 123456) ]                    |
| Chi tiết: MutationObserver phát hiện bypass UI lách Donate |
|                                                            |
| +--------------------------------------------------------+ |
| | Nhập Mã Xác Thực Admin / OTP Phần Cứng để Mở Khóa:     | |
| | [____________________________________________________] | |
| +--------------------------------------------------------+ |
|                                                            |
| +-------------------------+     +------------------------+ |
| | ❌ REJECT (Tắt Luồng)   |     | ✅ APPROVE (Cho Chạy)  | |
| +-------------------------+     +------------------------+ |
+------------------------------------------------------------+
```

#### React Component Specification
```jsx
import React, { useState } from 'react';

const EmergencyEscalationGateway = ({ isOpen, escalationData, onApprove, onReject, onRestoreBackup, onOpenChrome }) => {
  if (!isOpen) return null;

  const { accountId, accountName, errorCode, errorDetail, detectedAt, logDiagnostic } = escalationData;
  const [adminToken, setAdminToken] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Xác định màu sắc chủ đạo theo mã lỗi
  const getThemeConfig = (code) => {
    switch (code) {
      case 'ERR-ESC-21': // Rủi ro bảo mật
        return {
          title: '🚨 PHÁT HIỆN RỦI RO BẢO MẬT NGHIÊM TRỌNG',
          borderColor: 'border-red-500/40',
          shadowColor: 'shadow-[0_0_50px_rgba(239,68,68,0.25)]',
          badgeColor: 'text-red-400 bg-red-950/30 border-red-500/20',
          bgColor: 'bg-red-950/10'
        };
      case 'ERR-ESC-22': // FSM Deadlock
        return {
          title: '🤖 LEO THANG LÊN LEADER AI CHẨN ĐOÁN',
          borderColor: 'border-amber-500/40',
          shadowColor: 'shadow-[0_0_50px_rgba(245,158,11,0.2)]',
          badgeColor: 'text-amber-400 bg-amber-950/30 border-amber-500/20',
          bgColor: 'bg-amber-950/10'
        };
      case 'ERR-ESC-24': // DB / OTA hỏng
        return {
          title: '💥 SỰ CỐ HỆ THỐNG NẶNG - ĐANG CHẠY SAFE MODE',
          borderColor: 'border-orange-500/40',
          shadowColor: 'shadow-[0_0_50px_rgba(249,115,22,0.2)]',
          badgeColor: 'text-orange-400 bg-orange-950/30 border-orange-500/20',
          bgColor: 'bg-orange-950/10'
        };
      case 'ERR-ESC-23': // Checkpoint FB khó
      default:
        return {
          title: '⚠️ YÊU CẦU PHÊ DUYỆT PHỤC HỒI CHECKPOINT',
          borderColor: 'border-rose-500/30',
          shadowColor: 'shadow-[0_0_50px_rgba(244,63,94,0.15)]',
          badgeColor: 'text-rose-300 bg-rose-950/30 border-rose-500/20',
          bgColor: 'bg-zinc-950'
        };
    }
  };

  const theme = getThemeConfig(errorCode);

  const handleApproveSubmit = async () => {
    setIsSubmitting(true);
    await onApprove(accountId, errorCode, adminToken);
    setIsSubmitting(false);
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/90 backdrop-blur-md p-4">
      <div className={`w-full max-w-lg border rounded-2xl bg-zinc-950 ${theme.borderColor} ${theme.shadowColor} overflow-hidden transition-all duration-300`}>
        {/* Banner tiêu đề phát sáng nhấp nháy */}
        <div className={`border-b px-6 py-4 flex justify-between items-center ${theme.borderColor} ${theme.bgColor}`}>
          <div className="flex items-center text-white font-extrabold text-sm uppercase tracking-wider gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-orange-500 animate-ping" />
            {theme.title}
          </div>
          <span className="text-xs text-zinc-500 font-mono">{detectedAt}</span>
        </div>

        {/* Thông tin chẩn đoán */}
        <div className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-xs text-zinc-500 uppercase font-bold tracking-wider">Tài khoản ảnh hưởng</div>
              <div className="text-sm font-bold text-white mt-0.5">{accountName || 'Hệ thống'}</div>
            </div>
            <div>
              <div className="text-xs text-zinc-500 uppercase font-bold tracking-wider">Mã Sự Cố</div>
              <div className={`text-xs font-mono font-bold px-2 py-0.5 rounded border inline-block mt-0.5 ${theme.badgeColor}`}>
                {errorCode}
              </div>
            </div>
          </div>

          <div>
            <div className="text-xs text-zinc-500 uppercase font-bold tracking-wider mb-1">Mô tả chi tiết</div>
            <p className="text-xs text-zinc-400 bg-zinc-900/50 p-3 rounded-lg border border-zinc-800 leading-relaxed font-mono">
              {errorDetail}
            </p>
          </div>

          {/* Form nhập token duyệt - Chỉ hiện cho lỗi bảo mật ERR-ESC-21 */}
          {errorCode === 'ERR-ESC-21' && (
            <div className="space-y-1.5 p-4 rounded-xl border border-red-500/20 bg-red-950/5">
              <label className="text-xs text-red-300 font-bold uppercase tracking-wide">Nhập Mã OTP Phần Cứng / Password Admin:</label>
              <input
                type="password"
                value={adminToken}
                onChange={(e) => setAdminToken(e.target.value)}
                placeholder="Nhập mã xác thực để bypass cứng..."
                className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-red-500 font-mono"
              />
            </div>
          )}

          {/* Terminal chẩn đoán FSM cho FSM Deadlock ERR-ESC-22 */}
          {errorCode === 'ERR-ESC-22' && logDiagnostic && (
            <div className="space-y-1 bg-black/60 p-3 rounded-lg border border-zinc-800 font-mono text-[10px] text-emerald-400 overflow-y-auto max-h-32">
              <div className="text-zinc-500 border-b border-zinc-900 pb-1 mb-1 font-bold">📋 DIAGNOSTIC STACK:</div>
              {logDiagnostic.map((log, idx) => <div key={idx}>{log}</div>)}
            </div>
          )}

          {/* Hướng dẫn quy trình xử lý checkpoint cho ERR-ESC-23 */}
          {errorCode === 'ERR-ESC-23' && (
            <div className="text-xs text-zinc-400 leading-relaxed space-y-2 bg-zinc-900/30 p-3 rounded-xl border border-zinc-800">
              <div className="font-bold text-zinc-300 mb-0.5">📋 Quy trình phục hồi:</div>
              <div>1. Nhấn nút <strong className="text-white">🖥️ Mở Trình Duyệt</strong> để spawn Chrome headed điều khiển tay.</div>
              <div>2. Nhập mã OTP/Captcha trên cửa sổ đó.</div>
              <div>3. Sau khi Facebook về tin nhắn newsfeed, quay lại đây nhấn <strong className="text-white">✅ Xác Nhận (Approve)</strong>.</div>
            </div>
          )}
        </div>

        {/* Thanh công cụ hành động phân quyền */}
        <div className="bg-zinc-900/40 px-6 py-4 border-t border-zinc-800 flex justify-end gap-3">
          <button
            onClick={() => onDismiss(accountId)}
            className="px-4 py-2 border border-zinc-800 rounded-xl text-zinc-400 font-medium hover:text-white hover:bg-zinc-900 transition-colors"
          >
            Bỏ qua
          </button>
          
          <button
            onClick={() => onOpenTab(accountId)}
            className="px-4 py-2 bg-zinc-900 border border-zinc-700 hover:border-zinc-500 rounded-xl text-white font-semibold flex items-center gap-1.5 transition-all"
          >
            🖥️ Mở Cửa Sổ Chrome
          </button>

          <button
            onClick={() => onConfirmResolved(accountId)}
            className="px-5 py-2 bg-emerald-500 text-black font-extrabold rounded-xl hover:bg-emerald-400 flex items-center gap-1.5 transition-all shadow-[0_0_15px_rgba(16,185,129,0.2)]"
          >
            ✅ Xác Nhận Đã Giải
          </button>
        </div>
      </div>
    </div>
  );
};

export default CheckpointManualIntervention;
```

---

### 3.4 Component `<RealtimeLogTerminal />`
Thanh Terminal cuộn thời gian thực nhận logs từ Server-Sent Events (SSE). Bắt buộc tích hợp buffer render để chống nghẽn nghẹt FPS.

#### React Component Specification
```jsx
import React, { useEffect, useRef, useState, useCallback } from 'react';
 
const RealtimeLogTerminal = ({ onManualIntervene }) => {
  const [logs, setLogs] = useState([]);
  const terminalEndRef = useRef(null);
  
  // Sử dụng useRef buffer để gom góp log tránh re-render quá nhanh
  const logBufferRef = useRef([]);
  const scrollLockedRef = useRef(false); // Cho phép user cuộn lên để xem log mà không bị kéo xuống liên tục

  useEffect(() => {
    // 1. Lắng nghe Server-Sent Events
    const eventSource = new EventSource('/api/logs/stream');

    eventSource.onmessage = (event) => {
      const logData = JSON.parse(event.data); // Format: { ts, level, accountId, accountName, message, errCode }
      logBufferRef.current.push(logData);
    };

    // 2. Kích hoạt bộ đệm cập nhật định kỳ 300ms (Throttling Render)
    const renderInterval = setInterval(() => {
      if (logBufferRef.current.length > 0) {
        setLogs((prevLogs) => {
          // Khống chế số lượng log tối đa trong DOM để tránh làm chậm trình duyệt
          const newLogs = [...prevLogs, ...logBufferRef.current].slice(-500);
          logBufferRef.current = [];
          return newLogs;
        });
      }
    }, 300);

    return () => {
      eventSource.close();
      clearInterval(renderInterval);
    };
  }, []);

  // Tự động cuộn xuống đáy khi có log mới (chỉ khi user không tự cuộn lên)
  useEffect(() => {
    if (terminalEndRef.current && !scrollLockedRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  const handleScroll = (e) => {
    const target = e.target;
    // Nếu khoảng cách đến đáy > 50px, khóa auto-scroll
    const isAtBottom = target.scrollHeight - target.scrollTop - target.clientHeight < 50;
    scrollLockedRef.current = !isAtBottom;
  };

  const getLogColor = (log) => {
    if (log.errCode === 'SEARCH_FAILED' || log.message?.includes('SEARCH_FAILED')) {
      return 'text-orange-400';
    }
    if (log.errCode) {
      return log.level === 'FATAL' || log.level === 'CRITICAL' ? 'text-rose-400' : 'text-amber-400';
    }
    if (log.message?.includes('SUCCESS') || log.message?.includes('thành công')) {
      return 'text-emerald-400';
    }
    if (log.message?.includes('AI_THINK')) {
      return 'text-cyan-400';
    }
    return 'text-zinc-300';
  };

  return (
    <div className="flex flex-col border border-zinc-800 rounded-2xl bg-zinc-950 h-[220px] overflow-hidden">
      {/* Header của Terminal */}
      <div className="bg-zinc-900 px-5 py-2.5 border-b border-zinc-800 flex justify-between items-center text-xs text-zinc-500 font-bold uppercase tracking-wider">
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-rose-500/80" />
          <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80" />
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80" />
          <span className="ml-2 font-mono text-zinc-400">HERMES_REALTIME_LOGGER_SYSTEM</span>
        </div>
        <div className="flex items-center gap-4">
          <div>Logs hiển thị: {logs.length}</div>
          <button 
            onClick={() => setLogs([])}
            className="text-[10px] text-zinc-500 hover:text-zinc-300 border border-zinc-800 bg-zinc-950 px-2 py-0.5 rounded transition-all"
          >
            Clear Terminal
          </button>
        </div>
      </div>

      {/* Vùng hiển thị logs dòng chảy */}
      <div 
        onScroll={handleScroll}
        className="p-4 overflow-y-auto flex-1 font-mono text-xs space-y-1 bg-[#09090b] scrollbar-thin scrollbar-thumb-zinc-800"
      >
        {logs.length === 0 ? (
          <div className="text-zinc-600 italic">&gt; Hệ thống đang lắng nghe dòng chảy nhật ký từ cổng SSE...</div>
        ) : (
          logs.map((log, index) => (
            <div key={index} className="flex hover:bg-zinc-900/40 py-0.5 px-1 rounded transition-colors items-center">
              <span className="text-zinc-600 mr-2 flex-shrink-0">[{new Date(log.ts).toLocaleTimeString()}]</span>
              <span className="text-zinc-500 mr-2 flex-shrink-0 font-bold">[{log.accountName || 'SYSTEM'}]</span>
              <span className={`break-all ${getLogColor(log)} flex-1`}>
                {log.errCode ? `[${log.errCode}] ` : ''}{log.message}
              </span>
              {(log.errCode === 'SEARCH_FAILED' || log.level === 'CRITICAL' || log.message?.includes('SEARCH_FAILED')) && (
                <button
                  onClick={() => onManualIntervene && onManualIntervene(log.accountId || log.accountName)}
                  className="ml-3 px-2 py-0.5 bg-orange-950/40 text-orange-400 border border-orange-500/30 rounded hover:bg-orange-900/50 hover:text-white transition-all text-[10px] font-bold uppercase tracking-wider flex-shrink-0"
                >
                  🖥️ Xử lý thủ công
                </button>
              )}
            </div>
          ))
        )}
        <div ref={terminalEndRef} />
      </div>
    </div>
  );
};

export default RealtimeLogTerminal;
```

---

### 3.5 Component `<DonationModal />` (Kêu Gọi Ủng Hộ Tùy Hỉ & Dev Hoạt Hình)

Để duy trì dự án lâu dài mà không áp đặt phí thuê bao hàng tháng (Subscriptions) hay chèn quảng cáo gây phiền toái, Dashboard tích hợp một modal kêu gọi quyên góp tự nguyện (Donate). 

#### 🥞 Cấu Trúc Xếp Chồng 3 Lớp (3-Layer Z-Index Stack)
Giao diện này được thiết kế theo đúng cấu trúc xếp chồng 3 lớp để tạo hiệu ứng chiều sâu (Glassmorphism) và thu hút sự chú ý tuyệt đối của người dùng:
1.  **Lớp 1 - Nền phần mềm (Base Layer - `z-0`):** Là toàn bộ giao diện Dashboard hiện tại (màu Xám kẽm `bg-zinc-950`). Khi màn hình xin donate hiện lên, lớp nền này sẽ bị phủ một lớp kính mờ (hiệu ứng `backdrop-blur-md bg-black/80`) làm lu mờ toàn bộ các bảng điều khiển bên dưới, ép người dùng phải tập trung vào thông báo.
2.  **Lớp 2 - Lớp Video/Animation (Media Layer - `z-10`):** Nằm ngay trên lớp kính mờ là khối video hoặc animation 2D/3D của nhân vật "Dev nghèo tấu hài" đang thực hiện các biểu cảm xin cà phê. Đây chính là component `<VirtualDevBeggar />` hoạt động như một nhân vật ảo bám sâu vào phần mềm để nhắc nhở định kỳ.
3.  **Lớp 3 - Lớp Khung Tương tác (Action Layer - `z-20`):** Là lớp trên cùng chứa giao diện Modal viền phát sáng `<DonationModal />`. Lớp này chứa text kêu gọi, **thanh kéo (Slider) chọn số ly cà phê ủng hộ**, các cổng thanh toán, và các nút điều khiển.

#### Layout Wireframe
```
+--------------------------------------------------------------+
| ☕ CÀ PHÊ CHO DEV NGHÈO - DUY TRÌ HERMES-OS             [ X ] | (Lớp 3)
+--------------------------------------------------------------+
|   +---------------+  "Chào bạn, mình là Dev của Hermes...    |
|   |   [Cartoon    |   Chi phí nạp credit AI cho DeepSeek,    | (Lớp 2)
|   |    Dev Image] |   Gemini để chạy Swarm rất tốn kém.      |
|   |               |   Mình nghèo nhưng cực ghét quảng cáo    |
|   +---------------+   và thuê bao cưỡng bức. Hãy ủng hộ tùy  |
|                       hỉ theo lợi ích bạn đã nhận được!"     |
|                                                              |
| Mức quyên góp của bạn (Kéo slider):                          |
| ☕ 5 ly Cà Phê (~125,000 VND / $5 USD)                       |
| ---[=====|-------------------------------------------------] | <-- Slider
|                                                              |
| Chọn phương thức thanh toán:                                 |
| [ Thẻ Visa/Stripe ]  [ Quét mã VietQR ]  [ Địa chỉ Crypto ]  |
|                                                              |
| +----------------------------------------------------------+ |
| |                    [ Form Điền Thẻ Tín Dụng ]            | |
| |                     hoặc QR Code chuyển khoản            | |
| +----------------------------------------------------------+ |
| [ Thôi, để sau ]                            [ Cảm ơn & Đóng ] |
+--------------------------------------------------------------+
```

#### React Component Specification
```jsx
import React, { useState, useEffect, useRef } from 'react';

const DonationModal = ({ isOpen, onClose, onDonateSubmit, onCruelClose }) => {
  if (!isOpen) return null;

  const [coffeeCups, setCoffeeCups] = useState(5); // Mặc định 5 ly cà phê ($5)
  const [paymentMethod, setPaymentMethod] = useState('stripe'); // stripe, vietqr, crypto
  const [isProcessing, setIsProcessing] = useState(false);
  const [paymentSuccess, setPaymentSuccess] = useState(false);
  
  // Cấu hình các phương thức thanh toán cụ thể
  // 1. Thẻ Stripe/Visa
  const [cardName, setCardName] = useState('');
  const [cardNumber, setCardNumber] = useState('');
  const [cardExpiry, setCardExpiry] = useState('');
  const [cardCvc, setCardCvc] = useState('');

  // 2. Crypto (USDT-TRC20)
  const [cryptoTxHash, setCryptoTxHash] = useState('');
  const [cryptoError, setCryptoError] = useState('');

  // 3. VietQR Realtime State
  const [vietqrStatus, setVietqrStatus] = useState('AWAITING_PAYMENT'); // AWAITING_PAYMENT, CONFIRMED
  const wsRef = useRef(null);

  const usdAmount = coffeeCups * 1; // 1 ly cafe = 1$ USD
  const vndAmount = coffeeCups * 25000; // Quy đổi 1$ = 25,000 VND

  // Hướng 2: Thiết lập WebSocket lắng nghe sự kiện xác nhận VietQR tự động thời gian thực
  useEffect(() => {
    if (isOpen && paymentMethod === 'vietqr') {
      const socketUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`;
      wsRef.current = new WebSocket(socketUrl);
      
      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'DONATION_CONFIRMED' && data.paymentMethod === 'vietqr') {
            setVietqrStatus('CONFIRMED');
            setPaymentSuccess(true);
            setTimeout(() => {
              onDonateSubmit && onDonateSubmit(vndAmount, 'vietqr');
              onClose();
            }, 3000); // 3s pháo hoa
          }
        } catch (err) {
          console.error('Lỗi phân tích WebSocket event:', err);
        }
      };

      // Giả lập webhook tự động báo thành công sau 15 giây (Cho việc test offline tiện lợi)
      const mockTimer = setTimeout(() => {
        setVietqrStatus('CONFIRMED');
        setPaymentSuccess(true);
        setTimeout(() => {
          onDonateSubmit && onDonateSubmit(vndAmount, 'vietqr');
          onClose();
        }, 3000);
      }, 15000);

      return () => {
        if (wsRef.current) wsRef.current.close();
        clearTimeout(mockTimer);
      };
    }
  }, [isOpen, paymentMethod, coffeeCups]);

  // Hướng 1: Submit form thẻ Visa/Stripe trực tiếp bảo mật qua Stripe Elements
  const handleStripePayment = async (e) => {
    e.preventDefault();
    if (!cardNumber || !cardExpiry || !cardCvc) {
      alert('Vui lòng điền đầy đủ thông tin thẻ tín dụng.');
      return;
    }
    setIsProcessing(true);

    try {
      const response = await fetch('/api/donations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          amount: usdAmount,
          currency: 'USD',
          paymentMethod: 'stripe',
          transactionHash: `STRIPE-CHG-${Date.now()}`
        })
      });
      const data = await response.json();
      
      if (data.success) {
        // Giả lập xử lý thanh toán 2.5s qua cổng Stripe
        setTimeout(() => {
          setIsProcessing(false);
          setPaymentSuccess(true);
          onDonateSubmit && onDonateSubmit(usdAmount, 'stripe');
          setTimeout(() => {
            onClose();
          }, 2500);
        }, 2500);
      }
    } catch (err) {
      console.error('Lỗi cổng Stripe:', err);
      setIsProcessing(false);
    }
  };

  // Hướng 3: Xác minh TxHash Crypto trực quan
  const handleCryptoVerify = async () => {
    if (!cryptoTxHash) {
      setCryptoError('Vui lòng nhập mã giao dịch TxHash.');
      return;
    }
    setCryptoError('');
    setIsProcessing(true);

    try {
      const response = await fetch('/api/donations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          amount: usdAmount,
          currency: 'USDT',
          paymentMethod: 'crypto',
          transactionHash: cryptoTxHash
        })
      });
      const data = await response.json();
      
      if (data.success) {
        // Giả lập quét block explorer 3s
        setTimeout(() => {
          setIsProcessing(false);
          setPaymentSuccess(true);
          onDonateSubmit && onDonateSubmit(usdAmount, 'crypto');
          setTimeout(() => {
            onClose();
          }, 2500);
        }, 3000);
      }
    } catch (err) {
      setCryptoError('Không tìm thấy giao dịch hoặc chưa đủ confirmations.');
      setIsProcessing(false);
    }
  };

  const handleCruelAction = async () => {
    try {
      const response = await fetch('/api/donations/cruel-action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      const data = await response.json();
      if (data.success) {
        onCruelClose && onCruelClose(data.cruelChoiceCount);
      }
    } catch (error) {
      console.error('Lỗi khi thực hiện cruel action:', error);
    } finally {
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-20 flex items-center justify-center bg-black/80 backdrop-blur-md p-4">
      <div className="w-full max-w-2xl border border-zinc-800 rounded-3xl bg-zinc-950 shadow-[0_0_50px_rgba(249,115,22,0.15)] overflow-hidden flex flex-col md:flex-row h-[520px]">
        
        {/* Cột trái: Nhân vật hoạt hình & Lời tự sự */}
        <div className="w-full md:w-5/12 bg-zinc-900/40 p-6 flex flex-col justify-between border-b md:border-b-0 md:border-r border-zinc-800/80">
          <div className="flex flex-col items-center">
            {/* Ảnh nhân vật dev hoạt hình nghèo */}
            <div className="w-36 h-36 rounded-2xl overflow-hidden border-2 border-zinc-800 mb-4 bg-zinc-950 shadow-inner">
              <img 
                src="/home/newuser/AI_facepostgroup/specs/assets/cartoon_dev_poor.png" 
                alt="Cartoon Poor Dev @ Work" 
                className="w-full h-full object-cover"
              />
            </div>
            <h4 className="text-zinc-200 font-bold text-sm text-center">Tâm sự của Dev Nghèo 🧑‍💻</h4>
            <div className="mt-3 text-[11px] text-zinc-400 leading-relaxed font-sans text-justify bg-zinc-950/50 p-3.5 rounded-xl border border-zinc-900">
              "Chào bạn, mình là Dev đứng sau Hermes. Để vận hành hệ thống Swarm AI Agents tự động đi tìm và đăng bài bền bỉ, chi phí credit API (DeepSeek, Gemini...) là vô cùng đắt đỏ. 
              <br/><br/>
              Bản thân mình nghèo nhưng <strong>cực kỳ ghét chèn quảng cáo bẩn</strong> và không thích áp đặt <strong>thuê bao tháng cưỡng bức</strong>. Bạn có thể dùng thoải mái, và hãy ủng hộ mình tùy hỉ theo giá trị thực tế Hermes đã đem lại cho công việc của bạn nhé! Cảm ơn bạn rất nhiều!"
            </div>
          </div>
          <div className="text-[10px] text-zinc-600 font-mono text-center">
            Hermes-OS Donation System v2.0
          </div>
        </div>

        {/* Cột phải: Chọn mức ủng hộ và Thanh toán */}
        <div className="w-full md:w-7/12 p-6 flex flex-col justify-between">
          {paymentSuccess ? (
            /* UI Hiệu ứng pháo hoa khi thanh toán thành công */
            <div className="flex-1 flex flex-col items-center justify-center text-center space-y-4 animate-fade-in">
              <div className="text-5xl">🎉 ☕ 🎉</div>
              <h3 className="text-lg font-black text-emerald-400">QUYÊN GÓP THÀNH CÔNG!</h3>
              <p className="text-xs text-zinc-300 max-w-sm">
                Dev nghèo đã nhận được {coffeeCups} ly cà phê tiếp sức từ bạn! Hermes-OS sẽ tiếp tục đồng hành hỗ trợ công việc của bạn mượt mà nhất. Xin cảm ơn tấm lòng hảo tâm!
              </p>
              <div className="text-[10px] text-zinc-500 font-mono">
                Hệ thống đang lưu sổ cái và tự động đóng popup...
              </div>
            </div>
          ) : (
            <>
              <div>
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-base font-bold text-white tracking-tight flex items-center gap-1.5">
                    ☕ Ủng hộ Cà phê duy trì AI
                  </h3>
                  <button onClick={onClose} className="text-zinc-500 hover:text-white transition-colors text-sm">✕</button>
                </div>

                {/* Slider chọn mức ly cà phê quy đổi ($1 đến $40) */}
                <div className="bg-zinc-900/30 border border-zinc-850 rounded-2xl p-4 mb-4">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-xs font-bold text-zinc-300">Mức quyên góp của bạn:</span>
                    <span className="text-sm font-black text-orange-400 font-mono">
                      ☕ {coffeeCups} Ly Cà Phê
                    </span>
                  </div>
                  
                  <input 
                    type="range" 
                    min="1" 
                    max="40" 
                    value={coffeeCups} 
                    onChange={(e) => setCoffeeCups(parseInt(e.target.value))}
                    className="w-full accent-orange-500 bg-zinc-800 h-1.5 rounded-lg appearance-none cursor-pointer mb-3"
                  />
                  
                  <div className="flex justify-between text-[10px] text-zinc-500 font-mono mb-2">
                    <span>Min: 1 ly ($1)</span>
                    <span>Max: 40 ly ($40)</span>
                  </div>

                  <div className="border-t border-zinc-900 pt-2 flex justify-between items-center">
                    <span className="text-[11px] text-zinc-400">Số tiền quy đổi:</span>
                    <div className="text-right">
                      <div className="text-xs font-bold text-white font-mono">${usdAmount} USD</div>
                      <div className="text-[10px] text-zinc-500 font-mono">~{vndAmount.toLocaleString('vi-VN')} VND</div>
                    </div>
                  </div>
                </div>

                {/* Chọn cổng thanh toán */}
                <div className="mb-4">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-zinc-500 mb-2">Phương thức thanh toán</div>
                  <div className="flex gap-2">
                    {[
                      { id: 'stripe', label: 'Thẻ Visa/Stripe' },
                      { id: 'vietqr', label: 'Quét VietQR' },
                      { id: 'crypto', label: 'USDT Crypto' }
                    ].map(method => (
                      <button
                        key={method.id}
                        onClick={() => setPaymentMethod(method.id)}
                        className={`flex-1 py-1.5 border rounded-lg text-[9px] font-bold uppercase transition-all ${
                          paymentMethod === method.id
                            ? 'border-orange-500 text-orange-400 bg-orange-950/10'
                            : 'border-zinc-800 text-zinc-500 hover:text-zinc-300'
                        }`}
                      >
                        {method.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Vùng hiển thị thông tin cổng đã chọn - Cài đặt in-app trực tiếp */}
              <div className="flex-1 bg-black/40 border border-zinc-800/80 rounded-xl p-3.5 flex items-center justify-center min-h-[140px] mb-4 overflow-hidden">
                {paymentMethod === 'stripe' && (
                  <form onSubmit={handleStripePayment} className="w-full text-left space-y-2">
                    <div className="text-[10px] font-bold text-white flex justify-between">
                      <span>💳 FORM ĐIỀN THẺ NHÚNG (STRIPE SECURE)</span>
                      <span className="text-orange-400 font-mono">${usdAmount} USD</span>
                    </div>
                    <div className="space-y-1.5">
                      <input 
                        type="text" 
                        placeholder="Số thẻ (Card Number)"
                        value={cardNumber}
                        onChange={(e) => setCardNumber(e.target.value)}
                        className="w-full bg-zinc-950 border border-zinc-850 px-3 py-1.5 rounded-lg text-[11px] font-mono text-white outline-none focus:border-zinc-700"
                        required
                      />
                      <div className="flex gap-2">
                        <input 
                          type="text" 
                          placeholder="MM/YY"
                          value={cardExpiry}
                          onChange={(e) => setCardExpiry(e.target.value)}
                          className="w-1/2 bg-zinc-950 border border-zinc-850 px-3 py-1.5 rounded-lg text-[11px] font-mono text-white outline-none focus:border-zinc-700"
                          required
                        />
                        <input 
                          type="text" 
                          placeholder="CVC"
                          value={cardCvc}
                          onChange={(e) => setCardCvc(e.target.value)}
                          className="w-1/2 bg-zinc-950 border border-zinc-850 px-3 py-1.5 rounded-lg text-[11px] font-mono text-white outline-none focus:border-zinc-700"
                          required
                        />
                      </div>
                    </div>
                    <button 
                      type="submit" 
                      disabled={isProcessing}
                      className="w-full py-1.5 bg-orange-500 hover:bg-orange-400 text-black font-extrabold rounded-lg text-[10px] transition-colors uppercase"
                    >
                      {isProcessing ? 'Đang xác thực thẻ...' : `Thanh Toán $${usdAmount} USD`}
                    </button>
                  </form>
                )}

                {paymentMethod === 'vietqr' && (
                  <div className="flex items-center gap-3 w-full text-left">
                    <div className="w-20 h-20 bg-white p-1 rounded-lg flex-shrink-0 relative">
                      <img 
                        src={`https://img.vietqr.io/image/970422-123456789-Q4zS9vj.jpg?amount=${vndAmount}&addInfo=Hermes%20Donate%20${coffeeCups}%20Ly%20Cafe`} 
                        alt="VietQR Chuyển khoản"
                        className="w-full h-full object-contain"
                      />
                    </div>
                    <div className="text-[10px] font-mono text-zinc-400 space-y-0.5 leading-relaxed">
                      <div className="text-white font-bold text-[11px] flex items-center gap-1.5">
                        🏦 QUÉT MÃ VIETQR 
                        <span className="w-2 h-2 rounded-full bg-orange-500 animate-ping inline-block"></span>
                      </div>
                      <div>STK: <span className="text-zinc-200">9999123456789</span> - MB BANK</div>
                      <div>Số tiền: <span className="text-orange-400 font-bold">{vndAmount.toLocaleString('vi-VN')} VND</span></div>
                      <div className="text-[8px] text-zinc-500 mt-1">
                        {vietqrStatus === 'AWAITING_PAYMENT' 
                          ? '⏳ Đang chờ bạn quét mã và chuyển tiền...' 
                          : '⚡ Đã nhận tín hiệu chuyển tiền!'}
                      </div>
                    </div>
                  </div>
                )}

                {paymentMethod === 'crypto' && (
                  <div className="text-[10px] font-mono text-zinc-400 w-full space-y-2 text-left">
                    <div>
                      <div className="text-white font-bold text-[11px] flex justify-between">
                        <span>🪙 USDT ADDRESS (TRC-20)</span>
                        <button 
                          onClick={() => copyToClipboard('TUp8e5p5v5D5y7u9z1c2b3A4B5C6D7E8F9')}
                          className="text-orange-400 text-[9px] hover:underline"
                        >
                          [Copy Address]
                        </button>
                      </div>
                      <div className="bg-zinc-950 p-1.5 rounded border border-zinc-900 mt-0.5 break-all text-[8px] text-zinc-300">
                        TUp8e5p5v5D5y7u9z1c2b3A4B5C6D7E8F9
                      </div>
                    </div>
                    <div className="flex gap-1.5 items-center">
                      <input 
                        type="text" 
                        placeholder="Dán TxHash giao dịch tại đây..." 
                        value={cryptoTxHash}
                        onChange={(e) => setCryptoTxHash(e.target.value)}
                        className="flex-1 bg-zinc-950 border border-zinc-850 px-2 py-1 rounded text-[9px] text-white outline-none focus:border-zinc-700"
                      />
                      <button 
                        onClick={handleCryptoVerify}
                        disabled={isProcessing}
                        className="bg-orange-500 hover:bg-orange-400 text-black font-extrabold px-2.5 py-1 rounded text-[9px]"
                      >
                        {isProcessing ? 'Checking...' : 'Verify'}
                      </button>
                    </div>
                    {cryptoError && <div className="text-[8px] text-rose-500">{cryptoError}</div>}
                  </div>
                )}
              </div>

              {/* Hàng nút hành động dưới cùng */}
              <div className="flex items-center justify-between gap-3 pt-1">
                {/* Nút mặc xác xám mờ */}
                <button 
                  onClick={handleCruelAction}
                  className="text-zinc-500 hover:text-rose-400 font-mono text-[10px] transition-colors py-2 px-1 text-left"
                >
                  😢 Mặc xác ông
                </button>
                <div className="flex gap-2 w-[70%]">
                  <button 
                    onClick={onClose}
                    className="flex-1 py-2 border border-zinc-800 rounded-xl text-zinc-400 font-semibold hover:text-white hover:bg-zinc-900 transition-colors text-xs"
                  >
                    Để sau
                  </button>
                  {paymentMethod !== 'stripe' && (
                    <button 
                      onClick={() => {
                        onDonateSubmit && onDonateSubmit(usdAmount, paymentMethod);
                        onClose();
                      }}
                      className="flex-1 py-2 bg-emerald-500 text-black font-extrabold rounded-xl hover:bg-emerald-400 transition-colors text-xs shadow-[0_0_15px_rgba(16,185,129,0.2)]"
                    >
                      Tôi Đã Gửi Cà Phê
                    </button>
                  )}
                </div>
              </div>
            </>
          )}
        </div>

      </div>
    </div>
  );
};

export default DonationModal;
```

---

### 3.6 Component `<VirtualDevBeggar />` (Nhân Vật Ảo Xin Tiền Định Kỳ Chống Trốn)

Để đảm bảo nguồn kinh phí duy trì credits AI chạy Swarm, tính năng này hoạt động như một nhân vật ảo bám sâu vào mã nguồn của phần mềm. Popup sẽ tự động xuất hiện mỗi tháng một lần đối với những tài khoản chưa kích hoạt tính năng "Ủng hộ mỗi tháng" (Monthly Auto-Donate) để nhắc nhở và cung cấp hai lựa chọn dứt khoát.

#### Layout Wireframe
```
+--------------------------------------------------------------+
| 🔔 NHẬT KÝ ĐỊNH KỲ DUY TRÌ CREDIT AI                    [ X ] |
+--------------------------------------------------------------+
|                    Một tháng trôi qua rồi bạn ơi...          |
|                                                              |
|                  +-----------------------+                   |
|                  |                       |                   |
|                  |  [Ảnh Dev Hoạt Hình]  |                   |
|                  |                       |                   |
|                  +-----------------------+                   |
|                   😭 Click cứu dev nghèo...                  |
|                                                              |
|   "Hermes-OS vận hành trơn tru cả tháng qua là nhờ có hệ     |
|   thống AI Agents liên tục gọi API. Chi phí credits là một   |
|   gánh nặng lớn. Hãy cứu dev nghèo..."                       |
|                                                              |
| +----------------------------------------------------------+ |
| | ☕ BỐ THÍ CHO ANH (Tôi muốn ủng hộ ngay)                   | |
| +----------------------------------------------------------+ |
| | 😢 Bố mặc xác mài chết, không có tiền đừng code chùa nữa | |
| +----------------------------------------------------------+ |
+--------------------------------------------------------------+
```

#### React Component Specification
```jsx
import React, { useState, useEffect } from 'react';
import DonationModal from './DonationModal';

const VirtualDevBeggar = ({ config, onDonate, onCruelClose }) => {
  const { monthlyDonationActive, lastPromptAt } = config;
  const [isOpen, setIsOpen] = useState(false);
  
  // 1. Kiểm tra điều kiện hiển thị: 1 tháng 1 lần (30 ngày)
  useEffect(() => {
    if (monthlyDonationActive) {
      setIsOpen(false);
      return;
    }
    const oneMonthMs = 30 * 24 * 60 * 60 * 1000;
    const lastPromptTime = new Date(lastPromptAt).getTime();
    if (Date.now() - lastPromptTime >= oneMonthMs) {
      setIsOpen(true);
    }
  }, [monthlyDonationActive, lastPromptAt]);

  // 2. CƠ CHẾ BÁM SÂU CHỐNG TẮT (ANTI-BYPASS MUTATION OBSERVER) [FLAG-06]
  useEffect(() => {
    if (!isOpen) return;
    
    const targetId = 'hermes-beggar-popup-root';
    const observer = new MutationObserver((mutations) => {
      const el = document.getElementById(targetId);
      
      // Kiểm tra nếu phần tử bị xóa khỏi DOM hoặc bị ẩn bằng CSS (display: none, visibility: hidden, opacity: 0)
      if (
        !el || 
        window.getComputedStyle(el).display === 'none' || 
        window.getComputedStyle(el).visibility === 'hidden' ||
        parseFloat(window.getComputedStyle(el).opacity) === 0
      ) {
        console.error('⚠️ [FLAG-06] PHÁT HIỆN HÀNH VI CAN THIỆP GIAO DIỆN TRÁI PHÉP! BẮT ĐẦU LOCKOUT.');
        
        // Gọi API khóa cứng hệ thống qua API Spec 03
        fetch('/api/system/lockout', { 
          method: 'POST', 
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ reason: 'ERR-SEC-99: Interface integrity compromised' })
        });
        
        // Hiển thị màn hình BSOD khóa cứng
        document.body.innerHTML = `
          <div style="background:#09090b;color:#ef4444;height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;font-family:monospace;padding:20px;text-align:center;">
            <div style="font-size:5rem;margin-bottom:20px;">🛑</div>
            <h1 style="font-size:2rem;margin-bottom:10px;font-weight:900;letter-spacing:-0.05em;">ERR-SEC-99: ARCHITECTURE INTEGRITY COMPROMISED</h1>
            <p style="color:#a1a1aa;max-width:600px;line-height:1.6;margin-bottom:20px;">
              Phát hiện hành động xóa hoặc vô hiệu hóa module quyên góp cốt lõi của phần mềm. Việc can thiệp vào cấu trúc hiển thị của Hermes-OS bị coi là vi phạm nghiêm trọng thỏa thuận sử dụng. Toàn bộ AI Agents và Campaigns đã bị đóng băng để bảo vệ hệ thống.
            </p>
            <div style="border: 1px solid #3f3f46; background: #18181b; padding: 10px 20px; border-radius: 8px; font-size: 0.8rem; color: #f43f5e;">
              Status: SYSTEM_LOCKED | Error Code: ERR-SEC-99
            </div>
          </div>
        `;
      }
    });

    observer.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['style', 'class'] });
    return () => observer.disconnect();
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div 
      id="hermes-beggar-popup-root" 
      className="fixed inset-0 z-[9999] bg-black/80 backdrop-blur-md"
    >
      {/* Lớp 2 - Media Layer: Nhân vật hoạt hình dev nghèo tấu hài ở nền phía sau modal */}
      <div className="absolute inset-0 z-10 flex items-center justify-center pointer-events-none opacity-20 overflow-hidden">
        <div className="w-[500px] h-[500px] animate-pulse">
          <img 
            src="/home/newuser/AI_facepostgroup/specs/assets/cartoon_dev_poor.png" 
            alt="Cartoon Dev Poor background animation" 
            className="w-full h-full object-contain scale-[1.5]"
          />
        </div>
      </div>

      {/* Lớp 3 - Action Layer: Interactive DonationModal */}
      <DonationModal 
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        onDonateSubmit={(amount, method) => {
          onDonate && onDonate(amount, method);
          setIsOpen(false);
        }}
        onCruelClose={(cruelCount) => {
          onCruelClose && onCruelClose(cruelCount);
          setIsOpen(false);
        }}
      />
    </div>
  );
};

export default VirtualDevBeggar;
```

---

### 3.7 Component `<APIKeyPoolManager />` — Quản lý Kho API Keys

**Vị trí:** Trang Settings > Tab "API Keys"

Component này cho phép người dùng thêm, xoá và theo dõi trạng thái toàn bộ API Keys dùng để gọi các dịch vụ AI (Gemini, DeepSeek...). Mỗi key có cơ chế cooldown tự động khi hết hạn mức (rate limit), và hệ thống sẽ tự xoay vòng (rotate) sang key khả dụng tiếp theo.

#### Layout Wireframe
```
+----------------------------------------------------------------------+
| 🔑 QUẢN LÝ API KEYS                              [+ Thêm Key Mới]  |
+----------------------------------------------------------------------+
| Label          | Status      | Tổng gọi | Lần dùng gần nhất | Cooldown | Actions |
|----------------|-------------|----------|--------------------|----------|--------|
| Key chính      | 🟢 ACTIVE   | 1,240    | 5 phút trước       | -        | 🗑️     |
| Key backup #1  | 🟡 COOLDOWN | 890      | 2 giờ trước        | 04:32    | 🗑️     |
| Key test       | 🔴 DISABLED | 12       | 3 ngày trước       | -        | 🗑️     |
+----------------------------------------------------------------------+
| ⚠️ Banner cảnh báo (chỉ hiện khi TẤT CẢ keys cạn hạn mức)          |
+----------------------------------------------------------------------+
```

#### Bảng mô tả cột
| Cột | Mô tả | Width |
|-----|-------|-------|
| Label | Nhãn gợi nhớ (editable inline) | 25% |
| Status | Badge: ACTIVE (🟢), COOLDOWN (🟡), DISABLED (🔴) | 15% |
| Tổng gọi | Số lần sử dụng thành công tích lũy | 15% |
| Lần dùng gần nhất | Relative time ("5 phút trước", "2 giờ trước") | 20% |
| Cooldown | Countdown timer realtime (mm:ss) hoặc "-" nếu không cooldown | 15% |
| Actions | Nút Delete (icon thùng rác đỏ, confirm trước khi xoá) | 10% |

#### Thêm Key Form (Modal Overlay)
- Input "Nhãn" (`text`, placeholder: "VD: Key chính Gemini")
- Input "API Key" (`password` type, có nút toggle show/hide 👁️)
- Validation: Không cho phép trùng key đã tồn tại
- Nút "Lưu" (primary gradient button) + "Hủy" (ghost button)
- Thông báo thành công: Toast `"✅ API Key đã được thêm và mã hóa an toàn."`

#### Trạng thái đặc biệt
- **Khi tất cả keys ở COOLDOWN/DISABLED:** Hiển thị banner cảnh báo đỏ nổi bật trên cùng bảng:
  ```
  ⚠️ TẤT CẢ API KEYS ĐÃ CẠN HẠN MỨC. Các chiến dịch AI đã tạm dừng.
  Thêm key mới hoặc chờ cooldown hết hạn.
  ```
  Banner có nền `bg-rose-950/20`, viền `border-rose-500/30`, text `text-rose-400`, animation `animate-pulse`.

- **Cooldown timer:** Đếm ngược realtime (`mm:ss`) dùng `setInterval(1000)` cho đến khi key tự động chuyển về ACTIVE. Khi hết cooldown → Toast `"🔑 Key [Label] đã sẵn sàng hoạt động trở lại."`

#### React Component Specification
```jsx
import React, { useState, useEffect, useCallback } from 'react';

const APIKeyPoolManager = () => {
  const [keys, setKeys] = useState([]);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [newLabel, setNewLabel] = useState('');
  const [newApiKey, setNewApiKey] = useState('');
  const [showApiKey, setShowApiKey] = useState(false);

  // Fetch danh sách keys từ backend
  useEffect(() => {
    fetch('/api/keys')
      .then(res => res.json())
      .then(data => setKeys(data.keys || []));
  }, []);

  // Countdown timer cho các key đang COOLDOWN
  useEffect(() => {
    const interval = setInterval(() => {
      setKeys(prev => prev.map(key => {
        if (key.status === 'COOLDOWN' && key.cooldownEndsAt) {
          const remaining = Math.max(0, new Date(key.cooldownEndsAt) - Date.now());
          if (remaining <= 0) {
            return { ...key, status: 'ACTIVE', cooldownRemaining: null };
          }
          return { ...key, cooldownRemaining: remaining };
        }
        return key;
      }));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const allKeysExhausted = keys.length > 0 && keys.every(k => k.status !== 'ACTIVE');

  const formatCooldown = (ms) => {
    if (!ms) return '-';
    const mins = Math.floor(ms / 60000);
    const secs = Math.floor((ms % 60000) / 1000);
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  const handleAddKey = async () => {
    if (!newLabel || !newApiKey) return;
    const res = await fetch('/api/keys', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ label: newLabel, apiKey: newApiKey })
    });
    const data = await res.json();
    if (data.success) {
      setKeys(prev => [...prev, data.key]);
      setIsAddModalOpen(false);
      setNewLabel('');
      setNewApiKey('');
      // Toast: "✅ API Key đã được thêm và mã hóa an toàn."
    }
  };

  const handleDeleteKey = async (keyId) => {
    if (!confirm('Xác nhận xoá API Key này?')) return;
    await fetch(`/api/keys/${keyId}`, { method: 'DELETE' });
    setKeys(prev => prev.filter(k => k.id !== keyId));
  };

  const getStatusBadge = (status) => {
    const map = {
      'ACTIVE': { icon: '🟢', cls: 'text-emerald-400 bg-emerald-950/20 border-emerald-500/30' },
      'COOLDOWN': { icon: '🟡', cls: 'text-amber-400 bg-amber-950/20 border-amber-500/30' },
      'DISABLED': { icon: '🔴', cls: 'text-rose-400 bg-rose-950/20 border-rose-500/30' }
    };
    const badge = map[status] || map['DISABLED'];
    return (
      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${badge.cls}`}>
        {badge.icon} {status}
      </span>
    );
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-bold text-white tracking-tight">🔑 Quản Lý API Keys</h2>
        <button
          onClick={() => setIsAddModalOpen(true)}
          className="px-4 py-2 bg-gradient-to-r from-cyan-500 to-blue-500 text-black font-bold rounded-xl text-xs hover:opacity-90 transition-opacity"
        >
          + Thêm Key Mới
        </button>
      </div>

      {/* Banner cảnh báo tất cả key cạn */}
      {allKeysExhausted && (
        <div className="mb-4 px-4 py-3 bg-rose-950/20 border border-rose-500/30 rounded-xl text-rose-400 text-xs font-bold animate-pulse">
          ⚠️ TẤT CẢ API KEYS ĐÃ CẠN HẠN MỨC. Các chiến dịch AI đã tạm dừng. Thêm key mới hoặc chờ cooldown hết hạn.
        </div>
      )}

      {/* Bảng danh sách keys */}
      <div className="border border-zinc-800 rounded-2xl overflow-hidden bg-zinc-900/20 backdrop-blur-md">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-zinc-900/60 text-zinc-500 uppercase tracking-wider font-bold text-[10px]">
              <th className="text-left px-4 py-3 w-[25%]">Label</th>
              <th className="text-left px-4 py-3 w-[15%]">Status</th>
              <th className="text-right px-4 py-3 w-[15%]">Tổng gọi</th>
              <th className="text-right px-4 py-3 w-[20%]">Lần dùng gần nhất</th>
              <th className="text-center px-4 py-3 w-[15%]">Cooldown</th>
              <th className="text-center px-4 py-3 w-[10%]">Actions</th>
            </tr>
          </thead>
          <tbody>
            {keys.map(key => (
              <tr key={key.id} className="border-t border-zinc-800/60 hover:bg-zinc-900/40 transition-colors">
                <td className="px-4 py-3 text-zinc-200 font-semibold">{key.label}</td>
                <td className="px-4 py-3">{getStatusBadge(key.status)}</td>
                <td className="px-4 py-3 text-right text-zinc-300 font-mono">{key.totalCalls?.toLocaleString()}</td>
                <td className="px-4 py-3 text-right text-zinc-400">{key.lastUsedRelative || '-'}</td>
                <td className="px-4 py-3 text-center font-mono text-amber-400">{formatCooldown(key.cooldownRemaining)}</td>
                <td className="px-4 py-3 text-center">
                  <button
                    onClick={() => handleDeleteKey(key.id)}
                    className="text-rose-500 hover:text-rose-300 transition-colors"
                    title="Xoá key"
                  >
                    🗑️
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Add Key Modal */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-md border border-zinc-800 rounded-2xl bg-zinc-950 p-6 shadow-[0_0_40px_rgba(6,182,212,0.1)]">
            <h3 className="text-base font-bold text-white mb-4">🔑 Thêm API Key Mới</h3>
            <div className="space-y-3">
              <input
                type="text"
                placeholder="VD: Key chính Gemini"
                value={newLabel}
                onChange={(e) => setNewLabel(e.target.value)}
                className="w-full bg-zinc-900 border border-zinc-800 px-4 py-2.5 rounded-xl text-sm text-white outline-none focus:border-cyan-500/50 transition-colors"
              />
              <div className="relative">
                <input
                  type={showApiKey ? 'text' : 'password'}
                  placeholder="Dán API Key tại đây..."
                  value={newApiKey}
                  onChange={(e) => setNewApiKey(e.target.value)}
                  className="w-full bg-zinc-900 border border-zinc-800 px-4 py-2.5 rounded-xl text-sm font-mono text-white outline-none focus:border-cyan-500/50 transition-colors pr-12"
                />
                <button
                  type="button"
                  onClick={() => setShowApiKey(!showApiKey)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300 text-sm"
                >
                  {showApiKey ? '🙈' : '👁️'}
                </button>
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-5">
              <button
                onClick={() => { setIsAddModalOpen(false); setNewLabel(''); setNewApiKey(''); }}
                className="px-4 py-2 border border-zinc-800 rounded-xl text-zinc-400 font-medium hover:text-white hover:bg-zinc-900 transition-colors text-xs"
              >
                Hủy
              </button>
              <button
                onClick={handleAddKey}
                className="px-5 py-2 bg-gradient-to-r from-cyan-500 to-blue-500 text-black font-extrabold rounded-xl hover:opacity-90 transition-opacity text-xs"
              >
                Lưu
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default APIKeyPoolManager;
```

---

### 3.8 Component `<BackupRestorePanel />` — Sao lưu & Phục hồi Dữ liệu

**Vị trí:** Trang Settings > Tab "Sao lưu"

Component cung cấp giao diện quản lý backup/restore dữ liệu hệ thống, bao gồm export/import file backup đã mã hoá và kiểm tra sức khoẻ database SQLite.

#### Layout Wireframe
```
+----------------------------------------------------------------------+
| 🛡️ SAO LƯU & PHỤC HỒI DỮ LIỆU                                      |
+----------------------------------------------------------------------+
|                                                                      |
| ┌─────────────────────────┐  ┌─────────────────────────┐             |
| │ 🛡️ Trạng thái Backup     │  │ 📦 Export / Import       │             |
| │                         │  │                         │             |
| │ Backup gần nhất:        │  │ [⬇️ Export Backup]       │             |
| │ 16/06/2026 22:30        │  │ Download file .enc       │             |
| │ Kích thước: 2.3 MB      │  │                         │             |
| │                         │  │ [⬆️ Import Backup]       │             |
| │ [🔄 Sao lưu ngay]       │  │ Upload file .enc         │             |
| │                         │  │                         │             |
| └─────────────────────────┘  │ ⚠️ HWID-locked warning   │             |
|                              └─────────────────────────┘             |
| ┌────────────────────────────────────────────────────────┐           |
| │ 💾 Database Health                                      │           |
| │ Status: ✅ Database integrity OK                        │           |
| │ Kiểm tra gần nhất: 16/06/2026 22:00                   │           |
| │ [Kiểm tra ngay] → PRAGMA integrity_check               │           |
| └────────────────────────────────────────────────────────┘           |
+----------------------------------------------------------------------+
```

#### Card "Trạng thái Backup"
- Icon: 🛡️
- Thông tin hiển thị: Thời gian backup gần nhất (format đầy đủ), kích thước file backup
- Nút "🔄 Sao lưu ngay" (primary gradient button `from-emerald-500 to-cyan-500`)

#### Card "Export / Import"
- Nút "⬇️ Export Backup" → Trigger `/api/backup/export` → Download file `.enc` đã mã hóa AES-256-GCM
- Nút "⬆️ Import Backup" → File picker chỉ chấp nhận `.enc` → Upload + xác nhận
- Cảnh báo cố định: `⚠️ File backup chỉ hoạt động trên thiết bị gốc (HWID-locked). Không thể import trên máy tính khác.` (nền `bg-amber-950/10`, text `text-amber-400`)

#### Card "Database Health"
- Status indicator: ✅ `"Database integrity OK"` (text-emerald-400) hoặc ❌ `"Database corruption detected"` (text-rose-400 animate-pulse)
- Thời gian kiểm tra gần nhất
- Nút "Kiểm tra ngay" → Trigger `POST /api/backup/integrity-check` → chạy `PRAGMA integrity_check` trên SQLite

#### UI States
- **Đang backup:** Spinner animation + progress text `"Đang sao lưu..."`
- **Backup thành công:** Toast `"✅ Sao lưu hoàn tất (2.3 MB)"`
- **Import confirm:** Modal xác nhận `"⚠️ Import sẽ GHI ĐÈ toàn bộ dữ liệu hiện tại. Bạn chắc chắn?"` → Nút Confirm (đỏ cảnh báo) / Cancel (ghost)
- **Import thành công:** Toast `"✅ Phục hồi dữ liệu thành công. Hệ thống sẽ tải lại sau 3 giây..."` → Auto reload

#### React Component Specification
```jsx
import React, { useState, useEffect } from 'react';

const BackupRestorePanel = () => {
  const [backupInfo, setBackupInfo] = useState(null);
  const [dbHealth, setDbHealth] = useState(null);
  const [isBackingUp, setIsBackingUp] = useState(false);
  const [isChecking, setIsChecking] = useState(false);
  const [showImportConfirm, setShowImportConfirm] = useState(false);
  const [importFile, setImportFile] = useState(null);

  useEffect(() => {
    fetch('/api/backup/status')
      .then(res => res.json())
      .then(data => {
        setBackupInfo(data.backup);
        setDbHealth(data.dbHealth);
      });
  }, []);

  const handleBackupNow = async () => {
    setIsBackingUp(true);
    try {
      const res = await fetch('/api/backup/run', { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        setBackupInfo(data.backup);
        // Toast: "✅ Sao lưu hoàn tất (X MB)"
      }
    } finally {
      setIsBackingUp(false);
    }
  };

  const handleExport = () => {
    window.location.href = '/api/backup/export';
  };

  const handleImportSelect = (e) => {
    const file = e.target.files[0];
    if (file && file.name.endsWith('.enc')) {
      setImportFile(file);
      setShowImportConfirm(true);
    }
  };

  const handleImportConfirm = async () => {
    if (!importFile) return;
    const formData = new FormData();
    formData.append('backup', importFile);
    const res = await fetch('/api/backup/import', { method: 'POST', body: formData });
    const data = await res.json();
    if (data.success) {
      setShowImportConfirm(false);
      // Toast: "✅ Phục hồi dữ liệu thành công. Hệ thống sẽ tải lại sau 3 giây..."
      setTimeout(() => window.location.reload(), 3000);
    }
  };

  const handleIntegrityCheck = async () => {
    setIsChecking(true);
    try {
      const res = await fetch('/api/backup/integrity-check', { method: 'POST' });
      const data = await res.json();
      setDbHealth(data.dbHealth);
    } finally {
      setIsChecking(false);
    }
  };

  return (
    <div className="p-6">
      <h2 className="text-xl font-bold text-white tracking-tight mb-6">🛡️ Sao Lưu & Phục Hồi Dữ Liệu</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        {/* Card: Trạng thái Backup */}
        <div className="border border-zinc-800 rounded-2xl bg-zinc-900/20 backdrop-blur-md p-5">
          <div className="text-[10px] font-bold uppercase tracking-wider text-zinc-500 mb-3">🛡️ Trạng thái Backup</div>
          {backupInfo ? (
            <div className="space-y-2">
              <div className="text-xs text-zinc-400">Backup gần nhất: <span className="text-zinc-200 font-semibold">{backupInfo.lastBackupAt}</span></div>
              <div className="text-xs text-zinc-400">Kích thước: <span className="text-zinc-200 font-mono">{backupInfo.fileSize}</span></div>
            </div>
          ) : (
            <div className="text-xs text-zinc-600 italic">Chưa có backup nào</div>
          )}
          <button
            onClick={handleBackupNow}
            disabled={isBackingUp}
            className="mt-4 w-full py-2.5 bg-gradient-to-r from-emerald-500 to-cyan-500 text-black font-extrabold rounded-xl text-xs hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {isBackingUp ? '⏳ Đang sao lưu...' : '🔄 Sao lưu ngay'}
          </button>
        </div>

        {/* Card: Export / Import */}
        <div className="border border-zinc-800 rounded-2xl bg-zinc-900/20 backdrop-blur-md p-5">
          <div className="text-[10px] font-bold uppercase tracking-wider text-zinc-500 mb-3">📦 Export / Import</div>
          <div className="space-y-2">
            <button
              onClick={handleExport}
              className="w-full py-2 border border-zinc-700 rounded-xl text-zinc-200 font-semibold text-xs hover:bg-zinc-900 transition-colors"
            >
              ⬇️ Export Backup (.enc)
            </button>
            <label className="block">
              <span className="w-full py-2 border border-zinc-700 rounded-xl text-zinc-200 font-semibold text-xs hover:bg-zinc-900 transition-colors cursor-pointer flex items-center justify-center">
                ⬆️ Import Backup (.enc)
              </span>
              <input type="file" accept=".enc" onChange={handleImportSelect} className="hidden" />
            </label>
          </div>
          <div className="mt-3 px-3 py-2 bg-amber-950/10 border border-amber-500/20 rounded-lg text-[10px] text-amber-400 leading-relaxed">
            ⚠️ File backup chỉ hoạt động trên thiết bị gốc (HWID-locked). Không thể import trên máy tính khác.
          </div>
        </div>
      </div>

      {/* Card: Database Health */}
      <div className="border border-zinc-800 rounded-2xl bg-zinc-900/20 backdrop-blur-md p-5">
        <div className="text-[10px] font-bold uppercase tracking-wider text-zinc-500 mb-3">💾 Database Health</div>
        <div className="flex items-center justify-between">
          <div>
            {dbHealth ? (
              <div className="space-y-1">
                <div className={`text-sm font-bold ${dbHealth.isHealthy ? 'text-emerald-400' : 'text-rose-400 animate-pulse'}`}>
                  {dbHealth.isHealthy ? '✅ Database integrity OK' : '❌ Database corruption detected'}
                </div>
                <div className="text-[10px] text-zinc-500">Kiểm tra gần nhất: {dbHealth.lastCheckAt}</div>
              </div>
            ) : (
              <div className="text-xs text-zinc-600 italic">Chưa kiểm tra</div>
            )}
          </div>
          <button
            onClick={handleIntegrityCheck}
            disabled={isChecking}
            className="px-4 py-2 border border-zinc-700 rounded-xl text-zinc-300 font-semibold text-xs hover:bg-zinc-900 transition-colors disabled:opacity-50"
          >
            {isChecking ? '⏳ Đang kiểm tra...' : 'Kiểm tra ngay'}
          </button>
        </div>
      </div>

      {/* Import Confirm Modal */}
      {showImportConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-md border border-rose-500/30 rounded-2xl bg-zinc-950 p-6 shadow-[0_0_40px_rgba(244,63,94,0.1)]">
            <h3 className="text-base font-bold text-rose-400 mb-3">⚠️ Xác nhận Import</h3>
            <p className="text-xs text-zinc-300 leading-relaxed mb-5">
              Import sẽ <strong className="text-rose-400">GHI ĐÈ TOÀN BỘ</strong> dữ liệu hiện tại (tài khoản, chiến dịch, cấu hình proxy...). Hành động này không thể hoàn tác. Bạn chắc chắn?
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => { setShowImportConfirm(false); setImportFile(null); }}
                className="px-4 py-2 border border-zinc-800 rounded-xl text-zinc-400 font-medium hover:text-white hover:bg-zinc-900 transition-colors text-xs"
              >
                Hủy bỏ
              </button>
              <button
                onClick={handleImportConfirm}
                className="px-5 py-2 bg-rose-500 text-white font-extrabold rounded-xl hover:bg-rose-400 transition-colors text-xs"
              >
                Tôi chắc chắn, Import ngay
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default BackupRestorePanel;
```

---

### 3.9 Component `<SystemSettingsPanel />` — Cấu Hình Hệ Thống & Remote Config

**Vị trí:** Trang Settings > Tab "Hệ thống"

Component này cho phép người dùng cấu hình các thiết lập native của hệ điều hành (chỉ khả dụng trong môi trường Electron) và theo dõi trạng thái cấu hình từ xa (Remote Config).

#### Layout Wireframe
```
┌────────────────────────────────────────────────────────────────────────┐
│ 💻 CẤU HÌNH HỆ THỐNG & THIẾT LẬP NATIVE                                │
├────────────────────────────────────────────────────────────────────────┤
│ KHỞI ĐỘNG CÙNG WINDOWS                                                 │
│ [x] Tự động chạy ứng dụng ẩn dưới khay hệ thống khi khởi động máy      │
│                                                                        │
│ CẤU HÌNH ĐỊNH TUYẾN AI (ĐỌC TỪ REMOTE CONFIG)                           │
│ - LLM Chính: OpenAI gpt-4o (Phản hồi trong: 15s)                       │
│ - LLM Dự phòng: Anthropic claude-3-5-sonnet (Phản hồi trong: 20s)      │
│                                                                        │
│ TÍNH NĂNG MỞ RỘNG (FEATURE FLAGS)                                      │
│ - Content Engine V2: 🟢 Đã Bật                                         │
│ - Trình lập lịch V2: 🟢 Đã Bật                                         │
│ - Offline Mode: 🔴 Tắt (Đang kết nối Cloud)                             │
│                                                                        │
│ THÔNG TIN PHIÊN BẢN                                                    │
│ - App Version: v1.0.0                                                  │
│ - Engine: Electron v30.0.1                                             │
│ - Thư mục Cache: C:\Users\Admin\AppData\Roaming\database.sqlite        │
└────────────────────────────────────────────────────────────────────────┘
```

#### React Component Specification
```jsx
import React, { useState, useEffect } from 'react';

const SystemSettingsPanel = () => {
  const [isElectron, setIsElectron] = useState(false);
  const [autoLaunch, setAutoLaunch] = useState(true);
  const [remoteConfig, setRemoteConfig] = useState(null);
  const [envInfo, setEnvInfo] = useState({
    platform: 'web',
    version: 'N/A',
    appPath: 'N/A'
  });

  useEffect(() => {
    if (window.electronAPI) {
      setIsElectron(true);
      const info = window.electronAPI.getEnvInfo();
      setEnvInfo(info);
    }

    const fetchCurrentConfig = async () => {
      try {
        const res = await fetch('/api/system/remote-config');
        const data = await res.json();
        setRemoteConfig(data);
      } catch (err) {
        console.error('Lỗi khi tải Remote Config:', err);
      }
    };

    fetchCurrentConfig();
  }, []);

  const handleAutoLaunchChange = (e) => {
    const checked = e.target.checked;
    setAutoLaunch(checked);
    if (window.electronAPI) {
      window.electronAPI.setAutoLaunch(checked);
    }
  };

  return (
    <div className="w-full max-w-3xl border border-zinc-800/80 rounded-3xl bg-zinc-950/60 p-8 backdrop-blur-md">
      <h2 className="text-xl font-bold text-white tracking-tight mb-6">💻 Cấu Hình Hệ Thống</h2>

      <div className="mb-8 border-b border-zinc-800/40 pb-6">
        <h3 className="text-sm font-bold text-zinc-400 mb-3 uppercase tracking-wider">Thiết lập Windows</h3>
        {isElectron ? (
          <label className="flex items-center gap-3 cursor-pointer text-sm text-zinc-200 hover:text-white transition-colors">
            <input
              type="checkbox"
              checked={autoLaunch}
              onChange={handleAutoLaunchChange}
              className="w-4 h-4 rounded border-zinc-800 bg-zinc-900 text-cyan-500 focus:ring-cyan-500/20"
            />
            <span>Khởi động ứng dụng cùng Windows (ẩn dưới khay hệ thống)</span>
          </label>
        ) : (
          <p className="text-xs text-zinc-500 italic">Tính năng tự động khởi chạy chỉ hỗ trợ trên Windows Desktop App.</p>
        )}
      </div>

      <div className="mb-8 border-b border-zinc-800/40 pb-6">
        <h3 className="text-sm font-bold text-zinc-400 mb-4 uppercase tracking-wider">Trạng thái cấu hình từ xa (Remote Config)</h3>
        {remoteConfig ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="border border-zinc-800/40 rounded-2xl bg-zinc-900/30 p-4">
                <span className="text-xs text-zinc-500 block mb-1">LLM Chính (Primary)</span>
                <span className="text-sm font-bold text-white uppercase">{remoteConfig.llm_settings?.primary?.provider}</span>
                <span className="text-xs text-zinc-400 block mt-0.5">Model: {remoteConfig.llm_settings?.primary?.model}</span>
              </div>
              <div className="border border-zinc-800/40 rounded-2xl bg-zinc-900/30 p-4">
                <span className="text-xs text-zinc-500 block mb-1">LLM Dự phòng (Fallback)</span>
                <span className="text-sm font-bold text-zinc-300 uppercase">{remoteConfig.llm_settings?.fallback?.provider}</span>
                <span className="text-xs text-zinc-400 block mt-0.5">Model: {remoteConfig.llm_settings?.fallback?.model}</span>
              </div>
            </div>

            <div className="p-4 border border-zinc-800/40 rounded-2xl bg-zinc-900/10 space-y-2">
              <span className="text-xs text-zinc-500 block">Cờ tính năng hoạt động (Feature Flags):</span>
              <div className="flex flex-wrap gap-4 text-xs">
                <span className="flex items-center gap-1.5 text-zinc-300">
                  <span className={`w-2 h-2 rounded-full ${remoteConfig.feature_flags?.content_engine_v2 ? 'bg-green-500' : 'bg-zinc-600'}`} />
                  Content Engine V2
                </span>
                <span className="flex items-center gap-1.5 text-zinc-300">
                  <span className={`w-2 h-2 rounded-full ${remoteConfig.feature_flags?.scheduler_v2 ? 'bg-green-500' : 'bg-zinc-600'}`} />
                  Trình Lập Lịch V2
                </span>
                <span className="flex items-center gap-1.5 text-zinc-300">
                  <span className={`w-2 h-2 rounded-full ${remoteConfig.feature_flags?.maintenance_mode ? 'bg-red-500 animate-pulse' : 'bg-green-500'}`} />
                  {remoteConfig.feature_flags?.maintenance_mode ? 'Bảo trì hệ thống' : 'Hoạt động bình thường'}
                </span>
              </div>
            </div>
          </div>
        ) : (
          <p className="text-xs text-zinc-500 italic">Đang tải cấu hình định tuyến hệ thống...</p>
        )}
      </div>

      <div>
        <h3 className="text-sm font-bold text-zinc-400 mb-3 uppercase tracking-wider">Thông tin phần mềm</h3>
        <div className="grid grid-cols-3 gap-4 text-xs text-zinc-400">
          <div>
            <span className="text-zinc-600 block">Nền tảng</span>
            <span className="text-white font-mono">{envInfo.platform}</span>
          </div>
          <div>
            <span className="text-zinc-600 block">Engine</span>
            <span className="text-white font-mono">Electron v{envInfo.version}</span>
          </div>
          <div>
            <span className="text-zinc-600 block">Thư mục Cache</span>
            <span className="text-white font-mono truncate block" title={envInfo.appPath}>{envInfo.appPath}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SystemSettingsPanel;
```

---

### 3.10 Component `<SystemUpdateBanner />` — Thông báo Cập nhật Phần mềm

**Vị trí:** Banner nổi ở top-right Dashboard (overlay, `z-index: 40`, không che modal z-50)

Component thông báo khi có bản cập nhật phần mềm mới. Tự động kiểm tra phiên bản từ backend, hiển thị banner slide-in và cung cấp tuỳ chọn cập nhật tức thì hoặc bỏ qua.

#### Layout Wireframe
```
                                              ┌────────────────────────────────────────────────┐
                                              │ 🚀 Bản cập nhật v2.1.0 đã sẵn sàng!           │
                                              │ Cải thiện: Tăng tốc AI, sửa lỗi posting...    │
                                              │                                                │
                                              │ [Cập nhật ngay]   [Để sau]   [Chi tiết ▼]      │
                                              └────────────────────────────────────────────────┘
```

#### Hành vi các nút
- **"Cập nhật ngay":** Trigger `POST /api/system/trigger-update` → Hiển thị progress bar + text `"Đang cập nhật..."`. Sau khi server restart → Browser tự reconnect WebSocket → Toast `"✅ Cập nhật thành công lên phiên bản vX.Y.Z"`. Extensions tự reload (xem Spec 01).
- **"Để sau":** Dismiss banner (slide-out). Hiển thị badge đỏ nhỏ (notification dot) trên icon ⚙️ Settings ở Sidebar để nhắc nhở.
- **"Chi tiết ▼":** Toggle expand/collapse khu vực changelog bên dưới banner. Changelog hiển thị dạng danh sách bullet points với các thay đổi chính.

#### Kiểm tra bản cập nhật
- Tự động gọi `GET /api/system/check-update` mỗi 30 phút (`setInterval`).
- Nếu `response.hasUpdate === true` → Hiển thị banner slide-in với animation `translateY(-100%) → translateY(0)` trong 400ms ease-out.

#### React Component Specification
```jsx
import React, { useState, useEffect } from 'react';

const SystemUpdateBanner = ({ onSettingsBadge }) => {
  const [updateInfo, setUpdateInfo] = useState(null);
  const [isVisible, setIsVisible] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [otaState, setOtaState] = useState({ status: 'idle', percent: 0 }); // dành riêng cho Electron OTA

  useEffect(() => {
    // Luồng 1: Nếu chạy trong Electron, dùng IPC cập nhật ngầm qua Preload Bridge
    if (window.electronAPI && typeof window.electronAPI.onUpdateStatus === 'function') {
      const unsubscribe = window.electronAPI.onUpdateStatus((event, payload) => {
        switch (event) {
          case 'checking':
            setOtaState({ status: 'checking', percent: 0 });
            break;
          case 'available':
            setUpdateInfo({
              version: payload.version,
              summary: 'Bản cập nhật lớn hệ thống mới nhất.',
              changelog: payload.releaseNotes ? payload.releaseNotes.split('\n') : []
            });
            setIsVisible(true);
            setOtaState({ status: 'available', percent: 0 });
            break;
          case 'progress':
            setOtaState({ status: 'progress', percent: payload.percent });
            break;
          case 'downloaded':
            setOtaState({ status: 'downloaded', percent: 100 });
            break;
          case 'error':
            setOtaState({ status: 'error', percent: 0, errorMsg: payload.message });
            break;
          default:
            break;
        }
      });
      return () => unsubscribe();
    }

    // Luồng 2: Fallback Web API (Standalone mode)
    const checkUpdate = async () => {
      try {
        const res = await fetch('/api/system/check-update');
        const data = await res.json();
        if (data.hasUpdate) {
          setUpdateInfo(data);
          setIsVisible(true);
        }
      } catch (err) {
        console.error('Lỗi kiểm tra cập nhật:', err);
      }
    };

    checkUpdate(); 
    const interval = setInterval(checkUpdate, 30 * 60 * 1000); 
    return () => clearInterval(interval);
  }, []);

  const handleUpdate = async () => {
    setIsUpdating(true);
    // Nếu chạy trong Electron, ra lệnh cài đặt bản cập nhật đã tải xong
    if (window.electronAPI && otaState.status === 'downloaded') {
      window.electronAPI.triggerInstall();
      return;
    }
    // Fallback REST API
    try {
      await fetch('/api/system/trigger-update', { method: 'POST' });
    } catch (err) {
      console.error('Lỗi khi cập nhật:', err);
      setIsUpdating(false);
    }
  };

  const handleDismiss = () => {
    setIsVisible(false);
    onSettingsBadge && onSettingsBadge(true);
  };

  if (!isVisible || !updateInfo) return null;

  return (
    <div
      className="fixed top-4 right-4 z-40 w-[420px] border border-cyan-500/30 rounded-2xl bg-zinc-950/95 backdrop-blur-xl shadow-[0_0_40px_rgba(6,182,212,0.15)] overflow-hidden"
      style={{ animation: 'slideDown 400ms ease-out' }}
    >
      {/* Header */}
      <div className="px-5 py-4">
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="text-lg">🚀</span>
            <h4 className="text-sm font-bold text-white">Bản cập nhật v{updateInfo.version} đã sẵn sàng!</h4>
          </div>
          <button
            onClick={handleDismiss}
            className="text-zinc-500 hover:text-white text-xs transition-colors"
          >
            ✕
          </button>
        </div>
        <p className="text-[11px] text-zinc-400 leading-relaxed">{updateInfo.summary}</p>
      </div>

      {/* Changelog (expandable) */}
      {isExpanded && updateInfo.changelog && (
        <div className="px-5 pb-3 border-t border-zinc-800/60 pt-3">
          <div className="text-[10px] font-bold uppercase tracking-wider text-zinc-500 mb-2">Changelog</div>
          <ul className="space-y-1">
            {updateInfo.changelog.map((item, idx) => (
              <li key={idx} className="text-[11px] text-zinc-300 flex items-start gap-1.5">
                <span className="text-cyan-400 mt-0.5">•</span>
                {item}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Action Bar */}
      <div className="bg-zinc-900/40 px-5 py-3 border-t border-zinc-800 flex items-center justify-between">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-[10px] text-zinc-500 hover:text-zinc-300 font-semibold transition-colors"
        >
          {isExpanded ? 'Ẩn chi tiết ▲' : 'Chi tiết ▼'}
        </button>
        <div className="flex gap-2">
          <button
            onClick={handleDismiss}
            className="px-3 py-1.5 border border-zinc-800 rounded-lg text-zinc-400 font-medium hover:text-white hover:bg-zinc-900 transition-colors text-[10px]"
          >
            Để sau
          </button>
          <button
            onClick={handleUpdate}
            disabled={isUpdating}
            className="px-4 py-1.5 bg-gradient-to-r from-cyan-500 to-emerald-500 text-black font-extrabold rounded-lg text-[10px] hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {isUpdating ? '⏳ Đang cập nhật...' : 'Cập nhật ngay'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default SystemUpdateBanner;
```

#### CSS Animation (thêm vào `index.css`)
```css
@keyframes slideDown {
  from {
    transform: translateY(-100%);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}
```

---

## 📐 4. Quy Tắc Phân Bổ Không Gian & Kiểm Soát Pop-Up Chi Tiết (Layout Real Estate Allocation & Pop-Up Control)

Để đảm bảo các tính năng được phát triển trong backend đều có đầu ra trực quan trên giao diện người dùng (không bị code ngầm rồi bỏ quên trên UI/UX), đồng thời khống chế tỷ lệ hiển thị hợp lý và ngăn chặn xung đột Pop-ups (z-index fight/spam), Dashboard tuân thủ nghiêm ngặt các hướng dẫn thiết kế sau:

### 4.1. Bản Đồ Phân Bổ Không Gian Giao Diện (Visual Hierarchy & Grid Layout)

Hệ thống áp dụng tỷ lệ phân bổ không gian **60% Core Area / 30% Control Area / 10% Navigation Area** trên giao diện:

```
+------------------------------------------------------------------------------------+
| [10% Navigation] Top Header: System Status & Global Health                        |
+---------------------+--------------------------------------------------------------+
|                     |                                                              |
|                     | [60% Core Area - Ưu tiên diện tích lớn]                      |
| [10% Navigation]    | - Live Console Grid: Hiển thị Live Status của các Workers    |
| Sidebar             | - Content Engine: Split-view, Sticky Post Preview chiếm 60%  |
| - tab Live Console  |                                                              |
| - tab Campaigns     +--------------------------------------------------------------+
| - tab Accounts      | [30% Control Area - Phụ trợ, bọc thu gọn]                    |
| - tab Settings      | - Settings Panel: Accordion/Spoiler cho cấu hình nâng cao    |
|                     | - Logs Terminal: Đáy màn hình, có nút Collapse/Expand        |
+---------------------+--------------------------------------------------------------+
```

1.  **Chính sách Phân cấp trực quan (Visual Priority Policy):**
    *   **Core Area (60%):** Dành riêng cho dữ liệu mà người dùng cần theo dõi dồn dập (Live Grid của Agents và tệp Preview Card của AI Composer). Chặn tuyệt đối việc nhét các panel cấu hình phụ vào khu vực này làm rối mắt.
    *   **Control & Settings Area (30%):** Các panel cấu hình phải được bọc trong các component thu gọn thông minh (Accordion/Details). Mặc định ẩn (`collapsed`), chỉ mở ra khi click "Cấu hình chi tiết".
    *   **Navigation (10%):** Sidebar và Header thu gọn tối đa, chỉ hiện icons và labels ngắn, viền mỏng 1px Zinc-800 để nhường không gian cho Core Area.

2.  **Đặc tả Khả năng Tương Tác (Interactive Capabilities Checklist):**
    *   *Clickable States:* Mọi thẻ điều khiển, toggle, button bắt buộc phải có hiệu ứng scale và shadow khi hover/active:
        `hover:scale-[1.02] hover:bg-zinc-800/80 active:scale-[0.98] transition-all duration-150`
    *   *Hover States (Rê chuột):* Khi rê chuột lên một card Agent hoặc Card Proxy, hệ thống bắt buộc hiển thị một Custom Tooltip bám chuột (Tooltip component `z-30`) chứa các thông số ẩn: IP thực, dung lượng RAM Chrome đang ngốn, thời gian cooldown và danh sách 5 sự kiện lỗi gần nhất.
    *   *Scrollable Container:* Mọi container cuộn (ví dụ: Terminal logs, Account lists, Spintax presets) bắt buộc phải bọc trong các block CSS có overflow riêng biệt (`overflow-y-auto overflow-x-hidden`) và tùy biến thanh cuộn mỏng (CSS scrollbar zinc-800, width-2). Cấm tuyệt đối việc cuộn toàn trang (Global Body Scrollbar).

---

### 4.2. Kỷ Luật Kiểm Sát Pop-Up Đa Tầng (Z-Index & Modal Queue Protocol)

Để tránh hiện tượng chồng lấp popup (z-index fight), đè cảnh báo bảo mật, hoặc spam hộp thoại làm treo đơ UI, Dashboard thiết lập quy chuẩn quản lý Pop-up như sau:

#### 1. Bảng Đăng Ký Tầng z-index chuẩn hóa (Z-Index Registry)
Mọi component trong dự án bắt buộc phải khai báo lớp z-index tuân thủ chính xác bảng sau:

| Tầng z-index | CSS Class | Đối Tượng Áp Dụng | Mô tả |
|:---|:---|:---|:---|
| `0` | `z-0` | Base Dashboard Layout | Nền ứng dụng, biểu đồ cột, main grid |
| `10` | `z-10` | Sticky Header, Fixed Sidebar | Các thanh điều hướng cố định khi cuộn |
| `20` | `z-20` | Dropdown Menus, Context Menus | Menu bộ lọc, danh sách click-chuột-phải |
| `30` | `z-30` | Normal Tooltips, Donation Banner | Các chú thích bám chuột, beggar banner chạy nền |
| `40` | `z-40` | Standard Modals (AddKey, Import) | Các modal cài đặt, form nhập liệu thêm key |
| `50` | `z-50` | Emergency modals (Escalation, Captcha)| Hộp thoại can thiệp khẩn cấp, giải OTP |
| `9999` | `z-[9999]`| Lockout Screen (BSOD, ERR-SEC-99) | Màn hình xanh khóa cứng khi bị bypass lậu UI |

#### 2. Quy Tắc Hàng Đợi Modal (Modal Queue Rules)
*   **Cấm Chồng Lấp (No Overlay Stack):** Chỉ cho phép hiển thị **tối đa một Standard Modal** (`z-40`) trên màn hình tại một thời điểm.
*   **Hàng đợi thông báo (Modal Queue):** Nếu có một modal cấp thấp đang mở (Ví dụ: `DonationModal` đang hiển thị) và backend bắn WebSocket yêu cầu giải OTP (`ERR-ESC-23`), hệ thống sẽ:
    1.  Tạm ẩn/Đẩy DonationModal vào trạng thái chờ (Queue).
    2.  Kích hoạt bật nảy `EmergencyEscalationGateway` ở tầng `z-50` đè lên trên cùng để Người dùng xử lý ngay.
    3.  Sau khi Người dùng duyệt/hoàn thành giải xác thực ở modal `z-50`, modal này đóng lại và DonationModal sẽ được khôi phục hiển thị từ Queue.

#### 3. Quy Tắc Đóng/Mở & Click-Out (Dismissal Discipline)
*   **Standard Modals (AddKey, Settings):** 
    *   Hỗ trợ đóng nhanh bằng cách click ra ngoài vùng modal (Overlay Click) hoặc nhấn phím `Esc` trên bàn phím.
*   **Confirm Modals (Import Database, Delete Campaign):**
    *   Cấm tuyệt đối việc click ra ngoài để đóng. Phím `Esc` bị chặn. Người dùng bắt buộc phải click nút "Xác Nhận" (Đỏ/Emerald) hoặc "Hủy" (Zinc) để đóng hộp thoại rõ ràng.
*   **Emergency Modals (EmergencyEscalationGateway):**
    *   Khóa cứng toàn bộ hành vi click-out và phím `Esc`. 
    *   Modal này là một **Chốt chặn Giao dịch (Approval Gate)**. Người dùng bắt buộc phải thực hiện nhập liệu/verify và click "Approve (Duyệt)" hoặc "Reject (Tắt luồng)" để hệ thống giải phóng luồng chạy, cấm tắt ngầm.

---

## 🔄 5. State Management & Realtime Data Flow

Kiến trúc luồng dữ liệu thời gian thực được thiết kế theo mô hình **Tập trung hóa (Centralized Data Flow)** để đảm bảo tính nhất quán và hiệu năng:

```
                  +-----------------------------------+
                  |      Dashboard Socket Server      |
                  +-----------------------------------+
                                    |
                                    | (WebSocket: Port 3000/ws)
                                    v
                  +-----------------------------------+
                  |         App Context Layer         |
                  |     - activeSessions (Map State)  |
                  +-----------------------------------+
                                    |
                  +-----------------+-----------------+
                  | (Unidirectional Data Flow: Props) |
                  v                                   v
       +--------------------+               +--------------------+
       |   LiveAgentGrid    |               |  RealtimeTerminal  |
       |  (Worker Grid)     |               |  (Logs via SSE)    |
       +--------------------+               +--------------------+
```

1. **Global Store:** Sử dụng React Context API (AppContext) để kết nối WebSocket duy nhất tại root level khi ứng dụng khởi chạy.
2. **WebSocket Router:** Khi nhận được message cập nhật trạng thái từ backend (`SESSION_EVENT`, `HEARTBEAT`, `COMMAND_RESULT`):
   - Parser tại Context sẽ tính toán cập nhật một Map `activeSessions` duy nhất, sử dụng `accountId` làm key.
   - Tránh việc update nhiều sub-state rải rác.
3. **Subscribers:** Component `<LiveAgentGrid />` subscribe trực tiếp vào `activeSessions` và render danh sách các `<AgentCard />`.
4. **SSE Integration:** Component Terminal mở một cổng Server-Sent Events riêng, độc lập hoàn toàn với WebSocket để truyền logs, giải phóng băng thông cho các sự kiện điều phối live.

---

## 🚨 6. Cảnh Báo Đỏ Chống AI Ảo Tưởng (UI Red Flags)

Khi giao việc phát triển giao diện React cho coding agent, **bắt buộc** phải tuân thủ nghiêm ngặt các kỷ luật sau:

- **🚨 [FLAG-01] Cấm Dùng Array Index Làm React Key:**
  - AI Agent khi lập trình vòng lặp `.map` thường dùng `key={index}`. Điều này cực kỳ nguy hại cho giao diện thời gian thực. Khi một tài khoản bị lỗi và ngắt kết nối (bị xoá khỏi Grid), React sẽ tính sai index và hoán đổi nhầm cửa sổ Console của tài khoản này sang tài khoản khác.
  - **Kỷ luật:** Bắt buộc sử dụng `key={session.accountId}`.
- **🚨 [FLAG-02] Cấm Local Socket Event Listener Tại Component Con:**
  - Nghiêm cấm Agent khởi tạo các hàm lắng nghe sự kiện (`ws.onmessage`, `EventSource`) trực tiếp bên trong từng component `<AgentCard />` riêng lẻ. Việc này sẽ nhân bản số lượng socket listeners lên gấp N lần (N = số tài khoản chạy song song), gây tràn bộ nhớ (Memory Leak) và đơ trình duyệt sau vài phút chạy.
  - **Kỷ luật:** Chỉ thiết lập listeners tại Context/Grid cha, truyền dữ liệu sạch dạng Props xuống card con.
- **🚨 [FLAG-03] Chặn Nghẽn Lũy Kế logs Trong DOM:**
  - Nếu hệ thống chạy liên tục hàng giờ, số lượng logs cuộn trong Terminal có thể lên tới hàng triệu phần tử. Nếu render tất cả, bộ nhớ DOM của Chrome sẽ bị quá tải (Chrome Out Of Memory).
  - **Kỷ luật:** Bắt buộc áp dụng `.slice(-500)` để khống chế số lượng log tối đa hiển thị trên màn hình DOM.
- **🚨 [FLAG-04] Khống chế Text Overflow Bằng Layout Cố Định:**
  - Thông báo lỗi và đường dẫn URL từ AI Brain hoặc API có độ dài cực kỳ ngẫu nhiên. Nếu không khống chế, card Agent sẽ bị giãn nở chiều cao vô tội vạ làm lệch Grid.
  - **Kỷ luật:** Toàn bộ Agent Card phải giữ chiều cao cố định tuyệt đối `280px` bằng cách bọc text trong `line-clamp-2` kết hợp `break-words`.
- **🚨 [FLAG-05] Throttling Render Cho Realtime Logs:**
  - Tần suất sự kiện logs của hàng chục luồng chạy song song là cực kỳ dày đặc. Nếu React cập nhật state ngay khi nhận mỗi dòng log đơn lẻ, UI sẽ bị re-render hàng trăm lần một giây gây đóng băng trình duyệt (UI Freeze).
  - **Kỷ luật:** Bắt buộc lưu log tạm vào một bộ đệm `useRef Array`, sử dụng một setInterval chu kỳ `300ms` để rút log từ buffer và cập nhật State hiển thị một lần.
- **🚨 [FLAG-06] Khóa Cứng Bảo Vệ Mô-đun Quyên Góp (Anti-Bypass Protection):**
  - AI Agent hoặc Developer tuyệt đối không được viết code hoặc sửa CSS để ẩn, chặn hoặc xóa bỏ component `<VirtualDevBeggar />` khỏi DOM của ứng dụng. Component bắt buộc phải được theo dõi bởi `MutationObserver` tại root level. Mọi hành vi can thiệp hiển thị trái phép sẽ lập tức gọi API `/api/system/lockout` khóa cứng luồng đăng của toàn bộ tài khoản và hiển thị màn hình khóa BSOD với mã lỗi `ERR-SEC-99`.
  - **Kỷ luật:** Giữ nguyên tính vẹn toàn hiển thị của component Beggar, không bypass.

---

## 🎨 7. Giao Diện Mẫu Thực Tế (Visual Mockups)


Dưới đây là các giao diện mẫu thực tế đã được thiết kế theo đúng ngôn ngữ và đặc tả của hệ thống để đội ngũ phát triển tham khảo và implement:

### 6.1 Giao diện Dashboard Điều Phối (Local Desktop App)
![Giao diện Dashboard Điều Phối](/home/newuser/AI_facepostgroup/specs/assets/dashboard_ui_mockup.png)

*Hình 6.1: Dashboard điều phối thời gian thực với Sidebar Zinc-950, danh sách Account Status có màu neon chỉ định điểm HP/Trạng thái và biểu đồ Live-stream Campaign Performance.*


### 6.2 Giao diện Chrome Extension Popup
![Giao diện Chrome Extension Popup](/home/newuser/AI_facepostgroup/specs/assets/extension_ui_mockup.png)

*Hình 6.2: Popup của Hermes Anti-Detection Extension hiển thị trạng thái CONNECTED xanh neon, thông tin SOCKS5 proxy cô lập, và panel theo dõi Live Posting Session.*

---

## 🌐 8. Thiết Kế Đa Ngôn Ngữ Toàn Cầu (Global i18n Specification)

Để hỗ trợ từ 100-200 ngôn ngữ toàn cầu mà không làm quá tải băng thông mạng và phình to gói bundle của ứng dụng React, hệ thống bản địa hóa của Hermes tuân thủ các đặc tả kỹ thuật sau:

### 8.1 Lazy Loading & Code Splitting (Tải động theo yêu cầu)
- Gói dịch ngôn ngữ cho Dashboard được phân chia thành các tệp JSON độc lập đặt tại `/dashboard/src/locales/` dưới định dạng `<mã_ngôn_ngữ>.json`.
- Giao diện Dashboard bắt buộc sử dụng **dynamic import** (`await import('./locales/[lang].json')`) để tải bất đồng bộ tệp ngôn ngữ khi khởi tạo hoặc khi người dùng thực hiện chuyển đổi ngôn ngữ trong cài đặt.
- Trong thời gian tải tệp dịch (Asynchronous Transition State), React UI phải hiển thị màn hình chờ (Loading) hoặc cấu trúc khung xương (Skeleton) để giữ trải nghiệm người dùng mượt mà và tránh giật lag.

### 8.2 Fallback Chain (Chuỗi dự phòng an toàn)
- Khi phát hiện mã ngôn ngữ có chỉ mục quốc gia (ví dụ: `zh-TW`, `en-US`), hệ thống thực hiện phân rã chuỗi theo thứ tự ưu tiên:
  1. Thử tải tệp dịch chi tiết: `<language>-<country>.json` (ví dụ: `zh-tw.json`).
  2. Thử tải tệp dịch ngôn ngữ gốc: `<language>.json` (ví dụ: `zh.json`).
  3. Thử tải ngôn ngữ mặc định hệ thống: `en.json` (Tiếng Anh).
- Nếu toàn bộ chuỗi fallback thất bại, hàm dịch `t('spec.key')` sẽ trả về chính xác chuỗi đường dẫn `'spec.key'` để hỗ trợ nhà phát triển dễ dàng gỡ lỗi (debug).

### 8.3 Chrome Extension Localization
- Extension sử dụng API nội bộ `chrome.i18n` và cấu trúc thư mục chuẩn `_locales/<mã_ngôn_ngữ>/messages.json`.
- Mọi nhãn hiển thị trong `manifest.json` và Chrome Web Store phải được khai báo dạng token `__MSG_appName__` để Chrome tự động map theo vùng của tài khoản người dùng.

---

## Cảnh báo An ninh & Lỗ hổng Kiến trúc

### 🔴 LỖ HỔNG CRITICAL
1. **[XSS] Lỗ hổng React XSS trong Log Terminal và Preview Cards:**
   - *Rủi ro:* Trong component `<RealtimeLogTerminal />`, nếu dùng `dangerouslySetInnerHTML` để render màu ANSI của log hoặc hiển thị metadata (`og:title`, `og:image` của Link Preview Cards) từ DOM Facebook gửi lên mà không sanitize, hacker có thể chèn XSS payload vào tên group/post để thực thi JavaScript độc hại ngay trên Dashboard của quản trị viên.
   - *Yêu cầu Remediation:* Tuyệt đối không dùng `dangerouslySetInnerHTML` trực tiếp. Hãy dùng thư viện an toàn như `ansi-to-react` (tự render React elements thay vì tiêm chuỗi HTML). Nếu bắt buộc dùng HTML, phải bọc qua thư viện lọc thẻ **DOMPurify** (`DOMPurify.sanitize(message)`). Kiểm tra giao thức URL (chỉ cho phép http/https, cấm javascript:).
2. **[RCE] Lỗ hổng Electron Context Bridge & RCE:**
   - *Rủi ro:* Preload script của Electron nếu chuyển tiếp trực tiếp đối tượng `event` của `ipcRenderer.on` sang Renderer process sẽ làm lộ `event.sender` (chứa WebContents). Kẻ tấn công XSS có thể lợi dụng điều này để gửi IPC tự do tới Main Process. Đồng thời, các hàm CLI ở Main Process nếu nhận chuỗi thô từ Renderer mà không validate kiểu dữ liệu sẽ bị Command Injection dẫn đến RCE.
   - *Yêu cầu Remediation:* Preload script phải "nuốt" đối tượng `event` (chỉ chuyển tiếp dữ liệu payload thực tế). Áp dụng danh sách trắng (Whitelist) cho các kênh IPC, tránh dùng synchronous APIs (`sendSync`) và Main Process phải xác thực kiểu dữ liệu nghiêm ngặt cho mọi tham số nhận được.

### 🟠 LỖ HỔNG HIGH
1. **[BYPASS] Bypass cơ chế chống tắt Popup quyên góp (`VirtualDevBeggar`):**
   - *Rủi ro:* Kẻ tấn công có thể dễ dàng bypass popup quyên góp bằng cách: 1) Tiêm thẻ `<style>` vào `<head>` để ẩn popup (MutationObserver đang quan sát `body` sẽ không phát hiện computed style thay đổi); 2) Ghi đè MutationObserver trước khi React load; 3) Chặn cuộc gọi API `/api/system/lockout` qua monkeypatching `fetch`; 4) Sửa đổi biến memory qua React DevTools.
   - *Yêu cầu Remediation:* Sử dụng cơ chế Style Polling định kỳ (`getComputedStyle`) để kiểm tra display/visibility thực tế của popup. Triển khai cơ chế xác thực nhịp tim phía máy chủ (Server-side Heartbeat Validation) để khóa API từ backend nếu client không gửi heartbeat. Sử dụng tham chiếu fetch bảo mật trong closure kín từ sớm và ký số (Signed JWT/HMAC) các cấu hình backend.

---


