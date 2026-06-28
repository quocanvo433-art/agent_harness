# Windows Desktop Automation MCP Setup Guide

> **Date of Implementation:** 2026-06-28  
> **Status:** ACTIVE  
> **Target Environment:** Windows 10/11 Local Host (Antigravity CLI / Hub)

This guide explains how to configure and run the Windows Desktop Automation MCP server (`windows_os_mcp.py`) locally on your Windows machine, allowing your Antigravity Agent (CLI or Hub) to interact with and test the actual packaged desktop application in real-time.

---

## 🛠️ Architecture Overview

```text
[ Antigravity Hub / Local CLI ]
              │
              ▼ (Stdio Transport / Local Execution)
[ Windows OS MCP Server ] (windows_os_mcp.py)
   ├── PyAutoGUI (Mouse Click, Type, Key Simulation)
   └── OpenCV / Pillow (Image Template Detection, Vision-Based Screenshots)
              │
              ▼ (Direct OS Control API)
[ Hermes Desktop App (.exe) ] (Packaged Portable Application)
```

---

## 📋 Pre-requisites

You need Python 3.10+ installed on your local Windows system. Install the required libraries by running:

```powershell
pip install mcp pyautogui pillow opencv-python
```

---

## ⚙️ Configuration & Installation

### Step 1: Configure Antigravity Config File
To register the server so that your agent can discover and invoke its tools, you need to add it to your global Antigravity config file.

On Windows, the config file is located at:
`C:\Users\<Username>\.config\antigravity\config.json` (or `C:\Users\<Username>\AppData\Local\agy\config\config.json`).

Open it and add the following entry under `"mcpServers"`:

```json
{
  "mcpServers": {
    "windows-desktop": {
      "command": "python",
      "args": ["C:/AI_Facepost/agent_harness/harness/windows_os_mcp.py"]
    }
  }
}
```

### Step 2: Enable Unrestricted Mode
Since the agent needs to invoke system commands (like launching the `.exe` file) and capture the screen, you must set the workspace security preset to **Unrestricted**. 

You can set this in your project configuration or via global CLI settings:
```json
"security_preset": "Unrestricted"
```

---

## 🧪 Verification & Local Testing

After registering the server, you can verify it directly from your PowerShell terminal using the `agy` command-line tool.

### Test 1: Get Resolution & Capture Desktop
Run this command in your console:
```powershell
agy "Hãy lấy độ phân giải màn hình hiện tại của tôi và chụp ảnh màn hình"
```
The agent should call `get_screen_size` and `capture_desktop`, saving the screenshot file to `C:\AI_Facepost\desktop_state.png`.

### Test 2: Launch the Hermes Desktop App
Run this command:
```powershell
agy "Khởi chạy ứng dụng tại C:\AI_Facepost\hermes-desktop\dist\Hermes FacePost-Group 1.0.0.exe và báo cáo kết quả"
```

---

## 🔮 E2E Visual Test Prompt Template (Hub & CLI)

Once connected, you can direct the agent to perform complete visual user flows. Copy and paste the template below to run a test:

```text
Hãy thực hiện quy trình kiểm thử giao diện (UI E2E Test) cho ứng dụng của tôi bằng cách sử dụng windows-desktop-automation MCP server:

1. Khởi chạy ứng dụng tại C:\AI_Facepost\hermes-desktop\dist\Hermes FacePost-Group 1.0.0.exe.
2. Chờ 3 giây cho ứng dụng load xong, sau đó chụp ảnh màn hình (capture_desktop).
3. Đọc ảnh màn hình chụp được, tìm nút 'Config' (bánh răng) của tài khoản đầu tiên và click vào tọa độ tương ứng (hoặc click vào tọa độ nút Browser).
4. Nhập proxy cấu hình test bằng cách gõ phím (type_text).
5. Chụp lại màn hình một lần nữa để xác minh giao diện popup cấu hình xuất hiện bình thường và không bị lỗi vỡ khung.
6. Trả về báo cáo kết quả kiểm thử giao diện dưới dạng Markdown.
```

---
*Hermes Visual QA Harness — Windows Compliant Setup Guide v1.0.0*
