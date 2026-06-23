# -*- coding: utf-8 -*-
"""
Live Context Loader for AI Facepostgroup System
Cross-platform (Windows & Linux compatible) Python loader
"""

import os
import sys
import json
import re
import tempfile
import ast
from datetime import datetime

def read_file_safe(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"⚠️ [LỖI] Không thể đọc nội dung: {e}"

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

def get_python_dependencies(content, dir_path, abs_workspace):
    dependencies = []
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    parts = alias.name.split('.')
                    # Try resolving relative to dir_path
                    test_path_module = os.path.join(dir_path, *parts) + ".py"
                    if os.path.exists(test_path_module) and os.path.isfile(test_path_module):
                        rel = os.path.relpath(test_path_module, abs_workspace).replace("\\", "/")
                        dependencies.append(rel)
                    else:
                        test_path_pkg = os.path.join(dir_path, parts[0] + ".py")
                        if os.path.exists(test_path_pkg) and os.path.isfile(test_path_pkg):
                            rel = os.path.relpath(test_path_pkg, abs_workspace).replace("\\", "/")
                            dependencies.append(rel)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    parts = node.module.split('.')
                    if node.level > 0:
                        # relative import, e.g. from .utils import database
                        target_dir = dir_path
                        for _ in range(node.level - 1):
                            target_dir = os.path.dirname(target_dir)
                        test_path_mod = os.path.join(target_dir, *parts) + ".py"
                        if os.path.exists(test_path_mod) and os.path.isfile(test_path_mod):
                            rel = os.path.relpath(test_path_mod, abs_workspace).replace("\\", "/")
                            dependencies.append(rel)
                    else:
                        # absolute import
                        test_path_mod = os.path.join(dir_path, *parts) + ".py"
                        if os.path.exists(test_path_mod) and os.path.isfile(test_path_mod):
                            rel = os.path.relpath(test_path_mod, abs_workspace).replace("\\", "/")
                            dependencies.append(rel)
                else:
                    # from . import name
                    if node.level > 0:
                        target_dir = dir_path
                        for _ in range(node.level - 1):
                            target_dir = os.path.dirname(target_dir)
                        for alias in node.names:
                            test_path_name = os.path.join(target_dir, alias.name + ".py")
                            if os.path.exists(test_path_name) and os.path.isfile(test_path_name):
                                rel = os.path.relpath(test_path_name, abs_workspace).replace("\\", "/")
                                dependencies.append(rel)
    except Exception as e:
        print(f"[WARNING] AST parse failed for Python file: {e}")
    return dependencies

def get_file_dependencies(source_file_path, abs_workspace):
    """
    Quét mã nguồn thô của file để tìm các tệp tin phụ thuộc (dependencies) được import/require.
    """
    dependencies = []
    if not os.path.exists(source_file_path):
        return dependencies
        
    try:
        with open(source_file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            
        ext = os.path.splitext(source_file_path)[1].lower()
        dir_path = os.path.dirname(source_file_path)
        
        # 1. Quét JS/TS/JSX
        if ext in [".js", ".jsx", ".ts", ".tsx"]:
            # Remove comments to avoid false matches in comments
            content_no_comments = re.sub(r"/\*.*?\*/|//.*?$", "", content, flags=re.MULTILINE | re.DOTALL)
            pattern_require = r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)"
            pattern_import = r"from\s*['\"]([^'\"]+)['\"]"
            
            paths = re.findall(pattern_require, content_no_comments) + re.findall(pattern_import, content_no_comments)
            
            for p in paths:
                if p.startswith("."):
                    dep_abs = os.path.abspath(os.path.join(dir_path, p))
                    possible_paths = [
                        dep_abs,
                        dep_abs + ".js",
                        dep_abs + ".jsx",
                        dep_abs + ".ts",
                        dep_abs + ".tsx",
                        os.path.join(dep_abs, "index.js"),
                        os.path.join(dep_abs, "index.jsx")
                    ]
                    for test_path in possible_paths:
                        if os.path.exists(test_path) and os.path.isfile(test_path):
                            rel = os.path.relpath(test_path, abs_workspace).replace("\\", "/")
                            dependencies.append(rel)
                            break
                            
        # 2. Quét Python
        elif ext == ".py":
            dependencies = get_python_dependencies(content, dir_path, abs_workspace)
    except Exception as e:
        print(f"[WARNING] Không thể phân tích dependency cho {source_file_path}: {e}")
        
    return list(set(dependencies))

def find_spec_for_file(rel_path, mappings):
    norm_source = rel_path.replace("\\", "/").strip("/")
    for mapping in mappings:
        for source_pattern in mapping.get("source_files", []):
            norm_pattern = source_pattern.replace("\\", "/").strip("/")
            if norm_pattern == norm_source:
                return mapping
    return None

def load_context(source_file_path, workspace_root=None):
    if not workspace_root:
        workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    abs_workspace = os.path.abspath(workspace_root)
    abs_source = os.path.abspath(source_file_path)
    if not abs_source.startswith(abs_workspace) and not os.path.isabs(source_file_path):
        abs_source = os.path.abspath(os.path.join(abs_workspace, source_file_path))
    
    # Security Guard: Path Traversal Check
    if not abs_source.startswith(abs_workspace):
        print(f"[ERROR] Đường dẫn file '{source_file_path}' nằm ngoài ranh giới workspace cho phép.")
        sys.exit(1)
        
    # Input Validation: Is it a valid file?
    if not os.path.isfile(abs_source):
        print(f"[ERROR] Đường dẫn '{source_file_path}' không phải là một tệp tin hợp lệ hoặc không tồn tại.")
        sys.exit(1)
        
    rel_source_path = os.path.relpath(abs_source, abs_workspace).replace("\\", "/")
    
    sanitized_filename = rel_source_path.replace("/", "_").replace("\\", "_").replace(".", "_") + ".context.md"
    live_context_path = os.path.join(workspace_root, "agent_harness", "live_context", "cache", sanitized_filename)
    
    # 1. Read context_map.json configuration
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
        
    specs_dir = config.get("specs_dir", "specs/")
    mappings = config.get("mappings", [])
    
    # 2. Search for the corresponding main spec mapping
    main_mapping = find_spec_for_file(rel_source_path, mappings)
    if not main_mapping:
        print(f"[WARNING] Không tìm thấy ánh xạ spec cho file: {rel_source_path}. Sử dụng Spec 00 mặc định.")
        main_mapping = {
            "spec_id": "Spec 00",
            "spec_file": "facepost_00_shared_types.md"
        }
        
    # 3. Dynamic Dependency Spec Resolution with Deduplication
    dep_specs = []
    seen_spec_ids = set([main_mapping["spec_id"], "Spec 00"])
    dep_files = get_file_dependencies(abs_source, abs_workspace)
    for dep_file in dep_files:
        mapping = find_spec_for_file(dep_file, mappings)
        if mapping:
            s_id = mapping.get("spec_id")
            if s_id and s_id not in seen_spec_ids:
                seen_spec_ids.add(s_id)
                dep_specs.append(mapping)
            
    # 4. Aggregate spec contents (Full Spec Hydration)
    spec_sections = []
    
    # - Nạp Spec 00 (Hiến pháp shared types)
    spec_00_path = os.path.join(abs_workspace, specs_dir, "facepost_00_shared_types.md")
    if os.path.exists(spec_00_path):
        spec_sections.append(f"### 🌐 [SHARED TYPES CONSTITUTION] Spec 00 - facepost_00_shared_types.md\n\n" + read_file_safe(spec_00_path))
        
    # - Nạp Spec chính
    if main_mapping["spec_id"] != "Spec 00":
        main_spec_path = os.path.join(abs_workspace, specs_dir, main_mapping["spec_file"])
        spec_sections.append(f"### 🎯 [PRIMARY MODULE SPEC] {main_mapping['spec_id']} - {main_mapping['spec_file']}\n\n" + read_file_safe(main_spec_path))
        
    # - Nạp Spec của các file dependencies liên đới (đã lọc trùng)
    for dep in dep_specs:
        dep_path = os.path.join(abs_workspace, specs_dir, dep["spec_file"])
        if os.path.exists(dep_path):
            spec_sections.append(f"### 🔗 [DEPENDENCY MODULE SPEC] {dep['spec_id']} - {dep['spec_file']}\n\n" + read_file_safe(dep_path))
            
    aggregated_specs = "\n\n---\n\n".join(spec_sections)
    
    # 5. Generate template content
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    main_spec_url = os.path.abspath(os.path.join(abs_workspace, specs_dir, main_mapping["spec_file"])).replace("\\", "/")
    
    live_markdown = f"""# 📖 LIVE CONTEXT - NGỮ CẢNH PHIÊN LÀM VIỆC DỰ ÁN (APEX Swarm v3.0)

> ⚡ **CẢNH BÁO CHO AI AGENT (ANTIGRAVITY 2.0 NATIVE):** File này được sinh tự động bởi `live_context_loader.py`.
> **Thời gian cập nhật:** {timestamp}
> **File đang thao tác:** `{rel_source_path}`
> **Tài liệu đặc tả chính:** [{main_mapping["spec_id"]} - {main_mapping["spec_file"]}](file:///{main_spec_url})
> **Năng lực vận hành:** Kiến trúc Swarm phi trạng thái tận dụng cửa sổ ngữ cảnh cực đại để nạp Specs đầy đủ (Full Spec Hydration), triệt tiêu hoàn toàn lỗi lệch giao thức/thiếu kiểu.

---

## I. TỔNG HỢP CÁC ĐẶC TẢ KỸ THUẬT VÀ HỢP ĐỒNG LIÊN QUAN

{aggregated_specs}

---

## II. NGUYÊN TẮC VẬN HÀNH BẮT BUỘC TRONG PHIÊN
1. Phải tham chiếu chính xác các hàm và biến được mô tả trong các tài liệu Spec trên.
2. Không tự ý thay đổi giao thức truyền tin (ví dụ: đổi schema websocket) mà không cập nhật tài liệu thiết kế.
3. Chú ý các nguyên tắc tối ưu hóa SQLite (WAL mode) khi thay đổi logic DB.
"""

    # 6. Overwrite the specific cache context file atomically
    try:
        write_file_atomic(live_context_path, live_markdown, encoding="utf-8")
        print(f"[SUCCESS] Đã nạp thành công ngữ cảnh liên đới đa chiều vào cache file.")
        print(f"[CONTEXT_FILE] {os.path.abspath(live_context_path)}")
    except Exception as e:
        print(f"[ERROR] Lỗi khi ghi file context: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Sử dụng: python live_context_loader.py <source_file_path> [workspace_root]")
        sys.exit(1)
        
    source_file = sys.argv[1]
    workspace = sys.argv[2] if len(sys.argv) >= 3 else None
    
    load_context(source_file, workspace)
