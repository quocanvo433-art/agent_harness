# HỆ THỐNG NẠP NGỮ CẢNH ĐỘNG (LIVE CONTEXT SYSTEM)
## TÀI LIỆU THIẾT KẾ HỆ THỐNG

> **Trạng thái hệ thống:** THIẾT KẾ - CHƯA TRIỂN KHAI
> **Mục tiêu:** Tự động hóa quá trình đồng bộ và làm mới ngữ cảnh đặc tả kỹ thuật (Spec) cho AI Coding Agent dựa trên file mã nguồn đang thao tác, ngăn ngừa hiện tượng trôi/lệch context trong các phiên làm việc dài.

---

## 1. TRIẾT LÝ VÀ CƠ CHẾ HOẠT ĐỘNG

Khi thực hiện các tác vụ lập trình phức tạp, các AI Coding Agent thường gặp phải hai vấn đề lớn:
1. **Lệch Ngữ Cảnh (Context Drift)**: AI cố gắng sửa đổi một file dựa trên các hiểu biết chung chung, không đúng với tài liệu đặc tả (Spec) ban đầu của hệ thống.
2. **Tràn Cửa Sổ Ngữ Cảnh (Context Window Bloat)**: Việc nhồi nhét tất cả 10 file Specs vào prompt khiến AI bị quá tải thông tin, giảm khả năng suy luận chính xác và tăng chi phí token.

**Live Context System** giải quyết bài toán này bằng cơ chế **"Nạp Đúng Lúc - Đọc Đúng File" (Just-In-Time Context)**:
- Trước khi AI thực hiện chỉnh sửa bất kỳ file mã nguồn nào, một công cụ tự động (`live_context_loader.py`) sẽ được gọi.
- Công cụ này quét qua sơ đồ ánh xạ cấu hình (`context_map.json`) để xác định file code này thuộc phân hệ nào và tương ứng với tài liệu đặc tả (Spec) nào.
- Sau đó, nó tổng hợp thông tin và ghi đè một tệp tin duy nhất là `live_context.md`.
- AI Coding Agent bắt buộc phải đọc file `live_context.md` này để tự cập nhật tri thức trước khi đưa ra đề xuất thay đổi mã nguồn.

---

## 2. ĐỊNH NGHĨA JSON SCHEMA CHO `context_map.json`

File `context_map.json` đóng vai trò là bảng tra cứu chính. Dưới đây là JSON Schema định nghĩa cấu trúc của tệp cấu hình này:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ContextMap",
  "description": "Bản đồ ánh xạ các file mã nguồn sang tài liệu đặc tả tương ứng trong dự án AI Facepostgroup",
  "type": "object",
  "required": ["project_name", "specs_dir", "mappings"],
  "properties": {
    "project_name": {
      "type": "string",
      "description": "Tên dự án"
    },
    "specs_dir": {
      "type": "string",
      "description": "Thư mục chứa các tài liệu đặc tả (relative path)"
    },
    "mappings": {
      "type": "array",
      "description": "Danh sách các liên kết ánh xạ",
      "items": {
        "type": "object",
        "required": ["spec_id", "spec_file", "source_files"],
        "properties": {
          "spec_id": {
            "type": "string",
            "pattern": "^Spec [0-9]{2}$",
            "description": "Mã số của tài liệu đặc tả (VD: Spec 01)"
          },
          "spec_file": {
            "type": "string",
            "description": "Tên file tài liệu đặc tả (VD: spec_01_persona_management.md)"
          },
          "source_files": {
            "type": "array",
            "description": "Danh sách các file mã nguồn thuộc phạm vi của spec này",
            "items": {
              "type": "string",
              "description": "Đường dẫn tương đối tới file code"
            }
          }
        }
      }
    }
  }
}
```

### Ví dụ cấu hình thực tế của `context_map.json`:
```json
{
  "project_name": "AI_facepostgroup",
  "specs_dir": "docs/",
  "mappings": [
    {
      "spec_id": "Spec 01",
      "spec_file": "spec_01_persona_management.md",
      "source_files": [
        "persona_store.js",
        "persona_agent.js"
      ]
    },
    {
      "spec_id": "Spec 02",
      "spec_file": "spec_02_chrome_extension_mv3.md",
      "source_files": [
        "extension/background.js",
        "extension/content.js",
        "extension/popup.js"
      ]
    },
    {
      "spec_id": "Spec 04",
      "spec_file": "spec_04_websocket_api_server.md",
      "source_files": [
        "wsServer.js",
        "app.js"
      ]
    },
    {
      "spec_id": "Spec 06",
      "spec_file": "spec_06_comment_reply_agent.md",
      "source_files": [
        "comment_reply_agent.js",
        "comment_analyzer.js"
      ]
    }
  ]
}
```

---

## 3. CẤU TRÚC MẪU CỦA FILE `live_context.md`

Tệp `live_context.md` sẽ bị ghi đè hoàn toàn mỗi khi chạy loader. Cấu trúc chuẩn hóa của nó như sau:

```markdown
# 📖 LIVE CONTEXT - NGỮ CẢNH PHIÊN LÀM VIỆC DỰ ÁN

> ⚡ **CẢNH BÁO CHO AI AGENT:** File này được sinh tự động. Đọc kỹ và tuân thủ các neo kiến trúc dưới đây. Không tự ý chỉnh sửa file này.
> **Thời gian cập nhật:** {{TIMESTAMP}}
> **File đang thao tác:** `{{SOURCE_FILE}}`
> **Tài liệu neo tương ứng:** [{{SPEC_ID}} - {{SPEC_NAME}}]({{SPEC_FILE_PATH}})

---

## I. MỤC TIÊU THIẾT KẾ CỦA PHÂN HỆ VÀ SPEC CHỦ ĐẠO
{{NOI_DUNG_SPEC_TRICH_XUAT}}

---

## II. CÁC NGUYÊN TẮC CỐT LÕI CỦA SPEC NÀY
1. **Nguyên tắc 1:** ...
2. **Nguyên tắc 2:** ...

---

## III. CAM KẾT SỬ DỤNG CODE
- Tuyệt đối không viết code phá vỡ các giả định trong Spec này.
- Mọi hàm mới sinh ra phải được ghi chú và đối chiếu với thiết kế chung.
```

---

## 4. MÃ NGUỒN GIẢ LẬP (PSEUDOCODE) CỦA CÔNG CỤ `live_context_loader.py`

Công cụ này được thiết kế để chạy trên môi trường **Windows** (hoặc Linux), tự động tra cứu cấu hình và tổng hợp tệp `live_context.md`.

```python
# -*- coding: utf-8 -*-
"""
Live Context Loader for AI Facepostgroup System
Trạng thái: Thiết kế giả lập (Windows Compatible)
"""

import os
import sys
import json
from datetime import datetime

def load_context(source_file_path, workspace_root):
    # Định nghĩa các đường dẫn tệp tin
    context_map_path = os.path.join(workspace_root, "agent_harness", "live_context", "context_map.json")
    live_context_path = os.path.join(workspace_root, "agent_harness", "live_context", "live_context.md")
    
    # Chuẩn hóa đường dẫn file code đầu vào sang dạng relative path
    rel_source_path = os.path.relpath(source_file_path, workspace_root).replace("\\", "/")
    
    # 1. Đọc file cấu hình context_map.json
    if not os.path.exists(context_map_path):
        print(f"[ERROR] Không tìm thấy file cấu hình tại {context_map_path}")
        sys.exit(1)
        
    with open(context_map_path, "r", encoding="utf-8") as f:
        config = json.load(f)
        
    specs_dir = config.get("specs_dir", "docs/")
    mappings = config.get("mappings", [])
    
    # 2. Tìm kiếm spec tương ứng với file code
    matched_mapping = None
    for mapping in mappings:
        # Hỗ trợ tìm kiếm chính xác hoặc tìm kiếm dạng chứa (substring)
        for source_pattern in mapping.get("source_files", []):
            if source_pattern in rel_source_path or rel_source_path in source_pattern:
                matched_mapping = mapping
                break
        if matched_mapping:
            break
            
    if not matched_mapping:
        print(f"[WARNING] Không tìm thấy ánh xạ spec cho file: {rel_source_path}. Sử dụng Spec 00 mặc định.")
        # Fallback về Spec 00
        matched_mapping = {
            "spec_id": "Spec 00",
            "spec_file": "spec_00_overview_architecture.md"
        }
        
    spec_id = matched_mapping["spec_id"]
    spec_file_name = matched_mapping["spec_file"]
    spec_full_path = os.path.join(workspace_root, specs_dir, spec_file_name)
    
    # 3. Đọc nội dung spec tương ứng
    spec_content = ""
    if os.path.exists(spec_full_path):
        with open(spec_full_path, "r", encoding="utf-8") as f:
            spec_content = f.read()
    else:
        spec_content = f"⚠️ [CẢNH BÁO] File đặc tả {spec_file_name} chưa được khởi tạo trên thực tế."

    # 4. Tạo nội dung cho live_context.md
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    live_markdown = f"""# 📖 LIVE CONTEXT - NGỮ CẢNH PHIÊN LÀM VIỆC DỰ ÁN

> ⚡ **CẢNH BÁO CHO AI AGENT:** File này được sinh tự động bởi `live_context_loader.py`. Đọc kỹ và tuân thủ các neo kiến trúc dưới đây.
> **Thời gian cập nhật:** {timestamp}
> **File đang thao tác:** `{rel_source_path}`
> **Tài liệu neo tương ứng:** [{spec_id} - {spec_file_name}](file:///{spec_full_path.replace('\\', '/')})

---

## I. MỤC TIÊU THIẾT KẾ CỦA PHÂN HỆ VÀ SPEC CHỦ ĐẠO

{spec_content}

---

## II. NGUYÊN TẮC VẬN HÀNH BẮT BUỘC TRONG PHIÊN
1. Phải tham chiếu chính xác các hàm và biến được mô tả trong tài liệu Spec này.
2. Không tự ý thay đổi giao thức truyền tin (ví dụ: đổi schema websocket) mà không cập nhật tài liệu thiết kế.
3. Chú ý các nguyên tắc tối ưu hóa SQLite (WAL mode) khi thay đổi logic DB.
"""

    # 5. Ghi đè vào file live_context.md
    os.makedirs(os.path.dirname(live_context_path), exist_ok=True)
    with open(live_context_path, "w", encoding="utf-8") as f:
        f.write(live_markdown)
        
    print(f"[SUCCESS] Đã nạp thành công ngữ cảnh của [{spec_id}] vào live_context.md")

if __name__ == "__main__":
    # Nhận tham số truyền vào từ IDE
    # sys.argv[1]: Đường dẫn tuyệt đối đến file đang active trên IDE
    # sys.argv[2]: Đường dẫn thư mục gốc workspace
    if len(sys.argv) < 3:
        print("Sử dụng: python live_context_loader.py <absolute_file_path> <workspace_root>")
        sys.exit(1)
        
    load_context(sys.argv[1], sys.argv[2])
```

---

## 5. KỶ LUẬT SỬ DỤNG 4 BƯỚC CỦA LIVE CONTEXT SYSTEM

Đối với bất kỳ AI Coding Agent nào tham gia phát triển dự án này, việc tuân thủ quy trình dưới đây là **KỶ LUẬT SẮT BẮT BUỘC**:

### 🛠️ BƯỚC 1: NHẬN DIỆN & KÍCH HOẠT (Identify & Trigger)
- Trước khi thực hiện chỉnh sửa bất kỳ file mã nguồn nào, Agent **bắt buộc** phải gọi công cụ loader (hoặc giả lập hành vi chạy loader nếu hệ thống chưa tự động hóa) để tạo ra tệp tin `live_context.md` mới nhất tương ứng với file code đó.
- *Lệnh mẫu:* `python agent_harness/live_context/live_context_loader.py <tên_file_sắp_sửa> <đường_dẫn_workspace>`

### 📖 BƯỚC 2: NẠP & THẤU HIỂU (Load & Absorb)
- Agent sử dụng tool đọc file để nạp toàn bộ nội dung của `/home/newuser/AI_facepostgroup/agent_harness/live_context/live_context.md` vào bộ nhớ context của mình.
- Nghiêm cấm việc bỏ qua bước đọc file này để tự ý sửa code bừa bãi.

### 📐 BƯỚC 3: ĐỐI CHIẾU & ĐỀ XUẤT (Align & Propose)
- Agent phân tích và đối chiếu logic muốn viết với các quy định, ràng buộc được nêu trong phần `I. MỤC TIÊU THIẾT KẾ` của `live_context.md`.
- Đảm bảo rằng đề xuất thay đổi không vi phạm bất kỳ Architectural Decision (AD) nào trong `master_context.md`.

### 🧪 BƯỚC 4: KIỂM CHỨNG & CẬP NHẬT (Verify & Update)
- Sau khi chỉnh sửa code thông qua các tool của IDE, Agent kiểm tra lại xem logic có hoàn toàn khớp với đặc tả không.
- Ghi nhận trạng thái hoàn thành vào nhật ký làm việc của phiên.
