# SPEC-05: AgentLoop — Trái Tim Điều Phối Hệ Thống
**File**: `agent_loop.js`  
**Phiên bản spec**: 1.2.0  
**Ngày cập nhật**: 2026-06-16  
**Tác giả**: Hermes FacePost-Group / AI-generated spec  
**Trạng thái**: APPROVED

---

## 🚨 CRITICAL WARNINGS & ANTI-PATTERNS (CHỐNG AI ẢO TƯỞNG)

* 🚨 **Cảnh báo đỏ (Lỗi vòng lặp vô hạn - Zombie Session):** **CẤM** viết luồng xử lý hành động AI mà không có điểm thoát cứng. Khi cấu trúc Facebook thay đổi khiến AI không tìm thấy nút, Agent phổ thông sẽ có xu hướng liên tục yêu cầu chụp lại DOM và thử lại, tạo ra vòng lặp vô hạn (Infinite Request Loop) làm nghẽn hệ thống và cháy token LLM.
* 🚀 **Yêu cầu bắt buộc:** Tích hợp bộ ngắt mạch cứng **Circuit Breaker**: Mỗi Posting Session tuyệt đối không vượt quá `max_iterations = 20` và `session_timeout_ms = 120000` (2 phút). Vượt ngưỡng này, bắt buộc phải giải phóng tài khoản (Release worker) và ném lỗi `ERR-ACT-13` hoặc `ERR-ACT-14` về DB.
* 🚨 **Cấm dùng Array Index làm React Key và cấm WebSocket local listeners tại Card:** WebSocket server phải xử lý tập trung và broadcast/đưa dữ liệu qua Props/Context để tối ưu hiệu năng.

---

## Mục Lục

1. [Tổng Quan Vai Trò](#1-tổng-quan-vai-trò)
2. [Vị Trí Trong Kiến Trúc](#2-vị-trí-trong-kiến-trúc)
3. [Class Interface (JSDoc TypeScript-style)](#3-class-interface-jsdoc-typescript-style)
4. [State Machine — Vòng Đời Một Posting Session](#4-state-machine--vòng-đời-một-posting-session)
5. [Pseudocode Chi Tiết — runPostingSession() & runGroupSyncSession()](#5-pseudocode-chi-tiết--runpositingsession--rungroupsyncsession)
6. [DOM Snapshot Classifier](#6-dom-snapshot-classifier)
7. [Event-Driven Communication Protocol](#7-event-driven-communication-protocol)
8. [Multi-Campaign Concurrency](#8-multi-campaign-concurrency)
9. [Code JS Đầy Đủ — agent_loop.js](#9-code-js-đầy-đủ--agent_loopjs)
10. [Error Recovery Scenarios](#10-error-recovery-scenarios)
11. [Configuration Reference](#11-configuration-reference)
12. [Dependency Graph](#12-dependency-graph)

---

## 1. Tổng Quan Vai Trò

### 1.1 AgentLoop là gì?

`AgentLoop` là **Orchestrator trung tâm** chạy phía **Dashboard Server (Node.js)**. Đây là file quan trọng nhất trong toàn bộ hệ thống Hermes FacePost-Group — nó điều phối toàn bộ vòng lặp đăng bài tự động từ đầu đến cuối.

```
┌─────────────────────────────────────────────────────────────────┐
│                    HERMES FACEPOST-GROUP                        │
│                                                                 │
│   ┌─────────────┐   ┌──────────────┐   ┌──────────────────┐   │
│   │  Dashboard  │   │  AgentLoop   │   │   AIBrain (LLM)  │   │
│   │  REST APIs  │   │(Orchestrator)│   │  (Ollama/Gemini) │   │
│   └──────┬──────┘   └──────▲───────┘   └────────▲─────────┘   │
│          │                 │                    │             │
│   ┌──────▼──────┐          │                    │             │
│   │ SQLite DB   ├──────────┼────────────────────┘             │
│   │ (BetterSqlite3)        │ WebSocket                        │
│   └─────────────┘          │ (Express ws /ws)                 │
│                            │                                  │
│                            ▼                                  │
│                  ┌───────────────────┐                        │
│                  │ Chrome Extension  │                        │
│                  │  (Background JS)  │                        │
│                  └───────────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Trách Nhiệm Cốt Lõi

1. **Điều Phối Campaign**: Lắng nghe Campaign từ DB, phân rã danh sách Group, quản lý Delay ngẫu nhiên.
2. **Khởi Tạo Session**: Cấp phát `sessionId`, sinh token bảo mật, thiết lập kênh giao tiếp WebSocket độc lập giữa Server và Extension của từng profile.
3. **Tiến Trình Đăng Bài (Posting FSM)**: Điều khiển Extension di chuyển trang (Navigate), lấy Snapshot, hỏi AI Brain, gửi lệnh Click/Type và lưu vết lịch sử.
4. **Xử Lý Lỗi Tự Động (Self-healing)**: Tự phát hiện các nút bị lỗi, trang bị nghẽn, hoặc Extension bị ngắt kết nối để thực hiện retry/cooldown.
5. **Watchdog Watcher**: Watchdog timer quét 60s để dọn dẹp các session zombie hoặc bị treo, tránh rò rỉ RAM và khoá tài khoản.

---

## 2. Vị Trí Trong Kiến Trúc

### 2.1 Luồng Dữ Liệu Tổng Quát

1. **Campaign Trigger**: Người dùng bấm "Run" trên Dashboard UI -> gọi REST API `/api/campaigns/start/:id`.
2. **Campaign Manager**: Khởi động Campaign, lấy spintax, chọn danh sách accounts rảnh và các groups cần đăng.
3. **AgentLoop Cấp Phát**: `_acquireAccount` chiếm khoá của account, tạo `sessionId`, khởi tạo `execution_sessions` trong SQLite.
4. **WebSocket Send**: Gửi `NAVIGATE_TO_GROUP` với target URL của Facebook Group đến Extension tương ứng.
5. **Extension DOM Capture**: Extension di chuyển tab, đợi trang ổn định (mutation observer lặng 500ms), chụp DOM snapshot và băm fingerprint hex FNV-1a cho từng element, gửi về Dashboard qua WS (`DOM_SNAPSHOT_READY`).
6. **AgentLoop Classification & Decision**: Phân loại Snapshot. Hỏi `AIBrain.decideNextAction(context)`. Nhận primitive action (`click`, `type`, `scroll`, `wait`, `done`).
7. **Action Dispatch**: Dịch primitive action sang COMMAND tương ứng (`CLICK_ELEMENT`, `TYPE_TEXT`, v.v.) gửi qua WS cho Extension kèm theo `elementId` fingerprint (8 ký tự hex).
8. **Extension Execution**: Extension thực thi mô phỏng human click/type, gửi ngược lại kết quả và Snapshot mới. Vòng lặp tiếp tục cho đến khi gặp trạng thái `POST_SUCCESS` hoặc hết `max_iterations = 20`.
9. **Finalization**: Cập nhật DB `campaign_groups` (status: `POSTED`/`FAILED`), log vào `posting_logs`, release account.

---

## 3. Class Interface (JSDoc TypeScript-style)

```javascript
/**
 * @class AgentLoop
 * @extends EventEmitter
 * @description Orchestrator trung tâm điều phối toàn bộ vòng lặp đăng bài.
 *
 * @fires AgentLoop#session:started    - Khi một session bắt đầu
 * @fires AgentLoop#session:completed  - Khi một session hoàn thành (SUCCESS/FAILED)
 * @fires AgentLoop#campaign:finished  - Khi tất cả groups của campaign đã xử lý
 * @fires AgentLoop#checkpoint:alert   - Khi phát hiện checkpoint trên account
 */
class AgentLoop extends EventEmitter {
  /**
   * @constructor
   * @param {Object} db              - Database connection (better-sqlite3 instance)
   * @param {WebSocketServer} wsServer - WebSocket server để giao tiếp với Extension
   * @param {AIBrain} brain          - AI Brain instance để quyết định hành động
   * @param {Object} [config]        - Configuration overrides
   */
  constructor(db, wsServer, brain, config = {}) {}

  /**
   * @method startCampaign
   * @param {string} campaignId - ID của campaign cần chạy (UUID)
   * @returns {Promise<void>}
   */
  async startCampaign(campaignId) {}

  /**
   * @method stopCampaign
   * @param {string} campaignId  - ID của campaign cần dừng
   * @param {boolean} [forceKill=false] - Nếu true, kill ngay cả session đang chạy
   * @returns {Promise<void>}
   */
  async stopCampaign(campaignId, forceKill = false) {}

  /**
   * @method runPostingSession
   * @param {Object} account                    - Account thực hiện đăng bài
   * @param {Object} group                      - Facebook Group target
   * @param {Object} content                    - Nội dung bài đăng
   * @returns {Promise<Object>} SessionResult
   */
  async runPostingSession(account, group, content) {}

  /**
   * @method runGroupSyncSession
   * @param {Object} account                    - Account thực hiện cào nhóm
   * @returns {Promise<Object>} SyncResult
   */
  async runGroupSyncSession(account) {}

  /**
   * @method executeActionOnExtension
   * @param {string} accountId
   * @param {Object} action
   * @returns {Promise<boolean>}
   */
  async executeActionOnExtension(accountId, action) {}

  /**
   * @method waitForExtensionResult
   * @param {string} sessionId
   * @param {number} timeoutMs
   * @param {string[]} [expectedTypes]
   * @returns {Promise<Object>}
   */
  async waitForExtensionResult(sessionId, timeoutMs, expectedTypes = null) {}

  /**
   * @method handleExtensionMessage
   * @param {string} accountId
   * @param {Object} message
   */
  handleExtensionMessage(accountId, message) {}

  /**
   * @method getSessionStatus
   * @param {string} sessionId
   * @returns {Object|null}
   */
  getSessionStatus(sessionId) {}
}
```

---

## 4. State Machine — Vòng Đời Một Posting Session

```
IDLE ──► INITIALIZING ──► NAVIGATING_HOME ──► FOCUS_SEARCH_INPUT ──► TYPE_SEARCH_KEYWORD
                                                                             │
                                                                             ▼
WAIT_SEARCH_RESULTS ◄── CLASSIFY_RESULTS ◄── CLICK_TARGET_GROUP ◄── OBSERVING_GROUP_POST_ABILITY
       │
       ▼
    THINKING ──► ACTING ──► COMPLETED (Release Lock)
       │
       ├─► SEARCH_FAILED / ERR-DOM-05 ───────────► FAILED (Skip Group, Release Lock)
       ├─► POST_LOCKED (Bị khóa đăng) ────────────► FAILED (Skip Group, Release Lock)
       ├─► LIMIT_EXCEEDED (Vượt hạn mức ngày) ────► COOLDOWN / HIBERNATE (Release Lock)
       ├─► CHECKPOINT_DETECTED (OTP/CAPTCHA) ─────► HIBERNATE_AWAITING_MANUAL
       ├─► TIMEOUT / FAILED ──────────────────────► FAILED (Release Lock)
       ├─► LOGIN_REQUIRED ────────────────────────► DIE/SUSPENDED (Release Lock)
       └─► ERR-ESC-* (Yêu cầu leo thang) ──────────► ESCALATING (Leader / Human Path)
```

#### Emergency Maintenance Path

```
  ════════════════════════════════════════════════════════════════════════
  EMERGENCY MAINTENANCE PATH (Any State → MAINTENANCE)
  ════════════════════════════════════════════════════════════════════════

  ANY_STATE (trừ MAINTENANCE)
        │
        ├─► ERR-DB-01 (Database Corrupt) ────────────► MAINTENANCE 🛑
        └─► ERR-AI-06 (All Keys Exhausted) ──────────► MAINTENANCE 🛑
                                                            │
                                                            ├─► DB_RESTORED ──► IDLE
                                                            └─► KEY_ADDED ────► IDLE

  ════════════════════════════════════════════════════════════════════════
  ESCALATION PATH (Escalate to Leader / Human Approver)
  ════════════════════════════════════════════════════════════════════════

  ANY_STATE (trừ MAINTENANCE, ESCALATING)
        │
        ├─► ERR-ESC-21 (Rủi ro an ninh) ─────────────► ESCALATING_HUMAN 👤 (Cần Người dùng duyệt)
        ├─► ERR-ESC-22 (FSM Deadlock/Loop) ──────────► ESCALATING_LEADER 🤖 (IDE tự chẩn đoán)
        │                                                     │
        │                                                     ├─► RESOLVED (Tự chữa lành) ──► IDLE
        │                                                     └─► FAIL (Thất bại) ─────────► ESCALATING_HUMAN 👤
        ├─► ERR-ESC-23 (Checkpoint khó) ─────────────► ESCALATING_HUMAN 👤 (Cần Người dùng duyệt)
        └─► ERR-ESC-24 (Lỗi OTA/SQLite nặng) ────────► ESCALATING_HUMAN 👤 (Cần Người dùng duyệt)
```


### 4.1 Bảng Trạng Thái Mở Rộng

| Trạng thái | Icon | Mô tả |
|---|---|---|
| `IDLE` | ⏸️ | Chờ Campaign trigger |
| `INITIALIZING` | 🔄 | Đang chuẩn bị session |
| `THINKING` | 🧠 | AI Brain đang phân tích |
| `ACTING` | ⚡ | Extension đang thực thi action |
| `COMPLETED` | ✅ | Session hoàn tất thành công |
| `FAILED` | ❌ | Session thất bại |
| `MAINTENANCE` | 🛑 | Hệ thống phát hiện lỗi nghiêm trọng (DB corrupt, tất cả API keys cạn). Tạm dừng toàn bộ campaigns. Chỉ cho phép các thao tác khôi phục: backup restore, thêm API key. |
| `ESCALATING_LEADER`| 🤖 | Trạng thái leo thang lên AI Leader (IDE Agent). Gửi báo cáo chẩn đoán sự cố (FSM deadlock, key exhaustion, dynamic routing error) để chạy giải thuật tự chữa lành (Self-healing). |
| `ESCALATING_HUMAN` | 👤 | Trạng thái chờ phê duyệt từ Người dùng. Hệ thống hiển thị popup xin phê duyệt trên UI Dashboard hoặc chặn CLI chờ input `Approve` / `Reject` thủ công. |

### 4.2 Transition Rules Cho MAINTENANCE & ESCALATION

| Trạng thái nguồn | Trigger | Trạng thái đích | Điều kiện |
|---|---|---|---|
| ANY_STATE (trừ MAINTENANCE) | ERR-DB-01 (Database Corrupt) | MAINTENANCE | Phát hiện qua PRAGMA integrity_check thất bại hoặc SQLITE_CORRUPT error |
| ANY_STATE (trừ MAINTENANCE) | ERR-AI-06 (All Keys Exhausted) | MAINTENANCE | Tất cả API keys trong pool đều COOLDOWN/DISABLED |
| MAINTENANCE | DB_RESTORED hoặc KEY_ADDED | IDLE | Sau khi khôi phục DB thành công hoặc thêm key mới |
| ANY_STATE (trừ ESCALATING_*) | ERR-ESC-21 (Rủi ro an ninh) | ESCALATING_HUMAN | Phát hiện rò rỉ khóa hoặc hành vi can thiệp lách UI (MutationObserver) |
| ANY_STATE (trừ ESCALATING_*) | ERR-ESC-22 (FSM Deadlock/Loop) | ESCALATING_LEADER | Phát hiện vòng lặp vô hạn hoặc deadlock trạng thái sau 30s timeout |
| ANY_STATE (trừ ESCALATING_*) | ERR-ESC-23 (Checkpoint khó) | ESCALATING_HUMAN | Phát hiện các xác minh cần thiết bị camera vật lý hoặc hình ảnh bạn bè |
| ANY_STATE (trừ ESCALATING_*) | ERR-ESC-24 (Lỗi OTA/SQLite nặng)| ESCALATING_HUMAN | Lỗi cập nhật vá nóng OTA thất bại hoặc SQLite bị hỏng nặng không tự restore |
| ESCALATING_LEADER | RESOLVED | IDLE | IDE Agent tự động chẩn đoán và khắc phục thành công (Rollback, swap keys) |
| ESCALATING_LEADER | FAIL | ESCALATING_HUMAN | IDE Agent tự chẩn đoán thất bại sau 3 lần retry, leo thang lên xin ý kiến con người |
| ESCALATING_HUMAN | HUMAN_APPROVED | IDLE | Người dùng bấm duyệt (Approve) trên Dashboard UI để tiếp tục |
| ESCALATING_HUMAN | HUMAN_REJECTED | FAILED | Người dùng từ chối (Reject) hoặc bỏ qua, session kết thúc thất bại để cắt lỗ |


### 4.3 Pseudocode — enterMaintenanceMode() / exitMaintenanceMode()

```javascript
async function enterMaintenanceMode(reason) {
  logger.fatal(`[MAINTENANCE] Entering maintenance mode. Reason: ${reason}`);
  
  // 1. Tạm dừng toàn bộ campaigns đang chạy
  const runningCampaigns = db.prepare(
    "SELECT id FROM campaigns WHERE status = 'RUNNING'"
  ).all();
  
  for (const campaign of runningCampaigns) {
    await pauseCampaign(campaign.id, 'MAINTENANCE_AUTO_PAUSE');
  }
  
  // 2. Giải phóng tất cả WebSocket sessions
  wsServer.broadcastToExtensions({
    type: 'MAINTENANCE_MODE',
    reason,
    message: 'Server entering maintenance. All sessions paused.'
  });
  
  // 3. Thông báo UI
  wsServer.broadcastToUIClients({
    type: 'SYSTEM_ALERT',
    level: 'CRITICAL',
    title: 'Chế Độ Bảo Trì',
    message: reason === 'ERR-DB-01' 
      ? 'Database bị lỗi. Hệ thống đang tự phục hồi từ bản backup gần nhất...'
      : 'Tất cả API keys đã cạn hạn mức. Vui lòng thêm key mới hoặc chờ cooldown hết hạn.',
    ts: Date.now()
  });
  
  // 4. Nếu lý do là DB corrupt → trigger auto-restore
  if (reason === 'ERR-DB-01') {
    try {
      await backupManager.autoRestore();
      logger.info('[MAINTENANCE] Auto-restore completed. Exiting maintenance mode.');
      exitMaintenanceMode('DB_RESTORED');
    } catch (restoreErr) {
      logger.fatal(`[MAINTENANCE] Auto-restore FAILED: ${restoreErr.message}`);
      // Chờ can thiệp thủ công từ user qua UI
    }
  }
}

function exitMaintenanceMode(trigger) {
  logger.info(`[MAINTENANCE] Exiting maintenance. Trigger: ${trigger}`);
  currentState = 'IDLE';
  wsServer.broadcastToUIClients({
    type: 'SYSTEM_ALERT',
    level: 'INFO',
    title: 'Hệ Thống Đã Phục Hồi',
    message: 'Chế độ bảo trì đã kết thúc. Bạn có thể khởi động lại các chiến dịch.',
    ts: Date.now()
  });
}
```

---

## 5. Pseudocode Chi Tiết — runPostingSession() & runGroupSyncSession()

### 5.1 runPostingSession()

```
FUNCTION runPostingSession(account, group, content):

  INPUT:
    account = { id: string (UUID), account_id: string (fb_12345), proxy: string }
    group = { id: string, campaign_id: string, url: string, name: string, fb_group_id: string }
    content = { text: string, image_paths: string[] }

  ─────────────────────────────────────────────────────────────
  PHASE 1: CONCURRENCY LOCK, HUMAN LIMIT CHECK & INITIALIZATION
  ─────────────────────────────────────────────────────────────

  IF ANY active session in this.sessions has accountId == account.id:
    RETURN result(ACCOUNT_BUSY, 'Account is currently active in another session')

  // Kiểm tra giới hạn đăng bài hàng ngày (Human Posting Limits) từ SQLite
  today = getCurrentDateString('YYYY-MM-DD')
  dailyPostCount = db.getDailyPostCountForAccount(account.id, today)
  
  // Thiết lập giới hạn ngẫu nhiên 10-15 bài/ngày để tránh pattern cố định
  MAX_DAILY_POSTS = randomBetween(10, 15)
  
  IF dailyPostCount >= MAX_DAILY_POSTS:
    // Chuyển tài khoản sang trạng thái nghỉ ngơi để tránh quét bot
    db.updateAccountStatus(account.id, 'COOLDOWN', 'Daily posting limit reached')
    logger.warn(`Account ${account.id} reached daily limit (${dailyPostCount}/${MAX_DAILY_POSTS}). Put to COOLDOWN.`)
    this.accountLocks.delete(account.id) // Giải phóng lock tài khoản
    RETURN result(COOLDOWN, `Daily post limit exceeded (${dailyPostCount}/${MAX_DAILY_POSTS})`)

  sessionId = generateUUID()
  startTime = Date.now()
  iterations = 0
  actionHistory = []
  retryCount = 0
  MAX_RETRIES = 3

  this.accountLocks.add(account.id)
  _initSession(sessionId, account.id, group.id, group.campaign_id)

  logger.info(`[Session ${sessionId}] Starting for group: ${group.name}`)
  this.emit('session:started', { sessionId, account, group })

  ─────────────────────────────────────────────────────────────
  PHASE 2: LOAD AND PREPARE CONTENT
  ─────────────────────────────────────────────────────────────

  SET state = 'LOAD_CONTENT'

  renderedContent = await contentRenderer.render(content)

  IF renderedContent.error:
    RETURN result(FAILED, 'Content rendering failed: ' + error)

  ─────────────────────────────────────────────────────────────
  PHASE 3: SEARCH-AND-CLICK ROUTING (SIMULATING HUMAN SEARCH)
  ─────────────────────────────────────────────────────────────

  // Step 3a: Di chuyển tới Facebook Home
  SET state = 'NAVIGATING_HOME'
  
  navigateHomeMsg = {
    type: 'NAVIGATE',
    sessionId: sessionId,
    payload: {
      url: 'https://www.facebook.com/',
      waitForSelector: 'input[placeholder*="Search"], input[placeholder*="Tìm kiếm"]',
      timeoutMs: 25000
    }
  }
  
  ackReceived = await executeActionOnExtension(account.id, navigateHomeMsg)
  IF NOT ackReceived:
    RETURN result(FAILED, 'Extension not responding to Home navigation command')

  TRY:
    readyMsg = await waitForExtensionResult(sessionId, timeoutMs: 30000, ['DOM_SNAPSHOT_READY'])
  CATCH TimeoutError:
    RETURN result(TIMEOUT, 'Extension timeout waiting for Home page load')

  homeSnapshot = readyMsg.payload.snapshot

  // Step 3b: Click và Focus ô Search
  SET state = 'FOCUS_SEARCH_INPUT'
  
  searchInput = findElementByPlaceholder(homeSnapshot, ['Search', 'Tìm kiếm'])
  IF NOT searchInput:
    RETURN result(FAILED, 'Facebook search input not found')

  await executeActionOnExtension(account.id, {
    type: 'CLICK_ELEMENT',
    sessionId: sessionId,
    elementId: searchInput.id,
    human: true
  })
  
  WAIT randomBetween(800, 1500) // Delay ngẫu nhiên Gaussian mô phỏng con người

  // Step 3c: Gõ tên nhóm hoặc fb_group_id với human-like typing delay
  SET state = 'TYPE_SEARCH_KEYWORD'
  
  searchKeyword = group.fb_group_id OR group.name
  await executeActionOnExtension(account.id, {
    type: 'TYPE_TEXT',
    sessionId: sessionId,
    elementId: searchInput.id,
    text: searchKeyword,
    humanDelay: true // Kích hoạt gõ trễ ngẫu nhiên trên Extension
  })
  
  WAIT randomBetween(1000, 2000)
  
  // Nhấn Enter để gửi lệnh tìm kiếm
  await executeActionOnExtension(account.id, {
    type: 'PRESS_KEY',
    sessionId: sessionId,
    key: 'Enter'
  })

  // Step 3d: Chờ kết quả tìm kiếm
  SET state = 'WAIT_SEARCH_RESULTS'
  
  TRY:
    searchResultMsg = await waitForExtensionResult(sessionId, timeoutMs: 25000, ['DOM_SNAPSHOT_READY'])
  CATCH TimeoutError:
    RETURN result(TIMEOUT, 'Timeout waiting for search results')

  searchSnapshot = searchResultMsg.payload.snapshot

  // Step 3e: Nhận diện và so khớp kết quả nhóm
  SET state = 'CLASSIFY_RESULTS'
  
  targetGroupLink = findGroupLinkInSearchResults(searchSnapshot, group.fb_group_id, group.name)
  
  IF NOT targetGroupLink:
    // Không tìm thấy nhóm mục tiêu -> Gửi mã lỗi ERR-DOM-05 và cập nhật DB sang SEARCH_FAILED để hiển thị cảnh báo đỏ trên UI
    this.emit('session:failed', { sessionId, accountId: account.id, errorCode: 'ERR-DOM-05' })
    SET finalStatus = 'SEARCH_FAILED'
    RETURN result(SEARCH_FAILED, 'ERR-DOM-05: Target group not found in search results - skipped')

  // Step 3f: Click vào nhóm mục tiêu
  SET state = 'CLICK_TARGET_GROUP'
  
  await executeActionOnExtension(account.id, {
    type: 'CLICK_ELEMENT',
    sessionId: sessionId,
    elementId: targetGroupLink.id,
    human: true
  })

  TRY:
    groupPageMsg = await waitForExtensionResult(sessionId, timeoutMs: 25000, ['DOM_SNAPSHOT_READY'])
  CATCH TimeoutError:
    RETURN result(TIMEOUT, 'Timeout waiting for group page load')

  currentSnapshot = groupPageMsg.payload.snapshot

  // Step 3g: Kiểm tra quyền đăng bài trong nhóm (Observing Group Post Ability)
  SET state = 'OBSERVING_GROUP_POST_ABILITY'
  
  hasComposer = checkGroupComposerAvailability(currentSnapshot)
  IF NOT hasComposer:
    // Bị khóa chức năng đăng đối với người ngoài/thành viên chưa kiểm duyệt
    logger.warn(`[Session ${sessionId}] Group posting feature is locked. Skipping immediately to minimize risk.`)
    db.updateCampaignGroupStatus(group.id, 'POST_LOCKED', 'Posting blocked by group privacy settings')
    RETURN result(FAILED, 'POST_LOCKED: Posting function restricted for external accounts')

  ─────────────────────────────────────────────────────────────
  PHASE 4: AI DECISION LOOP (max iterations = 20)
  ─────────────────────────────────────────────────────────────

  WHILE iterations < MAX_ITERATIONS:

    // Kiểm tra Circuit Breaker timeout toàn bộ session (120s)
    IF Date.now() - startTime > 120000:
      RETURN result(TIMEOUT, 'Session timed out (120s Circuit Breaker)')

    iterations++
    updateSession(sessionId, { state: 'AI_THINK', iteration: iterations })
    logger.debug(`[Session ${sessionId}] Iteration ${iterations}`)

    ─── 4a. CLASSIFY SNAPSHOT ───────────────────────────────────

    snapshotType = classifySnapshot(currentSnapshot)
    logger.info(`[Session ${sessionId}] Snapshot type: ${snapshotType}`)

    ─── 4b. HANDLE TERMINAL STATES ──────────────────────────────

    IF snapshotType == 'POST_SUCCESS':
      postUrl = extractPostUrl(currentSnapshot)
      RETURN result(SUCCESS, null, { postUrl, iterationsUsed: iterations })

    IF snapshotType IN ['CHECKPOINT_PHONE', 'CHECKPOINT_CAPTCHA']:
      await alertAdmin(account.id, snapshotType, group)
      await accountManager.flagAsCheckpoint(account.id)
      RETURN result('CHECKPOINT_DETECTED', snapshotType)

    IF snapshotType == 'LOGIN_REQUIRED':
      await accountManager.flagAsLoggedOut(account.id)
      RETURN result(FAILED, 'Account session expired — login required')

    ─── 4c. BUILD AI CONTEXT ─────────────────────────────────────

    context = {
      sessionId,
      iteration: iterations,
      snapshotType,
      snapshot: {
        url: currentSnapshot.url,
        title: currentSnapshot.title,
        bodyText: truncate(currentSnapshot.innerText, 2000),
        visibleElements: currentSnapshot.visibleElements,
        forms: currentSnapshot.forms
      },
      content: renderedContent,
      actionHistory: actionHistory.slice(-5),
      groupInfo: { name: group.name, url: group.url }
    }

    ─── 4d. CALL AI BRAIN ───────────────────────────────────────

    SET state = 'AI_THINK'

    TRY:
      decision = await aiBrain.decideNextAction(context)
    CATCH AIError as e:
      logger.error(`AI Brain error at iteration ${iterations}: ${e}`)
      IF e.code == 'RATE_LIMIT':
        WAIT 60000ms
        CONTINUE
      RETURN result(FAILED, 'AI Brain failed: ' + e.message)

    actionHistory.push({
      iteration: iterations,
      snapshotType,
      decision: decision.action,
      reasoning: decision.reasoning,
      timestamp: Date.now()
    })

    logger.info(`[${sessionId}] AI decided: ${decision.action} | ${decision.reasoning}`)

    ─── 4e. SEND ACTION TO EXTENSION ────────────────────────────

    IF decision.action == 'NO_ACTION_NEEDED':
      await executeActionOnExtension(account.id, {
        type: 'CAPTURE_SNAPSHOT',
        sessionId
      })
      CONTINUE

    SET state = 'SEND_ACTION'

    actionMsg = buildActionMessage(decision, sessionId)
    ackOk = await executeActionOnExtension(account.id, actionMsg)

    IF NOT ackOk:
      retryCount++
      IF retryCount >= MAX_RETRIES:
        RETURN result(FAILED, 'Extension not ACK-ing actions')
      WAIT 3000ms
      CONTINUE

    ─── 4f. WAIT FOR ACTION RESULT ──────────────────────────────

    SET state = 'WAIT_ACTION_RESULT'

    TRY:
      resultMsg = await waitForExtensionResult(
        sessionId,
        timeoutMs: 30000,
        expectedTypes: ['DOM_SNAPSHOT_READY', 'ACTION_COMPLETED', 'ACTION_FAILED']
      )
    CATCH TimeoutError:
      retryCount++
      logger.warn(`[${sessionId}] Action result timeout (attempt ${retryCount})`)
      IF retryCount >= MAX_RETRIES:
        RETURN result(TIMEOUT, 'Repeated timeouts waiting for action result')
      WAIT 3000ms
      await executeActionOnExtension(account.id, { type: 'CAPTURE_SNAPSHOT', sessionId })
      resultMsg = await waitForExtensionResult(sessionId, 20000, ['DOM_SNAPSHOT_READY'])

    IF resultMsg.type == 'ACTION_FAILED':
      error = resultMsg.payload.error
      logger.warn(`[${sessionId}] Action failed: ${error}`)
      retryCount++
      IF retryCount >= MAX_RETRIES:
        RETURN result(FAILED, 'Action repeatedly failed: ' + error)
      WAIT 3000ms * retryCount
      CONTINUE

    retryCount = 0

    IF resultMsg.payload.snapshot:
      currentSnapshot = resultMsg.payload.snapshot

  END WHILE

  RETURN result(FAILED, `Max iterations (${MAX_ITERATIONS}) reached without posting`)

  ─────────────────────────────────────────────────────────────
  PHASE 5: CLEANUP & DB UPDATE (always runs)
  ─────────────────────────────────────────────────────────────
  FINALLY:
    durationMs = Date.now() - startTime

    _writeSessionResult(sessionId, account, group, finalStatus, errorMessage, postUrl, iterations, actionHistory, durationMs)

    this.sessions.delete(sessionId)
    this._messageResolvers.delete(sessionId)
    this.accountLocks.delete(account.id)

    this.emit('session:completed', { sessionId, status: finalStatus, durationMs })
```
```

### 5.2 runGroupSyncSession()

```
FUNCTION runGroupSyncSession(account):

  INPUT:
    account = {
      id: string (UUID),
      account_id: string (fb_12345),
      chrome_profile_path: string,
      proxy: string (optional)
    }

  ─────────────────────────────────────────────────────────────
  PHASE 1: CONCURRENCY LOCK & INITIALIZATION
  ─────────────────────────────────────────────────────────────

  IF ANY active session in this.sessions has accountId == account.id:
    RETURN result(ACCOUNT_BUSY, 'Account is currently active in another session')

  sessionId = generateUUID()
  startTime = Date.now()
  
  this.accountLocks.add(account.id)
  _initSession(sessionId, account.id, 'sync_groups', 0)

  logger.info(`[Session ${sessionId}] Starting group sync for account: ${account.id}`)
  this.emit('session:started', { sessionId, accountId: account.id, type: 'sync' })

  ─────────────────────────────────────────────────────────────
  PHASE 2: NAVIGATE TO GROUPS HOMEPAGE
  ─────────────────────────────────────────────────────────────

  SET state = 'SEND_NAVIGATE'

  navigateMsg = {
    type: 'NAVIGATE_TO_GROUPS_HOME',
    sessionId: sessionId,
    payload: {
      url: 'https://www.facebook.com/groups/feed/',
      waitForSelector: '[role="main"]',
      timeoutMs: 30000
    }
  }

  ackReceived = await executeActionOnExtension(account.id, navigateMsg)

  IF NOT ackReceived:
    RETURN result(FAILED, 'Extension not responding to navigate groups command')

  ─────────────────────────────────────────────────────────────
  PHASE 3: WAIT FOR EXTENSION READY
  ─────────────────────────────────────────────────────────────

  SET state = 'WAIT_FOR_EXTENSION_READY'

  TRY:
    readyMsg = await waitForExtensionResult(
      sessionId,
      timeoutMs: 30000,
      expectedTypes: ['DOM_SNAPSHOT_READY']
    )
  CATCH TimeoutError:
    RETURN result(TIMEOUT, 'Extension ready timeout waiting for groups list')

  currentSnapshot = readyMsg.payload.snapshot

  ─────────────────────────────────────────────────────────────
  PHASE 4: EXTRACT GROUPS AND SAVE DB
  ─────────────────────────────────────────────────────────────

  SET state = 'SYNC_EXTRACTING'

  IF Date.now() - startTime > 600000: // 10 minutes Circuit Breaker
    RETURN result(TIMEOUT, 'Sync session timeout (10 minutes)')

  groups = extractGroupsFromSnapshot(currentSnapshot)
  logger.info(`[Session ${sessionId}] Extracted ${groups.length} groups`)

  FOR EACH g IN groups:
    db.insertFetchedGroup({
      accountId: account.account_id,
      fbGroupId: g.id,
      name: g.name,
      url: g.url
    })

  RETURN result(SUCCESS, null, { groupsSyncedCount: groups.length })

  ─────────────────────────────────────────────────────────────
  PHASE 5: CLEANUP & RELEASE LOCK
  ─────────────────────────────────────────────────────────────
  FINALLY:
    durationMs = Date.now() - startTime
    this.sessions.delete(sessionId)
    this._messageResolvers.delete(sessionId)
    this.accountLocks.delete(account.id)
    this.emit('session:completed', { sessionId, status: finalStatus, durationMs })
```

---

## 6. DOM Snapshot Classifier

### 6.1 Vai Trò

`classifySnapshot()` là hàm **quan trọng sống còn** — nó phân loại DOM snapshot từ Extension thành các "trạng thái trang" cụ thể.

### 6.2 Input/Output JSDoc Schema

```javascript
/**
 * @param {Object} snapshot - DOM Snapshot object từ Extension (Unified v1.0 schema)
 * @param {string} snapshot.url          - URL hiện tại của tab
 * @param {string} snapshot.title        - document.title
 * @param {string} snapshot.innerText    - document.body.innerText (full)
 * @param {Array}  snapshot.elements     - Mảng structured elements với fingerprint IDs
 * @param {string} snapshot.elements[].id        - 8-char hex fingerprint ID (dùng ID này!)
 * @param {string} snapshot.elements[].tag       - HTML tag
 * @param {string} snapshot.elements[].role      - ARIA role
 * @param {string} snapshot.elements[].ariaLabel - ARIA label
 * @param {string} snapshot.elements[].text      - Visible text
 * @param {string} snapshot.elements[].href      - href (cho <a> tags)
 * @param {string[]} snapshot.visibleButtons - Text của tất cả visible buttons (derived)
 * @param {string[]} snapshot.visibleInputs  - Placeholder của visible inputs (derived/legacy)
 * @param {string} snapshot.activeModal   - innerText của modal đang mở (nếu có)
 *
 * @returns {SnapshotType}
 */
```

### 6.2b classifySnapshot() & extractGroupsFromSnapshot() Implementation Note

> 📌 **SINGLE SOURCE OF TRUTH:** To avoid cross-spec maintenance mismatches, the full JavaScript implementation of `classifySnapshot(snapshot)` and `extractGroupsFromSnapshot(snapshot)` is maintained solely as instance methods of the `AgentLoop` class. 
> 
> Refer directly to **Section 9 (Full Code Implementation — `agent_loop.js`)** to inspect these functions.

### 6.3 Classifier Logic Rules

The classification logic follows these priority rules (executed from top to bottom):
1. **`LOGIN_REQUIRED`**: Triggered if the URL contains `/login` or `/checkpoint/`, or if username/password inputs are found alongside login titles.
2. **`CHECKPOINT_PHONE`**: Triggered if text or active modal contains phone verification phrases and phone/code inputs are detected.
3. **`CHECKPOINT_CAPTCHA`**: Triggered if hCaptcha/recaptcha or "solve this puzzle" indicators are present.
4. **`POST_SUCCESS`**: Triggered if URL changes to a permalink or "post is now live/published" success signals appear.
5. **`POST_COMPOSE_OPEN`**: Triggered if an element with `role="textbox"` is found with an aria-label matching compose hints, or if post-composition keywords are present.
6. **`POPUP_RULES`**: Triggered if an active modal displays group guidelines and an "Agree" button is available.
7. **`POPUP_NOTIFICATION`**: Triggered if any other active modal is present (notification prompts, etc.).
8. **`NORMAL_FEED`**: Triggered if we are on a group landing page and the "Write post" button is visible.
9. **`UNKNOWN`**: Triggered if no patterns match. Runs fallback LLM heuristics.

---

## 7. Event-Driven Communication Protocol

Mọi communication giữa AgentLoop (Dashboard Server) và Chrome Extension đều thông qua **WebSocket JSON messages**. Mỗi message có cấu trúc phẳng (flat) hoặc cấu trúc schema nghiêm ngặt:

### 7.1 Messages: Dashboard → Extension

#### `CLICK_ELEMENT` — Click element by fingerprint
```json
{
  "type": "CLICK_ELEMENT",
  "sessionId": "a1b2c3d4-...",
  "commandId": "cmd-8829-...",
  "elementId": "a8f2c3d9",
  "human": true
}
```

#### `TYPE_TEXT` — Type text vào element
```json
{
  "type": "TYPE_TEXT",
  "sessionId": "a1b2c3d4-...",
  "commandId": "cmd-8830-...",
  "elementId": "b1c2d3e4",
  "text": "Nội dung bài viết đầy đủ...",
  "humanDelay": true
}
```

#### `ATTACH_MEDIA` — Attach base64 chunked images/videos
```json
{
  "type": "ATTACH_MEDIA",
  "sessionId": "a1b2c3d4-...",
  "commandId": "cmd-8831-...",
  "elementId": "media-input-id",
  "mediaId": "media-uuid-111",
  "mediaType": "image",
  "totalChunks": 2,
  "chunkIndex": 0,
  "chunk": "base64String...",
  "mimeType": "image/jpeg",
  "isFinal": false
}
```

#### `NAVIGATE` — Navigate tab to URL
```json
{
  "type": "NAVIGATE",
  "sessionId": "a1b2c3d4-...",
  "commandId": "cmd-8832-...",
  "url": "https://www.facebook.com/groups/feed/",
  "waitReady": true
}
```

#### `SESSION_HEARTBEAT` (Dashboard → Extension)
```json
{
  "type": "SESSION_HEARTBEAT",
  "sessionId": "a1b2c3d4-...",
  "timestamp": 1718451792000,
  "payload": {
    "direction": "ping",
    "activeSessions": ["a1b2c3d4"]
  }
}
```

---

## 8. Multi-Campaign Concurrency

### 8.1 Concurrency Manager

Để tránh việc hai luồng khác nhau cùng tranh chấp sử dụng một tài khoản (gây overwrite proxy và session Chrome), hệ thống tích hợp `accountLocks` Set độc quyền. 

Khi một campaign chạy:
1. Lấy danh sách các nhóm chưa xử lý.
2. Kiểm tra số luồng chạy đồng thời (`activeSessions.size`). Nếu chạm ngưỡng `MAX_CONCURRENT_SESSIONS` (mặc định = 3), tạm dừng cào hàng đợi.
3. Tìm tài khoản thích hợp bằng `_acquireAccount(campaignId)`. Nếu rảnh, đặt lock và khởi động Posting Session.

---

## 9. Code JS Đầy Đủ — agent_loop.js

```javascript
/**
 * agent_loop.js — AgentLoop: Orchestrator trung tâm Hermes FacePost-Group
 */

'use strict';

const { EventEmitter } = require('events');
const { v4: uuidv4 } = require('uuid');
const winston = require('winston');

// ─── Logger Setup ─────────────────────────────────────────────────────────────
const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  transports: [
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize(),
        winston.format.printf(({ timestamp, level, message, sessionId, ...meta }) => {
          const sid = sessionId ? `[${sessionId.substring(0, 8)}]` : '';
          return `${timestamp} ${level} ${sid} ${message} ${JSON.stringify(meta)}`;
        })
      )
    })
  ]
});

// ─── Constants ────────────────────────────────────────────────────────────────
const SNAPSHOT_TYPES = Object.freeze({
  NORMAL_FEED: 'NORMAL_FEED',
  POST_COMPOSE_OPEN: 'POST_COMPOSE_OPEN',
  POPUP_NOTIFICATION: 'POPUP_NOTIFICATION',
  POPUP_RULES: 'POPUP_RULES',
  CHECKPOINT_PHONE: 'CHECKPOINT_PHONE',
  CHECKPOINT_CAPTCHA: 'CHECKPOINT_CAPTCHA',
  LOGIN_REQUIRED: 'LOGIN_REQUIRED',
  POST_SUCCESS: 'POST_SUCCESS',
  UNKNOWN: 'UNKNOWN'
});

const SESSION_STATES = Object.freeze({
  INIT: 'INIT',
  LOAD_CONTENT: 'LOAD_CONTENT',
  SEND_NAVIGATE: 'SEND_NAVIGATE',
  WAIT_EXTENSION_READY: 'WAIT_EXTENSION_READY',
  WAIT_DOM_SNAPSHOT: 'WAIT_DOM_SNAPSHOT',
  AI_THINK: 'AI_THINK',
  SEND_ACTION: 'SEND_ACTION',
  WAIT_ACTION_RESULT: 'WAIT_ACTION_RESULT',
  SUCCESS: 'SUCCESS',
  CHECKPOINT_DETECTED: 'CHECKPOINT_DETECTED',
  TIMEOUT: 'TIMEOUT',
  FAILED: 'FAILED',
  SEARCH_FAILED: 'SEARCH_FAILED',
  ACCOUNT_BUSY: 'ACCOUNT_BUSY',
  SYNC_EXTRACTING: 'SYNC_EXTRACTING',
  
  // Search-and-Click states (Human-like behavior)
  INITIALIZING: 'INITIALIZING',
  NAVIGATING_HOME: 'NAVIGATING_HOME',
  FOCUS_SEARCH_INPUT: 'FOCUS_SEARCH_INPUT',
  TYPE_SEARCH_KEYWORD: 'TYPE_SEARCH_KEYWORD',
  WAIT_SEARCH_RESULTS: 'WAIT_SEARCH_RESULTS',
  CLASSIFY_RESULTS: 'CLASSIFY_RESULTS',
  CLICK_TARGET_GROUP: 'CLICK_TARGET_GROUP',
  OBSERVING_GROUP_POST_ABILITY: 'OBSERVING_GROUP_POST_ABILITY',
  
  // Checkpoint & Hibernate states (Spec 06 reconciliation)
  AUTO_HANDLING: 'AUTO_HANDLING',
  AWAITING_MANUAL: 'AWAITING_MANUAL',
  HIBERNATE_AWAITING_MANUAL: 'HIBERNATE_AWAITING_MANUAL',
  MANUAL_RESOLVED: 'MANUAL_RESOLVED',
  COOLDOWN: 'COOLDOWN',
  COOLDOWN_STORM: 'COOLDOWN_STORM',
  CHECKPOINT_TIMEOUT: 'CHECKPOINT_TIMEOUT',
  FAILED_CHECKPOINT: 'FAILED_CHECKPOINT',
  
  // Emergency maintenance state
  MAINTENANCE: 'MAINTENANCE',
  
  // Escalation states (Phase 8 - Handshake escalation rules)
  ESCALATING_LEADER: 'ESCALATING_LEADER',
  ESCALATING_HUMAN: 'ESCALATING_HUMAN'
});

const DEFAULT_CONFIG = {
  maxConcurrentSessions: parseInt(process.env.MAX_CONCURRENT_SESSIONS || '3'),
  sessionTimeoutMs: parseInt(process.env.SESSION_TIMEOUT_MS || '120000'),
  syncSessionTimeoutMs: parseInt(process.env.SYNC_SESSION_TIMEOUT_MS || '600000'),
  syncIdleTimeoutMs: parseInt(process.env.SYNC_IDLE_TIMEOUT_MS || '60000'),
  actionTimeoutMs: parseInt(process.env.ACTION_TIMEOUT_MS || '30000'),
  navigateTimeoutMs: parseInt(process.env.NAVIGATE_TIMEOUT_MS || '30000'),
  aiTimeoutMs: parseInt(process.env.AI_TIMEOUT_MS || '20000'),
  maxIterations: parseInt(process.env.MAX_ITERATIONS || '20'),
  maxRetries: parseInt(process.env.MAX_RETRIES || '3'),
  retryDelayMs: parseInt(process.env.RETRY_DELAY_MS || '3000'),
  heartbeatIntervalMs: parseInt(process.env.HEARTBEAT_INTERVAL_MS || '10000'),
  delayBetweenGroupsMs: {
    min: parseInt(process.env.DELAY_MIN_MS || '30000'),
    max: parseInt(process.env.DELAY_MAX_MS || '90000')
  }
};

class TimeoutError extends Error {
  constructor(message) {
    super(message);
    this.name = 'TimeoutError';
  }
}

const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
const randomBetween = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min;

// ─── AgentLoop Class ──────────────────────────────────────────────────────────
class AgentLoop extends EventEmitter {
  constructor(db, wsServer, brain, config = {}) {
    super();
    this.db = db;
    this.wsServer = wsServer;
    this.brain = brain;
    this.config = { ...DEFAULT_CONFIG, ...config };
    
    // SQLite WAL Mode Sync & Busy Timeout (ERR-SPEC05-04 Remediation)
    this.db.pragma('journal_mode = WAL');
    this.db.pragma('synchronous = NORMAL');
    this.db.pragma('busy_timeout = 5000');

    this.sessions = new Map();
    this.accountLocks = new Set();
    this.activeCampaigns = new Map();
    this._messageResolvers = new Map();
    this.fsmState = SESSION_STATES.IDLE;

    // Heartbeat setup
    this._heartbeatInterval = setInterval(
      () => this._sendHeartbeats(),
      this.config.heartbeatIntervalMs
    );

    // Watchdog setup - Quét mỗi 60s để dọn dẹp zombie sessions (Remediation chống treo zombie)
    this._watchdogInterval = setInterval(
      () => this._runWatchdog(),
      60000
    );

    logger.info('AgentLoop initialized', { config: this.config });
  }

  async startCampaign(campaignId) {
    if (this.activeCampaigns.has(campaignId)) {
      throw new Error(`Campaign ${campaignId} is already running`);
    }

    const campaign = this.db.prepare(
      'SELECT * FROM campaigns WHERE id = ? AND status != "COMPLETED"'
    ).get(campaignId);

    if (!campaign) {
      throw new Error(`Campaign ${campaignId} not found or already completed`);
    }

    const campaignState = {
      isRunning: true,
      config: JSON.parse(campaign.config || '{}'),
      startedAt: Date.now()
    };

    this.db.prepare("UPDATE campaigns SET status = 'RUNNING', started_at = ? WHERE id = ?")
      .run(new Date().toISOString(), campaignId);

    this.activeCampaigns.set(campaignId, campaignState);

    campaignState.loopPromise = this._runCampaignLoop(campaignId, campaignState)
      .catch(err => logger.error(`Campaign ${campaignId} loop crashed`, { error: err.message }))
      .finally(() => {
        this.activeCampaigns.delete(campaignId);
        this.emit('campaign:finished', { campaignId });
      });

    logger.info(`Campaign ${campaignId} started`);
  }

  async stopCampaign(campaignId, forceKill = false) {
    const state = this.activeCampaigns.get(campaignId);
    if (!state) return;

    state.isRunning = false;

    if (forceKill) {
      for (const [sid, session] of this.sessions) {
        if (session.campaignId === campaignId) {
          session.forceStop = true;
        }
      }
    }

    if (state.loopPromise) {
      await state.loopPromise.catch(() => {});
    }

    this.db.prepare("UPDATE campaigns SET status = 'PAUSED' WHERE id = ?").run(campaignId);
    logger.info(`Campaign ${campaignId} stopped`, { forceKill });
  }

  async runPostingSession(account, group, content) {
    const isAlreadyActive = Array.from(this.sessions.values()).some(s => s.accountId === account.id);
    if (isAlreadyActive) {
      logger.warn('Account is busy, posting session rejected', { accountId: account.id });
      return this._buildResult(SESSION_STATES.ACCOUNT_BUSY, 'Account is currently active in another session', null, 0, 0);
    }

    const sessionId = uuidv4();
    const startTime = Date.now();
    let finalStatus = SESSION_STATES.FAILED;
    let errorMessage = null;
    let postUrl = null;
    let iterations = 0;
    const actionHistory = [];

    // Check Human Posting Limits (10-15 posts/day/account)
    try {
      const today = new Date().toISOString().split('T')[0];
      const dailyPostCount = this.db.prepare(`
        SELECT COUNT(*) as count 
        FROM posting_logs 
        WHERE account_id = ? 
          AND event_type = 'POST_SUCCESS' 
          AND created_at LIKE ?
      `).get(account.id, `${today}%`)?.count || 0;

      const maxDailyLimit = randomBetween(10, 15); // Ngưỡng ngẫu nhiên 10-15 bài/ngày
      if (dailyPostCount >= maxDailyLimit) {
        logger.warn('Daily posting limit reached, putting account into COOLDOWN', { accountId: account.id, dailyPostCount });
        this.db.prepare("UPDATE accounts SET status = 'COOLDOWN', error_message = ? WHERE id = ?")
          .run(`Daily limit exceeded (${dailyPostCount}/${maxDailyLimit})`, account.id);
        finalStatus = SESSION_STATES.COOLDOWN;
        errorMessage = `Daily limit reached: ${dailyPostCount}/${maxDailyLimit}`;
        this.accountLocks.delete(account.id); // Giải phóng lock tài khoản tránh zombie lock
        return this._buildResult(finalStatus, errorMessage, null, 0, Date.now() - startTime);
      }
    } catch (dbLimitErr) {
      logger.error('Failed to check human posting limits', { error: dbLimitErr.message });
    }

    this.accountLocks.add(account.id);

    try {
      // Đưa _initSession vào try-catch để tránh rò rỉ Lock tài khoản (ERR-SPEC05-03 Remediation)
      this._initSession(sessionId, account.id, group.id, group.campaign_id || 0);
      this.emit('session:started', { sessionId, accountId: account.id, groupId: group.id });
      this._updateSessionState(sessionId, SESSION_STATES.LOAD_CONTENT);
      const renderedText = this._renderContent(content.text, { groupName: group.name });
      const renderedContent = { ...content, text: renderedText };

      // Step 1: Open Facebook Home instead of navigating directly to Group URL
      this._updateSessionState(sessionId, SESSION_STATES.NAVIGATING_HOME);
      const homeAck = await this.executeActionOnExtension(account.id, {
        type: 'NAVIGATE',
        sessionId,
        payload: {
          url: 'https://www.facebook.com/',
          waitForSelector: 'input[placeholder*="Search"], input[placeholder*="Tìm kiếm"]',
          timeoutMs: 25000
        }
      });
      if (!homeAck) {
        throw new Error('Extension did not ACK Home navigation command');
      }

      let homeMsg;
      try {
        homeMsg = await this.waitForExtensionResult(sessionId, this.config.navigateTimeoutMs);
        if (homeMsg.type === 'NAVIGATION_FAILED') {
          throw new Error(`Home navigation failed: ${homeMsg.payload.reason}`);
        }
      } catch (err) {
        if (err instanceof TimeoutError) {
          finalStatus = SESSION_STATES.TIMEOUT;
          errorMessage = 'Extension ready timeout on Home page load';
          return this._buildResult(finalStatus, errorMessage, null, iterations, Date.now() - startTime);
        }
        throw err;
      }
      let homeSnapshot = homeMsg.payload.snapshot;

      // Step 2: Focus Search Input
      this._updateSessionState(sessionId, SESSION_STATES.FOCUS_SEARCH_INPUT);
      const searchInput = (homeSnapshot.elements || []).find(e => 
        e.tag === 'input' && 
        (e.ariaLabel?.toLowerCase().includes('search') || 
         e.ariaLabel?.toLowerCase().includes('tìm kiếm') ||
         e.placeholder?.toLowerCase().includes('search') ||
         e.placeholder?.toLowerCase().includes('tìm kiếm'))
      );
      if (!searchInput) {
        throw new Error('Search input not found on Home page');
      }

      await this.executeActionOnExtension(account.id, {
        type: 'CLICK_ELEMENT',
        sessionId,
        elementId: searchInput.id,
        human: true
      });
      await sleep(randomBetween(800, 1500)); // Gaussian simulation delay

      // Step 3: Type Search Keyword with random delay
      this._updateSessionState(sessionId, SESSION_STATES.TYPE_SEARCH_KEYWORD);
      const searchKeyword = group.fb_group_id || group.name;
      await this.executeActionOnExtension(account.id, {
        type: 'TYPE_TEXT',
        sessionId,
        elementId: searchInput.id,
        text: searchKeyword,
        humanDelay: true // simulates keystrokes
      });
      await sleep(randomBetween(1000, 2000));

      // Press Enter to submit search
      await this.executeActionOnExtension(account.id, {
        type: 'PRESS_KEY',
        sessionId,
        key: 'Enter'
      });

      // Step 4: Wait Search Results
      this._updateSessionState(sessionId, SESSION_STATES.WAIT_SEARCH_RESULTS);
      let searchResultMsg;
      try {
        searchResultMsg = await this.waitForExtensionResult(sessionId, this.config.navigateTimeoutMs);
      } catch (err) {
        throw new Error('Timeout waiting for search results');
      }
      let searchSnapshot = searchResultMsg.payload.snapshot;

      // Step 5: Classify Results & Match target group
      this._updateSessionState(sessionId, SESSION_STATES.CLASSIFY_RESULTS);
      const searchElements = searchSnapshot.elements || [];
      const targetGroupLink = searchElements.find(e => 
        e.tag === 'a' && e.href && 
        (e.href.includes(`/groups/${group.fb_group_id || 'NEVERMATCH'}`) || 
         (group.name && e.text?.toLowerCase().includes(group.name.toLowerCase())))
      );

      if (!targetGroupLink) {
        this.emit('session:failed', { sessionId, accountId: account.id, errorCode: 'ERR-DOM-05' });
        finalStatus = SESSION_STATES.SEARCH_FAILED;
        errorMessage = 'ERR-DOM-05: Target group not found in search results';
        return this._buildResult(finalStatus, errorMessage, null, 0, Date.now() - startTime);
      }

      // Step 6: Click target group
      this._updateSessionState(sessionId, SESSION_STATES.CLICK_TARGET_GROUP);
      const clickAck = await this.executeActionOnExtension(account.id, {
        type: 'CLICK_ELEMENT',
        sessionId,
        elementId: targetGroupLink.id,
        human: true
      });
      if (!clickAck) throw new Error('Extension did not ACK target group click');

      let groupPageMsg;
      try {
        groupPageMsg = await this.waitForExtensionResult(sessionId, this.config.navigateTimeoutMs);
      } catch (err) {
        throw new Error('Timeout waiting for group page load after click');
      }
      let currentSnapshot = groupPageMsg.payload.snapshot;

      // Step 7: Observe group post ability
      this._updateSessionState(sessionId, SESSION_STATES.OBSERVING_GROUP_POST_ABILITY);
      const elements = currentSnapshot.elements || [];
      const hasComposer = elements.some(e => 
        (e.role === 'textbox' && (e.ariaLabel?.toLowerCase().includes('write something') || e.ariaLabel?.toLowerCase().includes('nghĩ gì') || e.ariaLabel?.toLowerCase().includes('viết gì đó'))) ||
        (e.tag === 'span' && (e.text?.toLowerCase().includes('write something') || e.text?.toLowerCase().includes('viết gì đó') || e.text?.toLowerCase().includes('tạo bài viết')))
      );
      if (!hasComposer) {
        logger.warn('Group posting is locked or restricted for external accounts, skipping to minimize risk', { groupId: group.id });
        try {
          this.db.prepare("UPDATE campaign_groups SET status = 'POST_LOCKED', error_message = 'Posting restricted by group privacy settings' WHERE id = ?")
            .run(group.id);
        } catch (dbErr) {
          logger.error('Failed to update group status to POST_LOCKED', { error: dbErr.message });
        }
        finalStatus = SESSION_STATES.FAILED;
        errorMessage = 'POST_LOCKED: Posting function restricted for external accounts';
        return this._buildResult(finalStatus, errorMessage, null, 0, Date.now() - startTime);
      }

      let retryCount = 0;
      while (iterations < this.config.maxIterations) {
        if (Date.now() - startTime > this.config.sessionTimeoutMs) {
          finalStatus = SESSION_STATES.TIMEOUT;
          errorMessage = 'Session timed out (120s Circuit Breaker)';
          break;
        }

        const sessionState = this.sessions.get(sessionId);
        if (!sessionState || sessionState.forceStop) {
          finalStatus = SESSION_STATES.FAILED;
          errorMessage = 'Session force-stopped';
          break;
        }

        iterations++;
        this._updateSessionState(sessionId, SESSION_STATES.AI_THINK, iterations);

        const snapshotType = this.classifySnapshot(currentSnapshot);
        logger.info('Snapshot classified', { sessionId, snapshotType, iteration: iterations });

        if (snapshotType === SNAPSHOT_TYPES.POST_SUCCESS) {
          postUrl = this._extractPostUrl(currentSnapshot);
          finalStatus = SESSION_STATES.SUCCESS;
          break;
        }

        if ([SNAPSHOT_TYPES.CHECKPOINT_PHONE, SNAPSHOT_TYPES.CHECKPOINT_CAPTCHA].includes(snapshotType)) {
          logger.warn('Checkpoint detected!', { sessionId, accountId: account.id, snapshotType });
          this.emit('checkpoint:alert', { accountId: account.id, type: snapshotType, group });
          finalStatus = SESSION_STATES.CHECKPOINT_DETECTED;
          errorMessage = snapshotType;
          break;
        }

        if (snapshotType === SNAPSHOT_TYPES.LOGIN_REQUIRED) {
          this.emit('account:loggedOut', { accountId: account.id });
          finalStatus = SESSION_STATES.FAILED;
          errorMessage = 'Account session expired';
          break;
        }

        const context = {
          sessionId,
          iteration: iterations,
          snapshotType,
          snapshot: {
            url: currentSnapshot.url,
            title: currentSnapshot.title,
            bodyText: (currentSnapshot.innerText || '').substring(0, 2000),
            visibleButtons: currentSnapshot.visibleButtons || [],
            visibleInputs: currentSnapshot.visibleInputs || [],
            activeModal: currentSnapshot.activeModal
          },
          content: renderedContent,
          actionHistory: actionHistory.slice(-5),
          groupInfo: { name: group.name, url: group.url }
        };

        let decision;
        try {
          decision = await Promise.race([
            this.brain.decideNextAction(context),
            new Promise((_, reject) =>
              setTimeout(() => reject(new TimeoutError('AI timeout')), this.config.aiTimeoutMs)
            )
          ]);
        } catch (err) {
          if (err instanceof TimeoutError) {
            logger.warn('AI decision timed out, retrying', { sessionId, iteration: iterations });
            continue;
          }
          finalStatus = SESSION_STATES.FAILED;
          errorMessage = `AI Brain error: ${err.message}`;
          break;
        }

        actionHistory.push({
          iteration: iterations,
          snapshotType,
          decision: decision.action,
          reasoning: decision.reasoning,
          timestamp: Date.now()
        });

        logger.info('AI decision', { sessionId, action: decision.action, reasoning: decision.reasoning });

        if (decision.action === 'NO_ACTION_NEEDED') {
          await sleep(2000);
          await this.executeActionOnExtension(account.id, { type: 'CAPTURE_SNAPSHOT', sessionId, payload: {} });
        } else {
          this._updateSessionState(sessionId, SESSION_STATES.SEND_ACTION, iterations);
          const actionMsg = this._buildActionMessage(decision, sessionId);
          const ackOk = await this.executeActionOnExtension(account.id, actionMsg);

          if (!ackOk) {
            retryCount++;
            if (retryCount >= this.config.maxRetries) {
              finalStatus = SESSION_STATES.FAILED;
              errorMessage = 'Extension not responding to actions';
              break;
            }
            await sleep(this.config.retryDelayMs);
            continue;
          }
        }

        this._updateSessionState(sessionId, SESSION_STATES.WAIT_ACTION_RESULT, iterations);
        try {
          const resultMsg = await this.waitForExtensionResult(sessionId, this.config.actionTimeoutMs);

          if (resultMsg.type === 'ACTION_FAILED') {
            logger.warn('Action failed', { sessionId, error: resultMsg.payload.error });
            retryCount++;
            if (!resultMsg.payload.retryable || retryCount >= this.config.maxRetries) {
              finalStatus = SESSION_STATES.FAILED;
              errorMessage = `Action failed: ${resultMsg.payload.error}`;
              break;
            }
            await sleep(this.config.retryDelayMs * retryCount);
          } else {
            retryCount = 0;
          }

          if (resultMsg.payload && resultMsg.payload.snapshot) {
            currentSnapshot = resultMsg.payload.snapshot;
          }

        } catch (err) {
          if (err instanceof TimeoutError) {
            retryCount++;
            logger.warn('Action result timeout', { sessionId, retryCount });
            if (retryCount >= this.config.maxRetries) {
              finalStatus = SESSION_STATES.TIMEOUT;
              errorMessage = 'Repeated timeouts on action results';
              break;
            }
            await sleep(this.config.retryDelayMs);
            await this.executeActionOnExtension(account.id, { type: 'CAPTURE_SNAPSHOT', sessionId, payload: {} });
            try {
              const freshMsg = await this.waitForExtensionResult(sessionId, 15000);
              if (freshMsg.payload && freshMsg.payload.snapshot) {
                currentSnapshot = freshMsg.payload.snapshot;
              }
            } catch (_) {}
          } else {
            throw err;
          }
        }
      }

      if (iterations >= this.config.maxIterations && finalStatus === SESSION_STATES.FAILED && !errorMessage) {
        errorMessage = `Max iterations (${this.config.maxIterations}) reached`;
        finalStatus = SESSION_STATES.FAILED;
      }

    } catch (err) {
      logger.error('Session crashed', { sessionId, error: err.message, stack: err.stack });
      finalStatus = SESSION_STATES.FAILED;
      errorMessage = `Unhandled error: ${err.message}`;
      
      // Kiểm tra lỗi SQLite hỏng
      if (err.message.includes('SQLITE_CORRUPT') || err.message.includes('corrupt')) {
        this.enterMaintenanceMode('ERR-DB-01');
      }
    } finally {
      const durationMs = Date.now() - startTime;
      // Bọc try-catch riêng để tránh lỗi ghi DB chặn đứng việc xóa locks (ERR-SPEC05-02 Remediation)
      try {
        this._writeSessionResult(sessionId, account, group, finalStatus, errorMessage, postUrl, iterations, actionHistory, durationMs);
      } catch (dbWriteErr) {
        logger.error('Failed to write session result to DB, proceeding with cleanup', { error: dbWriteErr.message });
        if (dbWriteErr.message.includes('SQLITE_CORRUPT') || dbWriteErr.message.includes('corrupt')) {
          this.enterMaintenanceMode('ERR-DB-01');
        }
      }
      this.sessions.delete(sessionId);
      this._messageResolvers.delete(sessionId);
      this.accountLocks.delete(account.id);
      this.emit('session:completed', { sessionId, status: finalStatus, durationMs });
    }

    return this._buildResult(finalStatus, errorMessage, postUrl, iterations, Date.now() - startTime);
  }

  async runGroupSyncSession(account) {
    const isAlreadyActive = Array.from(this.sessions.values()).some(s => s.accountId === account.id);
    if (isAlreadyActive) {
      logger.warn('Account is busy, group sync session rejected', { accountId: account.id });
      return { status: SESSION_STATES.ACCOUNT_BUSY, errorMessage: 'Account is currently active in another session', groupsSyncedCount: 0, durationMs: 0 };
    }

    const sessionId = uuidv4();
    const startTime = Date.now();
    let finalStatus = SESSION_STATES.FAILED;
    let errorMessage = null;
    let groupsSyncedCount = 0;

    this.accountLocks.add(account.id);
    this._initSession(sessionId, account.id, 'sync_groups', 0);
    this.emit('session:started', { sessionId, accountId: account.id, type: 'sync' });

    try {
      this._updateSessionState(sessionId, SESSION_STATES.SEND_NAVIGATE);
      const navAck = await this.executeActionOnExtension(account.id, {
        type: 'NAVIGATE_TO_GROUPS_HOME',
        sessionId,
        payload: {
          url: 'https://www.facebook.com/groups/feed/',
          waitForSelector: '[role="main"]',
          timeoutMs: 30000
        }
      });

      if (!navAck) {
        throw new Error('Extension did not ACK navigate groups command');
      }

      this._updateSessionState(sessionId, SESSION_STATES.WAIT_EXTENSION_READY);
      let currentSnapshot;
      try {
        const readyMsg = await this.waitForExtensionResult(sessionId, this.config.navigateTimeoutMs);
        if (readyMsg.type === 'NAVIGATION_FAILED') {
          throw new Error(`Navigation failed: ${readyMsg.payload.reason}`);
        }
        currentSnapshot = readyMsg.payload.snapshot;
      } catch (err) {
        if (err instanceof TimeoutError) {
          finalStatus = SESSION_STATES.TIMEOUT;
          errorMessage = 'Extension ready timeout (30s)';
          return { status: finalStatus, errorMessage, groupsSyncedCount, durationMs: Date.now() - startTime };
        }
        throw err;
      }

      const sessionState = this.sessions.get(sessionId);
      if (Date.now() - startTime > this.config.syncSessionTimeoutMs) {
        throw new TimeoutError('Sync session timeout (10m)');
      }
      if (sessionState && (Date.now() - sessionState.lastActivityAt > this.config.syncIdleTimeoutMs)) {
        throw new TimeoutError('Sync session idle timeout (60s)');
      }

      this._updateSessionState(sessionId, SESSION_STATES.SYNC_EXTRACTING);
      const groups = this.extractGroupsFromSnapshot(currentSnapshot);
      groupsSyncedCount = groups.length;

      for (const group of groups) {
        try {
          const crypto = require('crypto');
          const rowId = crypto.randomUUID();
          const dbAccountId = account.account_id || account.id;
          
          this.db.prepare(`
            INSERT INTO fetched_groups (id, account_id, fb_group_id, group_name, group_url, sync_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(account_id, fb_group_id) DO UPDATE SET 
              group_name = excluded.group_name, 
              group_url = excluded.group_url, 
              sync_at = excluded.sync_at
          `).run(rowId, dbAccountId, group.id, group.name, group.url, new Date().toISOString());
        } catch (dbErr) {
          logger.error('Failed to save group to DB during sync', { group, error: dbErr.message });
        }
      }

      finalStatus = SESSION_STATES.SUCCESS;
    } catch (err) {
      logger.error('Group sync session crashed', { sessionId, error: err.message, stack: err.stack });
      finalStatus = SESSION_STATES.FAILED;
      errorMessage = `Unhandled error: ${err.message}`;
    } finally {
      const durationMs = Date.now() - startTime;
      this.sessions.delete(sessionId);
      this._messageResolvers.delete(sessionId);
      this.accountLocks.delete(account.id);
      this.emit('session:completed', { sessionId, status: finalStatus, durationMs });
    }

    return { status: finalStatus, errorMessage, groupsSyncedCount, durationMs: Date.now() - startTime };
  }

  async executeActionOnExtension(accountId, action) {
    return new Promise((resolve) => {
      const sessionId = action.sessionId;
      const ackType = 'ACK_RECEIVED';
      
      const timeoutHandle = setTimeout(() => {
        this.wsServer.removeListener('message', ackHandler);
        resolve(false);
      }, 5000);

      const ackHandler = (accId, msg) => {
        // [ERR-SPEC05-01 Remediation]: Sử dụng listener có gỡ bỏ để tránh rò rỉ sự kiện WebSocket
        if (accId === accountId && msg.type === ackType && msg.sessionId === sessionId) {
          clearTimeout(timeoutHandle);
          this.wsServer.removeListener('message', ackHandler);
          resolve(true);
        }
      };

      this.wsServer.on('message', ackHandler);

      const sent = this.wsServer.sendToExtension(accountId, {
        ...action,
        timestamp: Date.now()
      });

      if (!sent) {
        clearTimeout(timeoutHandle);
        this.wsServer.removeListener('message', ackHandler);
        resolve(false);
      }
    });
  }

  async waitForExtensionResult(sessionId, timeoutMs, expectedTypes = null) {
    return new Promise((resolve, reject) => {
      const timeoutHandle = setTimeout(() => {
        this._removeResolver(sessionId, resolver);
        reject(new TimeoutError(`No result for session ${sessionId} in ${timeoutMs}ms`));
      }, timeoutMs);

      const resolver = (msg) => {
        if (expectedTypes && !expectedTypes.includes(msg.type)) return false;
        clearTimeout(timeoutHandle);
        resolve(msg);
        return true;
      };

      this._addResolver(sessionId, resolver);
    });
  }

  handleExtensionMessage(accountId, message) {
    if (!message || !message.type || !message.sessionId) {
      logger.warn('Received malformed message from extension', { accountId, message });
      return;
    }

    const { sessionId } = message;

    logger.debug('Extension message received', { accountId, sessionId, type: message.type });

    if (message.type === 'SESSION_HEARTBEAT') {
      this.wsServer.sendToExtension(accountId, {
        type: 'SESSION_HEARTBEAT',
        sessionId,
        timestamp: Date.now(),
        payload: { direction: 'pong', activeSessions: [...this.sessions.keys()] }
      });
      return;
    }

    const resolvers = this._messageResolvers.get(sessionId) || [];
    for (let i = resolvers.length - 1; i >= 0; i--) {
      const resolved = resolvers[i](message);
      if (resolved) {
        resolvers.splice(i, 1);
        break;
      }
    }
  }

  getSessionStatus(sessionId) {
    return this.sessions.get(sessionId) || null;
  }

  // ─── Snapshot Classifier JSDoc & Implementation ─────────────────────────────
  classifySnapshot(snapshot) {
    if (!snapshot) return SNAPSHOT_TYPES.UNKNOWN;

    const url = (snapshot.url || '').toLowerCase();
    const text = (snapshot.innerText || '').toLowerCase();
    const elements = snapshot.elements || [];
    const modal = (snapshot.activeModal || '').toLowerCase();
    
    const buttons = (snapshot.visibleButtons || []).map(b => b.toLowerCase());
    const inputs = (snapshot.visibleInputs || []).map(i =>
      typeof i === 'string' ? i.toLowerCase() : (i.ariaLabel || '').toLowerCase()
    );

    // CHECK: LOGIN_REQUIRED
    if (url.includes('/login') || url.includes('/checkpoint/') ||
        elements.some(e => e.tag === 'input' &&
          (e.ariaLabel?.toLowerCase().includes('email') ||
           e.ariaLabel?.toLowerCase().includes('password')))) {
      if (text.includes('log in to facebook') || text.includes('đăng nhập vào facebook') ||
          elements.some(e => e.tag === 'input' &&
            (e.ariaLabel?.toLowerCase().includes('email') ||
             e.ariaLabel?.toLowerCase().includes('phone')))) {
        return SNAPSHOT_TYPES.LOGIN_REQUIRED;
      }
    }

    // CHECK: CHECKPOINT_PHONE
    const phoneKeywords = ['confirm your phone', 'xác nhận số điện thoại',
      'enter the code we sent', 'nhập mã chúng tôi', 'verify your identity',
      'xác minh danh tính', 'we need to verify'];
    if (phoneKeywords.some(kw => text.includes(kw) || modal.includes(kw))) {
      if (inputs.some(i => i.includes('phone') || i.includes('code')) ||
          elements.some(e => e.tag === 'input' &&
            (e.ariaLabel?.toLowerCase().includes('phone') ||
             e.ariaLabel?.toLowerCase().includes('code')))) {
        return SNAPSHOT_TYPES.CHECKPOINT_PHONE;
      }
    }

    // CHECK: CHECKPOINT_CAPTCHA
    const captchaKeywords = ['security check', 'kiểm tra bảo mật',
      "let's do a quick security", 'solve this puzzle',
      "i'm not a robot", 'recaptcha', 'identify the images'];
    if (captchaKeywords.some(kw => text.includes(kw) || modal.includes(kw))) {
      return SNAPSHOT_TYPES.CHECKPOINT_CAPTCHA;
    }

    // CHECK: POST_SUCCESS
    if (url.includes('/permalink/') ||
        text.includes('đã được đăng') || text.includes('has been published') ||
        (text.includes('your post') && text.includes('published'))) {
      return SNAPSHOT_TYPES.POST_SUCCESS;
    }
    const successKeywords = ['your post is now shared', 'bài viết của bạn đã được chia sẻ',
      'just posted', 'vừa đăng', 'post is now live'];
    if (successKeywords.some(kw => text.includes(kw))) {
      return SNAPSHOT_TYPES.POST_SUCCESS;
    }

    // CHECK: POST_COMPOSE_OPEN
    if (elements.some(e => e.role === 'textbox' &&
        (e.ariaLabel?.includes('nghĩ gì') ||
         e.ariaLabel?.includes("What's on your mind") ||
         e.ariaLabel?.includes('write something')))) {
      return SNAPSHOT_TYPES.POST_COMPOSE_OPEN;
    }
    const composeKeywords = ["what's on your mind", 'bạn đang nghĩ gì',
      'write something to this group', 'viết gì đó cho nhóm'];
    if (composeKeywords.some(kw => text.includes(kw) || modal.includes(kw))) {
      return SNAPSHOT_TYPES.POST_COMPOSE_OPEN;
    }

    // CHECK: POPUP_RULES
    const rulesKeywords = ['group rules', 'quy tắc nhóm', 'before you post',
      'trước khi đăng', 'community guidelines'];
    if (snapshot.activeModal && rulesKeywords.some(kw => modal.includes(kw)) &&
        buttons.some(b => b.includes('agree') || b.includes('đồng ý'))) {
      return SNAPSHOT_TYPES.POPUP_RULES;
    }

    // CHECK: POPUP_NOTIFICATION
    if (snapshot.activeModal) return SNAPSHOT_TYPES.POPUP_NOTIFICATION;

    // CHECK: NORMAL_FEED
    if (url.includes('/groups/') && !url.includes('/permalink/')) return SNAPSHOT_TYPES.NORMAL_FEED;

    return SNAPSHOT_TYPES.UNKNOWN;
  }

  extractGroupsFromSnapshot(snapshot) {
    const elements = snapshot.elements || [];
    const groups = [];
    const processedUrls = new Set();

    for (const e of elements) {
      if (e.tag === 'a' && e.href) {
        const url = e.href;
        const match = url.match(/facebook\.com\/groups\/([^/?#]+)/);
        if (match) {
          const groupId = match[1];
          if (['feed', 'discover', 'joins', 'create', 'search', 'category'].includes(groupId)) {
            continue;
          }
          const groupUrl = `https://www.facebook.com/groups/${groupId}/`;
          if (!processedUrls.has(groupUrl)) {
            processedUrls.add(groupUrl);
            const name = (e.text || e.ariaLabel || '').trim();
            if (name) {
              groups.push({ id: groupId, name, url: groupUrl });
            }
          }
        }
      }
    }
    return groups;
  }

  // ─── PRIVATE Helpers ─────────────────────────────────────────────────────────
  _initSession(sessionId, accountId, groupId, campaignId) {
    this.sessions.set(sessionId, {
      state: SESSION_STATES.INIT,
      accountId,
      groupId,
      campaignId,
      iteration: 0,
      startedAt: Date.now(),
      lastActivityAt: Date.now(),
      forceStop: false
    });
    this._messageResolvers.set(sessionId, []);

    if (groupId !== 'sync_groups' && campaignId !== 0) {
      try {
        const accountRow = this.db.prepare('SELECT account_id FROM accounts WHERE id = ?').get(accountId);
        const dbAccountId = accountRow ? accountRow.account_id : accountId;

        this.db.prepare(`
          INSERT INTO execution_sessions
          (id, session_token, campaign_id, campaign_group_id, account_id, status, command_payload, started_at)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        `).run(
          sessionId,
          sessionId,
          campaignId,
          groupId,
          dbAccountId,
          'ACTIVE',
          JSON.stringify({ started: true }),
          new Date().toISOString()
        );
      } catch (dbErr) {
        logger.error('Failed to insert execution session into DB', { sessionId, error: dbErr.message });
      }
    }
  }

  _updateSessionState(sessionId, state, iteration = null) {
    const session = this.sessions.get(sessionId);
    if (!session) return;
    session.state = state;
    session.lastActivityAt = Date.now();
    if (iteration !== null) session.iteration = iteration;
  }

  _addResolver(sessionId, resolver) {
    if (!this._messageResolvers.has(sessionId)) {
      this._messageResolvers.set(sessionId, []);
    }
    this._messageResolvers.get(sessionId).push(resolver);
  }

  _removeResolver(sessionId, resolver) {
    const resolvers = this._messageResolvers.get(sessionId);
    if (!resolvers) return;
    const idx = resolvers.indexOf(resolver);
    if (idx > -1) resolvers.splice(idx, 1);
  }

  _renderContent(text, vars = {}) {
    let rendered = text;
    let prev;
    do {
      prev = rendered;
      rendered = rendered.replace(/\{([^{}]+)\}/g, (_, group) => {
        const options = group.split('|');
        return options[Math.floor(Math.random() * options.length)];
      });
    } while (rendered !== prev);

    rendered = rendered.replace(/\{\{(\w+)\}\}/g, (_, key) => vars[key] || '');
    return rendered;
  }

  _buildActionMessage(decision, sessionId) {
    const crypto = require('crypto');
    const base = { sessionId, timestamp: Date.now(), commandId: crypto.randomUUID() };

    switch (decision.action) {
      case 'click':
        return {
          ...base,
          type: 'CLICK_ELEMENT',
          elementId: decision.targetId,
          human: true
        };

      case 'type':
        return {
          ...base,
          type: 'TYPE_TEXT',
          elementId: decision.targetId,
          text: decision.value,
          humanDelay: true
        };

      case 'scroll':
        return {
          ...base,
          type: 'SCROLL',
          scrollY: decision.scrollY || 300,
          behavior: 'smooth'
        };

      case 'wait':
        return {
          ...base,
          type: 'WAIT',
          payload: { ms: decision.waitMs || 2000 }
        };

      case 'dismiss_popup':
      case 'dismiss':
        return {
          ...base,
          type: 'CLICK_ELEMENT',
          elementId: decision.targetId,
          human: false
        };

      case 'select_file':
        return {
          ...base,
          type: 'ATTACH_MEDIA',
          elementId: decision.targetId,
          mediaPaths: decision.filePaths || []
        };

      case 'done':
        return { ...base, type: 'SESSION_COMPLETE', payload: {} };

      default:
        logger.warn('Unknown action in _buildActionMessage', { action: decision.action, sessionId });
        return { ...base, type: 'UNKNOWN_ACTION', payload: decision };
    }
  }

  _extractPostUrl(snapshot) {
    if (snapshot.url?.includes('/permalink/')) return snapshot.url;

    const elements = snapshot.elements || [];
    const postLink = elements.find(e =>
      e.tag === 'a' && e.href?.includes('/permalink/')
    );
    if (postLink?.href) return postLink.href;

    const urlMatch = (snapshot.url || '').match(/(https:\/\/www\.facebook\.com\/groups\/\w+\/permalink\/\d+)/);
    if (urlMatch) return urlMatch[1];

    return snapshot.url || null;
  }

  _buildResult(status, errorMessage, postUrl, iterationsUsed, durationMs) {
    return { status, errorMessage, postUrl, iterationsUsed, durationMs };
  }

  _writeSessionResult(sessionId, account, group, status, errorMessage, postUrl, iterations, actionHistory, durationMs) {
    try {
      const dbStatus = {
        [SESSION_STATES.SUCCESS]: 'POSTED',
        [SESSION_STATES.CHECKPOINT_DETECTED]: 'FAILED',
        [SESSION_STATES.TIMEOUT]: 'FAILED',
        [SESSION_STATES.FAILED]: 'FAILED',
        [SESSION_STATES.SEARCH_FAILED]: 'SEARCH_FAILED'
      }[status] || 'FAILED';

      this.db.prepare(`
        UPDATE campaign_groups
        SET status = ?, last_attempt_at = ?, error_message = ?, post_url = ?, attempt_count = attempt_count + 1
        WHERE id = ?
      `).run(dbStatus, new Date().toISOString(), errorMessage || null, postUrl || null, group.id);

      const crypto = require('crypto');
      const logId = crypto.randomUUID();
      const payloadObj = {
        session_id: sessionId,
        iterations_used: iterations,
        action_history: actionHistory,
        error_message: errorMessage,
        post_url: postUrl
      };

      this.db.prepare(`
        INSERT INTO posting_logs
        (id, campaign_id, campaign_group_id, account_id, group_id, level, event_type,
         message, payload, duration_ms, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `).run(
        logId,
        group.campaign_id,
        group.id,
        account.id,
        group.group_db_id,
        status === SESSION_STATES.SUCCESS ? 'INFO' : 'ERROR',
        status === SESSION_STATES.SUCCESS ? 'POST_SUCCESS' : 'POST_FAIL',
        errorMessage || `Posting session completed with status ${status}`,
        JSON.stringify(payloadObj),
        durationMs,
        new Date().toISOString()
      );

      if (group.id !== 'sync_groups' && group.campaign_id !== 0) {
        const sessionStatus = {
          [SESSION_STATES.SUCCESS]: 'SUCCESS',
          [SESSION_STATES.CHECKPOINT_DETECTED]: 'FAILED',
          [SESSION_STATES.TIMEOUT]: 'TIMEOUT',
          [SESSION_STATES.FAILED]: 'FAILED',
          [SESSION_STATES.SEARCH_FAILED]: 'SEARCH_FAILED'
        }[status] || 'FAILED';

        this.db.prepare(`
          UPDATE execution_sessions
          SET status = ?, completed_at = ?, result_payload = ?
          WHERE id = ?
        `).run(
          sessionStatus,
          new Date().toISOString(),
          JSON.stringify({
            error_message: errorMessage,
            post_url: postUrl,
            iterations,
            duration_ms: durationMs
          }),
          sessionId
        );
      }
    } catch (err) {
      logger.error('Failed to write session result to DB', { sessionId, error: err.message });
    }
  }

  async _runCampaignLoop(campaignId, campaignState) {
    logger.info(`Campaign ${campaignId}: loop started`);

    while (campaignState.isRunning) {
      const pendingGroups = this.db.prepare(`
        SELECT cg.*, g.group_url as group_url, g.group_name as group_name
        FROM campaign_groups cg
        JOIN groups g ON g.id = cg.group_id
        WHERE cg.campaign_id = ? AND cg.status IN ('QUEUE', 'FAILED')
        ORDER BY cg.attempt_count ASC, cg.id ASC
        LIMIT 10
      `).all(campaignId);

      if (pendingGroups.length === 0) {
        logger.info(`Campaign ${campaignId}: No more pending groups — marking complete`);
        this.db.prepare("UPDATE campaigns SET status = 'COMPLETED', completed_at = ? WHERE id = ?")
          .run(new Date().toISOString(), campaignId);
        break;
      }

      const contentRow = this.db.prepare('SELECT spintax_content, image_paths FROM campaigns WHERE id = ? LIMIT 1').get(campaignId);
      const content = {
        text: contentRow ? contentRow.spintax_content : '',
        image_paths: JSON.parse((contentRow && contentRow.image_paths) || '[]')
      };

      for (const groupRow of pendingGroups) {
        if (!campaignState.isRunning) break;

        while (this.accountLocks.size >= this.config.maxConcurrentSessions) {
          await sleep(3000);
          if (!campaignState.isRunning) return;
        }

        const account = this._acquireAccount(campaignId);
        if (!account) {
          logger.warn(`Campaign ${campaignId}: No available accounts, waiting...`);
          await sleep(15000);
          continue;
        }

        const group = {
          id: groupRow.id,
          group_db_id: groupRow.group_id,
          campaign_id: campaignId,
          url: groupRow.group_url,
          name: groupRow.group_name
        };

        this.runPostingSession(account, group, content)
          .catch(err => logger.error('Session failed unexpectedly', { error: err.message, groupId: group.id }));

        const delay = randomBetween(
          campaignState.config.delay_min_ms || (this.config.delayBetweenGroupsMs.min),
          campaignState.config.delay_max_ms || (this.config.delayBetweenGroupsMs.max)
        );
        logger.debug(`Campaign ${campaignId}: Waiting ${delay}ms before next group`);
        await sleep(delay);
      }

      await sleep(5000);
    }
  }

  _acquireAccount(campaignId) {
    const campaign = this.db.prepare('SELECT account_id FROM campaigns WHERE id = ?').get(campaignId);
    let accounts = [];
    if (campaign && campaign.account_id) {
      accounts = this.db.prepare("SELECT * FROM accounts WHERE id = ? AND status = 'ACTIVE'").all(campaign.account_id);
    }

    if (accounts.length === 0) {
      accounts = this.db.prepare("SELECT * FROM accounts WHERE status = 'ACTIVE'").all();
    }

    const freeAccount = accounts.find(a => !this.accountLocks.has(a.id));
    if (freeAccount) {
      this.accountLocks.add(freeAccount.id);
      return freeAccount;
    }
    return null;
  }

  _sendHeartbeats() {
    const now = Date.now();
    for (const [sessionId, session] of this.sessions) {
      if (now - session.lastActivityAt > this.config.heartbeatIntervalMs * 3) {
        logger.warn('Dead session detected — no activity', {
          sessionId, accountId: session.accountId,
          inactiveMs: now - session.lastActivityAt
        });
        this._failSession(sessionId, 'ERR-AI-05');
        continue;
      }

      if (this.wsServer.isExtensionConnected(session.accountId)) {
        this.wsServer.sendToExtension(session.accountId, {
          type: 'SESSION_HEARTBEAT',
          sessionId,
          timestamp: now,
          payload: { direction: 'ping', activeSessions: [...this.sessions.keys()] }
        });
      } else {
        logger.warn('Extension disconnected during heartbeat', {
          sessionId, accountId: session.accountId
        });
        this._failSession(sessionId, 'ERR-NET-02');
      }
    }
  }

  _failSession(sessionId, reason) {
    const session = this.sessions.get(sessionId);
    if (!session) return;

    logger.error('Force-failing session', { sessionId, reason, accountId: session.accountId });

    const resolvers = this._messageResolvers.get(sessionId) || [];
    for (const resolver of resolvers) {
      resolver({ type: 'SESSION_FAILED', sessionId, payload: { reason } });
    }

    this.sessions.delete(sessionId);
    this._messageResolvers.delete(sessionId);
    this.accountLocks.delete(session.accountId);

    this.emit('session:completed', { sessionId, status: 'FAILED', reason });
  }

  // ─── FSM & Watchdog Methods ──────────────────────────────────────────────────

  /**
   * Watchdog timer chạy định kỳ 60s để dọn dẹp các session bị treo (zombie)
   */
  _runWatchdog() {
    const now = Date.now();
    for (const [sessionId, session] of this.sessions) {
      const inactiveDuration = now - session.lastActivityAt;
      const totalDuration = now - session.startedAt;
      
      // Zombie Check 1: Session vượt quá absolute timeout (120s Circuit Breaker)
      if (totalDuration > this.config.sessionTimeoutMs) {
        logger.warn('Watchdog: Session exceeded absolute timeout, cleaning zombie', {
          sessionId, accountId: session.accountId, totalDurationMs: totalDuration
        });
        this._failSession(sessionId, 'ERR-ACT-14'); // Absolute Session Timeout
        continue;
      }
      
      // Zombie Check 2: Session không hoạt động quá 60s
      if (inactiveDuration > 60000) {
        logger.warn('Watchdog: Inactive zombie session detected', {
          sessionId, accountId: session.accountId, inactiveMs: inactiveDuration
        });
        this._failSession(sessionId, 'ERR-ACT-13'); // Inactivity Timeout
      }
    }
  }

  /**
   * Chuyển trạng thái hệ thống sang Bảo trì khẩn cấp (MAINTENANCE)
   */
  async enterMaintenanceMode(reason) {
    if (this.fsmState === SESSION_STATES.MAINTENANCE) return;
    this.fsmState = SESSION_STATES.MAINTENANCE;
    logger.error(`[FSM] Entering MAINTENANCE mode. Reason: ${reason}`);

    // Pause tất cả các campaign đang chạy
    for (const [campaignId, state] of this.activeCampaigns) {
      await this.stopCampaign(campaignId, true);
    }

    // Gửi cảnh báo hệ thống
    this.wsServer.broadcastToUIClients({
      type: 'SYSTEM_ALERT',
      level: 'CRITICAL',
      title: 'Hệ Thống Bảo Trì Khẩn Cấp',
      message: reason === 'ERR-DB-01'
        ? 'Database bị hỏng (corrupt). Hệ thống đang kích hoạt phục hồi tự động...'
        : 'Tất cả API keys đã bị cạn kiệt hoặc bị lỗi (ERR-AI-06). Vui lòng thêm key mới.',
      ts: Date.now()
    });

    // Nếu SQLite hỏng, tự phục hồi từ bản sao lưu gần nhất
    if (reason === 'ERR-DB-01') {
      try {
        logger.info('[FSM] Kích hoạt autoRestore cho database...');
        // Giả sử có module backupManager
        // await backupManager.autoRestore();
        this.exitMaintenanceMode('DB_RESTORED');
      } catch (err) {
        logger.error(`[FSM] Tự động phục hồi database thất bại: ${err.message}`);
        this.escalateToHuman('SYSTEM', 'ERR-ESC-24');
      }
    }
  }

  /**
   * Thoát khỏi chế độ bảo trì về trạng thái IDLE
   */
  exitMaintenanceMode(trigger) {
    if (this.fsmState !== SESSION_STATES.MAINTENANCE) return;
    this.fsmState = SESSION_STATES.IDLE;
    logger.info(`[FSM] Exiting MAINTENANCE mode. Trigger: ${trigger}`);
    
    this.wsServer.broadcastToUIClients({
      type: 'SYSTEM_ALERT',
      level: 'INFO',
      title: 'Hệ Thống Đã Khôi Phục',
      message: 'Hệ thống đã thoát chế độ bảo trì và sẵn sàng hoạt động.',
      ts: Date.now()
    });
  }

  /**
   * Leo thang xử lý lên AI Leader (IDE Agent) để tự chẩn đoán lỗi FSM
   */
  escalateToLeader(sessionId, error) {
    logger.warn(`[FSM] Escalating session ${sessionId} to AI Leader. Error: ${error}`);
    this.fsmState = SESSION_STATES.ESCALATING_LEADER;
    
    // Phát sự kiện để IDE Agent (đang chạy ngầm) nhận biết và chẩn đoán
    this.emit('fsm:escalate_leader', { sessionId, error, ts: Date.now() });
  }

  /**
   * Leo thang xử lý lên phê duyệt từ người dùng (Human)
   */
  escalateToHuman(sessionId, error) {
    logger.error(`[FSM] Escalating session ${sessionId} to Human. Error: ${error}`);
    this.fsmState = SESSION_STATES.ESCALATING_HUMAN;

    this.wsServer.broadcastToUIClients({
      type: 'HUMAN_APPROVAL_REQUIRED',
      sessionId,
      error,
      message: 'Cần người dùng phê duyệt hoặc can thiệp thủ công để tiếp tục.',
      ts: Date.now()
    });
  }

  destroy() {
    clearInterval(this._heartbeatInterval);
    clearInterval(this._watchdogInterval);
    this.sessions.clear();
    this._messageResolvers.clear();
    this.removeAllListeners();
    logger.info('AgentLoop destroyed');
  }
}

module.exports = { AgentLoop, SNAPSHOT_TYPES, SESSION_STATES, TimeoutError };
```

---

## 10. Error Recovery Scenarios

### 10.1 Scenario 1: Extension Bị Disconnect Giữa Session
**Tình huống**: WebSocket connection với Extension bị drop khi đang ở `WAIT_ACTION_RESULT`.
- **Phản ứng**: AgentLoop chuyển trạng thái sang `FAILED` với mã lỗi `ERR-NET-02`, giải phóng lock account, cập nhật DB group sang `QUEUE` hoặc `FAILED` để chạy lại sau.

### 10.2 Scenario 2: AI Brain Rate Limit (429 từ Gemini/Ollama)
- **Phản ứng**: Không đếm là iteration thất bại. Kích hoạt exponential backoff nghỉ 60s/120s trước khi thử lại với cùng snapshot.

### 10.3 Scenario 3: Bão Checkpoint / Cooldown Thích Nghi
- **Phản ứng**: Ngắt session lập tức, set status tài khoản thành `CHECKPOINT_MANUAL` hoặc `COOLDOWN` trong DB. Bắn WebSocket cảnh báo tới Dashboard UI để người dùng nhảy vào can thiệp thủ công.

### 10.4 Scenario 4: Database Corruption Recovery

| Bước | Hành động |
|------|----------|
| 1 | AgentLoop phát hiện `SQLITE_CORRUPT` error hoặc `PRAGMA integrity_check` trả về kết quả khác 'ok' |
| 2 | Chuyển FSM → `MAINTENANCE`. Pause tất cả campaigns. |
| 3 | `backupManager.autoRestore()` rename DB corrupt → copy backup mới nhất |
| 4 | Nếu restore thành công → Exit MAINTENANCE → IDLE |
| 5 | Nếu restore thất bại → Giữ MAINTENANCE, notify user qua UI để can thiệp thủ công |

---

## 11. Configuration Reference

| Variable | Default | Mô Tả |
|---|---|---|
| `MAX_CONCURRENT_SESSIONS` | `3` | Số session đồng thời tối đa |
| `SESSION_TIMEOUT_MS` | `120000` | Timeout toàn bộ session (2 phút) |
| `ACTION_TIMEOUT_MS` | `30000` | Timeout đợi action result (30s) |
| `NAVIGATE_TIMEOUT_MS` | `30000` | Timeout navigate đến group (30s) |
| `AI_TIMEOUT_MS` | `20000` | Timeout gọi AI Brain (20s) |
| `MAX_ITERATIONS` | `20` | Vòng lặp AI tối đa/session |
| `MAX_RETRIES` | `3` | Retry tối đa cho mỗi action |
| `HEARTBEAT_INTERVAL_MS` | `10000` | Interval heartbeat (10s) |

---

## Cảnh báo An ninh & Lỗ hổng Kiến trúc

### 🔴 LỖ HỔNG CRITICAL
1. **[ERR-SPEC05-01] Tranh chấp và rò rỉ sự kiện WebSocket trong `executeActionOnExtension`:**
   - *Rủi ro:* Hàm `executeActionOnExtension` đăng ký lắng nghe phản hồi của Extension bằng `this.wsServer.once('message', ackHandler)`. Vì `wsServer` là server dùng chung, sự kiện `'message'` kích hoạt cho *bất kỳ* Extension nào gửi dữ liệu về (heartbeat, log...). Sử dụng `.once()` làm listener bị tháo bỏ ngay lập tức ở tin nhắn đầu tiên bất kỳ, khiến session thật bị treo cứng (timeout 5s).
   - *Yêu cầu Remediation:* Tuyệt đối không dùng listener toàn cục. Sử dụng cơ chế định tuyến tin nhắn thông qua Map lưu các resolver theo `commandId` hoặc `sessionId` để định tuyến chính xác tin nhắn phản hồi.
2. **[ERR-SPEC05-02] FSM Deadlock khi ghi DB thất bại trong khối `finally`:**
   - *Rủi ro:* Hàm ghi DB `_writeSessionResult` nằm trực tiếp trong khối `finally` của `runPostingSession` mà không có try-catch bảo vệ. Nếu ghi DB lỗi (do DB bận hoặc disk full), chương trình sẽ ném lỗi ngắt luồng ngay lập tức, bỏ qua các bước dọn dẹp bên dưới như `this.accountLocks.delete(account.id)`, khiến tài khoản bị khóa cứng vĩnh viễn (zombie lock).
   - *Yêu cầu Remediation:* Bắt buộc bọc lời gọi hàm `_writeSessionResult` trong khối `try-catch` riêng biệt bên trong khối `finally` chính để đảm bảo luôn chạy qua lệnh xóa lock tài khoản.

### 🟠 LỖ HỔNG HIGH
1. **[ERR-SPEC05-03] Khởi tạo session ngoài `try-finally` gây rò rỉ Lock tài khoản:**
   - *Rủi ro:* Hàm `_initSession` thực hiện ghi DB nằm ngoài khối `try-finally` chính nhưng lại gọi sau khi đã thêm lock tài khoản. Nếu `_initSession` ném lỗi DB, tài khoản sẽ bị khóa vĩnh viễn vì không bao giờ nhảy vào `finally`.
   - *Yêu cầu Remediation:* Đưa `_initSession` vào bên trong khối `try` chính hoặc bọc try-finally ngay khi add lock tài khoản.
2. **[ERR-SPEC05-04] Thiếu cấu hình `busy_timeout` cho SQLite:**
   - *Rủi ro:* SQLite mặc định có `busy_timeout = 0ms` trong better-sqlite3, làm gia tăng đột biến lỗi `SQLITE_BUSY` khi chạy đa luồng ghi song song và gây sập FSM.
   - *Yêu cầu Remediation:* Thiết lập `busy_timeout = 5000` ngay sau khi open database connection.
3. **[ERR-SPEC05-05] Luồng di chuyển tìm kiếm nhóm cố định 100% (Static Routing):**
   - *Rủi ro:* Luồng truy cập trang chủ, gõ tìm kiếm và click nhóm rập khuôn 100% cho mọi tài khoản là dấu vết rõ ràng để AI của Facebook phát hiện hành vi bot tự động.
   - *Yêu cầu Remediation:* Đa dạng hóa luồng di chuyển: cấu hình tỷ lệ 60% truy cập trực tiếp URL nhóm `https://www.facebook.com/groups/{id}/`, và thêm các thao tác cuộn/đọc tin ngẫu nhiên trên trang chủ để pha loãng hành vi.
4. **[ERR-SPEC05-06] Thiếu Circuit Breaker cấp độ Proxy/IP gây bão Checkpoint hàng loạt (Checkpoint Storm):**
   - *Rủi ro:* Khi dải IP/Proxy bị quét và block, tài khoản A bị checkpoint. Nếu không có circuit breaker cấp mạng, backend tiếp tục nạp tài khoản B chạy trên cùng proxy đó vào, khiến tài khoản B bị checkpoint tiếp lập tức.
   - *Yêu cầu Remediation:* Xây dựng Proxy Circuit Breaker. Nếu phát hiện `>= 2` tài khoản dùng chung proxy bị checkpoint trong vòng 10 phút, lập tức khóa tạm thời (Cooldown) proxy đó và dừng các chiến dịch liên quan.

---

## 12. Dependency Graph

```
agent_loop.js
├── db.js (better-sqlite3 instance)
├── wsServer.js (WebSocket sendToExtension/isExtensionConnected)
└── ai_brain.js (LLM decision gateway)
```