# 🤖 Agent Harness — Hermes FacePost-Group

> **Môi trường phát triển AI-driven cho dự án Hermes.**
> Đây là hệ thống điều phối các AI Coding Agent, định nghĩa roles, workflow, harness kiểm tra chất lượng,
> và cơ chế nạp ngữ cảnh tự động (live context) cho toàn bộ vòng đời phát triển dự án.
>
> 🧠 **Kiến trúc Swarm Phi Trạng Thái & Hướng Sự Kiện (Stateless & Event-driven Swarm):**
> Hệ thống không vận hành các tác tử dưới dạng daemon chạy ngầm liên tục gây lãng phí tài nguyên và ô nhiễm ngữ cảnh chéo. Mọi Agent (Architect, Coding, Auditor, QA, Evaluator) đều được sinh ra (spawn) theo nhu cầu của pipeline sự kiện, thực thi nhiệm vụ cô lập của mình, ra phán quyết/xuất code, rồi tự hủy (terminate). Thiết kế này đảm bảo cửa sổ ngữ cảnh (Context Window) luôn sạch sẽ tuyệt đối và các ranh giới xử lý (Boundaries) được kiểm soát chính xác 100%.
>
> 💡 **Tuyên ngôn dự án:** Tác giả dự án là một non-tech hoàn toàn không viết một dòng code nào. Đây là dự án tham vọng chứng minh rằng một mạng lưới Agent tự trị (Agentic Swarm) có thể tự lực gánh vác việc phát triển toàn bộ một sản phẩm phức tạp nếu được vận hành trong một hệ thống chốt chặn và khung kiểm thử (Harness) phù hợp.

| Metadata | Value |
|---|---|
| Version | `3.0.0` |
| Status | `ACTIVE` |
| Project | Hermes FacePost-Group |
| Creator | Non-Tech (0-line coding author, swarm-driven) |
| Spec Anchor | `facepost_00_shared_types.md` (Single Source of Truth) |
| Date | 2026-06-18 |


---

## 📋 Mục Lục

1. [Hệ thống là gì?](#hệ-thống-là-gì)
2. [Cấu trúc thư mục](#cấu-trúc-thư-mục)
3. [Nạp context khi bắt đầu phiên](#nạp-context-khi-bắt-đầu-phiên)
4. [Luồng 4 bước](#luồng-4-bước-architect--coding--auditor--qa)
5. [Quick Reference](#quick-reference)

---

## Hệ Thống Là Gì?

**Agent Harness** là lớp "não bộ tổ chức" nằm trên code thực tế của dự án Hermes. Nó không chứa source code — nó chứa **hệ thống quy tắc, phân vai, quy trình kiểm duyệt** để đảm bảo mọi AI Coding Agent đều:

- **Làm đúng việc** (theo spec, không vẽ thêm)
- **Không phạm anti-pattern** (gác bởi Auditor)
- **Được kiểm chứng trên Windows** (QA Agent chạy E2E thật)
- **Biết chính xác ngữ cảnh mình đang làm việc** (Live Context system)

Hệ thống mô phỏng cách một engineering team thực sự hoạt động — với Lead Architect (thiết kế), Feature Developers (code), Code Reviewer (audit), và QA Engineer (test) — nhưng tất cả đều là AI Agents.

---

## Cấu Trúc Thư Mục

```
agent_harness/
│
├── README.md                          ← File này — tổng quan hệ thống
│
├── roles/                             ← Định nghĩa vai trò cho từng Agent
│   ├── lead_architect.md              ← Kiến trúc sư tổng điều phối
│   ├── coding_agents.md               ← 3 Feature Coding Agents (ext/backend/network)
│   ├── auditor_agent.md               ← Anti-Pattern Auditor (gác cổng chất lượng)
│   ├── qa_agent.md                    ← Windows Sandbox QA Agent (chạy E2E thật)
│   └── qa_evaluator.md                ← Trọng tài thẩm định & Khử nhiễu QA (Spec Expert)
│
├── harness/                           ← Bộ kiểm tra & registry chuẩn
│   ├── anti_pattern_registry.md       ← Danh sách 32 anti-patterns bị cấm (có severity)
│   ├── error_code_registry.md         ← Toàn bộ error codes của hệ thống (ERR-*)
│   ├── specs_generation_guide.md      ← Hướng dẫn định hình spec chuẩn (Blueprint)
│   └── apex_sar_engine.py             ← Bộ máy Search-and-Replace (SAR) trần nguyên tử
│
├── workflow/                          ← Quy trình vận hành
│   └── 4step_assembly.md              ← Quy trình lắp ráp 4 bước đầy đủ
│
├── brain/                             ← Context tổng hợp cho Lead Architect
│   └── master_context.md              ← Map kiến trúc tổng, index specs, key decisions
│
└── live_context/                      ← Hệ thống tự động nạp ngữ cảnh động (ĐÃ TRIỂN KHAI)
    ├── DESIGN.md                      ← Thiết kế tổng thể của hệ thống nạp ngữ cảnh
    ├── context_map.json               ← Bản đồ ánh xạ File nguồn -> Spec ID
    ├── context_dispatcher.py          ← Script điều phối và phân phối live context
    ├── live_context_loader.py         ← Script nạp ngữ cảnh tự động vào cache
    ├── live_context.md                ← File nạp ngữ cảnh phiên hiện tại
    ├── cache/                         ← Thư mục lưu cache ngữ cảnh riêng lẻ từng file code
    └── archive/                       ← Kho lưu trữ ngữ cảnh của các spec đã nén/archive
```

### Mô tả chi tiết từng thành phần

| Path | Vai trò | Đọc bởi |
|---|---|---|
| `roles/lead_architect.md` | Role rules cho Architect Agent — không tự code, chỉ bóc tách task | Lead Architect |
| `roles/coding_agents.md` | Role rules cho 3 coding agents với context isolation nghiêm ngặt | extension/backend/network workers |
| `roles/auditor_agent.md` | Quy trình audit, format output, zero-tolerance cho CRITICAL | Auditor Agent |
| `roles/qa_agent.md` | Windows setup, tiered verification, Audit Package schema | QA Agent |
| `roles/qa_evaluator.md` | Trọng tài thẩm định lỗi thật/ảo, tăng retry_count, báo cáo Escalate | QA Evaluator |
| `harness/anti_pattern_registry.md` | 32 anti-patterns phân loại CRITICAL/HIGH/MEDIUM/LOW | Auditor + mọi Coding Agent |
| `harness/error_code_registry.md` | Toàn bộ ERR-* codes theo module prefix | QA + Coding Agents |
| `harness/specs_generation_guide.md` | Hướng dẫn thiết kế và định hình spec chuẩn (Blueprint) | Architect + Spec Writers |
| `harness/apex_sar_engine.py` | Bộ máy áp dụng khối Search-and-Replace cục bộ một cách deterministic | QA Evaluator |
| `workflow/4step_assembly.md` | Quy trình đầy đủ từ request → code → audit → test | Tất cả Agents |
| `brain/master_context.md` | Overview kiến trúc, index 13 specs, tech decisions | Lead Architect (boot context) |
| `live_context/DESIGN.md` | Thiết kế hệ thống tự động nạp context theo file | Developer / System |
| `live_context/context_map.json` | Bản đồ ánh xạ file nguồn sang Spec tương ứng | Loader + Dispatcher |
| `live_context/live_context_loader.py` | Script tự động nạp và cập nhật ngữ cảnh | IDE / Agent trigger |
| `live_context/context_dispatcher.py` | Điều phối và phân phối live context cho từng file | IDE / System |
| `live_context/cache/` | Thư mục cache lưu trữ ngữ cảnh động của từng file | Coding Agents |
| `live_context/archive/` | Kho lưu trữ ngữ cảnh của các spec đã nén/archive | System |

---

## Nạp Context Khi Bắt Đầu Phiên

### Bước 1 — Lead Architect Agent (boot sequence)

```
1. Đọc agent_harness/brain/master_context.md          ← Map tổng thể
2. Đọc specs/facepost_00_shared_types.md              ← Hiến pháp (bắt buộc)
3. Đọc agent_harness/harness/anti_pattern_registry.md ← Biết cấm gì
4. Đọc agent_harness/workflow/4step_assembly.md        ← Biết quy trình
5. Identify task → map sang spec sub-file tương ứng
6. Tạo Coding Tickets theo template trong lead_architect.md
```

### Bước 2 — Feature Coding Agent (context isolation)

```
1. Nhận Coding Ticket từ Architect
2. Đọc DUY NHẤT spec sub-file được chỉ định trong ticket
3. Đọc facepost_00_shared_types.md (Phần liên quan: DB Schema / Message Types)
4. Thực hiện nạp context: Gọi python live_context/live_context_loader.py <active_file_path> <workspace_root> hoặc thông qua mcp_context
5. Code theo function_signature và output_contract trong ticket
```

### Bước 3 — Auditor Agent (gate check)

```
1. Nhận code từ Coding Agent
2. Đọc agent_harness/harness/anti_pattern_registry.md
3. Chạy linter local (ESLint/Ruff) & quét AST trên git staged changes để phát hiện anti-pattern
4. Output [APPROVED] hoặc [REJECTED] kèm Audit Package JSON chi tiết
```

### Bước 4 — QA Agent (Windows runtime)

```
1. Nhận approved code từ Auditor
2. Đọc agent_harness/harness/error_code_registry.md
3. Chạy tiered verification: Static → Mock → E2E Windows
4. Output: Audit Package JSON hoặc PASS
```

### Bước 4b — QA Evaluator Agent (Validation Gate)

```
1. Nhận Audit Package JSON khi QA Agent báo thất bại (FAIL)
2. Đọc toàn bộ 13 Specs và mã nguồn để đối chiếu logic
3. Đánh giá lỗi: Lỗi thật (True Positive) hay Lỗi ảo (False Positive)
4. Xử lý:
   - Lỗi ảo: Reject báo cáo lỗi của QA, Approve mã nguồn để merge.
   - Lỗi thật: Sử dụng LLM sinh ra khối Structured Search-and-Replace (SAR) cực hẹp, vá trực tiếp qua `apex_sar_engine.py` trong sandbox và chạy lại test. Tăng retry_count thêm 1.
     ↳ Nếu retry_count <= 3: Tiếp tục chạy lại test trong sandbox.
     ↳ Nếu retry_count > 3 hoặc kích hoạt Escalation Boundary: Dừng luồng, kích hoạt FSM Maintenance Path (rollback/freeze), gửi QA Escalation Report (ESCALATED_HUMAN).
```

---

## Luồng 4 Bước: Architect → Coding → Auditor → QA → Validation Gate

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                    HERMES AGENT HARNESS — 4-STEP ASSEMBLY                ║
╚═══════════════════════════════════════════════════════════════════════════╝

  ┌─────────────────────────────────────────────────────────────────────┐
  │  INPUT: User request / Bug report / Feature spec                    │
  └─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │  STEP 1 — CONTEXT INJECTION                                         │
  │  Agent: Lead Architect                                              │
  │  ─────────────────────────────────────────────────────────────────  │
  │  • Đọc specs liên quan + Spec 00 (bắt buộc)                        │
  │  • Bóc tách micro-tasks theo module                                 │
  │  • Tạo Coding Tickets (JSON) với interface nghiêm ngặt             │
  │                                                                     │
  │  Output: Array<CodingTicket>                                        │
  └─────────────────────────────────────────────────────────────────────┘
                               │
                    ┌──────────┼──────────┐
                    ▼          ▼          ▼
  ┌──────────────────────────────────────────────────────────────────────┐
  │  STEP 2 — CODE ISOLATION GENERATION                                  │
  │  Agents: extension_worker | backend_worker | network_worker          │
  │  ─────────────────────────────────────────────────────────────────── │
  │  • Mỗi agent nhận ticket của mình (context isolation)               │
  │  • Chỉ đọc spec được chỉ định + Spec 00 (phần liên quan)           │
  │  • Viết code theo function_signature + output_contract              │
  │  • KHÔNG tự chạy — chỉ xuất code                                   │
  │                                                                      │
  │  Output: Code files                                                  │
  └──────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │  STEP 3 — REJECTION GATE                                            │
  │  Agent: Anti-Pattern Auditor                                        │
  │  ─────────────────────────────────────────────────────────────────  │
  │  • Grep code theo Detection Hints trong anti_pattern_registry.md    │
  │  • CRITICAL → REJECT ngay, không thương lượng                      │
  │  • HIGH/LOW → cảnh báo có suggestion                               │
  │  • Output: [APPROVED] hoặc [REJECTED] + evidence                   │
  │                                                                     │
  │  Output: Audit Result                                               │
  └─────────────────────────────────────────────────────────────────────┘
                   │                    │
            [APPROVED]            [REJECTED] ──┐
                   │                           │
                   ▼                           │
  ┌─────────────────────────────────────────┐  │
  │  STEP 4 — RUNTIME HARNESS               │  │
  │  Agent: Windows QA Agent                │  │
  │  ────────────────────────────────────── │  │
  │  • Vòng 1: Static Contract / Schema     │  │
  │  • Vòng 2: Mock Sandbox / Unit tests    │  │
  │  • Vòng 3: Windows Runtime E2E          │  │
  │                                         │  │
  │  Output: PASS hoặc Audit Package JSON   │  │
  └─────────────────────────────────────────┘  │
          │                │                   │
        PASS             FAIL                  │
          │                │                   │
          ▼                ▼                   │
  ┌──────────────┐ ┌─────────────────────────────────────────────────┐
  │   DONE ✅    │ │ STEP 4b — QA VALIDATION GATE                    │◄┘
  └──────────────┘ │ Agent: QA Evaluator (Referee)                   │
                   │ ─────────────────────────────────────────────── │
                   │ • Thẩm định lỗi thật/ảo (False Positive)        │
                   │ • Sinh Structured SAR patches qua apex_engine   │
                   │ • Tăng retry_count (Tối đa 3 lần)               │
                   └─────────────────────────────────────────────────┘
                                   │                     │
                    [REJECT QA REPORT] (Lỗi ảo)      [TRUE FAIL]
                                   │                     │
                                   ▼             retry_count <= 3?
                               [APPROVE]         ┌───────┴───────┐
                                   │          Có │               │ Không
                                   ▼             ▼               ▼
                                 [MERGE]       [HOTFIX]    [ESCALATED_HUMAN]
                                             (SAR Sandbox) (FSM Maintenance/User)
                                                 ▲               │
                                                 │               │
                                                 └───────────────┘ (Nếu được duyệt)
```

---

## Quick Reference

### Error Code Prefixes

| Prefix | Module |
|---|---|
| `ERR-DOM-*` | DOM manipulation errors |
| `ERR-NET-*` | Network / WebSocket errors |
| `ERR-AI-*` | LLM / AI Brain errors |
| `ERR-CHK-*` | Facebook checkpoint errors |
| `ERR-PRX-*` | Proxy relay errors |
| `ERR-SYS-*` | System / infrastructure errors |
| `ERR-CE-*` | Content Engine errors (Spec 08) |
| `ERR-HYB-*` | Hybrid Extension errors (Spec 09) |

### Coding Agent → Spec Mapping

| Agent | Spec chính | Phần Spec 00 / File liên quan |
|---|---|---|
| `extension_worker` | `facepost_01_chrome_extension.md`, `facepost_09_hybrid_extension.md` | Message Types (Phần 3) |
| `backend_worker` | spec module đang build (Spec 03, 10, 13) | DB Schema (Phần 5) |
| `network_worker` | `facepost_04_anti_detection.md` | LocalProxyRelay |
| `qa_agent` | `facepost_12_testing_qa.md` | Quy trình kiểm thử hợp đồng WS |

### Anti-Pattern Severity

| Severity | Hành động |
|---|---|
| `CRITICAL` | REJECT ngay — không code tiếp |
| `HIGH` | Cảnh báo bắt buộc fix trước merge |
| `MEDIUM` | Cần sửa, có thể sau sprint |
| `LOW` | Suggestion, không block |

---

## 🔄 Tái Sử Dụng & Tinh Chỉnh Cho Dự Án Khác (Portability Guide)

Bộ Harness này được thiết kế theo triết lý **tách rời cấu hình và logic vận hành (Decoupled Design)**, giúp anh dễ dàng áp dụng nó vào bất kỳ dự án phát triển phần mềm nào khác trong tương lai:

### 1. Quy trình 3 bước chuyển đổi sang dự án mới:
1. **Ánh xạ codebase (`context_map.json`):** Khai báo các file mã nguồn của dự án mới tương ứng với các file spec thiết kế tương ứng.
2. **Cập nhật Roadmap & Tasks (`context_dispatcher.py`):** Sửa cấu hình tuần (`WEEK_CONFIGS`) ở đầu file để định nghĩa lại lộ trình các tuần, QA Gates và danh sách các task mặc định của dự án mới.
3. **Định nghĩa luật chơi của AI (`roles/` và `AGENTS.md`):** Điều chỉnh lại mô tả công việc của Lead Architect, Coding Agents, QA, Auditor phù hợp với công nghệ của dự án mới (ví dụ: Rust ECS, Python, Go, AWS security...).

### 2. Các giá trị cốt lõi được giữ lại nguyên vẹn:
- **Cơ chế Cưỡng bức nạp context (Forced Hydration):** Nạp đúng tài liệu thiết kế vào live context của AI trước mỗi task phát triển.
- **Nén & Lưu trữ Spec (Context Archiving):** Tự động dọn dẹp các Spec đã hoàn thành thành Anchor Summary siêu nhẹ để giải phóng bộ nhớ context window cho AI.
- **Thư ký HOTZONE:** Quản lý tiến độ task, tính phần trăm %, vẽ thanh tiến độ và rollover sang tuần mới hoàn toàn tự động trên progress tracker.

---

## 📈 Nhật Ký Nâng Cấp (Changelog)

### v3.0.0 (2026-06-18) - Apex Swarm Upgrade (Antigravity 2.0 Native)
- **Tối Ưu Hoá Cho Antigravity 2.0 (Gemini 3.5)**: Loại bỏ giới hạn context cứng 2KB, áp dụng Full Spec Hydration để nạp Spec đầy đủ, loại bỏ lỗi thiếu interface.
- **Bộ Máy Search-and-Replace (SAR) Cục Bộ**: Triển khai `apex_sar_engine.py` giúp vá nóng mã nguồn một cách deterministic tuyệt đối, loại bỏ lỗi sinh patch Unified Diff `.patch`.
- **Tích Hợp Quét AST & Linter Local**: Nâng cấp Auditor Agent từ quét Regex tĩnh sang gọi trực tiếp ESLint/Ruff ở local sandbox, chỉ quét vùng mã nguồn có sự thay đổi (`git diff --staged`) và các file liên đới.
- **Ma Trận Khẩn Cấp FSM & Git Sandbox**: Bổ dung cơ chế FSM Maintenance Path (tự động freeze, rollback, xoay key) và chính sách phòng vệ Git branch cô lập (`sandbox/task-xxx`) cho mỗi ticket lập trình.
- **Mở rộng 32 Luật Chống Anti-Patterns**: Thêm chi tiết cho các anti-pattern từ AP-18 đến AP-25 ở các mức độ CRITICAL và HIGH để phòng thủ tối đa trước WAF của Facebook.

### v2.0.0 (2026-06-18) - Isolated Context & Auto Registration Upgrade
- **Cô Lập Ngữ Cảnh Sống (Isolated Context Cache)**: Loại bỏ file `live_context.md` dùng chung gây xung đột chéo (race condition). Chuyển sang cơ chế tạo file `.context.md` riêng biệt cho từng file nguồn trong thư mục `live_context/cache/`.
- **Khử Trùng Lặp Chuỗi (Substring Collision Fix)**: Chuyển đổi thuật toán so khớp Spec từ so khớp chứa (`in`) sang so khớp chính xác tuyệt đối sau khi chuẩn hóa đường dẫn (`==`).
- **Tăng Cường Tính Bền Bỉ (Parser Rigidity Fix)**: Bọc các parser phân tích tracker trong khối `try-except` với nguyên tắc No-Throw Guarantee để chống crash hệ thống khi cấu trúc file Markdown thay đổi nhẹ.
- **Tự Động Đăng Ký File Mới (Auto File Registration)**: Thêm chức năng CLI `register` tự động phân loại đường dẫn file mới thành các Spec ID tương ứng và chèn trực tiếp vào `context_map.json` một cách thông minh.

---

*Hermes FacePost-Group — Agent Harness v3.0.0*
*Xem `workflow/4step_assembly.md` để biết chi tiết vận hành.*

