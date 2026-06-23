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
import tempfile
from datetime import datetime

# Import load_context directly from live_context_loader
from live_context_loader import load_context

def get_week_configs(workspace_root):
    config_path = os.path.join(workspace_root, "agent_harness", "live_context", "sprint_schedule.json")
    if not os.path.exists(config_path):
        print(f"[WARNING] Không tìm thấy file cấu hình tuần tại {config_path}. Trả về cấu hình rỗng.")
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # JSON keys are strings, convert them back to integers
            return {int(k): v for k, v in data.items()}
    except Exception as e:
        print(f"[WARNING] Lỗi khi đọc file cấu hình tuần: {e}")
        return {}

def write_file_atomic(file_path, content, encoding="utf-8"):
    dir_name = os.path.dirname(file_path)
    os.makedirs(dir_name, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=dir_name, encoding=encoding, delete=False) as tf:
        tf.write(content)
        temp_name = tf.name
    try:
        os.replace(temp_name, file_path)
    except Exception as e:
        if os.path.exists(temp_name):
            os.remove(temp_name)
        raise e

def load_tracker_parts(tracker_path):
    try:
        with open(tracker_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        hotzone_pattern = r"##\s*🔴\s*HOTZONE"
        archive_pattern = r"##\s*📦\s*ARCHIVE"
        
        parts = re.split(hotzone_pattern, content, flags=re.IGNORECASE)
        if len(parts) < 2:
            print("[ERROR] Không tìm thấy marker HOTZONE trong tracker.")
            return None
        
        part1 = parts[0]
        rest = parts[1]
        
        parts2 = re.split(archive_pattern, rest, flags=re.IGNORECASE)
        if len(parts2) < 2:
            print("[ERROR] Không tìm thấy marker ARCHIVE trong tracker.")
            return None
        
        hotzone_content = parts2[0]
        part3 = "## 📦 ARCHIVE\n" + parts2[1]
        
        return part1, hotzone_content, part3
    except Exception as e:
        print(f"[ERROR] Lỗi khi xử lý cấu trúc tracker: {e}")
        return None

def parse_hotzone_tasks(hotzone_content):
    tasks = []
    in_task_section = False
    
    for line in hotzone_content.splitlines():
        line_strip = line.strip()
        
        if "### 🎯 ĐANG LÀM" in line_strip or "### ✅ ĐÃ XONG" in line_strip:
            in_task_section = True
            continue
        elif "### ⚡ BLOCKER" in line_strip or "### 🔑 CONTEXT" in line_strip or "### 🚪 QA-" in line_strip or line_strip.startswith("> **KHI PASS QA-"):
            in_task_section = False
            continue
            
        if in_task_section and (line_strip.startswith("- [ ]") or line_strip.startswith("- [x]")):
            done = line_strip.startswith("- [x]")
            task_text = line_strip[5:].strip()
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
    
    week_configs = get_week_configs(workspace_root)
    
    current_tasks = parse_hotzone_tasks(hotzone_content)
    if not current_tasks:
        cfg = week_configs.get(week_num, {})
        for t in cfg.get("tasks", []):
            current_tasks.append({"text": t, "done": True})
            
    done_count = sum(1 for t in current_tasks if t['done'])
    total_count = len(current_tasks) if current_tasks else 1
    
    current_cfg = week_configs.get(week_num, {"title": f"Tuần {week_num}", "specs": []})
    week_title = current_cfg["title"]
    specs_links = ", ".join([f"[{s}](file:///{workspace_root.replace('\\\\', '/')}/specs/{s})" for s in current_cfg["specs"]])
    
    tasks_md = "\n".join([f"   - [x] {t['text']}" for t in current_tasks])
    
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

    archive_header = "## 📦 ARCHIVE — TUẦN ĐÃ HOÀN THÀNH"
    placeholder_text = "*(Chưa có tuần hoàn thành — sẽ được nén vào đây sau khi pass QA-01)*"
    
    if placeholder_text in part3:
        part3 = part3.replace(placeholder_text, "")
        
    header_idx = part3.find(archive_header)
    # Sửa lỗi logic: Fallback tìm kiếm tiêu đề chuẩn nếu tiêu đề chi tiết không khớp
    if header_idx == -1:
        archive_header = "## 📦 ARCHIVE"
        header_idx = part3.find(archive_header)
        
    if header_idx != -1:
        insert_pos = header_idx + len(archive_header)
        part3 = part3[:insert_pos] + "\n" + archive_entry + part3[insert_pos:]

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

    for spec in current_cfg["specs"]:
        pattern = rf"\[{spec}\]\(.*?\| (🟢 ACTIVE|🟢 SPEC DONE)"
        match = re.search(pattern, part3)
        if match:
            full_match = match.group(0)
            status_group = match.group(1)
            new_match = full_match.replace(status_group, "📦 ARCHIVED")
            part3 = part3.replace(full_match, new_match)

    next_week = week_num + 1
    new_hotzone_content = ""
    if next_week <= 6:
        next_cfg = week_configs[next_week]
        next_qa_gate = next_cfg["qa_gate"]
        
        next_tasks_md = "\n".join([f"- [ ] {t}" for t in next_cfg["tasks"]])
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
    try:
        write_file_atomic(tracker_path, new_content, encoding="utf-8")
        print(f"[SUCCESS] Đã tự động cập nhật Progress Tracker sang Tuần {next_week if next_week <= 6 else 'Hoàn Thành'}!")
    except Exception as e:
        print(f"[ERROR] Không thể cập nhật Progress Tracker: {e}")

def update_task_status(task_keyword, status, workspace_root):
    tracker_path = os.path.join(workspace_root, "facepost_progress_tracker.md")
    if not os.path.exists(tracker_path):
        print(f"[ERROR] Không tìm thấy tracker tại {tracker_path}")
        sys.exit(1)
        
    try:
        with open(tracker_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"[ERROR] Lỗi khi đọc tracker: {e}")
        sys.exit(1)
        
    # Regex chia tracker lấy nguyên block HOTZONE để sửa đổi cục bộ
    hotzone_pattern = r"(##\s*🔴\s*HOTZONE[\s\S]*?)(##\s*📦\s*ARCHIVE|$)"
    match = re.search(hotzone_pattern, content, flags=re.IGNORECASE)
    if not match:
        print("[ERROR] Không tìm thấy vùng HOTZONE trong tracker.")
        sys.exit(1)
        
    hotzone_full = match.group(1)
    start_idx = match.start(1)
    end_idx = match.end(1)
    
    # Cập nhật trạng thái task trong hotzone_full
    status_done = status.lower() in ["done", "x", "fixed", "completed", "yes", "true"]
    new_checkbox = "- [x]" if status_done else "- [ ]"
    
    lines = hotzone_full.splitlines()
    found = False
    
    def clean_text(t):
        return t.replace("`", "").lower()
        
    keyword_clean = task_keyword.replace("`", "").lower()
    
    for i, line in enumerate(lines):
        if line.strip().startswith("- [ ]") or line.strip().startswith("- [x]"):
            task_part = line.split("]", 1)[1].strip()
            if keyword_clean in clean_text(task_part):
                lines[i] = re.sub(r"-\s*\[\s*[ xX]?\s*\]", new_checkbox, line, count=1)
                found = True
                print(f"[TASK] Đã cập nhật trạng thái task: '{task_part}' -> {'HOÀN THÀNH' if status_done else 'CẦN LÀM'}")
                
                # Tự động đăng ký file mới vào context_map khi task hoàn thành (nhập động)
                if status_done:
                    file_candidates = re.findall(r"[\w\-./]+\.(?:js|jsx|py|html|css|sql|yml|json|md)", task_part)
                    for fc in file_candidates:
                         fc_clean = fc.strip("`'\"()[]*")
                         full_path = os.path.join(workspace_root, fc_clean)
                         if os.path.exists(full_path) and os.path.isfile(full_path):
                             print(f"[AUTO-REGISTER] Tự động phát hiện file mới từ task: {fc_clean}")
                             register_file(full_path, workspace_root)
                break
                
    if not found:
        print(f"[WARNING] Không tìm thấy task nào chứa từ khóa '{task_keyword}' trong HOTZONE.")
        return
        
    # Tính toán lại tiến độ và cập nhật Progress Bar trong hotzone_full
    updated_tasks = []
    for line in lines:
        if line.strip().startswith("- [ ]") or line.strip().startswith("- [x]"):
            done = line.strip().startswith("- [x]")
            updated_tasks.append(done)
            
    if updated_tasks:
        done_count = sum(1 for d in updated_tasks if d)
        total_count = len(updated_tasks)
        percent = int((done_count / total_count) * 100)
        progress_bar = '█' * int(percent / 5) + '░' * (20 - int(percent / 5))
        
        for i, line in enumerate(lines):
            if "**Tiến độ:**" in line:
                lines[i] = f"> **Tiến độ:** {progress_bar} {percent}% ({done_count}/{total_count} tasks)"
                break
                
    new_hotzone = "\n".join(lines) + "\n"
    updated_content = content[:start_idx] + new_hotzone + content[end_idx:]
    
    try:
        write_file_atomic(tracker_path, updated_content, encoding="utf-8")
        print(f"[SUCCESS] Đã cập nhật tiến độ HOTZONE nguyên tử thành công!")
    except Exception as e:
        print(f"[ERROR] Không thể cập nhật tracker: {e}")
        sys.exit(1)

def hydrate(source_file, workspace_root):
    """
    Cưỡng bức nạp context bằng hàm load_context trực tiếp
    """
    try:
        load_context(source_file, workspace_root)
    except Exception as e:
        print(f"[ERROR] Chạy live_context_loader thất bại: {e}")
        sys.exit(1)

def archive_week(week_num, workspace_root):
    """
    Archive spec của tuần đã hoàn thành:
    1. Copy spec chi tiết sang thư mục archive/ dưới dạng .legacy.md
    2. Thay thế spec gốc bằng một bản rút gọn siêu nhẹ (Anchor Summary) để giải phóng context window.
    """
    archive_dir = os.path.join(workspace_root, "agent_harness", "live_context", "archive")
    os.makedirs(archive_dir, exist_ok=True)
    
    week_configs = get_week_configs(workspace_root)
    specs_to_archive = week_configs.get(week_num, {}).get("specs")
    
    if not specs_to_archive:
        print(f"[ERROR] Không tìm thấy cấu hình specs cho Tuần {week_num}")
        sys.exit(1)
        
    print(f"[ARCHIVE] Đang thực hiện nén và lưu trữ ngữ cảnh cho Tuần {week_num}...")
    
    for spec_name in specs_to_archive:
        src_path = os.path.join(workspace_root, "specs", spec_name)
        if not os.path.exists(src_path):
            print(f"[WARNING] File spec {spec_name} không tồn tại để nén. Bỏ qua.")
            continue
            
        # Kiểm tra xem file spec gốc đã ở trạng thái archive (bị nén) chưa để tránh ghi đè phá hủy dữ liệu gốc
        with open(src_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        if "Status:** 📦 ARCHIVED" in content or "Status: 📦 ARCHIVED" in content:
            print(f"[WARNING] File đặc tả {spec_name} đã được nén/lưu trữ từ trước. Bỏ qua để tránh mất dữ liệu.")
            continue
            
        # 1. Copy sang archive dưới dạng .legacy.md
        legacy_name = spec_name.replace(".md", ".legacy.md")
        dest_path = os.path.join(archive_dir, legacy_name)
        shutil.copy2(src_path, dest_path)
        print(f"   [COPY] Đã lưu trữ bản sao chi tiết: specs/{spec_name} -> archive/{legacy_name}")
        
        # 2. Lấy tiêu đề gốc
        lines = content.splitlines()
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
        try:
            write_file_atomic(src_path, anchor_summary, encoding="utf-8")
            print(f"   [COMPRESS] Đã nén thành công tệp gốc: specs/{spec_name} (dung lượng đã giảm >95%)")
        except Exception as e:
            print(f"[ERROR] Lỗi khi ghi đè file spec {spec_name}: {e}")
            sys.exit(1)
        
    print(f"[SUCCESS] Đã hoàn tất đóng gói và tối ưu hóa context cho Tuần {week_num}!")
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
        
    # 3. Chèn file vào spec_id tương ứng sau khi kiểm tra không bị map trùng chéo ở spec khác
    mappings = config.get("mappings", [])
    
    # Kiểm tra xem file đã được map chéo ở spec nào khác chưa
    for m in mappings:
        if m.get("spec_id") != spec_id:
            norm_files = [f.replace("\\", "/").strip("/") for f in m.get("source_files", [])]
            if rel_path.strip("/") in norm_files:
                print(f"[WARNING] File '{rel_path}' đã được map chéo ở spec '{m.get('spec_id')}'. Bỏ qua để tránh duplicate.")
                return

    found = False
    for mapping in mappings:
        if mapping.get("spec_id") == spec_id:
            source_files = mapping.get("source_files", [])
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
        
    # 4. Ghi lại context_map.json nguyên tử
    try:
        write_file_atomic(context_map_path, json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
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
        
    # Thêm đường dẫn workspace/agent_harness/live_context vào PATH để load context_loader.py khi chạy script
    sys.path.append(os.path.join(workspace, "agent_harness", "live_context"))
    
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
