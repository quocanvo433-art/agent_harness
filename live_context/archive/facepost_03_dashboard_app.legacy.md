# Hermes FacePost-Group — Dashboard App Spec v0.4
**File:** `facepost_03_dashboard_app.md`  
**Cập nhật:** 2026-06-15  
**Trạng thái:** ACTIVE — Đây là spec chính thức cho Local Dashboard.

## 🚨 CRITICAL WARNINGS & ANTI-PATTERNS (CHỐNG AI ẢO TƯỞNG)

### 8. `db.js` / `schema.sql` (SQLite Adapter)
* 🚨 **Cảnh báo đỏ (Lỗi cú pháp PostgreSQL):** Do các AI Agent hiện tại học rất nhiều code backend sử dụng PostgreSQL, chúng sẽ có xu hướng viết các cú pháp như `RETURNING id`, `ON CONFLICT DO UPDATE` hoặc sử dụng các hàm thời gian `NOW()`. Thư viện `better-sqlite3` của ứng dụng sẽ crash ngay khi biên dịch.
* 🚀 **Yêu cầu bắt buộc:** Khống chế Agent **CHỈ ĐƯỢC PHÉP** viết cú pháp SQLite thuần túy (`INSERT OR REPLACE`, dùng `datetime('now')` cho kiểu text). Đồng thời bắt buộc phải bọc các câu lệnh ghi bằng cơ chế xử lý lỗi `SQLITE_BUSY` đi kèm với cấu hình khóa `PRAGMA journal_mode=WAL;` để tránh xung đột ghi đa luồng từ nhiều tài khoản.

---

## Mục Lục

1. [Tổng Quan Kiến Trúc](#1-tổng-quan-kiến-trúc)
2. [Database Schema](#2-database-schema)
3. [Campaign Execution Flow](#3-campaign-execution-flow)
4. [Multi-client WebSocket Server](#4-multi-client-websocket-server)
5. [REST API Endpoints](#5-rest-api-endpoints)
6. [SpintaxResolver](#6-spintaxresolver)
7. [Dashboard UI Spec (React)](#7-dashboard-ui-spec-react)
8. [Graceful Shutdown Handler](#8-graceful-shutdown-handler)
9. [Error Codes & Recovery](#9-error-codes--recovery)
10. [Day-2 Resilience Services](#10-day-2-resilience-services)

---

## 1. Tổng Quan Kiến Trúc

```
┌─────────────────────────────────────────────────────────────┐
│                   Local Dashboard Server                     │
│                    Node.js + Express                         │
│                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌────────────────┐  │
│  │  REST API    │   │  WebSocket   │   │ CampaignManager│  │
│  │  /api/*      │   │  Server      │   │ (Orchestrator) │  │
│  └──────┬───────┘   └──────┬───────┘   └───────┬────────┘  │
│         │                  │                    │           │
│         └──────────────────┴────────────────────┘           │
│                            │                                │
│                    ┌───────┴───────┐                        │
│                    │   SQLite DB   │                        │
│                    │  (schema.sql) │                        │
│                    └───────────────┘                        │
└─────────────────────────────────────────────────────────────┘
         │                        │
         ▼                        ▼
  ┌─────────────┐        ┌────────────────┐
  │  React UI   │        │ Chrome Ext(s)  │
  │  (Browser)  │        │ accountId=A    │
  │  uiClients  │        │ accountId=B    │
  └─────────────┘        └────────────────┘
```

**Stack:**
- **Runtime:** Node.js 20+ LTS
- **Framework:** Express 4.x
- **Database:** SQLite3 (via `better-sqlite3`)
- **WebSocket:** `ws` library
- **Frontend:** React 18 + Vite (served từ `/public`)
- **SSE:** Native Node.js response streaming

**Cổng mặc định:** `3000` (HTTP + WS upgrade trên cùng server)

#### 🛡️ Port Conflict Guard (Cơ chế chống trùng cổng)
Để đảm bảo Dashboard Server luôn khởi động thành công ngay cả khi cổng `3000` đang bị chiếm dụng bởi tiến trình khác (lỗi `EADDRINUSE`), hệ thống triển khai cơ chế quét cổng động:
- **Quét cổng động:** Express server bắt đầu thử lắng nghe (listen) tại cổng mặc định `3000`. Nếu gặp lỗi `EADDRINUSE`, server sẽ tự động tăng số hiệu cổng lên `3001`, `3002`, `3003`... và tiếp tục thử cho đến khi tìm được một cổng trống để liên kết (bind) thành công.
- **Ghi nhớ cổng hoạt động:** Sau khi khởi động thành công trên cổng đã chọn (ví dụ: `3001`), server sẽ lập tức ghi số hiệu cổng thực tế này vào một file JSON tạm tại đường dẫn `data/active_port.json` với định dạng:
  ```json
  {
    "port": 3001
  }
  ```
- **Phục hồi & Đồng bộ kết nối (Chrome Extension):**
  Khi Chrome Extension cần thiết lập kết nối WebSocket tới server, nó không thể giả định cổng mặc định `3000`. Thay vào đó, Extension sẽ thực hiện một Native Messaging handshake hoặc gọi Native Messaging event để yêu cầu Native Host trả về số hiệu cổng thực tế được đọc từ `data/active_port.json`. Từ đó, WebSocket client của Extension sẽ kết nối đúng URL (ví dụ: `ws://127.0.0.1:3001`) một cách tự động và chính xác.

---

## 2. Database Schema

### 2.1 Full `schema.sql`

> ⚠️ **LƯU Ý QUAN TRỌNG:** Toàn bộ SQL trong spec này và Spec 06 phải dùng **SQLite syntax**.
> KHÔNG dùng PostgreSQL syntax: `BIGSERIAL`, `JSONB`, `TIMESTAMPTZ`, `plpgsql`, `LATERAL JOIN`, `EXTRACT(EPOCH FROM ...)`.
> Mọi timestamp → `TEXT DEFAULT (datetime('now'))`. Mọi BOOLEAN → `INTEGER` (0/1). Mọi JSON → `TEXT`.

```sql
-- =====================================================
-- Hermes FacePost-Group — Database Schema v0.4
-- Engine: SQLite 3.x
-- =====================================================

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA synchronous = NORMAL;

-- ─────────────────────────────────────────────────────
-- [MỚI v1.3 — Day-2 Resilience] PRAGMA Configurations
-- ─────────────────────────────────────────────────────
PRAGMA auto_vacuum = INCREMENTAL;
PRAGMA wal_autocheckpoint = 1000;

-- ─────────────────────────────────────────────────────
-- TABLE: accounts
-- Quản lý Facebook nick / accounts
-- ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS accounts (
    id              TEXT PRIMARY KEY,             -- PK UUID/hex string đồng bộ Spec 00
    account_id      TEXT NOT NULL UNIQUE,        -- Internal unique key (e.g. "fb_12345")
    fb_uid          TEXT,                         -- Facebook UID
    display_name    TEXT NOT NULL,
    cookies         TEXT,                         -- JSON serialized cookies
    status          TEXT NOT NULL DEFAULT 'ACTIVE'
                    CHECK(status IN ('ACTIVE','CHECKPOINT','DIE','SUSPENDED','COOLDOWN','HIBERNATED')),
    last_active_at  DATETIME,
    last_checked_at DATETIME,
    notes           TEXT,
    health_score    REAL NOT NULL DEFAULT 100.0,  -- [CR-02] Điểm sức khỏe tài khoản (0-100), Spec 06 checkpoint scoring
    auto_disabled   INTEGER NOT NULL DEFAULT 0,   -- [CR-02] Cờ tự động vô hiệu hóa (0/1)
    auto_disabled_reason TEXT,                     -- [CR-02] Lý do vô hiệu hóa tự động
    auto_disabled_at DATETIME,                     -- [CR-02] Thời điểm vô hiệu hóa
    penalty_multiplier REAL NOT NULL DEFAULT 1.0,  -- [CR-02] Hệ số phạt cooldown
    last_checkpoint_at DATETIME,                   -- [CR-02] Lần checkpoint gần nhất
    cooldown_until  DATETIME,                      -- [CR-02] Cooldown hết hạn lúc
    checkpoint_count_7d INTEGER NOT NULL DEFAULT 0, -- [CR-02] Số lần checkpoint trong 7 ngày
    ws_auth_secret  TEXT,                          -- [CR-02] HMAC secret cho WebSocket handshake
    created_at      DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at      DATETIME NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_accounts_status ON accounts(status);
CREATE INDEX IF NOT EXISTS idx_accounts_account_id ON accounts(account_id);

-- ─────────────────────────────────────────────────────
-- TABLE: groups
-- Danh sách Facebook Groups để đăng bài
-- ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS groups (
    id              TEXT PRIMARY KEY,             -- PK UUID/hex string đồng bộ Spec 00
    campaign_id     TEXT,                         -- [CONF-13 FIX] campaign link trong routes
    group_id        TEXT NOT NULL UNIQUE,         -- Facebook Group ID
    group_name      TEXT NOT NULL,
    group_url       TEXT,
    member_count    INTEGER DEFAULT 0,
    posting_status  TEXT NOT NULL DEFAULT 'ACTIVE'
                    CHECK(posting_status IN ('ACTIVE','INACTIVE','BANNED')),
    last_posted_at  DATETIME,
    notes           TEXT,
    created_at      DATETIME NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_groups_posting_status ON groups(posting_status);
CREATE INDEX IF NOT EXISTS idx_groups_campaign_id ON groups(campaign_id);

-- ─────────────────────────────────────────────────────
-- TABLE: fetched_groups
-- Lưu danh sách nhóm được fetch về từ tài khoản phục vụ Sync Groups (NinjaPoster)
-- ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fetched_groups (
    id              TEXT PRIMARY KEY,             -- PK UUID/hex string đồng bộ Spec 00
    account_id      TEXT NOT NULL,               -- Tham chiếu tới accounts.account_id (TEXT UNIQUE)
    fb_group_id     TEXT NOT NULL,               -- Facebook Group ID
    group_name      TEXT NOT NULL,
    group_url       TEXT,
    privacy         TEXT,                        -- PUBLIC / CLOSED / SECRET
    member_count    INTEGER DEFAULT 0,
    sync_at         DATETIME NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id) ON DELETE CASCADE,
    UNIQUE(account_id, fb_group_id)
);

CREATE INDEX IF NOT EXISTS idx_fetched_groups_account ON fetched_groups(account_id);

-- ─────────────────────────────────────────────────────
-- TABLE: campaigns
-- Campaign = bộ cài đặt đăng bài (spintax content + group list + schedule)
-- ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS campaigns (
    id              TEXT PRIMARY KEY,             -- PK UUID/hex string đồng bộ Spec 00
    name            TEXT NOT NULL,
    spintax_content TEXT NOT NULL,               -- Raw spintax template
    image_paths     TEXT,                         -- JSON array of image/video file paths [CR-03]
    account_id      TEXT,                         -- Preferred account FK (nullable = auto-select)
    delay_min       INTEGER NOT NULL DEFAULT 30,  -- Seconds between posts (min)
    delay_max       INTEGER NOT NULL DEFAULT 120, -- Seconds between posts (max)
    status          TEXT NOT NULL DEFAULT 'DRAFT'
                    CHECK(status IN ('DRAFT','QUEUED','RUNNING','PAUSED','COMPLETED','FAILED')),
    total_groups    INTEGER NOT NULL DEFAULT 0,
    posted_count    INTEGER NOT NULL DEFAULT 0,
    failed_count    INTEGER NOT NULL DEFAULT 0,
    config          TEXT DEFAULT '{}',            -- [GAP-03-02] JSON config tuỳ chỉnh
    started_at      DATETIME,
    completed_at    DATETIME,
    notes           TEXT,
    created_at      DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at      DATETIME NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status);

-- ─────────────────────────────────────────────────────
-- TABLE: campaign_groups
-- Junction: Campaign <-> Group (many-to-many) + trạng thái từng group
-- ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS campaign_groups (
    id              TEXT PRIMARY KEY,             -- PK UUID/hex string đồng bộ Spec 00
    campaign_id     TEXT NOT NULL,
    group_id        TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'QUEUE'
                    CHECK(status IN ('QUEUE','RUNNING','POSTED','FAILED','SKIPPED','POST_LOCKED')),
    resolved_content TEXT,                        -- Spintax đã được resolve (unique per group)
    resolved_media_paths TEXT,                    -- JSON array chứa media đã resolve (nếu có)
    post_url        TEXT,                         -- URL bài đã đăng (nếu thành công)
    attempt_count   INTEGER NOT NULL DEFAULT 0,
    last_attempt_at DATETIME,
    posted_at       DATETIME,
    error_message   TEXT,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE,
    FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
    UNIQUE(campaign_id, group_id)
);

CREATE INDEX IF NOT EXISTS idx_cg_campaign_status ON campaign_groups(campaign_id, status);

-- ─────────────────────────────────────────────────────
-- TABLE: posting_logs
-- [MỚI v0.3] Log chi tiết từng hành động đăng bài
-- ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS posting_logs (
    id              TEXT PRIMARY KEY,             -- PK UUID/hex string đồng bộ Spec 00
    campaign_id     TEXT NOT NULL,
    campaign_group_id TEXT,
    account_id      TEXT,
    group_id        TEXT,
    level           TEXT NOT NULL DEFAULT 'INFO'
                    CHECK(level IN ('DEBUG','INFO','WARN','ERROR','FATAL')),
    event_type      TEXT NOT NULL,               -- e.g. 'SESSION_START','POST_SUCCESS','POST_FAIL','SPINTAX_RESOLVE'
    message         TEXT NOT NULL,
    payload         TEXT,                         -- JSON: extra context (resolved_content, error stack, etc.)
    duration_ms     INTEGER,                      -- Thời gian thực thi (ms) cho event này
    created_at      DATETIME NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE,
    FOREIGN KEY (campaign_group_id) REFERENCES campaign_groups(id) ON DELETE SET NULL,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE SET NULL,
    FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_logs_campaign ON posting_logs(campaign_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_logs_level ON posting_logs(level);
CREATE INDEX IF NOT EXISTS idx_logs_event ON posting_logs(event_type);

-- ─────────────────────────────────────────────────────
-- TABLE: execution_sessions
-- [MỚI v0.3] Track trạng thái agent đang chạy (Chrome Extension)
-- Mỗi lần Extension nhận lệnh và bắt đầu thao tác = 1 session
-- ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS execution_sessions (
    id              TEXT PRIMARY KEY,             -- PK UUID/hex string đồng bộ Spec 00
    session_token   TEXT NOT NULL UNIQUE,         -- UUID token xác thực
    campaign_id     TEXT NOT NULL,
    campaign_group_id TEXT NOT NULL,
    account_id      TEXT NOT NULL,               -- refers to accounts.account_id (TEXT UNIQUE), NOT accounts.id
    status          TEXT NOT NULL DEFAULT 'PENDING'
                    CHECK(status IN ('PENDING','ACTIVE','SUCCESS','FAILED','TIMEOUT','CANCELLED')),
    command_payload TEXT NOT NULL,                -- JSON: lệnh gửi cho Extension
    result_payload  TEXT,                         -- JSON: kết quả trả về từ Extension
    started_at      DATETIME NOT NULL DEFAULT (datetime('now')),
    ack_at          DATETIME,                     -- Extension đã nhận lệnh
    completed_at    DATETIME,
    timeout_seconds INTEGER NOT NULL DEFAULT 120,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE,
    FOREIGN KEY (campaign_group_id) REFERENCES campaign_groups(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sessions_status ON execution_sessions(status, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_account ON execution_sessions(account_id, status);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON execution_sessions(session_token);

-- ─────────────────────────────────────────────────────
-- TABLE: account_events  [GAP-03-01]
-- Track các sự kiện quan trọng trên từng account (checkpoint, ban, post...)
-- ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS account_events (
    id          TEXT PRIMARY KEY,             -- PK UUID/hex string đồng bộ Spec 00
    account_id  TEXT NOT NULL,
    event_type  TEXT NOT NULL CHECK(event_type IN (
        'CHECKPOINT_PHONE','CHECKPOINT_CAPTCHA','CHECKPOINT_SELFIE',
        'POLICY_WARNING','POST_SUCCESS','POST_FAILED','LOGIN_REQUIRED',
        'ACCOUNT_BANNED','ACCOUNT_LOCKED'
    )),
    event_data  TEXT DEFAULT '{}',  -- JSON string (không phải JSONB)
    error_code  TEXT,
    severity    TEXT CHECK(severity IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    created_at  TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_account_events_account ON account_events(account_id);
CREATE INDEX IF NOT EXISTS idx_account_events_type ON account_events(event_type);
CREATE INDEX IF NOT EXISTS idx_account_events_created ON account_events(created_at);

-- ─────────────────────────────────────────────────────
-- TABLE: post_intervals  [GAP-03-01]
-- Lưu lịch sử khoảng cách giữa các lần đăng (để phân tích nhịp độ)
-- ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS post_intervals (
    id               TEXT PRIMARY KEY,             -- PK UUID/hex string đồng bộ Spec 00
    account_id       TEXT NOT NULL,
    group_id         TEXT,
    posted_at        TEXT NOT NULL,
    interval_minutes REAL,
    created_at       TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
);

-- ─────────────────────────────────────────────────────
-- TABLE: target_groups
-- Quản lý danh sách nhóm mục tiêu Facebook
-- ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS target_groups (
  id                     TEXT PRIMARY KEY, -- UUID PK
  fb_group_id            TEXT UNIQUE,
  group_name             TEXT,
  group_url              TEXT,
  keyword                TEXT,
  allow_non_member_post  INTEGER DEFAULT 1,
  status                 TEXT CHECK(status IN ('ACTIVE', 'REMOVED', 'RESTRICTED', 'SEARCH_FAILED')),
  created_at             TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_target_groups_fb_id ON target_groups(fb_group_id);

-- ─────────────────────────────────────────────────────
-- TABLE: donations
-- Lưu trữ lịch sử ủng hộ (donate) tự nguyện của người dùng
-- ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS donations (
  id                     TEXT PRIMARY KEY, -- UUID PK
  amount                 REAL NOT NULL, -- Số tiền ủng hộ
  currency               TEXT DEFAULT 'VND', -- Đơn vị tiền tệ (VND, USD, USDT)
  payment_method         TEXT CHECK(payment_method IN ('vietqr', 'momo', 'crypto')),
  transaction_hash       TEXT, -- Mã transaction hash nếu là crypto hoặc ID giao dịch VietQR/MoMo
  status                 TEXT CHECK(status IN ('PENDING', 'CONFIRMED', 'FAILED')),
  created_at             TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_donations_created ON donations(created_at);

-- ─────────────────────────────────────────────────────
-- TABLE: system_settings
-- Lưu trữ cấu hình toàn cục của hệ thống Dashboard
-- ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS system_settings (
  key                    TEXT PRIMARY KEY,
  value                  TEXT NOT NULL,
  updated_at             TEXT DEFAULT (datetime('now'))
);

-- ─────────────────────────────────────────────────────
-- TABLE: content_library
-- [MỚI v1.2] Lưu trữ các bài viết soạn thảo từ Content Engine
-- ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS content_library (
    id                     TEXT PRIMARY KEY, -- UUID PK
    persona_id             TEXT,             -- FK từ persona (nếu có)
    prompt                 TEXT,             -- Prompt ý đồ của người dùng
    generated_text         TEXT NOT NULL,    -- Văn bản sinh ra bởi AI
    media_paths            TEXT,             -- JSON array chứa đường dẫn các file ảnh/video đính kèm
    humanness_score        REAL,             -- Điểm Humanness của bài viết
    created_at             TEXT DEFAULT (datetime('now')),
    updated_at             TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_content_library_created ON content_library(created_at);

-- ─────────────────────────────────────────────────────
-- TABLE: slang_dictionary
-- [MỚI v1.2] Lưu trữ từ lóng, viết tắt quen thuộc trên mạng xã hội
-- ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS slang_dictionary (
    id              TEXT PRIMARY KEY,             -- UUID PK
    word            TEXT NOT NULL UNIQUE,         -- Từ lóng / viết tắt (ví dụ: 'ae', 'cmnr')
    meaning         TEXT NOT NULL,                -- Nghĩa gốc hoặc giải thích cách dùng
    category        TEXT NOT NULL DEFAULT 'SLANG' -- 'SLANG' | 'ABBREVIATION' | 'BUZZWORD'
                    CHECK(category IN ('SLANG','ABBREVIATION','BUZZWORD')),
    status          TEXT NOT NULL DEFAULT 'ACTIVE'
                    CHECK(status IN ('ACTIVE','INACTIVE')),
    created_at      DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at      DATETIME NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_slang_word ON slang_dictionary(word);
CREATE INDEX IF NOT EXISTS idx_slang_status ON slang_dictionary(status);

-- ─────────────────────────────────────────────────────
-- TABLE: api_key_pool
-- [MỚI v1.3] Lưu trữ pool các Gemini API Keys (mã hóa AES-256-GCM dính HWID)
-- ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS api_key_pool (
    id              TEXT PRIMARY KEY,             -- UUID PK
    label           TEXT NOT NULL,                -- Nhãn gợi nhớ (VD: 'Key chính', 'Key backup')
    encrypted_key   TEXT NOT NULL,                -- API Key đã mã hóa AES-256-GCM (HWID-locked)
    status          TEXT NOT NULL DEFAULT 'ACTIVE'
                    CHECK(status IN ('ACTIVE','COOLDOWN','DISABLED')),
    total_calls     INTEGER NOT NULL DEFAULT 0,   -- Tổng số lần gọi API thành công
    error_count     INTEGER NOT NULL DEFAULT 0,   -- Số lần lỗi liên tiếp
    last_used_at    TEXT,                         -- Thời gian sử dụng gần nhất
    cooldown_until  TEXT,                         -- Hết hạn cooldown (24h khi bị 429/403)
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_api_key_status ON api_key_pool(status);

-- Seed dữ liệu cấu hình quyên góp mặc định
INSERT OR IGNORE INTO system_settings (key, value) VALUES ('monthly_donation_active', '0');
INSERT OR IGNORE INTO system_settings (key, value) VALUES ('last_donation_prompt_at', '2026-06-16 00:00:00');
INSERT OR IGNORE INTO system_settings (key, value) VALUES ('cruel_choice_count', '0');

-- ─────────────────────────────────────────────────────
-- TRIGGERS: auto-update updated_at
-- ─────────────────────────────────────────────────────
CREATE TRIGGER IF NOT EXISTS accounts_updated_at
    AFTER UPDATE ON accounts
    BEGIN UPDATE accounts SET updated_at = datetime('now') WHERE id = NEW.id; END;

CREATE TRIGGER IF NOT EXISTS campaigns_updated_at
    AFTER UPDATE ON campaigns
    BEGIN UPDATE campaigns SET updated_at = datetime('now') WHERE id = NEW.id; END;

CREATE TRIGGER IF NOT EXISTS content_library_updated_at
    AFTER UPDATE ON content_library
    BEGIN UPDATE content_library SET updated_at = datetime('now') WHERE id = NEW.id; END;

CREATE TRIGGER IF NOT EXISTS slang_dictionary_updated_at
    AFTER UPDATE ON slang_dictionary
    BEGIN UPDATE slang_dictionary SET updated_at = datetime('now') WHERE id = NEW.id; END;

CREATE TRIGGER IF NOT EXISTS api_key_pool_updated_at
    AFTER UPDATE ON api_key_pool
    BEGIN UPDATE api_key_pool SET updated_at = datetime('now') WHERE id = NEW.id; END;

-- ─────────────────────────────────────────────────────
-- VIEWS: tiện truy vấn
-- ─────────────────────────────────────────────────────
CREATE VIEW IF NOT EXISTS v_campaign_progress AS
SELECT
    c.id            AS campaign_id,
    c.name          AS campaign_name,
    c.status        AS campaign_status,
    c.total_groups,
    c.posted_count,
    c.failed_count,
    (c.total_groups - c.posted_count - c.failed_count) AS remaining,
    ROUND(100.0 * c.posted_count / MAX(c.total_groups, 1), 1) AS pct_done,
    c.started_at,
    c.updated_at
FROM campaigns c;
```

### 2.2 `db.js` Adapter Specification

Hạ tầng SQLite Adapter sử dụng `better-sqlite3` đồng bộ hoàn toàn với AD-05. Đảm bảo cấu hình WAL mode, `busy_timeout` và xử lý lỗi `SQLITE_BUSY` bằng exponential backoff.

```javascript
// src/db/database.js
'use strict';

const Database = require('better-sqlite3');
const path = require('path');
const fs = require('fs');
const logger = require('../utils/logger');

// Thống nhất đường dẫn database an toàn (phù hợp với cả môi trường đóng gói ASAR read-only)
const dbPath = process.env.DATABASE_PATH || path.resolve(__dirname, '../../data/database.sqlite');

// Đảm bảo thư mục dữ liệu tồn tại
const dataDir = path.dirname(dbPath);
if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir, { recursive: true });
}

// Khởi tạo Database với busy_timeout 5000ms để tránh lock lỗi
const db = new Database(dbPath, { 
    verbose: (sql) => logger.debug(`[SQL] ${sql}`),
    timeout: 5000 
});

// Cấu hình PRAGMA cho sqlite3
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');
db.pragma('synchronous = NORMAL');

/**
 * [AD-05] Hàm helper để chạy write queries với Exponential Backoff retry
 * Tránh lỗi crash hệ thống do SQLITE_BUSY khi đa luồng cùng ghi.
 * 
 * @param {Function} dbOperationFn - Hàm chứa các logic prepared statement
 * @param {number} maxRetries - Số lần thử tối đa (default 10)
 * @returns {any} Kết quả của database query
 */
function withRetry(dbOperationFn, maxRetries = 10) {
    let attempts = 0;
    let delay = 50; // ms ban đầu

    while (attempts < maxRetries) {
        try {
            return dbOperationFn();
        } catch (error) {
            if (error.code === 'SQLITE_BUSY' || error.message.includes('busy')) {
                attempts++;
                if (attempts >= maxRetries) {
                    logger.error(`[DB] SQLITE_BUSY retry limit reached (${maxRetries}). Operation failed.`);
                    throw error;
                }
                // Jittered exponential delay
                const jitteredDelay = Math.round(delay * (0.8 + Math.random() * 0.7));
                logger.warn(`[DB] SQLITE_BUSY detected. Retrying in ${jitteredDelay}ms (attempt ${attempts}/${maxRetries})`);
                
                // Sleep đồng bộ (vì better-sqlite3 là synchronous)
                const start = Date.now();
                while (Date.now() - start < jitteredDelay) {
                    // spin lock/wait
                }
                delay = Math.min(delay * 2, 500); // cap ở 500ms
            } else {
                throw error; // Lỗi khác thì quăng trực tiếp
            }
        }
    }
}

// Chạy schema khởi tạo
const schemaSql = fs.readFileSync(path.resolve(__dirname, './schema.sql'), 'utf8');
withRetry(() => {
    db.exec(schemaSql);
});

module.exports = {
    db,
    withRetry
};
```

### 2.3 Incremental Database Migration Runner Specification

Cơ chế cập nhật cấu trúc cơ sở dữ liệu (Database Schema Migration) được thiết kế theo mô hình **Incremental Migration Runner** dựa trên `PRAGMA user_version` của SQLite. Cơ chế này đảm bảo việc cập nhật schema diễn ra tuần tự, an toàn, và cô lập hoàn toàn giữa các phiên bản nhằm chống mất mát hoặc sai lệch dữ liệu người dùng.

#### 2.3.1 Kiến trúc Thiết kế & Nguyên lý Hoạt động

1. **Theo dõi Phiên bản (Version Tracking):**
   - Phiên bản hiện tại của cơ sở dữ liệu được lưu trữ trực tiếp trong header của tệp SQLite thông qua `PRAGMA user_version` (một số nguyên lớn hơn hoặc bằng 0, mặc định là 0 khi vừa tạo tệp).
   - Phiên bản này được truy vấn bằng lệnh: `PRAGMA user_version;`.

2. **Quản lý Tệp di cư (Migration Files Structure):**
   - Các bản vá cơ sở dữ liệu được định nghĩa dưới dạng các tệp tin `.sql` tĩnh đặt trong thư mục `src/db/migrations/`.
   - Quy tắc đặt tên tệp bắt buộc: `XXX_description.sql` (với `XXX` là số hiệu phiên bản gồm 3 chữ số tăng dần, ví dụ: `001_init.sql`, `002_add_sessions.sql`, `003_add_slang_dictionary.sql`).

3. **Giao dịch Loại bỏ Xung đột Ghi (Conflict Resolution & Transactions):**
   - Quá trình chạy mỗi tệp di cư phải được bọc hoàn toàn bên trong một transaction với khóa ghi ngay từ đầu (`BEGIN IMMEDIATE TRANSACTION` hoặc `.immediate()` trong transaction của `better-sqlite3`). Điều này ngăn chặn tình trạng xung đột ghi (Database Lock / `SQLITE_BUSY`) nếu có nhiều tiến trình hoặc luồng cố gắng thay đổi cơ sở dữ liệu cùng lúc.
   - Việc cập nhật `PRAGMA user_version = new_version` phải thực thi thành công ở bước cuối cùng của transaction trước khi thực hiện commit.

4. **Cơ chế Fail-Fast (Dừng khẩn cấp khi gặp lỗi):**
   - Nếu bất kỳ tệp di cư nào gặp lỗi trong quá trình thực thi (lỗi cú pháp SQL, lỗi ràng buộc khóa ngoại, v.v.), transaction sẽ lập tức được rollback hoàn toàn để đưa database về trạng thái của phiên bản an toàn trước đó.
   - Tiến trình khởi chạy server sẽ bị hủy lập tức (`process.exit(1)`) đi kèm log chi tiết để ngăn chặn ứng dụng chạy với cấu trúc schema không nhất quán, tránh gây lỗi ở các tác vụ nghiệp vụ tiếp theo.

#### 2.3.2 Mã nguồn mẫu `migrationRunner.js`

Dưới đây là mã nguồn chuẩn hóa cho bộ chạy di cư cơ sở dữ liệu sử dụng thư viện `better-sqlite3`:

```javascript
// src/db/migrationRunner.js
'use strict';

const fs = require('fs');
const path = require('path');
const logger = require('../utils/logger');

/**
 * Khởi chạy tiến trình di cư cơ sở dữ liệu tuần tự
 * @param {object} db - Đối tượng database kết nối từ better-sqlite3
 * @param {string} migrationsDir - Đường dẫn tuyệt đối đến thư mục chứa các tệp .sql di cư
 */
function runMigrations(db, migrationsDir) {
    logger.info('[DB-MIGRATION] Bắt đầu kiểm tra cấu trúc cơ sở dữ liệu...');

    try {
        // 1. Đọc phiên bản hiện tại từ SQLite Header
        const currentVersion = db.pragma('user_version', { simple: true });
        logger.info(`[DB-MIGRATION] Phiên bản schema hiện tại của Database: v${currentVersion}`);

        // 2. Kiểm tra thư mục chứa file migrations
        if (!fs.existsSync(migrationsDir)) {
            logger.warn(`[DB-MIGRATION] Thư mục chứa các tệp di cư không tồn tại: ${migrationsDir}. Bỏ qua bước di cư.`);
            return;
        }

        // 3. Đọc danh sách các tệp di cư và phân tích cú pháp
        const migrationFiles = fs.readdirSync(migrationsDir)
            .filter(file => file.endsWith('.sql'))
            .map(file => {
                const match = file.match(/^(\d+)_(.+)\.sql$/);
                if (!match) {
                    throw new Error(`Tên tệp di cư không hợp lệ: ${file}. Định dạng yêu cầu: XXX_description.sql`);
                }
                return {
                    version: parseInt(match[1], 10),
                    filename: file,
                    filepath: path.join(migrationsDir, file)
                };
            })
            .sort((a, b) => a.version - b.version);

        // 4. Lọc và thực thi các bản vá có phiên bản lớn hơn phiên bản hiện tại
        for (const migration of migrationFiles) {
            if (migration.version <= currentVersion) {
                continue;
            }

            logger.info(`[DB-MIGRATION] Phát hiện bản vá mới. Đang áp dụng v${migration.version} (${migration.filename})...`);
            const sqlContent = fs.readFileSync(migration.filepath, 'utf8');

            // Khởi tạo transaction độc quyền ghi (IMMEDIATE) để chống ghi đè song song
            const migrationTx = db.transaction(() => {
                // Thực thi nội dung SQL di cư
                db.exec(sqlContent);
                // Cập nhật chỉ số phiên bản trong SQLite header
                db.pragma(`user_version = ${migration.version}`);
            });

            // Thực thi transaction ở chế độ IMMEDIATE
            migrationTx.immediate();
            logger.info(`[DB-MIGRATION] Áp dụng thành công bản vá v${migration.version}`);
        }

        logger.info('[DB-MIGRATION] Hoàn thành kiểm tra và cập nhật cấu trúc cơ sở dữ liệu.');
    } catch (error) {
        logger.error(`[DB-MIGRATION] [CRITICAL] Lỗi trong quá trình thực thi di cư cơ sở dữ liệu: ${error.message}`);
        // Cơ chế Fail-Fast: Ném lỗi lên tiến trình khởi chạy chính để crash app an toàn
        throw error;
    }
}

module.exports = {
    runMigrations
};
```

---

## 3. Campaign Execution Flow

### 3.1 Pseudocode — `CampaignManager.executeCampaign(campaignId)`

```
FUNCTION executeCampaign(campaignId):

  [1] LOAD CAMPAIGN
      campaign = DB.get("SELECT * FROM campaigns WHERE id = ?", campaignId)
      IF campaign.status NOT IN ('QUEUED', 'RUNNING'):
          THROW "Campaign không ở trạng thái hợp lệ"

      pendingGroups = DB.all(
          "SELECT cg.*, g.group_id, g.group_name
           FROM campaign_groups cg
           JOIN groups g ON g.id = cg.group_id
           WHERE cg.campaign_id = ? AND cg.status = 'QUEUE'
           ORDER BY cg.id ASC",
          campaignId
      )

      IF pendingGroups.length == 0:
          markCampaignCompleted(campaignId)
          RETURN

  [2] UPDATE STATUS
      DB.run("UPDATE campaigns SET status='RUNNING', started_at=NOW() WHERE id=?", campaignId)
      broadcastToUI({ type: 'CAMPAIGN_STARTED', campaignId })

  [3] LOOP qua từng pendingGroup:
      FOR EACH cg IN pendingGroups:

          IF campaignIsPaused(campaignId):
              LOG "Campaign bị pause, dừng loop"
              BREAK

          [3a] RESOLVE SPINTAX
               resolvedContent = SpintaxResolver.resolve(campaign.spintax_content)
               DB.run("UPDATE campaign_groups SET resolved_content=? WHERE id=?",
                      resolvedContent, cg.id)
               logEvent(campaignId, cg.id, 'SPINTAX_RESOLVE', resolvedContent)

          [3b] CHỌN ACCOUNT
               accountId = campaign.account_id ?? selectAvailableAccount()
               IF accountId == NULL:
                   logEvent(campaignId, cg.id, 'NO_ACCOUNT', 'Không có account ACTIVE')
                   markGroupFailed(cg.id, 'No available account')
                   CONTINUE

               account = DB.get("SELECT * FROM accounts WHERE account_id=? AND status='ACTIVE'", accountId)
               IF account == NULL:
                   markGroupFailed(cg.id, 'Account CHECKPOINT/DIE')
                   CONTINUE

          [3c] KIỂM TRA EXTENSION CLIENT
               wsClient = extensionClients.get(accountId)
               IF wsClient == NULL OR wsClient.readyState != OPEN:
                   logEvent(campaignId, cg.id, 'NO_WS_CLIENT', `Không có WS connection cho ${accountId}`)
                   markGroupFailed(cg.id, 'Extension not connected')
                   CONTINUE

          [3d] TẠO EXECUTION SESSION
               sessionToken = uuid()
               DB.run(
                   "INSERT INTO execution_sessions
                    (session_token, campaign_id, campaign_group_id, account_id, status, command_payload, timeout_seconds)
                    VALUES (?,?,?,?,'PENDING',?,?)",
                   sessionToken, campaignId, cg.id, accountId,
                   JSON({
                       action: 'POST_TO_GROUP',
                       groupId: cg.group_id,
                       content: resolvedContent,
                       images: campaign.image_paths
                   }),
                   campaign.timeout_seconds ?? 120
               )

          [3e] GỬI LỆNH QUA WEBSOCKET
               DB.run("UPDATE campaign_groups SET status='RUNNING', attempt_count=attempt_count+1,
                       last_attempt_at=NOW() WHERE id=?", cg.id)

               wsClient.send(JSON.stringify({
                   type: 'START_SESSION',
                   sessionToken,
                   groupId: cg.group_id,
                   groupUrl: cg.group_url,
                   content: resolvedContent,
                   images: campaign.image_paths ?? []
               }))

               broadcastToUI({
                   type: 'GROUP_POSTING',
                   campaignId,
                   groupId: cg.group_id,
                   groupName: cg.group_name
               })

          [3f] CHỜ KẾT QUẢ (Timeout-based Promise)
               result = AWAIT waitForSessionResult(sessionToken, timeout=120s)

               IF result.success:
                   DB.run("UPDATE campaign_groups SET status='POSTED', post_url=?, posted_at=NOW() WHERE id=?",
                          result.postUrl, cg.id)
                   DB.run("UPDATE campaigns SET posted_count=posted_count+1 WHERE id=?", campaignId)
                   logEvent(campaignId, cg.id, 'POST_SUCCESS', result.postUrl)
                   broadcastToUI({ type: 'GROUP_POSTED', campaignId, groupId: cg.group_id })

               ELSE:
                   markGroupFailed(cg.id, result.error)
                   DB.run("UPDATE campaigns SET failed_count=failed_count+1 WHERE id=?", campaignId)
                   broadcastToUI({ type: 'GROUP_FAILED', campaignId, groupId: cg.group_id, error: result.error })

          [3g] DELAY NGẪU NHIÊN
               delayMs = randomInt(campaign.delay_min * 1000, campaign.delay_max * 1000)
               logEvent(campaignId, cg.id, 'DELAY', `Chờ ${delayMs}ms trước group tiếp theo`)
               AWAIT sleep(delayMs)

  [4] HOÀN THÀNH
      remaining = DB.get("SELECT COUNT(*) as cnt FROM campaign_groups WHERE campaign_id=? AND status='QUEUE'", campaignId)
      IF remaining.cnt == 0:
          DB.run("UPDATE campaigns SET status='COMPLETED', completed_at=NOW() WHERE id=?", campaignId)
          broadcastToUI({ type: 'CAMPAIGN_COMPLETED', campaignId })
      ELSE IF campaignIsPaused(campaignId):
          DB.run("UPDATE campaigns SET status='PAUSED' WHERE id=?", campaignId)
          broadcastToUI({ type: 'CAMPAIGN_PAUSED', campaignId })

END FUNCTION
```

### 3.2 Helper Functions

```
FUNCTION selectAvailableAccount():
    -- Ưu tiên account nghỉ lâu nhất (last_active_at ASC) và status=ACTIVE
    -- Không chọn account đang có execution_session ACTIVE
    -- [GAP-03-05 FIX] Dùng EXCLUSIVE transaction để tránh TOCTOU race condition
    row = DB.get("""
        SELECT a.account_id FROM accounts a
        WHERE a.status = 'ACTIVE'
          AND a.account_id NOT IN (
              SELECT account_id FROM execution_sessions
              WHERE status IN ('PENDING','ACTIVE')
          )
        ORDER BY a.last_active_at ASC  -- ưu tiên account nghỉ lâu nhất
        LIMIT 1
    """)
    RETURN row?.account_id ?? NULL

FUNCTION waitForSessionResult(sessionToken, timeout):
    RETURN new Promise((resolve, reject) => {
        timer = setTimeout(() => {
            DB.run("UPDATE execution_sessions SET status='TIMEOUT' WHERE session_token=?", sessionToken)
            resolve({ success: false, error: 'TIMEOUT' })
        }, timeout * 1000)

        -- SessionResultEmitter nhận event khi Extension gửi kết quả về
        sessionResultEmitter.once(`result:${sessionToken}`, (result) => {
            clearTimeout(timer)
            resolve(result)
        })
    })

FUNCTION markGroupFailed(cgId, reason):
    DB.run("UPDATE campaign_groups SET status='FAILED', error_message=? WHERE id=?", reason, cgId)
```

### 3.3 selectAvailableAccount() — Implementation (GAP-03-05)

```javascript
// campaign_manager.js — dùng IMMEDIATE transaction để tránh TOCTOU race condition
function selectAvailableAccount(db) {
    // Dùng better-sqlite3 transaction với EXCLUSIVE lock
    return db.transaction(() => {
        const account = db.prepare(`
            SELECT a.account_id
            FROM accounts a
            WHERE a.status = 'ACTIVE'
              AND a.account_id NOT IN (
                  SELECT account_id FROM execution_sessions
                  WHERE status IN ('PENDING','ACTIVE')
              )
            ORDER BY a.last_active_at ASC  -- ưu tiên account nghỉ lâu nhất
            LIMIT 1
        `).get();
        return account;
    }).exclusive(); // EXCLUSIVE transaction = write lock, ngăn race condition
}
// Usage:
// const account = selectAvailableAccount(db);
// if (!account) throw new Error('ERR_NO_AVAILABLE_ACCOUNT');
// Ngay sau đó create execution_session trong cùng transaction
```

### 3.4 CampaignManager Class — pauseCampaign() (GAP-03-06)

```javascript
// campaign_manager.js
class CampaignManager {
    constructor(db, wsUiClients) {
        this.db = db;
        this.wsUiClients = wsUiClients;         // ref tới uiClients Set từ wsServer
        this.pausedCampaigns = new Set();        // Set<campaignId>
        this.runningLoops = new Map();           // campaignId → { promise, cancelFn }
    }

    pauseCampaign(campaignId) {
        this.pausedCampaigns.add(campaignId);
        this.db.prepare("UPDATE campaigns SET status='PAUSED' WHERE id=?").run(campaignId);
        broadcastToUI(this.wsUiClients, { type: 'CAMPAIGN_PAUSED', campaignId });
        return { success: true };
    }

    resumeCampaign(campaignId) {
        this.pausedCampaigns.delete(campaignId);
        this.db.prepare("UPDATE campaigns SET status='RUNNING' WHERE id=?").run(campaignId);
        broadcastToUI(this.wsUiClients, { type: 'CAMPAIGN_RESUMED', campaignId });
    }

    campaignIsPaused(campaignId) {
        return this.pausedCampaigns.has(campaignId);
    }

    static globalPause() {
        // Dùng trong graceful shutdown để stop tất cả campaigns
        _globalPauseFlag = true;
    }
}
let _globalPauseFlag = false;
```

---

## 4. Multi-client WebSocket Server

> **[BUG FIX B4]** Thay biến đơn `extensionClient` bằng `Map<accountId, WebSocket>` để hỗ trợ nhiều account đồng thời.  
> **[BUG FIX A4]** Bổ sung handshake auth token trước khi chấp nhận kết nối.

### 4.1 Full Code — `src/websocket/wsServer.js`

```javascript
// src/websocket/wsServer.js
'use strict';

const { WebSocketServer, WebSocket } = require('ws');
const { EventEmitter } = require('events');
const { v4: uuidv4 } = require('uuid');
const crypto = require('crypto');
const db = require('../db/database');
const logger = require('../utils/logger');

// ─────────────────────────────────────────────────────────────
// STATE
// ─────────────────────────────────────────────────────────────

/**
 * [FIX B4] Map thay vì biến đơn — hỗ trợ nhiều account/extension cùng lúc
 * Key: accountId (string)  Value: WebSocket instance
 */
const extensionClients = new Map();

/**
 * Set các WebSocket kết nối từ React Dashboard UI
 */
const uiClients = new Set();

/**
 * EventEmitter để truyền kết quả session về CampaignManager
 */
const sessionResultEmitter = new EventEmitter();
sessionResultEmitter.setMaxListeners(100);

// Cache chống replay attacks cho HMAC handshake
const usedNonces = new Set();

// ─────────────────────────────────────────────────────────────
// SETUP
// ─────────────────────────────────────────────────────────────

/**
 * @param {import('http').Server} httpServer
 */
function setupWebSocket(httpServer) {
    const wss = new WebSocketServer({ server: httpServer, path: '/ws' });

    wss.on('connection', (ws, req) => {
        // Mỗi connection bắt đầu ở trạng thái UNAUTHENTICATED
        ws._authenticated = false;
        ws._clientType = null;   // 'extension' | 'ui'
        ws._accountId = null;

        logger.info(`[WS] New connection from ${req.socket.remoteAddress}`);

        // Auth timeout: nếu sau 10s không gửi HELLO/AUTH → đóng
        const authTimeout = setTimeout(() => {
            if (!ws._authenticated) {
                logger.warn('[WS] Auth timeout, closing connection');
                ws.close(4001, 'Authentication timeout');
            }
        }, 10_000);

        ws.on('message', (rawData) => {
            let msg;
            try {
                msg = JSON.parse(rawData.toString());
            } catch {
                ws.send(JSON.stringify({ type: 'ERROR', code: 'INVALID_JSON' }));
                return;
            }

            // ── HELLO HANDSHAKE (HMAC-SHA256) ──────────────────
            if (msg.type === 'HELLO' || msg.type === 'AUTH') {
                clearTimeout(authTimeout);
                handleHello(ws, msg);
                return;
            }

            // Chặn mọi message khác nếu chưa auth
            if (!ws._authenticated) {
                ws.send(JSON.stringify({ type: 'ERROR', code: 'NOT_AUTHENTICATED' }));
                return;
            }

            // ── EXTENSION MESSAGES ────────────────────────────
            if (ws._clientType === 'extension') {
                handleExtensionMessage(ws, msg);
            }

            // ── UI MESSAGES ───────────────────────────────────
            if (ws._clientType === 'ui') {
                handleUiMessage(ws, msg);
            }
        });

        ws.on('close', (code, reason) => {
            clearTimeout(authTimeout);
            handleDisconnect(ws, code);
        });

        ws.on('error', (err) => {
            logger.error(`[WS] Error on ${ws._accountId ?? 'unknown'}: ${err.message}`);
        });
    });

    logger.info('[WS] WebSocket server initialized at /ws');
    return wss;
}

// ─────────────────────────────────────────────────────────────
// HANDSHAKE VERIFICATION
// ─────────────────────────────────────────────────────────────

/**
 * [AD-02] Handshake auth bằng HMAC-SHA256 cho Extension và Token cho UI
 */
function handleHello(ws, msg) {
    const { clientType, accountId, nonce, timestamp, signature, extensionVersion, token } = msg;

    // Phân luồng UI client auth (dashboard chạy cục bộ)
    if (clientType === 'ui' || msg.type === 'AUTH' && clientType === 'ui') {
        const UI_TOKEN = process.env.UI_AUTH_TOKEN || 'local-ui-token';
        const clientToken = token || msg.token;
        if (clientToken !== UI_TOKEN) {
            ws.send(JSON.stringify({ type: 'AUTH_REJECT', reason: 'Invalid UI token' }));
            ws.close(4003, 'Forbidden');
            return;
        }

        ws._authenticated = true;
        ws._clientType = 'ui';
        uiClients.add(ws);

        ws.send(JSON.stringify({ type: 'WELCOME', clientType: 'ui' }));
        logger.info(`[WS] UI client authenticated (total: ${uiClients.size})`);
        return;
    }

    // Luồng Extension client auth: HMAC-SHA256 challenge-response
    if (!accountId || !nonce || !timestamp || !signature) {
        ws.send(JSON.stringify({ type: 'AUTH_REJECT', reason: 'Missing handshake parameters (accountId, nonce, timestamp, signature)' }));
        ws.close(4002, 'Bad Request');
        logger.warn('[WS] Extension connection rejected: missing handshake parameters');
        return;
    }

    // 1. Kiểm tra độ lệch thời gian (Timestamp skew) - tối đa ±30 giây
    const now = Date.now();
    if (Math.abs(now - timestamp) > 30_000) {
        ws.send(JSON.stringify({ type: 'AUTH_REJECT', reason: 'Timestamp skew too large' }));
        ws.close(4003, 'Forbidden');
        logger.warn(`[WS] Handshake failed for accountId=${accountId}: timestamp skew too large (${Math.abs(now - timestamp)}ms)`);
        return;
    }

    // 2. Chống Replay Attack bằng cách lưu và kiểm tra nonce
    if (usedNonces.has(nonce)) {
        ws.send(JSON.stringify({ type: 'AUTH_REJECT', reason: 'Nonce already used' }));
        ws.close(4003, 'Forbidden');
        logger.warn(`[WS] Handshake failed for accountId=${accountId}: replay attack detected (nonce=${nonce})`);
        return;
    }
    usedNonces.add(nonce);
    setTimeout(() => usedNonces.delete(nonce), 60_000); // Giải phóng nonce sau 60 giây

    // 3. Tìm account và lấy ws_auth_secret từ database
    const account = db.prepare('SELECT ws_auth_secret, status FROM accounts WHERE account_id = ?').get(accountId);
    if (!account) {
        ws.send(JSON.stringify({ type: 'AUTH_REJECT', reason: 'Account not registered' }));
        ws.close(4003, 'Forbidden');
        logger.warn(`[WS] Handshake failed: accountId=${accountId} not found in database`);
        return;
    }

    // 4. Tính toán và verify HMAC-SHA256 signature
    const secret = account.ws_auth_secret;
    const computedSignature = crypto
        .createHmac('sha256', secret)
        .update(`${nonce}:${timestamp}`)
        .digest('hex');

    if (signature !== computedSignature) {
        ws.send(JSON.stringify({ type: 'AUTH_REJECT', reason: 'Invalid signature' }));
        ws.close(4003, 'Forbidden');
        logger.warn(`[WS] Handshake failed for accountId=${accountId}: signature mismatch`);
        return;
    }

    // 5. Kết nối thành công, dọn dẹp connection cũ từ cùng accountId (nếu có)
    if (extensionClients.has(accountId)) {
        const oldWs = extensionClients.get(accountId);
        if (oldWs.readyState === WebSocket.OPEN) {
            oldWs.close(4000, 'Replaced by new connection');
        }
        extensionClients.delete(accountId);
    }

    ws._authenticated = true;
    ws._clientType = 'extension';
    ws._accountId = accountId;
    extensionClients.set(accountId, ws);

    // Trả về WELCOME kèm sessionId UUID chuẩn Spec 00
    const sessionId = uuidv4();
    ws.send(JSON.stringify({ 
        type: 'WELCOME', 
        sessionId,
        serverTime: now,
        serverVersion: '2.1.0'
    }));

    logger.info(`[WS] Extension authenticated successfully: accountId=${accountId}, version=${extensionVersion}`);

    // Cập nhật thời gian hoạt động cuối cùng của account
    db.prepare(`UPDATE accounts SET last_active_at = datetime('now') WHERE account_id = ?`)
      .run(accountId);

    // Broadcast tới các UI client
    broadcastToUI({ type: 'EXTENSION_CONNECTED', accountId });
}

// ─────────────────────────────────────────────────────────────
// EXTENSION MESSAGE HANDLER
// ─────────────────────────────────────────────────────────────

function handleExtensionMessage(ws, msg) {
    const { type, sessionToken } = msg;

    switch (type) {

        case 'SESSION_ACK': {
            // Extension đã nhận lệnh, đang xử lý
            if (!sessionToken) return;
            db.prepare(`UPDATE execution_sessions SET status='ACTIVE', ack_at=datetime('now')
                        WHERE session_token=?`).run(sessionToken);
            logger.info(`[WS] Session ACK: ${sessionToken}`);
            broadcastToUI({ type: 'SESSION_ACK', sessionToken });
            break;
        }

        case 'SESSION_RESULT': {
            // Extension báo cáo kết quả (thành công hoặc thất bại)
            const { success, postUrl, error } = msg;

            if (!sessionToken) return;

            const newStatus = success ? 'SUCCESS' : 'FAILED';
            db.prepare(`UPDATE execution_sessions
                        SET status=?, result_payload=?, completed_at=datetime('now')
                        WHERE session_token=?`)
              .run(newStatus, JSON.stringify(msg), sessionToken);

            // Emit event để CampaignManager đang AWAIT nhận được kết quả
            sessionResultEmitter.emit(`result:${sessionToken}`, { success, postUrl, error });

            logger.info(`[WS] Session RESULT: ${sessionToken} → ${newStatus}`);
            break;
        }

        case 'HEARTBEAT': {
            // Extension gửi heartbeat định kỳ
            ws.send(JSON.stringify({ type: 'HEARTBEAT_OK', ts: Date.now() }));
            db.prepare(`UPDATE accounts SET last_active_at=datetime('now') WHERE account_id=?`)
              .run(ws._accountId);
            break;
        }

        case 'ACCOUNT_STATUS': {
            // Extension báo cáo trạng thái account (checkpoint, die...)
            const { status, reason } = msg;
            const validStatuses = ['ACTIVE','CHECKPOINT','DIE','SUSPENDED','COOLDOWN'];
            if (!validStatuses.includes(status)) break;

            db.prepare(`UPDATE accounts SET status=?, notes=?, updated_at=datetime('now')
                        WHERE account_id=?`)
              .run(status, reason ?? null, ws._accountId);

            broadcastToUI({
                type: 'ACCOUNT_STATUS_CHANGED',
                accountId: ws._accountId,
                status,
                reason
            });
            logger.warn(`[WS] Account ${ws._accountId} status → ${status}: ${reason}`);
            break;
        }

        case 'SEARCH_FAILED': {
            // Extension báo cáo tìm kiếm nhóm thất bại (Chốt AD-05 & Spec 00)
            const { fb_group_id, group_name } = msg;
            if (!fb_group_id) break;

            // Cập nhật trạng thái target_groups thành SEARCH_FAILED
            db.prepare("UPDATE target_groups SET status = 'SEARCH_FAILED' WHERE fb_group_id = ?")
              .run(fb_group_id);

            // Log event lỗi tìm kiếm vào account_events để UI hiển thị logs báo cáo lỗi tương ứng
            const eventId = uuidv4();
            db.prepare(`
                INSERT INTO account_events (id, account_id, event_type, event_data, severity, created_at)
                VALUES (?, ?, 'POST_FAILED', ?, 'HIGH', datetime('now'))
            `).run(
                eventId,
                ws._accountId,
                JSON.stringify({ fb_group_id, group_name, error: 'SEARCH_FAILED: Group not found via search' })
            );

            logger.error(`[WS] Search failed for group: ${group_name} (${fb_group_id})`);
            
            // Broadcast sự kiện tới toàn bộ UI client
            broadcastToUI({
                type: 'TARGET_GROUP_SEARCH_FAILED',
                accountId: ws._accountId,
                fb_group_id,
                group_name
            });
            break;
        }

        default:
            logger.warn(`[WS] Unknown extension message type: ${type}`);
    }
}

// ─────────────────────────────────────────────────────────────
// UI MESSAGE HANDLER
// ─────────────────────────────────────────────────────────────

function handleUiMessage(ws, msg) {
    // UI chủ yếu nhận broadcast; không cần nhiều handler phức tạp ở đây
    switch (msg.type) {
        case 'PING':
            ws.send(JSON.stringify({ type: 'PONG', ts: Date.now() }));
            break;
        default:
            break;
    }
}

// ─────────────────────────────────────────────────────────────
// DISCONNECT HANDLER
// ─────────────────────────────────────────────────────────────

function handleDisconnect(ws, code) {
    if (ws._clientType === 'extension' && ws._accountId) {
        extensionClients.delete(ws._accountId);
        logger.info(`[WS] Extension disconnected: ${ws._accountId} (code ${code})`);
        broadcastToUI({ type: 'EXTENSION_DISCONNECTED', accountId: ws._accountId });
    } else if (ws._clientType === 'ui') {
        uiClients.delete(ws);
        logger.info(`[WS] UI client disconnected (remaining: ${uiClients.size})`);
    }
}

// ─────────────────────────────────────────────────────────────
// BROADCAST HELPERS
// ─────────────────────────────────────────────────────────────

/**
 * Gửi message đến TẤT CẢ UI clients đang kết nối
 */
function broadcastToUI(payload) {
    const data = JSON.stringify(payload);
    for (const client of uiClients) {
        if (client.readyState === WebSocket.OPEN) {
            client.send(data);
        }
    }
}

/**
 * Gửi lệnh đến Extension của một accountId cụ thể
 * @returns {boolean} true nếu gửi thành công
 */
function sendToExtension(accountId, payload) {
    const client = extensionClients.get(accountId);
    if (!client || client.readyState !== WebSocket.OPEN) {
        logger.warn(`[WS] sendToExtension: No OPEN connection for accountId=${accountId}`);
        return false;
    }
    client.send(JSON.stringify(payload));
    return true;
}

/**
 * Kiểm tra Extension cho accountId có kết nối không
 */
function isExtensionConnected(accountId) {
    const client = extensionClients.get(accountId);
    return client?.readyState === WebSocket.OPEN;
}

module.exports = {
    setupWebSocket,
    extensionClients,
    uiClients,
    sessionResultEmitter,
    broadcastToUI,
    sendToExtension,
    isExtensionConnected,
};
```

---

## 5. REST API Endpoints

### 5.1 File: `src/routes/campaigns.js`

```javascript
// src/routes/campaigns.js
'use strict';

const express = require('express');
const router = express.Router();
const db = require('../db/database');
const { CampaignManager } = require('../services/campaignManager');
const manager = new CampaignManager();

// ── GET /api/campaigns ────────────────────────────────────────
// Lấy danh sách campaigns
router.get('/', (req, res) => {
    const { status, limit = 20, offset = 0 } = req.query;
    let query = 'SELECT * FROM v_campaign_progress';
    const params = [];
    if (status) {
        query += ' WHERE campaign_status = ?';
        params.push(status);
    }
    query += ' ORDER BY campaign_id DESC LIMIT ? OFFSET ?';
    params.push(Number(limit), Number(offset));

    const rows = db.prepare(query).all(...params);
    res.json({ data: rows });
});

// ── POST /api/campaigns ───────────────────────────────────────
// Tạo campaign mới
router.post('/', (req, res) => {
    const { name, spintax_content, group_ids, account_id, delay_min, delay_max, image_paths } = req.body;

    if (!name || !spintax_content || !Array.isArray(group_ids) || group_ids.length === 0) {
        return res.status(400).json({ error: 'Missing required fields: name, spintax_content, group_ids' });
    }

    const insertCampaign = db.prepare(`
        INSERT INTO campaigns (name, spintax_content, account_id, delay_min, delay_max, image_paths, total_groups, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'DRAFT')
    `);

    const insertGroup = db.prepare(`
        INSERT OR IGNORE INTO campaign_groups (campaign_id, group_id, status)
        VALUES (?, ?, 'QUEUE')
    `);

    const txn = db.transaction(() => {
        const info = insertCampaign.run(
            name, spintax_content, account_id ?? null,
            delay_min ?? 30, delay_max ?? 120,
            image_paths ? JSON.stringify(image_paths) : null,
            group_ids.length
        );
        const campaignId = info.lastInsertRowid;
        for (const gId of group_ids) {
            insertGroup.run(campaignId, gId);
        }
        return campaignId;
    });

    const campaignId = txn();
    res.status(201).json({ campaignId });
});

// ── POST /api/campaigns/start/:id ────────────────────────────
// Khởi động campaign
router.post('/start/:id', async (req, res) => {
    const campaignId = Number(req.params.id);
    const campaign = db.prepare('SELECT * FROM campaigns WHERE id = ?').get(campaignId);

    if (!campaign) return res.status(404).json({ error: 'Campaign not found' });
    if (!['DRAFT','QUEUED','PAUSED'].includes(campaign.status)) {
        return res.status(409).json({ error: `Campaign status is '${campaign.status}', cannot start` });
    }

    db.prepare(`UPDATE campaigns SET status='QUEUED' WHERE id=?`).run(campaignId);

    // Fire-and-forget: chạy async, không block response
    manager.executeCampaign(campaignId).catch((err) => {
        console.error(`[Campaign ${campaignId}] Fatal error:`, err);
    });

    res.json({ message: 'Campaign started', campaignId });
});

// ── POST /api/campaigns/pause/:id ────────────────────────────
// Tạm dừng campaign đang chạy
router.post('/pause/:id', (req, res) => {
    const campaignId = Number(req.params.id);
    const campaign = db.prepare('SELECT * FROM campaigns WHERE id = ?').get(campaignId);

    if (!campaign) return res.status(404).json({ error: 'Campaign not found' });
    if (campaign.status !== 'RUNNING') {
        return res.status(409).json({ error: 'Campaign is not running' });
    }

    manager.pauseCampaign(campaignId);
    // Status sẽ được update thành 'PAUSED' bởi CampaignManager sau khi hoàn thành group hiện tại
    res.json({ message: 'Pause signal sent', campaignId });
});

// ── GET /api/campaigns/:id/progress ──────────────────────────
// Chi tiết tiến trình campaign
router.get('/:id/progress', (req, res) => {
    const campaignId = Number(req.params.id);

    const campaign = db.prepare('SELECT * FROM v_campaign_progress WHERE campaign_id = ?').get(campaignId);
    if (!campaign) return res.status(404).json({ error: 'Campaign not found' });

    const groups = db.prepare(`
        SELECT cg.id, cg.status, cg.attempt_count, cg.posted_at, cg.error_message,
               g.group_name, g.group_id as fb_group_id
        FROM campaign_groups cg
        JOIN groups g ON g.id = cg.group_id
        WHERE cg.campaign_id = ?
        ORDER BY cg.id ASC
    `).all(campaignId);

    const activeSession = db.prepare(`
        SELECT * FROM execution_sessions
        WHERE campaign_id = ? AND status IN ('PENDING','ACTIVE')
        ORDER BY started_at DESC LIMIT 1
    `).get(campaignId);

    res.json({ campaign, groups, activeSession: activeSession ?? null });
});

module.exports = router;
```

### 5.2 File: `src/routes/accounts.js`

```javascript
// src/routes/accounts.js
'use strict';

const express = require('express');
const router = express.Router();
const { v4: uuidv4 } = require('uuid');
const db = require('../db/database');
const { isExtensionConnected } = require('../websocket/wsServer');

// ── GET /api/accounts ─────────────────────────────────────────
router.get('/', (req, res) => {
    const accounts = db.prepare(`
        SELECT a.*, 
               CASE WHEN a.account_id IN (?) THEN 1 ELSE 0 END as ws_connected
        FROM accounts a
        ORDER BY a.created_at DESC
    `).all('__placeholder__');

    // Thêm ws_connected flag
    const result = accounts.map(acc => ({
        ...acc,
        ws_connected: isExtensionConnected(acc.account_id)
    }));

    res.json({ data: result });
});

// ── POST /api/accounts/check-status ──────────────────────────
// Kiểm tra status nick — gửi lệnh qua WS tới Extension
router.post('/check-status', (req, res) => {
    const { account_ids } = req.body;
    if (!Array.isArray(account_ids) || account_ids.length === 0) {
        return res.status(400).json({ error: 'account_ids array required' });
    }

    const results = account_ids.map(accId => {
        const connected = isExtensionConnected(accId);
        return { accountId: accId, wsConnected: connected };
    });

    res.json({ results });
});

// ── POST /api/accounts/:id/sync-groups ────────────────────────
// [MỚI v0.3.2] Nhận danh sách group được sync từ NinjaPoster và lưu vào fetched_groups
router.post('/:id/sync-groups', (req, res) => {
    const accountId = req.params.id; // accounts.account_id
    const { groups } = req.body; // Array of { fb_group_id, group_name, group_url, privacy, member_count }

    if (!Array.isArray(groups)) {
        return res.status(400).json({ error: 'groups array required' });
    }

    try {
        saveFetchedGroups(accountId, groups);
        res.json({ success: true, count: groups.length });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// ── GET /api/accounts/:id/fetched-groups ─────────────────────
// [MỚI v0.3.2] Lấy danh sách group đã sync của một account
router.get('/:id/fetched-groups', (req, res) => {
    const accountId = req.params.id; // accounts.account_id
    try {
        const groups = db.prepare(`
            SELECT * FROM fetched_groups
            WHERE account_id = ?
            ORDER BY group_name ASC
        `).all(accountId);
        res.json({ success: true, groups });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

/**
 * Lưu các groups fetch được vào Database sử dụng SQLite Transaction
 * @param {string} accountId - accounts.account_id
 * @param {Array} groups - Array of groups fetched
 */
function saveFetchedGroups(accountId, groups) {
    const insertStmt = db.prepare(`
        INSERT INTO fetched_groups (id, account_id, fb_group_id, group_name, group_url, privacy, member_count, sync_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(account_id, fb_group_id) DO UPDATE SET
            group_name = excluded.group_name,
            group_url = excluded.group_url,
            privacy = excluded.privacy,
            member_count = excluded.member_count,
            sync_at = datetime('now')
    `);

    const txn = db.transaction((items) => {
        for (const g of items) {
            const id = uuidv4();
            insertStmt.run(
                id,
                accountId,
                g.fb_group_id,
                g.group_name,
                g.group_url || null,
                g.privacy || null,
                g.member_count || 0
            );
        }
    });

    txn(groups);
}

module.exports = router;
```

### 5.3 File: `src/routes/logs.js` — SSE Stream

```javascript
// src/routes/logs.js
'use strict';

const express = require('express');
const router = express.Router();
const db = require('../db/database');
const { sessionResultEmitter } = require('../websocket/wsServer');

// ── GET /api/logs ─────────────────────────────────────────────
// Phân trang logs thường
router.get('/', (req, res) => {
    const { campaign_id, level, limit = 50, offset = 0 } = req.query;
    let query = 'SELECT * FROM posting_logs WHERE 1=1';
    const params = [];

    if (campaign_id) { query += ' AND campaign_id = ?'; params.push(campaign_id); }
    if (level)       { query += ' AND level = ?';       params.push(level); }

    query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?';
    params.push(Number(limit), Number(offset));

    const rows = db.prepare(query).all(...params);
    res.json({ data: rows });
});

// ── GET /api/logs/stream ──────────────────────────────────────
// SSE: stream realtime logs tới UI
router.get('/stream', (req, res) => {
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.flushHeaders();

    const campaignId = req.query.campaign_id ? Number(req.query.campaign_id) : null;

    // Gửi keepalive mỗi 15s
    const keepAlive = setInterval(() => res.write(':\n\n'), 15_000);

    // [GAP-03-07] SSE backpressure: tạm ngừng lắng nghe khi buffer đầy, re-attach khi drain
    const onLog = (log) => {
        if (campaignId && log.campaign_id !== campaignId) return;
        const ok = res.write(`data: ${JSON.stringify(log)}\n\n`);
        if (!ok) {
            // Buffer đầy — tạm tắt listener, chờ drain
            sessionResultEmitter.off('log', onLog);
            res.once('drain', () => sessionResultEmitter.on('log', onLog));
        }
    };

    sessionResultEmitter.on('log', onLog);

    req.on('close', () => {
        clearInterval(keepAlive);
        sessionResultEmitter.off('log', onLog);
    });
});

module.exports = router;
```

### 5.4 File: `src/routes/groups.js` — Groups CRUD (GAP-03-04)

```javascript
// src/routes/groups.js — CRUD Groups
'use strict';

const express = require('express');
const router = express.Router();
const { v4: uuidv4 } = require('uuid');
const db = require('../db/database');

// ── GET /api/groups ───────────────────────────────────────────
router.get('/', (req, res) => {
    const { campaignId } = req.query;
    let query = 'SELECT * FROM groups';
    const params = [];
    if (campaignId) {
        // Lọc groups thuộc campaign
        query = `SELECT g.* FROM groups g
                 WHERE g.campaign_id = ?`;
        params.push(campaignId);
    }
    query += ' ORDER BY created_at DESC';
    const groups = db.prepare(query).all(...params);
    res.json({ success: true, data: groups });
});

// ── POST /api/groups ──────────────────────────────────────────
// [CONF-13 FIX] Thêm cột campaign_id khi chèn vào bảng groups và junction campaign_groups
router.post('/', (req, res) => {
    const { campaignId, groupUrl, groupName, groupId } = req.body;
    if (!campaignId || !groupUrl)
        return res.status(400).json({ error: 'campaignId và groupUrl bắt buộc' });
    
    const id = uuidv4();
    const fbGroupId = groupId || `fb_grp_${Date.now()}`;
    
    const insertTxn = db.transaction(() => {
        db.prepare(
            `INSERT INTO groups (id, campaign_id, group_id, group_url, group_name, posting_status)
             VALUES (?,?,?,?,?, 'ACTIVE')`
        ).run(id, campaignId, fbGroupId, groupUrl, groupName || groupUrl);

        db.prepare(
            `INSERT OR IGNORE INTO campaign_groups (id, campaign_id, group_id, status)
             VALUES (?, ?, ?, 'QUEUE')`
        ).run(uuidv4(), campaignId, id);
    });

    insertTxn();
    res.json({ success: true, id });
});

// ── DELETE /api/groups/:id ────────────────────────────────────
router.delete('/:id', (req, res) => {
    db.prepare('DELETE FROM groups WHERE id = ?').run(req.params.id);
    res.json({ success: true });
});

// ── POST /api/groups/import ───────────────────────────────────
// Nhập hàng loạt: body = { campaignId, groups: [{groupUrl, groupName, groupId}] }
// [CONF-13 FIX] Sửa cột campaign_id đồng bộ
router.post('/import', (req, res) => {
    const { campaignId, groups } = req.body;
    if (!campaignId || !Array.isArray(groups) || groups.length === 0)
        return res.status(400).json({ error: 'campaignId và groups[] bắt buộc' });

    const stmtGroup = db.prepare(
        `INSERT INTO groups (id, campaign_id, group_id, group_url, group_name, posting_status)
         VALUES (?,?,?,?,?, 'ACTIVE')`
    );

    const stmtJunction = db.prepare(
        `INSERT OR IGNORE INTO campaign_groups (id, campaign_id, group_id, status)
         VALUES (?, ?, ?, 'QUEUE')`
    );

    const insertMany = db.transaction((items) => {
        for (const g of items) {
            const id = uuidv4();
            const fbGroupId = g.groupId || `fb_grp_${Math.random().toString(36).substring(2, 9)}`;
            stmtGroup.run(id, campaignId, fbGroupId, g.groupUrl, g.groupName || g.groupUrl);
            stmtJunction.run(uuidv4(), campaignId, id);
        }
    });

    insertMany(groups);
    res.json({ success: true, count: groups.length });
});

module.exports = router;
```

**Mount trong `server.js`:**
```javascript
// server.js
app.use('/api/groups', require('./routes/groups'));
```

### 5.5 File: `src/routes/targetGroups.js` — Target Groups CRUD

```javascript
// src/routes/targetGroups.js — CRUD Target Groups
'use strict';

const express = require('express');
const router = express.Router();
const { v4: uuidv4 } = require('uuid');
const db = require('../db/database');

// ── GET /api/target-groups ────────────────────────────────────
// Lọc danh sách nhóm mục tiêu (theo keyword nếu có)
router.get('/', (req, res) => {
    const { keyword } = req.query;
    let query = 'SELECT * FROM target_groups';
    const params = [];
    if (keyword) {
        query += ' WHERE keyword LIKE ?';
        params.push(`%${keyword}%`);
    }
    query += ' ORDER BY created_at DESC';
    try {
        const groups = db.prepare(query).all(...params);
        res.json({ success: true, data: groups });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// ── POST /api/target-groups/import ────────────────────────────
// Nhập danh sách ID, tên đầy đủ và từ khóa
// body = { groups: [{ fb_group_id, group_name, group_url, keyword, allow_non_member_post }] }
router.post('/import', (req, res) => {
    const { groups } = req.body;
    if (!Array.isArray(groups) || groups.length === 0) {
        return res.status(400).json({ error: 'groups array required' });
    }

    // [Chốt Rule 8] Tránh ON CONFLICT DO UPDATE SET (PostgreSQL syntax) gây crash better-sqlite3.
    // Sử dụng cơ chế check-then-write thuần SQLite được bọc an toàn trong Transaction.
    const selectStmt = db.prepare('SELECT id FROM target_groups WHERE fb_group_id = ?');
    const insertStmt = db.prepare(`
        INSERT INTO target_groups (id, fb_group_id, group_name, group_url, keyword, allow_non_member_post, status)
        VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE')
    `);
    const updateStmt = db.prepare(`
        UPDATE target_groups 
        SET group_name = ?,
            group_url = COALESCE(?, group_url),
            keyword = COALESCE(?, keyword),
            allow_non_member_post = COALESCE(?, allow_non_member_post),
            status = 'ACTIVE'
        WHERE fb_group_id = ?
    `);

    try {
        const importTxn = db.transaction((items) => {
            for (const g of items) {
                if (!g.fb_group_id || !g.group_name) {
                    throw new Error('fb_group_id and group_name are required for each item');
                }
                const existing = selectStmt.get(g.fb_group_id);
                if (existing) {
                    updateStmt.run(
                        g.group_name,
                        g.group_url || null,
                        g.keyword || null,
                        g.allow_non_member_post !== undefined ? g.allow_non_member_post : null,
                        g.fb_group_id
                    );
                } else {
                    const id = uuidv4();
                    insertStmt.run(
                        id,
                        g.fb_group_id,
                        g.group_name,
                        g.group_url || null,
                        g.keyword || null,
                        g.allow_non_member_post !== undefined ? g.allow_non_member_post : 1
                    );
                }
            }
        });
        importTxn(groups);
        res.json({ success: true, count: groups.length });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// ── DELETE /api/target-groups/:id ──────────────────────────────
// Xóa nhóm khỏi danh sách target
router.delete('/:id', (req, res) => {
    try {
        const result = db.prepare('DELETE FROM target_groups WHERE id = ?').run(req.params.id);
        if (result.changes === 0) {
            return res.status(404).json({ error: 'Target group not found' });
        }
        res.json({ success: true });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

module.exports = router;
```

**Mount trong `server.js`:**
```javascript
// server.js
app.use('/api/target-groups', require('./routes/targetGroups'));
app.use('/api/donations', require('./routes/donations'));
app.use('/api/system', require('./routes/donations')); // Bản đồ hoá /api/system/lockout trực tiếp
```

### 5.6 File: `src/routes/donations.js` — Quản Lý Donate Quyên Góp

Router này cung cấp các endpoint ghi nhận lịch sử ủng hộ tự nguyện của người dùng, cập nhật trạng thái giao dịch và thống kê tổng số tiền nhận được để dev duy trì hệ thống credit AI.

```javascript
// src/routes/donations.js
const express = require('express');
const router = express.Router();
const db = require('../db');
const { v4: uuidv4 } = require('uuid');
const logger = require('../utils/logger');

// POST /api/donations - Ghi nhận một giao dịch quyên góp mới (Trạng thái PENDING)
router.post('/', (req, res) => {
  const { amount, currency, paymentMethod, transactionHash } = req.body;

  if (!amount || isNaN(amount) || parseFloat(amount) <= 0) {
    return res.status(400).json({ error: 'Mã lỗi [ERR-API-01]: Số tiền quyên góp không hợp lệ' });
  }

  const id = uuidv4();
  try {
    db.prepare(`
      INSERT INTO donations (id, amount, currency, payment_method, transaction_hash, status)
      VALUES (?, ?, ?, ?, ?, 'PENDING')
    `).run(id, parseFloat(amount), currency || 'VND', paymentMethod, transactionHash || null);

    logger.info(`[Donation] New donation registered: id=${id}, amount=${amount} ${currency || 'VND'} via ${paymentMethod}`);
    res.status(201).json({ success: true, id, status: 'PENDING' });
  } catch (err) {
    logger.error(`[Donation] DB insert error: ${err.message}`);
    res.status(500).json({ error: 'Lỗi máy chủ khi ghi nhận quyên góp' });
  }
});

// GET /api/donations/stats - Lấy tổng số tiền quyên góp nhận được
router.get('/stats', (req, res) => {
  try {
    const stats = db.prepare(`
      SELECT 
        SUM(CASE WHEN status = 'CONFIRMED' THEN amount ELSE 0 END) as totalConfirmed,
        COUNT(CASE WHEN status = 'CONFIRMED' THEN 1 END) as countConfirmed
      FROM donations
    `).get();

    res.json({
      totalConfirmed: stats.totalConfirmed || 0,
      countConfirmed: stats.countConfirmed || 0
    });
  } catch (err) {
    logger.error(`[Donation] Stats query error: ${err.message}`);
    res.status(500).json({ error: 'Lỗi truy vấn thống kê quyên góp' });
  }
});

// GET /api/donations/config - Lấy cấu hình hiển thị popup xin tiền định kỳ
router.get('/config', (req, res) => {
  try {
    const monthlyActive = db.prepare(`SELECT value FROM system_settings WHERE key = 'monthly_donation_active'`).get();
    const lastPrompt = db.prepare(`SELECT value FROM system_settings WHERE key = 'last_donation_prompt_at'`).get();
    const cruelCount = db.prepare(`SELECT value FROM system_settings WHERE key = 'cruel_choice_count'`).get();

    res.json({
      monthlyDonationActive: parseInt(monthlyActive?.value || '0'),
      lastPromptAt: lastPrompt?.value || '2026-06-16 00:00:00',
      cruelChoiceCount: parseInt(cruelCount?.value || '0')
    });
  } catch (err) {
    logger.error(`[Donation] Config query error: ${err.message}`);
    res.status(500).json({ error: 'Lỗi truy vấn cấu hình quyên góp' });
  }
});

// POST /api/donations/subscription - Bật/Tắt chế độ tự động ủng hộ mỗi tháng (gạt gạt toggle)
router.post('/subscription', (req, res) => {
  const { active } = req.body; // active: boolean
  const val = active ? '1' : '0';

  try {
    db.prepare(`UPDATE system_settings SET value = ?, updated_at = datetime('now') WHERE key = 'monthly_donation_active'`).run(val);
    logger.info(`[Donation] Monthly donation subscription updated: active=${active}`);
    res.json({ success: true, monthlyDonationActive: active });
  } catch (err) {
    logger.error(`[Donation] Subscription update error: ${err.message}`);
    res.status(500).json({ error: 'Lỗi cập nhật gạt tự động quyên góp' });
  }
});

// POST /api/donations/cruel-action - Ghi nhận lựa chọn đóng "tàn nhẫn"
router.post('/cruel-action', (req, res) => {
  try {
    // Tăng biến đếm cruel_choice_count lên 1
    db.prepare(`
      UPDATE system_settings 
      SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT), updated_at = datetime('now') 
      WHERE key = 'cruel_choice_count'
    `).run();
    
    // Cập nhật thời gian nhắc nhở cuối cùng về hiện tại (để đúng 30 ngày sau mới hỏi lại)
    db.prepare(`
      UPDATE system_settings 
      SET value = datetime('now'), updated_at = datetime('now') 
      WHERE key = 'last_donation_prompt_at'
    `).run();

    const currentCount = db.prepare(`SELECT value FROM system_settings WHERE key = 'cruel_choice_count'`).get();
    logger.warn(`[Donation] User chose cruel path. Total cruel choices: ${currentCount?.value}`);
    res.json({ success: true, cruelChoiceCount: parseInt(currentCount?.value || '0') });
  } catch (err) {
    logger.error(`[Donation] Cruel action log error: ${err.message}`);
    res.status(500).json({ error: 'Lỗi máy chủ khi ghi nhận hành vi đóng' });
  }
});

// POST /api/system/lockout - Khóa cứng phần mềm khi phát hiện can thiệp UI quyên góp cốt lõi
router.post('/system/lockout', (req, res) => {
  const { reason } = req.body;
  logger.error(`[SYSTEM LOCKOUT] ${reason || 'Interface integrity compromised'}. FREEZING CAMPAIGNS AND LOCKING SYSTEM.`);
  
  try {
    // 1. Tạm dừng toàn bộ campaigns đang RUNNING về PAUSED
    db.prepare(`UPDATE campaigns SET status = 'PAUSED', updated_at = datetime('now') WHERE status = 'RUNNING'`).run();
    // 2. Chuyển toàn bộ accounts đang chạy về HIBERNATE
    db.prepare(`UPDATE accounts SET status = 'HIBERNATE_AWAITING_MANUAL', notes = 'ERR-SEC-99: UI compromised' WHERE status = 'ACTIVE'`).run();
    
    res.json({ success: true, systemLocked: true });
  } catch (err) {
    logger.error(`[Lockout] Fail to lockout system cleanly: ${err.message}`);
    res.status(500).json({ error: 'Lỗi thực thi khóa cứng hệ thống' });
  }
});

module.exports = router;
```

### 5.7 File: `src/routes/slangs.js` — Slang Dictionary CRUD

Cung cấp các API RESTful để quản lý từ điển từ lóng, viết tắt phục vụ cho tính năng Slang Grounding trong Content Engine.

```javascript
// src/routes/slangs.js — CRUD Slang Dictionary
'use strict';

const express = require('express');
const router = express.Router();
const { v4: uuidv4 } = require('uuid');
const db = require('../db/database');

// ── GET /api/slangs ───────────────────────────────────────────
// Lấy danh sách từ lóng (hỗ trợ filter status/category)
router.get('/', (req, res) => {
    const { category, status } = req.query;
    let query = 'SELECT * FROM slang_dictionary WHERE 1=1';
    const params = [];

    if (category) {
        query += ' AND category = ?';
        params.push(category);
    }
    if (status) {
        query += ' AND status = ?';
        params.push(status);
    }

    query += ' ORDER BY word ASC';

    try {
        const slangs = db.prepare(query).all(...params);
        res.json({ success: true, data: slangs });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// ── POST /api/slangs ──────────────────────────────────────────
// Tạo mới từ lóng
router.post('/', (req, res) => {
    const { word, meaning, category, status } = req.body;
    if (!word || !meaning) {
        return res.status(400).json({ error: 'word và meaning là bắt buộc' });
    }

    const id = uuidv4();
    const cleanWord = word.trim().toLowerCase();

    try {
        db.prepare(
            `INSERT INTO slang_dictionary (id, word, meaning, category, status)
             VALUES (?, ?, ?, ?, ?)`
        ).run(
            id,
            cleanWord,
            meaning.trim(),
            category || 'SLANG',
            status || 'ACTIVE'
        );
        res.status(201).json({ success: true, id });
    } catch (err) {
        if (err.message.includes('UNIQUE constraint failed')) {
            return res.status(409).json({ error: 'Từ lóng này đã tồn tại trong từ điển' });
        }
        res.status(500).json({ error: err.message });
    }
});

// ── PUT /api/slangs/:id ────────────────────────────────────────
// Cập nhật thông tin từ lóng
router.put('/:id', (req, res) => {
    const { word, meaning, category, status } = req.body;
    const slangId = req.params.id;

    // Check existing
    const existing = db.prepare('SELECT id FROM slang_dictionary WHERE id = ?').get(slangId);
    if (!existing) {
        return res.status(404).json({ error: 'Không tìm thấy từ lóng này' });
    }

    // Build update query
    let query = 'UPDATE slang_dictionary SET updated_at = datetime("now")';
    const params = [];

    if (word !== undefined) {
        query += ', word = ?';
        params.push(word.trim().toLowerCase());
    }
    if (meaning !== undefined) {
        query += ', meaning = ?';
        params.push(meaning.trim());
    }
    if (category !== undefined) {
        query += ', category = ?';
        params.push(category);
    }
    if (status !== undefined) {
        query += ', status = ?';
        params.push(status);
    }

    query += ' WHERE id = ?';
    params.push(slangId);

    try {
        db.prepare(query).run(...params);
        res.json({ success: true });
    } catch (err) {
        if (err.message.includes('UNIQUE constraint failed')) {
            return res.status(409).json({ error: 'Từ lóng mới bị trùng lặp với từ khác' });
        }
        res.status(500).json({ error: err.message });
    }
});

// ── DELETE /api/slangs/:id ────────────────────────────────────
// Xóa từ lóng khỏi database
router.delete('/:id', (req, res) => {
    try {
        const result = db.prepare('DELETE FROM slang_dictionary WHERE id = ?').run(req.params.id);
        if (result.changes === 0) {
            return res.status(404).json({ error: 'Không tìm thấy từ lóng để xóa' });
        }
        res.json({ success: true });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

module.exports = router;
```

**Mount trong `server.js`:**
```javascript
// server.js
app.use('/api/slangs', require('./routes/slangs'));
```

### 5.8 API Key Pool Management (`/api/keys`)

> **[MỚI v0.4 — Day-2 Resilience]** Quản lý pool Gemini API Keys. Tất cả keys được mã hóa AES-256-GCM trước khi lưu DB.

```javascript
// src/routes/keys.js
'use strict';

const express = require('express');
const router = express.Router();
const crypto = require('crypto');
const { db, withRetry } = require('../db/database');
const { encryptWithHWID } = require('../utils/crypto');

// ── GET /api/keys ─────────────────────────────────────────────
// Danh sách API keys (KHÔNG trả về key gốc, chỉ trả masked + metadata)
router.get('/', (req, res) => {
  const keys = db.prepare(`
    SELECT id, label, status, total_calls, error_count, last_used_at, cooldown_until, created_at
    FROM api_key_pool ORDER BY created_at DESC
  `).all();
  res.json({ success: true, data: keys });
});

// ── POST /api/keys ────────────────────────────────────────────
// Thêm API key mới (mã hóa trước khi lưu)
router.post('/', (req, res) => {
  const { label, apiKey } = req.body;
  if (!label || !apiKey) return res.status(400).json({ error: 'label và apiKey bắt buộc' });
  const id = crypto.randomUUID();
  const encrypted_key = encryptWithHWID(apiKey); // AES-256-GCM + HWID
  db.prepare(`INSERT INTO api_key_pool (id, label, encrypted_key) VALUES (?, ?, ?)`)
    .run(id, label, encrypted_key);
  res.json({ success: true, id });
});

// ── DELETE /api/keys/:id ──────────────────────────────────────
router.delete('/:id', (req, res) => {
  const result = db.prepare('DELETE FROM api_key_pool WHERE id = ?').run(req.params.id);
  if (result.changes === 0) return res.status(404).json({ error: 'Key not found' });
  res.json({ success: true });
});

module.exports = router;
```

**Mount trong `server.js`:**
```javascript
// server.js
app.use('/api/keys', require('./routes/keys'));
```

### 5.9 Backup & Restore (`/api/backup`)

> **[MỚI v0.4 — Day-2 Resilience]** Backup/Restore database. File export được mã hóa AES-256-GCM dính HWID.

```javascript
// src/routes/backup.js
'use strict';

const express = require('express');
const router = express.Router();
const multer = require('multer');
const upload = multer({ dest: 'data/uploads/' });
const backupManager = require('../services/backupManager');

// ── GET /api/backup/status ────────────────────────────────────
// Lấy thông tin backup gần nhất
router.get('/status', (req, res) => {
  const backupInfo = backupManager.getLastBackupInfo();
  res.json({ success: true, data: backupInfo });
});

// ── POST /api/backup/run ──────────────────────────────────────
// Trigger backup thủ công
router.post('/run', async (req, res) => {
  try {
    const result = await backupManager.createBackup();
    res.json({ success: true, data: result });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ── GET /api/backup/export ────────────────────────────────────
// Export file backup đã mã hóa AES-256-GCM (HWID-locked)
router.get('/export', (req, res) => {
  const exportPath = backupManager.getExportPath();
  if (!exportPath) return res.status(404).json({ error: 'No backup available' });
  res.download(exportPath, 'hermes_backup.enc');
});

// ── POST /api/backup/import ───────────────────────────────────
// Import và giải mã file backup (chỉ hoạt động trên cùng HWID)
router.post('/import', upload.single('backup'), async (req, res) => {
  try {
    const result = await backupManager.importBackup(req.file.path);
    res.json({ success: true, data: result });
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

// ── POST /api/backup/integrity-check ──────────────────────────
// Chạy PRAGMA integrity_check trên database
router.post('/integrity-check', (req, res) => {
  try {
    const result = db.pragma('integrity_check');
    const isHealthy = result[0]?.integrity_check === 'ok';
    res.json({
      success: true,
      data: {
        isHealthy,
        lastCheckAt: new Date().toISOString(),
        details: isHealthy ? null : result
      }
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;
```

**Mount trong `server.js`:**
```javascript
// server.js
app.use('/api/backup', require('./routes/backup'));
```

### 5.10 System Updates (`/api/system`)

> **[MỚI v0.4 — Day-2 Resilience]** Kiểm tra và áp dụng bản cập nhật tự động. Server exit code `99` cho supervisor script tự restart.

```javascript
// src/routes/system.js (bổ sung vào file hiện có)
'use strict';

const autoUpdater = require('../services/autoUpdater');

// ── GET /api/system/version ───────────────────────────────────
router.get('/version', (req, res) => {
  const pkg = require('../package.json');
  res.json({ version: pkg.version, name: pkg.name });
});

// ── GET /api/system/check-update ──────────────────────────────
router.get('/check-update', async (req, res) => {
  const updateInfo = await autoUpdater.checkForUpdate();
  res.json({ success: true, data: updateInfo });
});

// ── POST /api/system/trigger-update ───────────────────────────
router.post('/trigger-update', async (req, res) => {
  try {
    const result = await autoUpdater.downloadAndApply();
    // Server sẽ exit(99) → supervisor script tự restart
    res.json({ success: true, message: 'Update applied. Server restarting...' });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// [HI-04] GET /api/system/remote-config — Trả về cấu hình Remote Config
// Được UI gọi (Spec 07 SystemUpdateBanner) để lấy feature flags, announcements
router.get('/remote-config', async (req, res) => {
  try {
    const cachedConfig = db.prepare('SELECT value FROM system_settings WHERE key = ?').get('remote_config_cache');
    if (cachedConfig) {
      return res.json(JSON.parse(cachedConfig.value));
    }
    return res.json({ features: {}, announcements: [] });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});
```

### 5.11 Summary Endpoint Table

| Method | Path | Mô tả |
|--------|------|-------|
| `GET`  | `/api/campaigns` | Danh sách campaigns |
| `POST` | `/api/campaigns` | Tạo campaign mới |
| `POST` | `/api/campaigns/start/:id` | Khởi động campaign |
| `POST` | `/api/campaigns/pause/:id` | Tạm dừng campaign |
| `GET`  | `/api/campaigns/:id/progress` | Chi tiết tiến trình |
| `GET`  | `/api/accounts` | Danh sách accounts + WS status |
| `POST` | `/api/accounts/check-status` | Kiểm tra WS connected |
| `GET`  | `/api/logs` | Phân trang logs |
| `GET`  | `/api/logs/stream` | SSE realtime log stream |
| `GET`  | `/api/groups` | Danh sách groups (filter by campaignId) |
| `POST` | `/api/groups` | Thêm group mới |
| `DELETE` | `/api/groups/:id` | Xoá group |
| `POST` | `/api/groups/import` | Nhập hàng loạt groups |
| `GET`  | `/api/target-groups` | Lọc danh sách target groups theo keyword |
| `POST` | `/api/target-groups/import` | Nhập danh sách target groups |
| `DELETE` | `/api/target-groups/:id` | Xóa target group khỏi danh sách |
| `POST` | `/api/donations` | Ghi nhận quyên góp mới |
| `GET`  | `/api/donations/stats` | Lấy thống kê tổng số tiền quyên góp |
| `GET`  | `/api/donations/config` | Lấy cấu hình hiển thị và đếm lần tàn nhẫn |
| `POST` | `/api/donations/subscription` | Cập nhật toggle gạt tự động quyên góp |
| `POST` | `/api/donations/cruel-action` | Ghi nhận click đóng "Mặc xác" và lùi lịch 30 ngày |
| `POST` | `/api/system/lockout` | Khóa cứng hệ thống khi can thiệp UI quyên góp |
| `GET`  | `/api/slangs` | Danh sách từ lóng / viết tắt |
| `POST` | `/api/slangs` | Thêm từ lóng mới |
| `PUT`  | `/api/slangs/:id` | Cập nhật từ lóng |
| `DELETE` | `/api/slangs/:id` | Xóa từ lóng khỏi từ điển |
| `GET`    | `/api/keys`                  | Danh sách API keys (masked)          |
| `POST`   | `/api/keys`                  | Thêm API key mới (mã hóa HWID)      |
| `DELETE` | `/api/keys/:id`              | Xóa API key                          |
| `GET`    | `/api/backup/status`         | Thông tin backup gần nhất            |
| `POST`   | `/api/backup/run`            | Trigger backup thủ công              |
| `GET`    | `/api/backup/export`         | Download file backup mã hóa          |
| `POST`   | `/api/backup/import`         | Import & giải mã backup (HWID-lock)  |
| `POST`   | `/api/backup/integrity-check` | Kiểm tra tính toàn vẹn database      |
| `GET`    | `/api/system/version`        | Phiên bản hiện tại                   |
| `GET`    | `/api/system/check-update`   | Kiểm tra bản cập nhật mới            |
| `POST`   | `/api/system/trigger-update` | Tải & áp dụng bản cập nhật           |
| `GET`    | `/api/system/remote-config`  | [HI-04] Trả về Remote Config JSON    |

---

## 6. SpintaxResolver

> **[BUG FIX B3]** Thay thuật toán regex đơn giản bằng recursive parser hỗ trợ nested spintax và malformed input protection.

### 6.1 Lý Do Cần Recursive Parser

Regex đơn giản `/{[^{}]+}/g` **không hoạt động** với nested spintax:
```
{Hello|{Hi|Hey}} {world|{earth|planet}}
```
Regex sẽ bắt `{[^{}]+}` → miss nhóm ngoài.

### 6.2 Thuật Toán Recursive — Pseudocode

```
FUNCTION resolve(template: string) → string:
    result = ""
    i = 0

    WHILE i < template.length:
        IF template[i] == '{':
            // Tìm closing bracket khớp (xét nesting)
            depth = 1
            j = i + 1
            WHILE j < template.length AND depth > 0:
                IF template[j] == '{': depth++
                IF template[j] == '}': depth--
                j++

            IF depth != 0:
                // Malformed: không tìm được closing bracket
                // Giữ nguyên '{' và tiếp tục (fail-safe)
                result += '{'
                i++
                CONTINUE

            // Nội dung bên trong (không tính 2 dấu ngoặc)
            inner = template[i+1 .. j-2]

            // Split theo '|' nhưng KHÔNG split bên trong nested {}
            options = splitTopLevel(inner, '|')

            // Chọn ngẫu nhiên 1 option
            chosen = options[randomInt(0, options.length - 1)]

            // Đệ quy resolve option được chọn
            result += resolve(chosen)
            i = j

        ELSE:
            result += template[i]
            i++

    RETURN result

FUNCTION splitTopLevel(text: string, delimiter: char) → string[]:
    parts = []
    depth = 0
    current = ""

    FOR EACH char IN text:
        IF char == '{': depth++
        IF char == '}': depth--
        IF char == delimiter AND depth == 0:
            parts.push(current)
            current = ""
        ELSE:
            current += char

    parts.push(current)  // last part
    RETURN parts
```

### 6.3 Full Implementation — `src/utils/spintaxResolver.js`

```javascript
// src/utils/spintaxResolver.js
'use strict';

/**
 * SpintaxResolver v2 — Recursive parser với malformed protection
 */
class SpintaxResolver {

    /**
     * Resolve một spintax template thành nội dung ngẫu nhiên
     * @param {string} template
     * @returns {string}
     */
    resolve(template) {
        if (typeof template !== 'string' || template.length === 0) return '';
        // Giới hạn độ dài để tránh DoS
        if (template.length > 100_000) {
            throw new Error('Spintax template too large (max 100KB)');
        }
        return this._resolveInternal(template);
    }

    _resolveInternal(template) {
        let result = '';
        let i = 0;

        while (i < template.length) {
            if (template[i] === '{') {
                // Tìm closing bracket khớp depth
                let depth = 1;
                let j = i + 1;

                while (j < template.length && depth > 0) {
                    if (template[j] === '{') depth++;
                    else if (template[j] === '}') depth--;
                    j++;
                }

                if (depth !== 0) {
                    // Malformed: closing bracket không tìm thấy → giữ nguyên
                    result += '{';
                    i++;
                    continue;
                }

                // inner = nội dung bên trong cặp ngoặc (không tính { và })
                const inner = template.slice(i + 1, j - 1);
                const options = this._splitTopLevel(inner, '|');

                if (options.length === 0) {
                    // Edge case: {} rỗng
                    i = j;
                    continue;
                }

                const chosen = options[Math.floor(Math.random() * options.length)];
                result += this._resolveInternal(chosen);
                i = j;

            } else {
                result += template[i];
                i++;
            }
        }

        return result;
    }

    /**
     * Split string theo delimiter, nhưng bỏ qua delimiter bên trong nested {}
     * @param {string} text
     * @param {string} delimiter
     * @returns {string[]}
     */
    _splitTopLevel(text, delimiter) {
        const parts = [];
        let depth = 0;
        let current = '';

        for (const char of text) {
            if (char === '{') {
                depth++;
                current += char;
            } else if (char === '}') {
                depth--;
                current += char;
            } else if (char === delimiter && depth === 0) {
                parts.push(current);
                current = '';
            } else {
                current += char;
            }
        }

        parts.push(current);
        return parts;
    }
}

module.exports = new SpintaxResolver();
```

### 6.4 Unit Tests — `src/utils/__tests__/spintaxResolver.test.js`

```javascript
// src/utils/__tests__/spintaxResolver.test.js
'use strict';

const resolver = require('../spintaxResolver');

describe('SpintaxResolver', () => {

    // ── Test Case 1: Simple spintax ────────────────────────────
    test('TC1 — Simple: chọn đúng 1 trong các options', () => {
        const template = '{Hello|Hi|Hey} {world|earth}';
        const result = resolver.resolve(template);

        const validGreetings = ['Hello', 'Hi', 'Hey'];
        const validWorlds = ['world', 'earth'];

        const [greeting, world] = result.split(' ');
        expect(validGreetings).toContain(greeting);
        expect(validWorlds).toContain(world);
    });

    // ── Test Case 2: Nested spintax ────────────────────────────
    test('TC2 — Nested: resolve đúng nested groups', () => {
        const template = '{Xin chào|{Chào|Hey}} {bạn|{anh|chị|em}}';
        const result = resolver.resolve(template);

        // Tất cả output hợp lệ từ nested resolve
        const validFirst = ['Xin chào', 'Chào', 'Hey'];
        const validSecond = ['bạn', 'anh', 'chị', 'em'];

        const parts = result.split(' ');
        expect(parts.length).toBe(2);
        expect(validFirst).toContain(parts[0]);
        expect(validSecond).toContain(parts[1]);
    });

    // ── Test Case 3: Malformed input ───────────────────────────
    test('TC3 — Malformed: không crash, giữ nguyên phần lỗi', () => {
        // Opening bracket không có closing
        const template = 'Hello {world|earth and missing bracket';
        const result = resolver.resolve(template);

        // Không throw, trả về string hợp lệ
        expect(typeof result).toBe('string');
        expect(result).toContain('Hello ');
        // '{' không có pair sẽ được giữ nguyên
        expect(result.startsWith('Hello {')).toBe(true);
    });

    // ── Bonus: Empty options ───────────────────────────────────
    test('TC4 — Edge: empty template trả về empty string', () => {
        expect(resolver.resolve('')).toBe('');
        expect(resolver.resolve('No spintax here')).toBe('No spintax here');
    });

    // ── Bonus: Single option ──────────────────────────────────
    test('TC5 — Single option: trả về chính xác option đó', () => {
        const result = resolver.resolve('{only one option}');
        expect(result).toBe('only one option');
    });
});
```

---

## 7. Dashboard UI Spec (React)

> **[FIX C5]** Bổ sung đầy đủ component list, state structure, WS management.

### 7.1 ASCII Layout Mockup

```
┌─────────────────────────────────────────────────────────────────┐
│  🚀 Hermes FacePost-Group Dashboard              v0.3           │
│  ● WS Connected  |  3 Accounts Active  |  1 Campaign Running   │
├──────────────────┬──────────────────────────────────────────────┤
│                  │                                              │
│  📋 NAVIGATION   │          MAIN CONTENT AREA                   │
│                  │                                              │
│  > Accounts      │  ┌──────────────────────────────────────┐   │
│    Campaigns     │  │  Campaign: "Sale T7 - Nhóm Bắc"      │   │
│    Groups        │  │  Status: RUNNING  ████████░░  78%     │   │
│    Logs          │  │  Posted: 45/58  Failed: 2             │   │
│                  │  │  Current: Nhóm Hà Nội Mua Bán        │   │
│                  │  └──────────────────────────────────────┘   │
│                  │                                              │
│                  │  ┌──────────────────────────────────────┐   │
│                  │  │ LOG VIEWER                            │   │
│                  │  │ [14:23:01] ✅ Đăng xong Nhóm HN...   │   │
│                  │  │ [14:22:30] 🔄 Resolving spintax...   │   │
│                  │  │ [14:22:00] ⏳ Chờ 45s trước group... │   │
│                  │  └──────────────────────────────────────┘   │
│                  │                                              │
│  ─────────────── │  ┌──────────────────────────────────────┐   │
│  ACCOUNTS        │  │ STATUS BAR                            │   │
│  🟢 fb_12345     │  │ CPU: 12%  DB: 2.3MB  WS Ext: 3/3    │   │
│  🟢 fb_67890     │  └──────────────────────────────────────┘   │
│  🔴 fb_11111     │                                              │
└──────────────────┴──────────────────────────────────────────────┘
```

### 7.2 Component Architecture

```
App
├── AppContext (Global State Provider)
├── StatusBar
├── Sidebar
│   ├── Navigation
│   └── AccountList (mini)
└── MainContent
    ├── AccountsPage
    │   └── AccountList (full)
    ├── CampaignsPage
    │   ├── CampaignForm (create/edit)
    │   └── CampaignCard[]
    │       └── GroupList (per campaign)
    ├── GroupsPage
    │   └── GroupList (full, with import CSV)
    └── LogsPage
        └── LogViewer
```

### 7.3 Global State Structure

```javascript
// src/frontend/context/AppContext.jsx
import React, { createContext, useContext, useReducer, useEffect, useRef } from 'react';

const initialState = {
    // Connection
    wsConnected: false,
    wsError: null,

    // Data
    accounts: [],           // Account[]
    campaigns: [],          // Campaign[]
    groups: [],             // Group[]
    logs: [],               // LogEntry[] (ring buffer, max 500)

    // Active campaign tracking
    activeCampaignId: null,
    campaignProgress: {},   // { [campaignId]: { pct, posted, failed, currentGroup } }

    // Extension status
    connectedExtensions: new Set(),   // Set<accountId>

    // UI state
    selectedPage: 'campaigns',
    isLoading: false,
    notification: null,     // { type: 'success'|'error', message, ts }
};

function reducer(state, action) {
    switch (action.type) {
        case 'WS_CONNECTED':
            return { ...state, wsConnected: true, wsError: null };
        case 'WS_DISCONNECTED':
            return { ...state, wsConnected: false };
        case 'WS_ERROR':
            return { ...state, wsError: action.error };

        case 'SET_ACCOUNTS':
            return { ...state, accounts: action.data };
        case 'SET_CAMPAIGNS':
            return { ...state, campaigns: action.data };
        case 'SET_GROUPS':
            return { ...state, groups: action.data };

        case 'APPEND_LOG': {
            const logs = [action.log, ...state.logs].slice(0, 500);
            return { ...state, logs };
        }

        case 'UPDATE_CAMPAIGN_PROGRESS':
            return {
                ...state,
                campaignProgress: {
                    ...state.campaignProgress,
                    [action.campaignId]: action.progress
                }
            };

        case 'EXTENSION_CONNECTED': {
            const ext = new Set(state.connectedExtensions);
            ext.add(action.accountId);
            return { ...state, connectedExtensions: ext };
        }
        case 'EXTENSION_DISCONNECTED': {
            const ext = new Set(state.connectedExtensions);
            ext.delete(action.accountId);
            return { ...state, connectedExtensions: ext };
        }

        case 'SET_PAGE':
            return { ...state, selectedPage: action.page };
        case 'SET_NOTIFICATION':
            return { ...state, notification: action.notification };

        default:
            return state;
    }
}

export const AppContext = createContext(null);

export function AppProvider({ children }) {
    const [state, dispatch] = useReducer(reducer, initialState);
    const wsRef = useRef(null);

    // ── WebSocket Management ──────────────────────────────────
    useEffect(() => {
        let reconnectDelay = 1000; // [GAP-03-08] exponential backoff state
        function connect() {
            // Đọc token từ Electron Bridge (nếu có) hoặc fallback biến build-time
            const UI_TOKEN = window.electronAPI ? window.electronAPI.getUiToken() : (import.meta.env.VITE_UI_TOKEN || 'local-ui-token');
            // Tự động phân giải địa chỉ websocket cục bộ động (phục vụ cả dev mode và packaged app)
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const host = window.location.host || 'localhost:3000';
            const ws = new WebSocket(`${protocol}//${host}/ws`);
            wsRef.current = ws;

            ws.onopen = () => {
                reconnectDelay = 1000; // reset delay khi connect thành công
                dispatch({ type: 'WS_CONNECTED' });
                // Gửi AUTH ngay khi mở kết nối
                ws.send(JSON.stringify({ type: 'AUTH', clientType: 'ui', token: UI_TOKEN }));
            };

            ws.onmessage = (event) => {
                let msg;
                try { msg = JSON.parse(event.data); } catch { return; }
                handleWsMessage(msg, dispatch);
            };

            // [GAP-03-08] Exponential backoff: 1s → 2s → 4s → ... → max 30s
            ws.onclose = () => {
                dispatch({ type: 'WS_DISCONNECTED' });
                const delay = reconnectDelay;
                reconnectDelay = Math.min(reconnectDelay * 2, 30000); // max 30s
                setTimeout(connect, delay);
            };

            ws.onerror = (err) => {
                dispatch({ type: 'WS_ERROR', error: err.message });
            };
        }

        connect();
        return () => wsRef.current?.close();
    }, []);

    // ── Initial Data Load ─────────────────────────────────────
    useEffect(() => {
        Promise.all([
            fetch('/api/accounts').then(r => r.json()),
            fetch('/api/campaigns').then(r => r.json()),
            fetch('/api/groups').then(r => r.json()),
        ]).then(([accounts, campaigns, groups]) => {
            dispatch({ type: 'SET_ACCOUNTS', data: accounts.data });
            dispatch({ type: 'SET_CAMPAIGNS', data: campaigns.data });
            dispatch({ type: 'SET_GROUPS', data: groups.data });
        });
    }, []);

    return (
        <AppContext.Provider value={{ state, dispatch, ws: wsRef }}>
            {children}
        </AppContext.Provider>
    );
}

function handleWsMessage(msg, dispatch) {
    switch (msg.type) {
        case 'AUTH_OK':
            dispatch({ type: 'WS_CONNECTED' });
            break;
        case 'CAMPAIGN_STARTED':
        case 'CAMPAIGN_PAUSED':
        case 'CAMPAIGN_COMPLETED':
        case 'GROUP_POSTING':
        case 'GROUP_POSTED':
        case 'GROUP_FAILED':
            dispatch({
                type: 'UPDATE_CAMPAIGN_PROGRESS',
                campaignId: msg.campaignId,
                progress: msg
            });
            dispatch({
                type: 'APPEND_LOG',
                log: { ts: Date.now(), ...msg }
            });
            break;
        case 'EXTENSION_CONNECTED':
            dispatch({ type: 'EXTENSION_CONNECTED', accountId: msg.accountId });
            break;
        case 'EXTENSION_DISCONNECTED':
            dispatch({ type: 'EXTENSION_DISCONNECTED', accountId: msg.accountId });
            break;
        default:
            break;
    }
}

export const useApp = () => useContext(AppContext);
```

### 7.4 Key Components

#### `AccountList`

```javascript
// Props: accounts[], connectedExtensions: Set
// State: filterStatus (local useState)
// Columns: display_name | status badge | WS connected dot | last_active_at | actions
// Notes: Nhúng thêm component SyncGroupButton và CheckpointAlertCard cho từng dòng account thích hợp
```

#### `CampaignForm`

```javascript
// Props: groups[], accounts[], onSubmit(formData)
// Fields:
//   - name (text)
//   - spintax_content (textarea + preview button)
//   - group_ids (multi-select with search)
//   - account_id (select, optional)
//   - delay_min / delay_max (range slider)
//   - image_paths (file upload, multiple)
// Validation: spintax preview calls SpintaxResolver on client-side
```

#### `LogViewer`

```javascript
// Props: logs[], campaignId? (filter)
// Features:
//   - Auto-scroll to bottom on new logs
//   - Level filter: ALL / ERROR / INFO
//   - Clear button
//   - Color-coded: ERROR=red, WARN=yellow, INFO=blue, SUCCESS=green
// Implementation: useEffect + scrollRef
```

#### `StatusBar`

```javascript
// Reads: wsConnected, connectedExtensions.size, campaigns (running count)
// Displays: WS status dot | Extensions connected | Active campaigns
// Refresh: every 5s via setInterval for server stats (optional)
```

### 7.5 Sync Groups Components (React + Tailwind CSS)

#### `SyncGroupButton.jsx`

```jsx
import React, { useState } from 'react';

/**
 * Premium SyncGroupButton Component với loading spinner và micro-animations
 */
export default function SyncGroupButton({ accountId, onSyncComplete }) {
    const [status, setStatus] = useState('idle'); // idle | syncing | success | error

    const handleSync = async () => {
        setStatus('syncing');
        try {
            const response = await fetch(`/api/accounts/${accountId}/sync-groups`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ groups: [] }) // Extension thực tế sẽ gửi qua WS
            });
            if (response.ok) {
                setStatus('success');
                if (onSyncComplete) onSyncComplete();
                setTimeout(() => setStatus('idle'), 3000);
            } else {
                setStatus('error');
                setTimeout(() => setStatus('idle'), 3000);
            }
        } catch (err) {
            setStatus('error');
            setTimeout(() => setStatus('idle'), 3000);
        }
    };

    return (
        <button
            onClick={handleSync}
            disabled={status === 'syncing'}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold shadow-md transition-all duration-300 transform active:scale-95 ${
                status === 'syncing'
                    ? 'bg-indigo-600/50 text-indigo-200 cursor-not-allowed'
                    : status === 'success'
                    ? 'bg-emerald-500 text-white shadow-emerald-500/20'
                    : status === 'error'
                    ? 'bg-rose-500 text-white shadow-rose-500/20'
                    : 'bg-gradient-to-r from-indigo-500 to-violet-600 hover:from-indigo-600 hover:to-violet-700 text-white shadow-indigo-500/20 hover:shadow-lg hover:-translate-y-0.5'
            }`}
        >
            <svg
                className={`w-4 h-4 ${status === 'syncing' ? 'animate-spin' : ''}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
            >
                <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 7.89M9 11l3 3L22 4"
                />
            </svg>
            {status === 'syncing' ? 'Syncing...' : status === 'success' ? 'Synced!' : status === 'error' ? 'Failed' : 'Sync Groups'}
        </button>
    );
}
```

#### `CheckpointAlertCard.jsx`

```jsx
import React from 'react';

/**
 * Glassmorphic CheckpointAlertCard Component với hiệu ứng pulse và hover mượt mà
 */
export default function CheckpointAlertCard({ account, onResolve }) {
    if (account.status !== 'CHECKPOINT') return null;

    return (
        <div className="relative overflow-hidden rounded-2xl border border-rose-500/30 bg-rose-950/20 p-5 backdrop-blur-xl transition-all duration-300 shadow-xl shadow-rose-950/20">
            {/* Ambient background glow */}
            <div className="absolute -left-10 -top-10 w-32 h-32 bg-rose-500/10 rounded-full blur-2xl pointer-events-none" />
            
            <div className="flex items-start gap-4">
                <div className="relative flex items-center justify-center p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-500">
                    <span className="absolute inline-flex h-2 w-2 rounded-full bg-rose-400 opacity-75 animate-ping" />
                    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                </div>
                <div className="flex-1">
                    <h4 className="text-base font-bold text-rose-300">Account Checkpoint Detected</h4>
                    <p className="mt-1 text-sm text-rose-400/80 leading-relaxed">
                        Tài khoản <span className="font-semibold text-rose-200">{account.display_name}</span> ({account.account_id}) đang bị khóa checkpoint từ Facebook. Vui lòng phê duyệt thủ tục bảo mật trên thiết bị hoặc cập nhật lại Cookies mới.
                    </p>
                    <div className="mt-4 flex flex-wrap gap-2">
                        <button
                            onClick={() => onResolve(account.account_id, 'cookies')}
                            className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-rose-500 hover:bg-rose-600 active:scale-95 text-white transition-all shadow-md shadow-rose-500/20"
                        >
                            Update Cookies
                        </button>
                        <button
                            onClick={() => onResolve(account.account_id, 'skip')}
                            className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 active:scale-95 text-slate-300 border border-slate-700/50 transition-all"
                        >
                            Dismiss
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
```

#### `GroupListModal.jsx`

```jsx
import React, { useState, useEffect } from 'react';

/**
 * GroupListModal Component dùng để hiển thị và chọn groups đã sync từ fetched_groups table
 */
export default function GroupListModal({ isOpen, onClose, accountId, onImport }) {
    const [groups, setGroups] = useState([]);
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedIds, setSelectedIds] = useState(new Set());
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (isOpen && accountId) {
            setLoading(true);
            fetch(`/api/accounts/${accountId}/fetched-groups`)
                .then(res => res.json())
                .then(data => {
                    setGroups(data.groups || []);
                    setLoading(false);
                })
                .catch(() => setLoading(false));
        }
    }, [isOpen, accountId]);

    const filteredGroups = groups.filter(g =>
        g.group_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        g.fb_group_id.includes(searchQuery)
    );

    const toggleSelect = (id) => {
        const next = new Set(selectedIds);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        setSelectedIds(next);
    };

    const toggleSelectAll = () => {
        if (selectedIds.size === filteredGroups.length) {
            setSelectedIds(new Set());
        } else {
            setSelectedIds(new Set(filteredGroups.map(g => g.fb_group_id)));
        }
    };

    const handleImport = () => {
        const selectedGroups = groups.filter(g => selectedIds.has(g.fb_group_id));
        onImport(selectedGroups);
        onClose();
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
            <div className="w-full max-w-2xl overflow-hidden rounded-2xl border border-slate-800 bg-slate-950 shadow-2xl transition-all duration-300">
                {/* Header */}
                <div className="flex items-center justify-between border-b border-slate-800 p-5 bg-gradient-to-r from-slate-950 to-slate-900">
                    <h3 className="text-lg font-bold text-transparent bg-clip-text bg-gradient-to-r from-white to-slate-400">
                        Fetched Groups List
                    </h3>
                    <button onClick={onClose} className="rounded-lg p-1 hover:bg-slate-900 text-slate-400 hover:text-slate-200 transition-colors">
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* Content */}
                <div className="p-5">
                    {/* Search Bar */}
                    <div className="relative mb-4">
                        <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-slate-500">
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                            </svg>
                        </span>
                        <input
                            type="text"
                            placeholder="Search by group name or ID..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-800 bg-slate-900/50 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
                        />
                    </div>

                    {/* Table Container */}
                    <div className="max-h-80 overflow-y-auto border border-slate-800/80 rounded-xl bg-slate-900/20 scrollbar-thin scrollbar-thumb-slate-800">
                        {loading ? (
                            <div className="flex flex-col items-center justify-center py-10 gap-3">
                                <div className="w-8 h-8 rounded-full border-2 border-indigo-500/20 border-t-indigo-500 animate-spin" />
                                <span className="text-xs text-slate-500">Loading synced groups...</span>
                            </div>
                        ) : filteredGroups.length === 0 ? (
                            <div className="py-10 text-center text-sm text-slate-500">No groups found</div>
                        ) : (
                            <table className="w-full border-collapse text-left text-sm text-slate-300">
                                <thead>
                                    <tr className="border-b border-slate-800 bg-slate-900/50 text-xs font-semibold uppercase tracking-wider text-slate-400">
                                        <th className="p-4 w-12 text-center">
                                            <input
                                                type="checkbox"
                                                checked={selectedIds.size === filteredGroups.length && filteredGroups.length > 0}
                                                onChange={toggleSelectAll}
                                                className="rounded border-slate-700 bg-slate-900 text-indigo-600 focus:ring-indigo-500 w-4 h-4"
                                            />
                                        </th>
                                        <th className="p-4">Group Name</th>
                                        <th className="p-4">Privacy</th>
                                        <th className="p-4 text-right">Members</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-800/40">
                                    {filteredGroups.map(g => (
                                        <tr
                                            key={g.fb_group_id}
                                            onClick={() => toggleSelect(g.fb_group_id)}
                                            className={`hover:bg-slate-900/40 cursor-pointer transition-colors ${selectedIds.has(g.fb_group_id) ? 'bg-indigo-950/10' : ''}`}
                                        >
                                            <td className="p-4 text-center" onClick={(e) => e.stopPropagation()}>
                                                <input
                                                    type="checkbox"
                                                    checked={selectedIds.has(g.fb_group_id)}
                                                    onChange={() => toggleSelect(g.fb_group_id)}
                                                    className="rounded border-slate-700 bg-slate-900 text-indigo-600 focus:ring-indigo-500 w-4 h-4"
                                                />
                                            </td>
                                            <td className="p-4">
                                                <div className="font-semibold text-slate-200">{g.group_name}</div>
                                                <div className="text-xs text-slate-500">{g.fb_group_id}</div>
                                            </td>
                                            <td className="p-4">
                                                <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${
                                                    g.privacy === 'PUBLIC'
                                                        ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                                                        : 'bg-amber-500/10 border-amber-500/20 text-amber-400'
                                                }`}>
                                                    {g.privacy || 'UNKNOWN'}
                                                </span>
                                            </td>
                                            <td className="p-4 text-right font-medium text-slate-400">
                                                {g.member_count?.toLocaleString() || 0}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </div>
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between border-t border-slate-800 p-5 bg-gradient-to-r from-slate-950 to-slate-900">
                    <span className="text-xs text-slate-500 font-medium">
                        Selected: <span className="text-indigo-400 font-semibold">{selectedIds.size}</span> / {filteredGroups.length}
                    </span>
                    <div className="flex gap-2">
                        <button
                            onClick={onClose}
                            className="px-4 py-2 rounded-xl text-sm font-semibold bg-slate-900 border border-slate-800 text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition-all active:scale-95"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={handleImport}
                            disabled={selectedIds.size === 0}
                            className="px-4 py-2 rounded-xl text-sm font-semibold bg-gradient-to-r from-indigo-500 to-violet-600 text-white shadow-lg shadow-indigo-500/20 hover:from-indigo-600 hover:to-violet-700 hover:shadow-indigo-500/30 transition-all active:scale-95 disabled:from-indigo-950 disabled:to-slate-900 disabled:text-slate-600 disabled:shadow-none disabled:cursor-not-allowed"
                        >
                            Import Groups
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
```

#### `TargetGroupTable.jsx`

```jsx
import React from 'react';

/**
 * Premium TargetGroupTable Component với trạng thái đổi màu hiển thị SEARCH_FAILED nổi bật
 * và kèm nút bấm xử lý thủ công (mở tab Chrome kiểm tra hoặc tự bấm đăng).
 */
export default function TargetGroupTable({ groups, onManualAction }) {
    return (
        <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-950 p-5 shadow-xl">
            <table className="w-full border-collapse text-left text-sm text-slate-300">
                <thead>
                    <tr className="border-b border-slate-800 bg-slate-900/50 text-xs font-semibold uppercase tracking-wider text-slate-400">
                        <th className="p-4">Tên nhóm</th>
                        <th className="p-4">Facebook Group ID</th>
                        <th className="p-4">Từ khóa</th>
                        <th className="p-4">Cho phép đăng không cần tham gia</th>
                        <th className="p-4">Trạng thái</th>
                        <th className="p-4 text-right">Thao tác</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/40">
                    {groups.map(group => {
                        const isSearchFailed = group.status === 'SEARCH_FAILED';
                        return (
                            <tr
                                key={group.id}
                                className={`transition-all duration-300 hover:bg-slate-900/40 ${
                                    isSearchFailed
                                        ? 'bg-amber-500/10 border-l-4 border-l-amber-500 hover:bg-amber-500/15'
                                        : ''
                                }`}
                            >
                                <td className="p-4 font-semibold text-slate-200">
                                    {group.group_name}
                                </td>
                                <td className="p-4 font-mono text-xs text-slate-400">
                                    {group.fb_group_id}
                                </td>
                                <td className="p-4">
                                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-900 text-slate-400 border border-slate-800">
                                        {group.keyword || '-'}
                                    </span>
                                </td>
                                <td className="p-4 text-center">
                                    <span className={`inline-flex items-center text-xs font-medium ${
                                        group.allow_non_member_post === 1 ? 'text-emerald-400' : 'text-slate-500'
                                    }`}>
                                        {group.allow_non_member_post === 1 ? 'Cho phép' : 'Không'}
                                    </span>
                                </td>
                                <td className="p-4">
                                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold border ${
                                        isSearchFailed
                                            ? 'bg-rose-500/20 border-rose-500/30 text-rose-400 animate-pulse'
                                            : group.status === 'ACTIVE'
                                            ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                                            : group.status === 'RESTRICTED'
                                            ? 'bg-amber-500/10 border-amber-500/20 text-amber-400'
                                            : 'bg-slate-800 border-slate-700 text-slate-500'
                                    }`}>
                                        {group.status}
                                    </span>
                                </td>
                                <td className="p-4 text-right">
                                    {isSearchFailed ? (
                                        <button
                                            onClick={() => onManualAction(group, 'handle')}
                                            className="px-3 py-1.5 rounded-xl text-xs font-bold bg-gradient-to-r from-amber-500 to-rose-600 hover:from-amber-600 hover:to-rose-700 text-white shadow-md shadow-amber-500/20 hover:shadow-lg transition-all duration-300 transform active:scale-95 hover:-translate-y-0.5"
                                        >
                                            Xử lý thủ công
                                        </button>
                                    ) : (
                                        <button
                                            onClick={() => window.open(group.group_url || `https://facebook.com/groups/${group.fb_group_id}`, '_blank')}
                                            className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-300 transition-all duration-300 transform active:scale-95"
                                        >
                                            Xem nhóm
                                        </button>
                                    )}
                                </td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>
        </div>
    );
}
```

---

## 8. Graceful Shutdown Handler

```javascript
// src/shutdown.js
'use strict';

const db = require('./db/database');
const { broadcastToUI, extensionClients } = require('./websocket/wsServer');
const { CampaignManager } = require('./services/campaignManager');
const logger = require('./utils/logger');

let isShuttingDown = false;

/**
 * Graceful Shutdown — xử lý SIGTERM / SIGINT
 * Thứ tự:
 *   1. Đánh dấu isShuttingDown = true (CampaignManager sẽ dừng loop sau group hiện tại)
 *   2. Broadcast SHUTDOWN_INITIATED tới tất cả UI
 *   3. Pause tất cả campaigns đang RUNNING trong DB
 *   4. Chờ CampaignManager hoàn thành group hiện tại (max 30s)
 *   5. Đóng WS connections
 *   6. Đóng DB
 *   7. Exit
 */
async function gracefulShutdown(signal) {
    if (isShuttingDown) return;
    isShuttingDown = true;

    logger.warn(`[Shutdown] Received ${signal}. Starting graceful shutdown...`);

    // Bước 1: Thông báo UI
    broadcastToUI({ type: 'SERVER_SHUTTING_DOWN', signal });

    // Bước 2: Signal CampaignManager dừng sau group hiện tại
    CampaignManager.globalPause();

    // Bước 3: Update DB — mọi campaign RUNNING → PAUSED
    try {
        const updated = db.prepare(`
            UPDATE campaigns SET status='PAUSED', updated_at=datetime('now')
            WHERE status='RUNNING'
        `).run();
        logger.info(`[Shutdown] Paused ${updated.changes} running campaigns in DB`);
    } catch (err) {
        logger.error(`[Shutdown] DB pause error: ${err.message}`);
    }

    // Bước 4: Update execution_sessions ACTIVE → CANCELLED
    try {
        db.prepare(`
            UPDATE execution_sessions SET status='CANCELLED'
            WHERE status IN ('PENDING','ACTIVE')
        `).run();
    } catch (err) {
        logger.error(`[Shutdown] Session cancel error: ${err.message}`);
    }

    // Bước 5: Chờ tối đa 30s cho inflight operations
    logger.info('[Shutdown] Waiting up to 30s for inflight operations...');
    await new Promise(resolve => setTimeout(resolve, 30_000));

    // Bước 6: Đóng tất cả WS connections
    for (const [accountId, ws] of extensionClients) {
        try {
            ws.close(1001, 'Server shutdown');
            logger.info(`[Shutdown] Closed WS for accountId=${accountId}`);
        } catch { /* ignore */ }
    }

    // Bước 7: Đóng DB
    try {
        db.close();
        logger.info('[Shutdown] Database closed');
    } catch (err) {
        logger.error(`[Shutdown] DB close error: ${err.message}`);
    }

    logger.info('[Shutdown] Goodbye. Exiting with code 0.');
    process.exit(0);
}

// ─────────────────────────────────────────────────────────────
// REGISTER SIGNALS
// ─────────────────────────────────────────────────────────────
process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT',  () => gracefulShutdown('SIGINT'));

process.on('uncaughtException', (err) => {
    logger.fatal(`[UNCAUGHT] ${err.stack}`);
    gracefulShutdown('UNCAUGHT_EXCEPTION');
});

process.on('unhandledRejection', (reason) => {
    logger.error(`[UNHANDLED_REJECTION] ${reason}`);
});

module.exports = { gracefulShutdown, isShuttingDown: () => isShuttingDown };
```

---

## 9. Error Codes & Recovery

| Code | Tên | Nguyên nhân | Hành động |
|------|-----|-------------|-----------|
| `E001` | `NO_EXTENSION` | accountId không có WS kết nối | Đánh dấu group FAILED, tiếp tục |
| `E002` | `SESSION_TIMEOUT` | Extension không respond trong timeout | Đánh dấu session TIMEOUT, group FAILED |
| `E003` | `ACCOUNT_CHECKPOINT` | Extension báo account bị checkpoint | Update account status, chọn account khác |
| `E004` | `SPINTAX_MALFORMED` | Template spintax lỗi cú pháp | Log WARN, dùng fallback text (raw template) |
| `E005` | `DB_LOCKED` | SQLite WAL lock | Retry với exponential backoff (3 lần) |
| `E006` | `WS_AUTH_FAIL` | Token không hợp lệ | Close connection 4003, log WARN |
| `E007` | `CAMPAIGN_NOT_FOUND` | campaignId không tồn tại | Return 404 |
| `E008` | `NO_AVAILABLE_ACCOUNT` | Tất cả accounts CHECKPOINT/DIE | Pause campaign, notify UI |
| `E009` | `DB_CORRUPT`    | Database integrity check failed   | Cô lập file corrupt, restore từ backup gần nhất |
| `E010` | `BACKUP_FAIL`   | Backup tạo không thành công       | Log ERROR, retry sau 1h |
| `E011` | `UPDATE_FAIL`   | Auto-update tải/giải nén lỗi      | Rollback từ backup, log ERROR |
| `E012` | `KEY_EXHAUSTED` | Tất cả API keys đều trong cooldown | Pause campaign, notify UI |

---

## 10. Day-2 Resilience Services

> **[MỚI v0.4]** Ba service module chạy background đảm bảo hệ thống tự vận hành ổn định dài hạn.

### 10.1 `cleanupService.js` — Module dọn dẹp tự động

**Mục đích:** Tự động dọn dẹp dữ liệu cũ và tối ưu database.

| Thuộc tính | Chi tiết |
|-----------|----------|
| **Lịch chạy** | Hàng ngày lúc 3:00 AM (dùng `node-cron`: `'0 3 * * *'`) |
| **Retention** | DELETE logs cũ hơn 30 ngày |
| **Batch size** | 1000 dòng / lô (tránh lock DB quá lâu) |
| **Vacuum** | `PRAGMA incremental_vacuum(100)` sau mỗi lần dọn |
| **WAL trim** | `PRAGMA wal_checkpoint(TRUNCATE)` thu hẹp WAL file |
| **Event Loop** | Nhường 50ms (`setTimeout`) giữa các lô để không block server |

```javascript
// src/services/cleanupService.js
'use strict';

const cron = require('node-cron');
const { db } = require('../db/database');
const logger = require('../utils/logger');

const BATCH_SIZE = 1000;
const RETENTION_DAYS = 30;

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function runCleanup() {
  logger.info('[CLEANUP] Bắt đầu dọn dẹp logs cũ...');
  const cutoff = new Date(Date.now() - RETENTION_DAYS * 86400000).toISOString();
  let totalDeleted = 0;

  while (true) {
    const result = db.prepare(`
      DELETE FROM posting_logs WHERE id IN (
        SELECT id FROM posting_logs WHERE created_at < ? LIMIT ?
      )
    `).run(cutoff, BATCH_SIZE);

    totalDeleted += result.changes;
    if (result.changes < BATCH_SIZE) break;
    await sleep(50); // Nhường Event Loop
  }

  // Vacuum & WAL checkpoint
  db.pragma('incremental_vacuum(100)');
  db.pragma('wal_checkpoint(TRUNCATE)');

  logger.info(`[CLEANUP] Hoàn thành. Đã xóa ${totalDeleted} logs cũ.`);
}

// Schedule: 3:00 AM hàng ngày
cron.schedule('0 3 * * *', () => {
  runCleanup().catch(err => logger.error(`[CLEANUP] Lỗi: ${err.message}`));
});

module.exports = { runCleanup };
```

### 10.2 `autoUpdater.js` — Module tự cập nhật

**Mục đích:** Kiểm tra, tải và áp dụng bản cập nhật mới từ remote server.

| Hàm | Mô tả |
|-----|--------|
| `checkForUpdate()` | Gọi API remote (`GET /api/releases/latest`) lấy version mới nhất. So sánh với `package.json` hiện tại. |
| `downloadAndApply()` | Tải zip bản mới, backup thư mục hiện tại → `data/backups/pre-update/`, giải nén đè. **Blacklist** bảo vệ: `.env`, `hermes.db`, `data/`, `node_modules/`. Sau đó gọi `process.exit(99)` cho supervisor script tự restart. |
| Post-update | Gửi WebSocket message `{ type: 'EXTENSION_RELOAD' }` cho tất cả connected extensions để chúng tự refresh. |

```javascript
// src/services/autoUpdater.js
'use strict';

const fs = require('fs');
const path = require('path');
const logger = require('../utils/logger');

const BLACKLIST = ['.env', 'database.sqlite', 'data/', 'node_modules/'];

// Kiểm tra xem có đang chạy trong môi trường đóng gói Electron không
const isElectron = !!(process.versions && process.versions.electron) || process.env.ELECTRON_RUN_AS_NODE === '1';

async function checkForUpdate() {
  if (isElectron) {
    logger.info('[AUTO-UPDATE] Đang chạy trong môi trường Electron. Bàn giao việc kiểm tra cập nhật cho Electron Main Process.');
    return {
      currentVersion: require('../../package.json').version,
      latestVersion: null,
      updateAvailable: false,
      isElectronDelegate: true
    };
  }

  const pkg = require('../../package.json');
  // TODO: Implement fetch to remote release API
  // const response = await fetch(RELEASE_URL);
  // const latest = await response.json();
  return {
    currentVersion: pkg.version,
    latestVersion: null, // Placeholder
    updateAvailable: false
  };
}

async function downloadAndApply() {
  if (isElectron) {
    logger.warn('[AUTO-UPDATE] Bị từ chối. Môi trường Electron yêu cầu nâng cấp thông qua electron-updater ở Main Process.');
    throw new Error('Môi trường Electron yêu cầu cập nhật thông qua electron-updater.');
  }

  // 1. Tải zip từ remote
  // 2. Backup thư mục hiện tại → data/backups/pre-update/
  // 3. Giải nén đè (bỏ qua BLACKLIST files)
  // 4. Exit cho supervisor restart
  logger.info('[AUTO-UPDATE] Applying update...');
  process.exit(99); // Supervisor script sẽ restart server
}

module.exports = { checkForUpdate, downloadAndApply };
```

### 10.3 `backupManager.js` — Module sao lưu & phục hồi

**Mục đích:** Sao lưu database an toàn, export mã hóa, import giải mã, và kiểm tra tính toàn vẹn.

| Hàm | Mô tả |
|-----|--------|
| `createBackup()` | Dùng SQLite Online Backup API (`db.backup()`), lưu vào `data/backups/hermes_YYYYMMDD_HHmmss.db` |
| `exportEncrypted()` | Mã hóa file backup bằng AES-256-GCM, key derive từ HWID (MAC address + Motherboard UUID + Salt) |
| `importBackup(filePath)` | Giải mã file `.enc` + integrity check (`PRAGMA integrity_check`) + copy đè `hermes.db` |
| `integrityCheck()` | Chạy `PRAGMA integrity_check` khi server khởi động. Nếu fail → rename corrupt db sang `hermes.db.corrupt.TIMESTAMP` → restore từ backup gần nhất |
| `getLastBackupInfo()` | Trả về metadata (path, size, created_at) của backup gần nhất |
| `getExportPath()` | Trả về path file `.enc` export gần nhất (hoặc `null`) |

```javascript
// src/services/backupManager.js
'use strict';

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { db } = require('../db/database');
const logger = require('../utils/logger');
const { getHWID, encryptBuffer, decryptBuffer } = require('../utils/crypto');

// Sử dụng thư mục AppData/userData an toàn khi chạy trong Electron đóng gói
const appDataDir = process.env.APPDATA_DIR || path.resolve(__dirname, '../../');
const BACKUP_DIR = path.join(appDataDir, 'data', 'backups');

// Đảm bảo thư mục backup tồn tại
if (!fs.existsSync(BACKUP_DIR)) {
  fs.mkdirSync(BACKUP_DIR, { recursive: true });
}

async function createBackup() {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const backupPath = path.join(BACKUP_DIR, `hermes_${timestamp}.db`);

  await db.backup(backupPath);
  logger.info(`[BACKUP] Created: ${backupPath}`);

  const stats = fs.statSync(backupPath);
  return { path: backupPath, size: stats.size, created_at: new Date().toISOString() };
}

function getLastBackupInfo() {
  if (!fs.existsSync(BACKUP_DIR)) return null;
  const files = fs.readdirSync(BACKUP_DIR)
    .filter(f => f.endsWith('.db'))
    .sort()
    .reverse();
  if (files.length === 0) return null;
  const filePath = path.join(BACKUP_DIR, files[0]);
  const stats = fs.statSync(filePath);
  return { path: filePath, filename: files[0], size: stats.size, created_at: stats.mtime.toISOString() };
}

function getExportPath() {
  if (!fs.existsSync(BACKUP_DIR)) return null;
  const files = fs.readdirSync(BACKUP_DIR)
    .filter(f => f.endsWith('.enc'))
    .sort()
    .reverse();
  return files.length > 0 ? path.join(BACKUP_DIR, files[0]) : null;
}

async function importBackup(filePath) {
  // 1. Giải mã file .enc bằng HWID key
  // 2. PRAGMA integrity_check trên file giải mã
  // 3. Copy đè hermes.db
  logger.info(`[BACKUP] Importing from: ${filePath}`);
  return { success: true, imported_at: new Date().toISOString() };
}

function integrityCheck() {
  const result = db.pragma('integrity_check');
  const isOk = result[0]?.integrity_check === 'ok';
  if (!isOk) {
    logger.error('[BACKUP] Database integrity check FAILED!');
    // Rename corrupt file và restore từ backup
    const dbPath = path.resolve(__dirname, '../../data/hermes.db');
    const corruptPath = `${dbPath}.corrupt.${Date.now()}`;
    fs.renameSync(dbPath, corruptPath);
    logger.info(`[BACKUP] Corrupt DB renamed to: ${corruptPath}`);
    // TODO: Auto-restore từ latest backup
  }
  return isOk;
}

async function autoRestore() {
  const dbPath = path.resolve(__dirname, '../../data/hermes.db');
  const corruptPath = `${dbPath}.corrupt.${Date.now()}`;
  
  // 1. Rename corrupt DB
  if (fs.existsSync(dbPath)) {
    fs.renameSync(dbPath, corruptPath);
    logger.info(`[BACKUP] Corrupt DB renamed to: ${corruptPath}`);
  }
  
  // 2. Tìm backup gần nhất
  const lastBackup = getLastBackupInfo();
  if (!lastBackup) {
    throw new Error('Không có backup nào khả dụng để khôi phục');
  }
  
  // 3. Copy backup → hermes.db
  fs.copyFileSync(lastBackup.path, dbPath);
  logger.info(`[BACKUP] Auto-restored từ: ${lastBackup.filename}`);
  
  return { restored_from: lastBackup.filename, restored_at: new Date().toISOString() };
}

module.exports = { createBackup, getLastBackupInfo, getExportPath, importBackup, integrityCheck, autoRestore };
```

---

## Cảnh báo An ninh & Lỗ hổng Kiến trúc

### 🔴 LỖ HỔNG CRITICAL
1. **[L-1.1] Treo luồng Event Loop Node.js do cơ chế Spin Wait:**
   - *Rủi ro:* Khi SQLite bị khóa (`SQLITE_BUSY`), hàm `withRetry` thực hiện vòng lặp `while` đồng bộ để đợi (Spin Lock). Vì Node.js đơn luồng, vòng lặp này đóng băng hoàn toàn Event Loop lên tới 500ms mỗi lượt (và tối đa 5 giây cho 10 lượt), làm Express ngưng phản hồi HTTP và làm sập các kết nối WebSocket (do timeout heartbeat).
   - *Yêu cầu Remediation:* Bắt buộc loại bỏ spin-wait đồng bộ. Cấu hình PRAGMA `busy_timeout = 5000` của SQLite khi khởi tạo DB để C++ tự xếp hàng đợi ngầm. Nếu retry ở JS, dùng Promise phi đồng bộ (`await new Promise(r => setTimeout(r, delay))`).
2. **[L-2.2] Thực thi mã từ xa (RCE) qua Import Backup ghi đè Database thô:**
   - *Rủi ro:* Nhận file database backup `.enc` từ người dùng, giải mã và ghi đè trực tiếp lên tệp database chính `hermes.db`. Kẻ tấn công có thể chèn các **SQL Triggers** độc hại vào file DB. Ngay khi backend thực hiện câu truy vấn đầu tiên trên DB mới, trigger sẽ tự động kích hoạt thực thi lệnh hệ điều hành (RCE).
   - *Yêu cầu Remediation:* Không ghi đè trực tiếp. Thực hiện giải mã tệp DB vào thư mục tạm, mở kết nối DB tạm thời đó ở chế độ chỉ đọc (`readonly: true`), kiểm tra schema khớp 100% với file gốc và quét bảng `sqlite_master` để xóa bỏ mọi trigger/view lạ trước khi import.
3. **[L-3.1] Thiếu Entropy & Data Loss của khóa mã hóa HWID trong Docker/VM:**
   - *Rủi ro:* Khóa mã hóa sinh từ HWID (`MAC + Motherboard UUID`). Trong Docker/VM/WSL, Motherboard UUID bị ảo hóa thành chuỗi tĩnh ("None" hoặc toàn số 0) khiến entropy khóa suy giảm nghiêm trọng. Đồng thời, địa chỉ MAC card mạng ảo thay đổi khi reboot/VPN sẽ khiến khóa thay đổi vĩnh viễn, dẫn đến việc không thể giải mã các API Key cũ (mất dữ liệu).
   - *Yêu cầu Remediation:* Sử dụng một App Secret Key ngẫu nhiên sinh 1 lần duy nhất khi cài đặt ứng dụng và lưu trữ an toàn trong OS Keystore (Windows Credential Manager / Keychain) hoặc file cấu hình cục bộ phân quyền `0600`.
4. **[L-3.2] Tái sử dụng IV (IV/Nonce Reuse) trong chế độ AES-256-GCM:**
   - *Rủi ro:* Sử dụng một IV tĩnh hoặc IV tuần tự dễ đoán cho AES-GCM. Kẻ tấn công thu thập được hai bản mã khác nhau có thể thực hiện phép toán XOR để khôi phục bản rõ (Plaintext Recovery) của API key hoặc file backup.
   - *Yêu cầu Remediation:* Bắt buộc sinh IV ngẫu nhiên 12-byte bằng `crypto.randomBytes(12)` cho mỗi lần mã hóa và lưu trữ IV đính kèm với bản mã (ví dụ: `iv:ciphertext`).

### 🟠 LỖ HỔNG HIGH
1. **[L-1.2] Rủi ro hỏng Database (Corruption) khi chạy đa tiến trình qua mạng:**
   - *Rủi ro:* Chạy SQLite trên các phân vùng mạng (NFS/SMB) sẽ khiến cơ chế khóa file hoạt động sai cách, gây hỏng dữ liệu (corruption) khi 2 tiến trình ghi song song. Chạy ghi DB trực tiếp trong file ASAR của Electron sẽ gây crash do write-protection.
   - *Yêu cầu Remediation:* Cấu hình tệp DB nằm ngoài thư mục ASAR (trỏ về AppData/userData của hệ điều hành). Cấm chạy DB trên network shares.
2. **[L-2.1] Từ chối dịch vụ (DoS) qua Multer file upload:**
   - *Rủi ro:* API `/api/backup/import` nhận upload file backup qua Multer mà không cấu hình giới hạn kích thước file (`fileSize`), cho phép hacker upload file dung lượng hàng chục GB gây đầy ổ cứng máy chạy bot.
   - *Yêu cầu Remediation:* Giới hạn kích thước file upload tối đa trong cấu hình Multer (e.g. `limits: { fileSize: 100 * 1024 * 1024 }` cho 100MB).
3. **[L-2.3] Path Traversal thông qua ZIP backup payload:**
   - *Rủi ro:* ZIP backup giải nén chứa các tên file tương đối kiểu `../../` để ghi đè lên các tệp mã nguồn chính (RCE).
   - *Yêu cầu Remediation:* Loại bỏ toàn bộ tiền tố `..`, `/` và `\` khỏi tên file giải nén, sử dụng `path.basename()` để đảm bảo file ghi hoàn toàn nằm trong thư mục chỉ định.
4. **[L-3.4] Bỏ qua xác thực chữ ký toàn vẹn (Auth Tag Bypass) khi giải mã AES-GCM:**
   - *Rủi ro:* Khi giải mã, nếu code không thiết lập tag xác thực `decipher.setAuthTag(tag)` hoặc không bắt lỗi tại `decipher.final()`, kẻ tấn công có thể thay đổi bản mã (Ciphertext Tampering) để chèn dữ liệu độc hại.
   - *Yêu cầu Remediation:* Trích xuất Auth Tag (16 bytes) từ tệp mã hóa, set auth tag đầy đủ khi giải mã và bọc trong khối try-catch để hủy phiên giải mã nếu xác thực tính toàn vẹn thất bại.

---

## Changelog

| Version | Ngày | Thay đổi |
|---------|------|---------|
| v0.4.0 | 2026-06-16 | **[Day-2 Resilience]** Thêm bảng `api_key_pool`, PRAGMA auto_vacuum/wal_checkpoint, API endpoints `/api/keys`, `/api/backup`, `/api/system`. Đặc tả 3 service modules: `cleanupService.js`, `autoUpdater.js`, `backupManager.js`. Thêm Error Codes E009-E012. |
| v0.3.1 | 2026-06-15 | **[GAP FIXES]** GAP-03-01: account_events + post_intervals tables (SQLite); GAP-03-02: campaigns.config column; GAP-03-03: FK clarification execution_sessions; GAP-03-04: /api/groups CRUD endpoints; GAP-03-05: selectAvailableAccount EXCLUSIVE transaction; GAP-03-06: CampaignManager.pauseCampaign() implementation; GAP-03-07: SSE backpressure drain handling; GAP-03-08: WS exponential backoff (1s→30s) |
| v0.3 | 2026-06-15 | Rewrite hoàn toàn: multi-client WS Map, Campaign execution flow, SpintaxResolver v2, SSE logs, execution_sessions table, posting_logs table, Graceful Shutdown |
| v0.2 | — | (Legacy — archived) |
| v0.1 | — | (Legacy — archived) |

