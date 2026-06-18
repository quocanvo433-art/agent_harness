# -*- coding: utf-8 -*-
"""
Live Context Loader for AI Facepostgroup System
Cross-platform (Windows & Linux compatible) Python loader
"""

import os
import sys
import json
from datetime import datetime

def load_context(source_file_path, workspace_root=None):
    # If workspace_root is not provided, calculate it relative to this script's directory.
    # Script is at AI_facepostgroup/agent_harness/live_context/live_context_loader.py
    if not workspace_root:
        workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Define paths
    context_map_path = os.path.join(workspace_root, "agent_harness", "live_context", "context_map.json")
    live_context_path = os.path.join(workspace_root, "agent_harness", "live_context", "live_context.md")
    
    # Convert workspace root to absolute path
    abs_workspace = os.path.abspath(workspace_root)
    
    # Determine the absolute path of source file
    abs_source = os.path.abspath(source_file_path)
    if not abs_source.startswith(abs_workspace) and not os.path.isabs(source_file_path):
        abs_source = os.path.abspath(os.path.join(abs_workspace, source_file_path))
        
    # Calculate the normalized relative path for the source file (always use /)
    rel_source_path = os.path.relpath(abs_source, abs_workspace).replace("\\", "/")
    
    # 1. Read context_map.json configuration
    if not os.path.exists(context_map_path):
        print(f"[ERROR] Không tìm thấy file cấu hình tại {context_map_path}")
        sys.exit(1)
        
    try:
        with open(context_map_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        print(f"[ERROR] Lỗi khi đọc file cấu hình: {e}")
        sys.exit(1)
        
    specs_dir = config.get("specs_dir", "specs/")
    mappings = config.get("mappings", [])
    
    # 2. Search for the corresponding spec mapping
    matched_mapping = None
    for mapping in mappings:
        for source_pattern in mapping.get("source_files", []):
            # Normalization of pattern just in case
            norm_pattern = source_pattern.replace("\\", "/")
            if norm_pattern == rel_source_path or norm_pattern in rel_source_path or rel_source_path in norm_pattern:
                matched_mapping = mapping
                break
        if matched_mapping:
            break
            
    if not matched_mapping:
        print(f"[WARNING] Không tìm thấy ánh xạ spec cho file: {rel_source_path}. Sử dụng Spec 00 mặc định.")
        matched_mapping = {
            "spec_id": "Spec 00",
            "spec_file": "facepost_00_shared_types.md"
        }
        
    spec_id = matched_mapping["spec_id"]
    spec_file_name = matched_mapping["spec_file"]
    spec_full_path = os.path.join(abs_workspace, specs_dir, spec_file_name)
    
    # 3. Read matched spec content
    spec_content = ""
    if os.path.exists(spec_full_path):
        try:
            with open(spec_full_path, "r", encoding="utf-8") as f:
                spec_content = f.read()
        except Exception as e:
            spec_content = f"⚠️ [LỖI] Không thể đọc nội dung file đặc tả: {e}"
    else:
        spec_content = f"⚠️ [CẢNH BÁO] File đặc tả {spec_file_name} chưa được khởi tạo trên thực tế."

    # 4. Generate the template content for live_context.md
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Normalize path formatting for the Markdown link url
    spec_url_path = os.path.abspath(spec_full_path).replace("\\", "/")
    
    live_markdown = f"""# 📖 LIVE CONTEXT - NGỮ CẢNH PHIÊN LÀM VIỆC DỰ ÁN

> ⚡ **CẢNH BÁO CHO AI AGENT:** File này được sinh tự động bởi `live_context_loader.py`. Đọc kỹ và tuân thủ các neo kiến trúc dưới đây.
> **Thời gian cập nhật:** {timestamp}
> **File đang thao tác:** `{rel_source_path}`
> **Tài liệu neo tương ứng:** [{spec_id} - {spec_file_name}](file://{spec_url_path})

---

## I. MỤC TIÊU THIẾT KẾ CỦA PHÂN HỆ VÀ SPEC CHỦ ĐẠO

{spec_content}

---

## II. NGUYÊN TẮC VẬN HÀNH BẮT BUỘC TRONG PHIÊN
1. Phải tham chiếu chính xác các hàm và biến được mô tả trong tài liệu Spec này.
2. Không tự ý thay đổi giao thức truyền tin (ví dụ: đổi schema websocket) mà không cập nhật tài liệu thiết kế.
3. Chú ý các nguyên tắc tối ưu hóa SQLite (WAL mode) khi thay đổi logic DB.
"""

    # 5. Overwrite live_context.md
    try:
        os.makedirs(os.path.dirname(live_context_path), exist_ok=True)
        with open(live_context_path, "w", encoding="utf-8") as f:
            f.write(live_markdown)
        print(f"[SUCCESS] Đã nạp thành công ngữ cảnh của [{spec_id}] vào live_context.md")
    except Exception as e:
        print(f"[ERROR] Lỗi khi ghi file live_context.md: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Sử dụng: python live_context_loader.py <source_file_path> [workspace_root]")
        sys.exit(1)
        
    source_file = sys.argv[1]
    workspace = sys.argv[2] if len(sys.argv) >= 3 else None
    
    load_context(source_file, workspace)
