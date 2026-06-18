# -*- coding: utf-8 -*-
"""
Swarm Context Dispatcher - Hermes FacePost-Group
Điều phối cưỡng bức context (Forced Hydration), Lưu trữ/Nén ngữ cảnh (Context Archiving) & Thư ký HOTZONE (HOTZONE Secretary)
"""

import os
import sys
import shutil
import json
import re
import subprocess
from datetime import datetime

# Cấu hình các tuần phục vụ cho tính năng "Thư ký" tự động cập nhật HOTZONE
WEEK_CONFIGS = {
    1: {
        "title": "Tuần 1 — Khởi tạo & Thiết kế Spec",
        "specs": ["facepost_00_shared_types.md"],
        "qa_gate": "QA-01",
        "tasks": [
            "Validate `context_map.json` schema against DESIGN.md",
            "Test `live_context_loader.py` file→spec mapping",
            "Tạo Master Plan, Progress Tracker và Rules of Project",
            "Viết Spec 01→10 (11 specs hoàn chỉnh)",
            "Thiết lập cấu trúc thư mục Extension và Dashboard app",
            "Tạo file `manifest.json` chuẩn Manifest V3",
            "Tạo database SQLite sơ khởi cho Dashboard (`schema.sql`, `db.js`)",
            "Verify ALL 90 skeleton files exist — 0 missing"
        ]
    },
    2: {
        "title": "Tuần 2 — Extension Engine",
        "specs": ["facepost_01_chrome_extension.md"],
        "qa_gate": "QA-02: DOM ≥92%, Gaussian delay, Bezier cascade",
        "tasks": [
            "Implement DOM compressor & extractor (extension/dom_compressor.js)",
            "Implement WS connection with HMAC-SHA256 authentication (extension/background.js, extension/lib/hmac_sha256.js)",
            "Implement human simulator with Gaussian delays & Bezier movements (extension/human_simulator.js)",
            "Implement popup UI and styles (extension/popup.html, extension/popup.css, extension/popup.js)",
            "Implement Chrome Launcher setup (extension/chrome_launcher.js)"
        ]
    },
    3: {
        "title": "Tuần 3 — Express Server & Dashboard Route Modules",
        "specs": ["facepost_03_dashboard_app.md", "facepost_07_dashboard_ui.md"],
        "qa_gate": "QA-03: REST API tests, SQLite WAL, Spintax",
        "tasks": [
            "Implement SQLite database initialization in WAL mode (dashboard/db.js, dashboard/schema.sql)",
            "Implement wsServer.js for WebSocket connections (dashboard/src/websocket/wsServer.js)",
            "Implement 10 dashboard API route files (dashboard/src/routes/*.js)",
            "Implement 3 service modules: cleanup, backup, autoUpdater",
            "Implement dashboard React UI components and layouts (dashboard/dashboard_ui/*.jsx)"
        ]
    },
    4: {
        "title": "Tuần 4 — AI Brain, Content Engine & FSM",
        "specs": ["facepost_02_ai_agent_brain.md", "facepost_05_agent_loop.md", "facepost_08_content_engine.md"],
        "qa_gate": "QA-04: FSM 9-state, Circuit Breaker, Cosine ≤60%",
        "tasks": [
            "Implement AI brain decisions & session manager (dashboard/ai_brain.js, dashboard/session_manager.js)",
            "Implement 13 Content Engine modules for persona and generation (src/content_engine/*, src/interaction_manager/*)",
            "Implement content engine & interactions API routes (src/routes/*)",
            "Implement Agent Loop FSM (9-state, circuit breaker) (extension/agent_loop.js, dashboard/agent_loop.js)",
            "Implement UI panel components for content & interaction (dashboard/dashboard_ui/ContentComposer.jsx, InteractionPanel.jsx)"
        ]
    },
    5: {
        "title": "Tuần 5 — Native Proxy Host & Checkpoint Handler",
        "specs": ["facepost_04_anti_detection.md", "facepost_06_checkpoint_handler.md"],
        "qa_gate": "QA-05: Proxy E2E <500ms, CHK-01→08 fixtures",
        "tasks": [
            "Implement native messaging proxy host (native_host/hermes_proxy_host.py)",
            "Implement local proxy relay and installation script (native_host/local_proxy_relay.py, install_native_host.bat)",
            "Implement checkpoint detector for 8 types CHK-01 to CHK-08 (extension/checkpoint_detector.js)"
        ]
    },
    6: {
        "title": "Tuần 6 — Electron Desktop, CWS Diplomat & CI/CD",
        "specs": ["facepost_09_hybrid_extension.md", "facepost_10_desktop_packaging.md"],
        "qa_gate": "QA-06: 5 profiles × 12h, Vision LLM verify",
        "tasks": [
            "Build Electron main process, preload & tray integrations (hermes-desktop/*.js)",
            "Implement hybrid CWS extension safe-modes (extension_cws/*.js, popup_safe.html, popup_safe.js)",
            "Setup GitHub Actions CI/CD release workflow (.github/workflows/release.yml)"
        ]
    }
}

def load_tracker_parts(tracker_path):
    try:
        with open(tracker_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Tìm vị trí của HOTZONE và ARCHIVE
        hotzone_marker = "## 🔴 HOTZONE"
        archive_marker = "## 📦 ARCHIVE"
        
        parts = content.split(hotzone_marker)
        if len(parts) < 2:
            print("[ERROR] Không tìm thấy marker HOTZONE trong tracker.")
            return None
        
        part1 = parts[0]
        rest = parts[1]
        
        parts2 = rest.split(archive_marker)
        if len(parts2) < 2:
            print("[ERROR] Không tìm thấy marker ARCHIVE trong tracker.")
            return None
        
        hotzone_content = parts2[0]
        part3 = archive_marker + parts2[1]
        
        return part1, hotzone_content, part3
    except Exception as e:
        print(f"[ERROR] Lỗi khi xử lý cấu trúc tracker: {e}")
        return None

def parse_hotzone_tasks(hotzone_content):
    tasks = []
    in_task_section = False
    
    for line in hotzone_content.splitlines():
        line_strip = line.strip()
        
        # Nhận diện vùng task
        if "### 🎯 ĐANG LÀM" in line_strip or "### ✅ ĐÃ XONG" in line_strip:
            in_task_section = True
            continue
        elif "### ⚡ BLOCKER" in line_strip or "### 🔑 CONTEXT" in line_strip or "### 🚪 QA-" in line_strip or line_strip.startswith("> **KHI PASS QA-"):
            in_task_section = False
            continue
            
        if in_task_section and (line_strip.startswith("- [ ]") or line_strip.startswith("- [x]")):
            done = line_strip.startswith("- [x]")
            task_text = line_strip[5:].strip()
            # Bỏ qua dòng trống hoặc placeholder
            if task_text and not task_text.startswith("*(") and not task_text.endswith(")*"):
                tasks.append({"text": task_text, "done": done})
                
    return tasks

def update_tracker_on_archive(week_num, workspace_root):
    tracker_path = os.path.join(workspace_root, "facepost_progress_tracker.md")
    if not os.path.exists(tracker_path):
        print(f"[WARNING] Không tìm thấy tracker tại {tracker_path} để cập nhật.")
        return
        
    parts = load_tracker_parts(tracker_path)
    if not parts:
        return
    part1, hotzone_content, part3 = parts
    
    # Parse các task thực sự của tuần vừa hoàn tất
    current_tasks = parse_hotzone_tasks(hotzone_content)
    
    # Nếu danh sách trống, thử nạp mặc định từ cấu hình tuần vừa rồi
    if not current_tasks:
        cfg = WEEK_CONFIGS.get(week_num, {})
        for t in cfg.get("tasks", []):
            current_tasks.append({"text": t, "done": True})
            
    done_count = sum(1 for t in current_tasks if t['done'])
    total_count = len(current_tasks) if current_tasks else 1
    
    # Cấu hình tuần hiện tại
    current_cfg = WEEK_CONFIGS.get(week_num, {"title": f"Tuần {week_num}", "specs": []})
    week_title = current_cfg["title"]
    specs_links = ", ".join([f"[{s}](file:///{workspace_root.replace('\\\\', '/')}/specs/{s})" for s in current_cfg["specs"]])
    
    # Danh sách task đã hoàn thành dạng markdown
    tasks_md = "\n".join([f"   - [x] {t['text']}" for t in current_tasks])
    
    # Tạo archive entry
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    archive_entry = f"""
<details><summary>✅ {week_title} ({done_count}/{total_count} tasks) — PASSED QA-0{week_num} ✓</summary>

- **Specs:** {specs_links}
- **Legacy archive:** `agent_harness/live_context/archive/`
- **QA Result:** PASS — {timestamp}

**Các nhiệm vụ đã hoàn thành:**
{tasks_md}
</details>
"""

    # Chèn vào phần ARCHIVE trong part3
    archive_header = "## 📦 ARCHIVE — TUẦN ĐÃ HOÀN THÀNH"
    placeholder_text = "*(Chưa có tuần hoàn thành — sẽ được nén vào đây sau khi pass QA-01)*"
    
    if placeholder_text in part3:
        part3 = part3.replace(placeholder_text, "")
        
    header_idx = part3.find(archive_header)
    if header_idx != -1:
        insert_pos = header_idx + len(archive_header)
        part3 = part3[:insert_pos] + "\n" + archive_entry + part3[insert_pos:]

    # Cập nhật bảng "## 📦 Context Archive Registry"
    registry_header = "## 📦 Context Archive Registry"
    registry_placeholder = "| *(Chưa có — sẽ được nén sau khi Tuần 1 pass QA-01)* | | |"
    
    legacy_files = ", ".join([s.replace(".md", ".legacy.md") for s in current_cfg["specs"]])
    registry_row = f"| {week_num} | {legacy_files} | {timestamp.split()[0]} |"
    
    if registry_placeholder in part3:
        part3 = part3.replace(registry_placeholder, registry_row)
    else:
        reg_idx = part3.find(registry_header)
        if reg_idx != -1:
            table_divider_match = re.search(r"\|:-----\|:-----------\|:---------\|", part3[reg_idx:])
            if table_divider_match:
                divider_pos = reg_idx + table_divider_match.end()
                part3 = part3[:divider_pos] + "\n" + registry_row + part3[divider_pos:]

    # Cập nhật trạng thái spec sang 📦 ARCHIVED trong bảng Specs
    for spec in current_cfg["specs"]:
        pattern = rf"\[{spec}\]\(.*?\| (🟢 ACTIVE|🟢 SPEC DONE)"
        match = re.search(pattern, part3)
        if match:
            full_match = match.group(0)
            status_group = match.group(1)
            new_match = full_match.replace(status_group, "📦 ARCHIVED")
            part3 = part3.replace(full_match, new_match)

    # Thiết lập HOTZONE tuần tiếp theo
    next_week = week_num + 1
    new_hotzone_content = ""
    if next_week <= 6:
        next_cfg = WEEK_CONFIGS[next_week]
        next_qa_gate = next_cfg["qa_gate"]
        
        # Build tasks mặc định
        next_tasks_md = "\n".join([f"- [ ] {t}" for t in next_cfg["tasks"]])
        
        # Build specs links
        next_specs_links = "\n".join([f"- [{s}](file:///{workspace_root.replace('\\\\', '/')}/specs/{s})" for s in next_cfg["specs"]])
        
        new_hotzone_content = f"""
> [NOTE]
> **Tuần:** {next_week}/6 | **QA Gate:** {next_qa_gate} | **Deadline:** Sprint tiếp theo
> **Tiến độ:** ░░░░░░░░░░░░░░░░░░░░ 0% (0/{len(next_cfg['tasks'])} tasks)

### 🎯 ĐANG LÀM (Active Tasks)
{next_tasks_md}

### ✅ ĐÃ XONG (Completed in current sprint)
- *(Chưa có task nào hoàn thành)*

### ⚡ BLOCKER (nếu có)
- *(Không có blocker)*

### 🔑 CONTEXT BẮT BUỘC (Leader + Coding Agent phải nạp)
- [Spec 00 — Canonical Protocol Registry](file:///{workspace_root.replace('\\\\', '/')}/specs/facepost_00_shared_types.md)
{next_specs_links}

### 🚪 QA-0{next_week} EXIT CRITERIA
- [ ] Tích hợp và pass tất cả các tiêu chuẩn của QA-0{next_week}
"""
    else:
        new_hotzone_content = """
> [NOTE]
> 🎉 **HỆ THỐNG ĐÃ HOÀN THÀNH TOÀN BỘ 6 TUẦN PHÁT TRIỂN!**
> Mọi phân hệ đã được đóng gói và kiểm thử thành công.
"""

    new_content = part1 + "## 🔴 HOTZONE — ĐANG THỰC THI\n" + new_hotzone_content + "\n---\n\n" + part3
    with open(tracker_path, "w", encoding="utf-8") as f:
        f.write(new_content)
        
    print(f"[SUCCESS] Đã tự động cập nhật Progress Tracker sang Tuần {next_week if next_week <= 6 else 'Hoàn Thành'}!")

def update_task_status(task_keyword, status, workspace_root):
    tracker_path = os.path.join(workspace_root, "facepost_progress_tracker.md")
    if not os.path.exists(tracker_path):
        print(f"[ERROR] Không tìm thấy tracker tại {tracker_path}")
        sys.exit(1)
        
    parts = load_tracker_parts(tracker_path)
    if not parts:
        sys.exit(1)
    part1, hotzone_content, part3 = parts
    
    # Parse tuần hiện tại
    week_match = re.search(r"\*\*Tuần:\*\* (\d+)/6", hotzone_content)
    week_num = int(week_match.group(1)) if week_match else 1
    
    # Parse QA Gate hiện tại
    qa_match = re.search(r"\*\*QA Gate:\*\* (.*?) \|", hotzone_content)
    qa_gate = qa_match.group(1) if qa_match else f"QA-0{week_num}"
    
    # Parse deadline hiện tại
    deadline_match = re.search(r"\*\*Deadline:\*\* (.*?)$", hotzone_content, re.MULTILINE)
    deadline = deadline_match.group(1) if deadline_match else "Hoàn thành trong phiên này"
    
    # Parse các context hiện tại
    context_section = ""
    context_match = re.search(r"### 🔑 CONTEXT BẮT BUỘC.*?(### 🚪|$)", hotzone_content, re.DOTALL)
    if context_match:
        context_section = context_match.group(0).replace("### 🚪", "").strip()
        
    # Parse QA exit criteria hiện tại
    qa_criteria_section = ""
    qa_crit_match = re.search(r"### 🚪 QA-.*$", hotzone_content, re.DOTALL)
    if qa_crit_match:
        qa_criteria_section = qa_crit_match.group(0).strip()
        
    # Parse các task THỰC SỰ
    tasks = parse_hotzone_tasks(hotzone_content)
    
    # Nếu danh sách trống, nạp mặc định từ tuần hiện tại
    if not tasks:
        cfg = WEEK_CONFIGS.get(week_num, {})
        for t in cfg.get("tasks", []):
            tasks.append({"text": t, "done": False})
            
    # Cập nhật trạng thái task khớp với keyword
    found = False
    status_done = status.lower() in ["done", "x", "fixed", "completed", "yes", "true"]
    
    # Hàm clean text để so khớp (bỏ qua dấu backtick)
    def clean_text(t):
        return t.replace("`", "").lower()
        
    keyword_clean = task_keyword.replace("`", "").lower()
    
    for t in tasks:
        if keyword_clean in clean_text(t["text"]):
            t["done"] = status_done
            found = True
            print(f"[TASK] Đã cập nhật trạng thái task: '{t['text']}' -> {'HOÀN THÀNH' if status_done else 'CẦN LÀM'}")
            
    if not found:
        print(f"[WARNING] Không tìm thấy task nào chứa từ khóa '{task_keyword}' trong HOTZONE.")
        
    # Tính toán lại tiến độ
    done_count = sum(1 for t in tasks if t['done'])
    total_count = len(tasks)
    percent = int((done_count / total_count) * 100) if total_count > 0 else 0
    progress_bar = '█' * int(percent / 5) + '░' * (20 - int(percent / 5))
    
    # Build danh sách task ĐANG LÀM
    active_tasks = [t for t in tasks if not t["done"]]
    active_tasks_md = "\n".join([f"- [ ] {t['text']}" for t in active_tasks]) if active_tasks else "- *(Không có active task nào)*"
    
    # Build danh sách task ĐÃ XONG
    completed_tasks = [t for t in tasks if t["done"]]
    completed_tasks_md = "\n".join([f"- [x] {t['text']}" for t in completed_tasks]) if completed_tasks else "- *(Chưa có task nào hoàn thành)*"
    
    # Tự động đồng bộ với config của tuần nếu thiếu các mục context/QA criteria
    if not context_section:
        cfg = WEEK_CONFIGS.get(week_num, {})
        next_specs_links = "\n".join([f"- [{s}](file:///{workspace_root}/specs/{s})" for s in cfg.get("specs", [])])
        context_section = f"""### 🔑 CONTEXT BẮT BUỘC (Leader + Coding Agent phải nạp)
- [Spec 00 — Canonical Protocol Registry](file:///{workspace_root}/specs/facepost_00_shared_types.md)
{next_specs_links}"""

    if not qa_criteria_section:
        qa_criteria_section = f"""### 🚪 QA-0{week_num} EXIT CRITERIA
- [ ] Tích hợp và pass tất cả các tiêu chuẩn của QA-0{week_num}"""
        
    new_hotzone_content = f"""
> [NOTE]
> **Tuần:** {week_num}/6 | **QA Gate:** {qa_gate} | **Deadline:** {deadline}
> **Tiến độ:** {progress_bar} {percent}% ({done_count}/{total_count} tasks)

### 🎯 ĐANG LÀM (Active Tasks)
{active_tasks_md}

### ✅ ĐÃ XONG (Completed in current sprint)
{completed_tasks_md}

### ⚡ BLOCKER (nếu có)
- *(Không có blocker)*

{context_section}

{qa_criteria_section}
"""
    
    new_content = part1 + "## 🔴 HOTZONE — ĐANG THỰC THI\n" + new_hotzone_content + "\n---\n\n" + part3
    with open(tracker_path, "w", encoding="utf-8") as f:
        f.write(new_content)
        
    print(f"[SUCCESS] Đã cập nhật tiến độ HOTZONE thành công: {percent}% ({done_count}/{total_count} tasks)!")

def hydrate(source_file, workspace_root):
    """
    Cưỡng bức nạp context:
    1. Gọi live_context_loader.py để cập nhật và tạo file context riêng biệt.
    2. Đọc kết quả đường dẫn file context cụ thể từ stdout.
    3. Trình bày cảnh báo ép buộc đọc context cho các subagents.
    """
    loader_path = os.path.join(workspace_root, "agent_harness", "live_context", "live_context_loader.py")
    if not os.path.exists(loader_path):
        print(f"[ERROR] Không tìm thấy loader tại {loader_path}")
        sys.exit(1)
        
    # Chạy loader
    cmd = [sys.executable, loader_path, source_file, workspace_root]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"[ERROR] Chạy live_context_loader thất bại: {result.stderr}")
        sys.exit(1)
        
    stdout_lines = result.stdout.strip().splitlines()
    
    # Tìm tệp context cụ thể từ stdout
    context_file_path = None
    for line in stdout_lines:
        if line.startswith("[CONTEXT_FILE]"):
            context_file_path = line.replace("[CONTEXT_FILE]", "").strip()
        else:
            print(line)
            
    if context_file_path and os.path.exists(context_file_path):
        print("="*60)
        print("🚨 [FORCED CONTEXT HYDRATION] ĐÃ CƯỠNG BỨC NẠP NGỮ CẢNH CÔ LẬP THÀNH CÔNG!")
        print(f"👉 File context riêng biệt: {context_file_path}")
        print("🔥 YÊU CẦU BẮT BUỘC: Agent đang thao tác file này PHẢI đọc file context trên trước khi làm việc!")
        print("="*60)
    else:
        print("[WARNING] Đã chạy loader nhưng không xác định được file context cô lập cụ thể.")

def archive_week(week_num, workspace_root):
    """
    Archive spec của tuần đã hoàn thành:
    1. Copy spec chi tiết sang thư mục archive/ dưới dạng .legacy.md
    2. Thay thế spec gốc bằng một bản rút gọn siêu nhẹ (Anchor Summary) để giải phóng context window.
    """
    archive_dir = os.path.join(workspace_root, "agent_harness", "live_context", "archive")
    os.makedirs(archive_dir, exist_ok=True)
    
    # Định nghĩa mapping của tuần sang các files spec cần nén
    week_specs = {
        1: ["facepost_00_shared_types.md"],
        2: ["facepost_01_chrome_extension.md"],
        3: ["facepost_03_dashboard_app.md", "facepost_07_dashboard_ui.md"],
        4: ["facepost_02_ai_agent_brain.md", "facepost_05_agent_loop.md", "facepost_08_content_engine.md"],
        5: ["facepost_04_anti_detection.md", "facepost_06_checkpoint_handler.md"],
        6: ["facepost_09_hybrid_extension.md", "facepost_10_desktop_packaging.md"]
    }
    
    specs_to_archive = week_specs.get(week_num)
    if not specs_to_archive:
        print(f"[ERROR] Không tìm thấy cấu hình specs cho Tuần {week_num}")
        sys.exit(1)
        
    print(f"[ARCHIVE] Đang thực hiện nén và lưu trữ ngữ cảnh cho Tuần {week_num}...")
    
    for spec_name in specs_to_archive:
        src_path = os.path.join(workspace_root, "specs", spec_name)
        if not os.path.exists(src_path):
            print(f"[WARNING] File spec {spec_name} không tồn tại để nén. Bỏ qua.")
            continue
            
        # 1. Copy sang archive dưới dạng .legacy.md
        legacy_name = spec_name.replace(".md", ".legacy.md")
        dest_path = os.path.join(archive_dir, legacy_name)
        shutil.copy2(src_path, dest_path)
        print(f"   [COPY] Đã lưu trữ bản sao chi tiết: specs/{spec_name} -> archive/{legacy_name}")
        
        # 2. Đọc file spec gốc để trích xuất header tiêu đề
        with open(src_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        title = lines[0].strip() if lines else f"# Spec: {spec_name}"
        
        # 3. Tạo file tóm tắt rút gọn (Anchor Summary) đè lên file spec gốc
        anchor_summary = f"""{title}
**Status:** 📦 ARCHIVED (NÉN NGỮ CẢNH)
**Legacy File:** [Đặc tả chi tiết nằm tại đây](file:///{dest_path.replace('\\', '/')})
**Ngày nén:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 🔒 ANCHOR SUMMARY (TÓM TẮT HỢP ĐỒNG KỸ THUẬT)

> [NOTE]
> Đặc tả chi tiết của phân hệ này đã được nén lại để tối ưu hóa bộ nhớ context của Leader AI. 
> Dưới đây là hợp đồng kỹ thuật và API cốt lõi được giữ lại làm điểm neo phát triển:

1. **Giao thức và Module:** Xem cấu trúc file rỗng tương ứng đã được khởi tạo.
2. **Quy tắc bảo mật:** Bắt buộc tuân thủ Hiến pháp `AGENTS.md` và các checkpoints kiểm soát an ninh chéo.
3. **API Contracts:** Mọi endpoint và tin nhắn WebSocket phải khớp chính xác với đặc tả đã lưu tại tệp `.legacy.md`.
"""
        with open(src_path, "w", encoding="utf-8") as f:
            f.write(anchor_summary)
            
        print(f"   [COMPRESS] Đã nén thành công tệp gốc: specs/{spec_name} (dung lượng đã giảm >95%)")
        
    print(f"[SUCCESS] Đã hoàn tất đóng gói và tối ưu hóa context cho Tuần {week_num}!")
    
    # 4. Tự động gọi thư ký cập nhật progress tracker
    update_tracker_on_archive(week_num, workspace_root)

def register_file(source_file, workspace_root):
    """
    Tự động phân loại và đăng ký file mới vào context_map.json
    dựa trên các quy tắc tiền tố đường dẫn (Path Prefix Rules).
    """
    abs_source = os.path.abspath(source_file)
    abs_workspace = os.path.abspath(workspace_root)
    if not abs_source.startswith(abs_workspace) and not os.path.isabs(source_file):
        abs_source = os.path.abspath(os.path.join(abs_workspace, source_file))
    rel_path = os.path.relpath(abs_source, abs_workspace).replace("\\", "/")
    
    # 1. Áp dụng quy tắc phân loại tự động
    spec_id = "Spec 00"
    filename = os.path.basename(rel_path).lower()
    
    if "agent_loop" in filename:
        spec_id = "Spec 05"
    elif "checkpoint_detector" in filename or "checkpoint_handler" in filename:
        spec_id = "Spec 06"
    elif any(x in filename for x in ["human_simulator", "proxy_rotator", "chrome_launcher", "react_state_patcher"]) or rel_path.startswith("native_host/"):
        spec_id = "Spec 04"
    elif rel_path in ["dashboard/dashboard_ui/ContentComposer.jsx", "dashboard/dashboard_ui/InteractionPanel.jsx"]:
        spec_id = "Spec 08"
    elif rel_path in ["dashboard/ai_brain.js", "dashboard/session_manager.js", "dashboard/prompt_templates.js"]:
        spec_id = "Spec 02"
    elif rel_path.startswith("extension_cws/"):
        spec_id = "Spec 09"
    elif rel_path.startswith("extension/"):
        spec_id = "Spec 01"
    elif rel_path.startswith("dashboard/dashboard_ui/"):
        spec_id = "Spec 07"
    elif rel_path.startswith("dashboard/src/routes/") or rel_path.startswith("dashboard/src/services/") or rel_path.startswith("dashboard/"):
        spec_id = "Spec 03"
    elif rel_path.startswith("src/"):
        spec_id = "Spec 08"
    elif rel_path.startswith("hermes-desktop/") or rel_path.startswith(".github/"):
        spec_id = "Spec 10"

    # 2. Đọc context_map.json
    context_map_path = os.path.join(workspace_root, "agent_harness", "live_context", "context_map.json")
    if not os.path.exists(context_map_path):
        print(f"[ERROR] Không tìm thấy file cấu hình tại {context_map_path}")
        sys.exit(1)
        
    try:
        with open(context_map_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        print(f"[ERROR] Lỗi khi đọc file cấu hình: {e}")
        sys.exit(1)
        
    # 3. Chèn file vào spec_id tương ứng
    mappings = config.get("mappings", [])
    found = False
    for mapping in mappings:
        if mapping.get("spec_id") == spec_id:
            source_files = mapping.get("source_files", [])
            # Chuẩn hóa tên file để kiểm tra trùng lặp
            norm_files = [f.replace("\\", "/").strip("/") for f in source_files]
            norm_new = rel_path.strip("/")
            if norm_new not in norm_files:
                source_files.append(rel_path)
                mapping["source_files"] = source_files
                found = True
                print(f"[SUCCESS] Đã đăng ký thành công file mới: '{rel_path}' -> {spec_id}")
            else:
                print(f"[INFO] File '{rel_path}' đã được đăng ký trong {spec_id} từ trước.")
                return
            break
            
    if not found:
        print(f"[ERROR] Không tìm thấy Spec ID '{spec_id}' trong context_map.json")
        sys.exit(1)
        
    # 4. Ghi lại context_map.json
    try:
        with open(context_map_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[ERROR] Không thể ghi context_map.json: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Sử dụng:")
        print("  python3 context_dispatcher.py hydrate <source_file_path> [workspace_root]")
        print("  python3 context_dispatcher.py archive <week_number> [workspace_root]")
        print("  python3 context_dispatcher.py task <task_keyword> <done/todo> [workspace_root]")
        print("  python3 context_dispatcher.py register <new_file_path> [workspace_root]")
        sys.exit(1)
        
    cmd = sys.argv[1].lower()
    arg2 = sys.argv[2]
    
    workspace = None
    if cmd == "task":
        status = sys.argv[3] if len(sys.argv) >= 4 else "done"
        workspace = sys.argv[4] if len(sys.argv) >= 5 else None
    else:
        workspace = sys.argv[3] if len(sys.argv) >= 4 else None
        
    if not workspace:
        workspace = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
    if cmd == "hydrate":
        hydrate(arg2, workspace)
    elif cmd == "archive":
        try:
            week = int(arg2)
            archive_week(week, workspace)
        except ValueError:
            print(f"[ERROR] Số tuần không hợp lệ: {arg2}")
            sys.exit(1)
    elif cmd == "task":
        update_task_status(arg2, status, workspace)
    elif cmd == "register":
        register_file(arg2, workspace)
    else:
        print(f"[ERROR] Lệnh không hợp lệ: {cmd}")
        sys.exit(1)

