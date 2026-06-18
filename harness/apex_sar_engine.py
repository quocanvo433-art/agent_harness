# -*- coding: utf-8 -*-
"""
Apex Swarm v3.0 - Deterministic Search-and-Replace (SAR) Engine
Thực hiện áp dụng các thay đổi mã nguồn dạng SEARCH/REPLACE một cách an toàn và phi trạng thái.
"""

import os
import sys
import re

class SAREngine:
    def __init__(self, target_file):
        self.target_file = target_file
        if not os.path.exists(target_file):
            raise FileNotFoundError(f"Không tìm thấy file mục tiêu: {target_file}")
            
    def parse_blocks(self, sar_content):
        """
        Phân tích cú pháp văn bản SAR chứa các khối:
        <<<<<<< SEARCH
        ...
        =======
        ...
        >>>>>>> REPLACE
        """
        # Regex tìm kiếm các khối SEARCH/REPLACE
        pattern = r"<<<<<<< SEARCH\n(.*?)\n=======\n(.*?)\n>>>>>>> REPLACE"
        matches = re.findall(pattern, sar_content, re.DOTALL)
        
        blocks = []
        for search, replace in matches:
            blocks.append({
                "search": search,
                "replace": replace
            })
        return blocks

    def apply_blocks(self, blocks):
        """
        Áp dụng các khối thay thế vào file nguồn.
        Thực hiện theo nguyên tắc nguyên tử (Atomic): Nếu 1 khối lỗi, rollback toàn bộ.
        """
        with open(self.target_file, "r", encoding="utf-8") as f:
            original_content = f.read()

        current_content = original_content
        for idx, block in enumerate(blocks):
            search_str = block["search"]
            replace_str = block["replace"]
            
            # 1. So khớp chính xác tuyệt đối (Exact Match)
            if search_str in current_content:
                # Kiểm tra trùng lặp (nếu xuất hiện nhiều hơn 1 lần, báo lỗi để tránh sửa sai chỗ)
                occurrences = current_content.count(search_str)
                if occurrences > 1:
                    print(f"[ERROR] Khối SEARCH #{idx+1} xuất hiện {occurrences} lần trong file. Yêu cầu thêm ngữ cảnh để độc nhất.")
                    return False
                    
                current_content = current_content.replace(search_str, replace_str, 1)
                print(f"[SUCCESS] Đã áp dụng khối #{idx+1} (Exact match).")
            else:
                # 2. So khớp linh hoạt (Fallback): Bỏ qua sự khác biệt về ký tự xuống dòng (\r\n vs \n)
                search_normalized = search_str.replace("\r\n", "\n")
                current_normalized = current_content.replace("\r\n", "\n")
                
                if search_normalized in current_normalized:
                    occurrences = current_normalized.count(search_normalized)
                    if occurrences > 1:
                        print(f"[ERROR] Khối #{idx+1} (Normalized) xuất hiện {occurrences} lần. Yêu cầu thêm ngữ cảnh.")
                        return False
                        
                    # Thực hiện thay thế bằng regex hoặc split/join để giữ nguyên line endings của các phần khác
                    parts = current_normalized.split(search_normalized, 1)
                    # Tái sinh lại content với dòng mới
                    current_content = parts[0] + replace_str + parts[1]
                    print(f"[SUCCESS] Đã áp dụng khối #{idx+1} (Normalized line endings).")
                else:
                    print(f"[ERROR] Không tìm thấy đoạn mã SEARCH của khối #{idx+1} trong file nguồn.")
                    print("--- ĐOẠN MÃ CẦN TÌM ---")
                    print(search_str)
                    print("-----------------------")
                    return False

        # Ghi đè file nếu tất cả đều thành công
        with open(self.target_file, "w", encoding="utf-8") as f:
            f.write(current_content)
        return True

def main():
    if len(sys.argv) < 3:
        print("Cú pháp: python3 apex_sar_engine.py <target_file> <sar_instruction_file>")
        sys.exit(1)
        
    target_file = sys.argv[1]
    sar_instruction_file = sys.argv[2]
    
    if not os.path.exists(sar_instruction_file):
        print(f"[ERROR] Không tìm thấy file chỉ thị SAR: {sar_instruction_file}")
        sys.exit(1)
        
    try:
        with open(sar_instruction_file, "r", encoding="utf-8") as f:
            sar_content = f.read()
            
        engine = SAREngine(target_file)
        blocks = engine.parse_blocks(sar_content)
        
        if not blocks:
            print("[ERROR] Không tìm thấy khối SEARCH/REPLACE nào hợp lệ trong file chỉ thị.")
            sys.exit(1)
            
        print(f"[INFO] Tìm thấy {len(blocks)} khối thay thế cần áp dụng.")
        success = engine.apply_blocks(blocks)
        
        if success:
            print("[INFO] Áp dụng toàn bộ các khối Search-and-Replace thành công.")
            sys.exit(0)
        else:
            print("[ERROR] Có khối thay thế thất bại. Đã hủy bỏ toàn bộ các thay đổi (Rollback).")
            sys.exit(1)
            
    except Exception as e:
        print(f"[ERROR] Sự cố khi thực thi SAR Engine: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
