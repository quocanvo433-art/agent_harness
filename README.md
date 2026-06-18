# 🤖 Agent Harness — Hermes FacePost-Group

> **Môi trường phát triển AI-driven cho dự án Hermes.**
> Đây là hệ thống điều phối các AI Coding Agent, định nghĩa roles, workflow, harness kiểm tra chất lượng,
> và cơ chế nạp ngữ cảnh tự động (live context) cho toàn bộ vòng đời phát triển dự án.

| Metadata | Value |
|---|---|
| Version | `1.0.0` |
| Status | `ACTIVE` |
| Project | Hermes FacePost-Group |
| Spec Anchor | `facepost_00_shared_types.md` (Single Source of Truth) |
| Date | 2026-06-16 |

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
│   └── qa_agent.md                    ← Windows Sandbox QA Agent (chạy E2E thật)
│
├── harness/                           ← Bộ kiểm tra & registry chuẩn
│   ├── anti_pattern_registry.md       ← Danh sách 16 anti-patterns bị cấm (có severity)
│   └── error_code_registry.md         ← Toàn bộ error codes của hệ thống (ERR-*)
│
├── workflow/                          ← Quy trình vận hành
│   └── 4step_assembly.md              ← Quy trình lắp ráp 4 bước đầy đủ
│
├── brain/                             ← Context tổng hợp cho Lead Architect
│   └── master_context.md              ← Map kiến trúc tổng, index specs, key decisions
│
└── live_context/                      ← Hệ thống nạp ngữ cảnh động (thiết kế)
    └── DESIGN.md                      ← Thiết kế Live Context Loader (chưa triển khai)
```

### Mô tả chi tiết từng thành phần

| Path | Vai trò | Đọc bởi |
|---|---|---|
| `roles/lead_architect.md` | Role rules cho Architect Agent — không tự code, chỉ bóc tách task | Lead Architect |
| `roles/coding_agents.md` | Role rules cho 3 coding agents với context isolation nghiêm ngặt | extension/backend/network workers |
| `roles/auditor_agent.md` | Quy trình audit, format output, zero-tolerance cho CRITICAL | Auditor Agent |
| `roles/qa_agent.md` | Windows setup, tiered verification, Audit Package schema | QA Agent |
| `harness/anti_pattern_registry.md` | 16 anti-patterns phân loại CRITICAL/HIGH/MEDIUM/LOW | Auditor + mọi Coding Agent |
| `harness/error_code_registry.md` | Toàn bộ ERR-* codes theo module prefix | QA + Coding Agents |
| `workflow/4step_assembly.md` | Quy trình đầy đủ từ request → code → audit → test | Tất cả Agents |
| `brain/master_context.md` | Overview kiến trúc, index 9 specs, tech decisions | Lead Architect (boot context) |
| `live_context/DESIGN.md` | Thiết kế hệ thống tự động nạp context theo file | Để triển khai sau |

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
4. (Tương lai) Gọi: python live_context/live_context_loader.py --file <target>
5. Code theo function_signature và output_contract trong ticket
```

### Bước 3 — Auditor Agent (gate check)

```
1. Nhận code từ Coding Agent
2. Đọc agent_harness/harness/anti_pattern_registry.md
3. Grep code theo Detection Hints trong registry
4. Output [APPROVED] hoặc [REJECTED] với evidence cụ thể
```

### Bước 4 — QA Agent (Windows runtime)

```
1. Nhận approved code từ Auditor
2. Đọc agent_harness/harness/error_code_registry.md
3. Chạy tiered verification: Static → Mock → E2E Windows
4. Output: Audit Package JSON hoặc PASS
```

---

## Luồng 4 Bước: Architect → Coding → Auditor → QA

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
            [APPROVED]            [REJECTED]
                   │                    │
                   ▼                    └──────────────────┐
  ┌─────────────────────────────────────────────────────┐  │
  │  STEP 4 — RUNTIME HARNESS                           │  │
  │  Agent: Windows QA Agent                            │  │
  │  ─────────────────────────────────────────────────  │  │
  │  • Vòng 1: Static Contract (JSON Schema, Protocol)  │  │
  │  • Vòng 2: Mock Sandbox (Unit test + DOM fixture)   │  │
  │  • Vòng 3: Windows Runtime E2E (Chrome thật)        │  │
  │                                                     │  │
  │  Output: PASS hoặc Audit Package JSON               │  │
  └─────────────────────────────────────────────────────┘  │
          │                │                               │
        PASS            FAIL                               │
          │                │                               │
          ▼                └──────────────► STEP 2 ◄───────┘
  ┌──────────────┐         (kèm Audit Package)
  │   DONE ✅   │
  └──────────────┘
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

| Agent | Spec chính | Phần Spec 00 |
|---|---|---|
| `extension_worker` | `facepost_01_chrome_extension.md` | Message Types (Phần 3) |
| `backend_worker` | spec module đang build | DB Schema (AD-05) |
| `network_worker` | `facepost_04_anti_detection.md` | LocalProxyRelay (AD-03) |

### Anti-Pattern Severity

| Severity | Hành động |
|---|---|
| `CRITICAL` | REJECT ngay — không code tiếp |
| `HIGH` | Cảnh báo bắt buộc fix trước merge |
| `MEDIUM` | Cần sửa, có thể sau sprint |
| `LOW` | Suggestion, không block |

---

*Hermes FacePost-Group — Agent Harness v1.0.0*
*Xem `workflow/4step_assembly.md` để biết chi tiết vận hành.*
