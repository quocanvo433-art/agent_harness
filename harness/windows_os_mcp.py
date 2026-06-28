# windows_os_mcp.py
# Module: Windows Desktop Automation MCP Server
# Purpose: Enables Gemini/Antigravity Agents to visually inspect and control the Windows GUI.

import sys
import os
import subprocess
import time
from typing import Optional

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("[ERROR] 'mcp' SDK is not installed. Please run: pip install mcp")
    sys.exit(1)

try:
    import pyautogui
    # Disable PyAutoGUI fail-safe pause to prevent agent commands from stalling
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.1
except ImportError:
    print("[ERROR] 'pyautogui' is not installed. Please run: pip install pyautogui pillow opencv-python")
    sys.exit(1)

# Initialize FastMCP Server
mcp = FastMCP("windows-desktop-automation")

@mcp.tool()
def get_screen_size() -> str:
    """Get the screen resolution (width and height in pixels).
    
    Returns:
        str: Width and height format, e.g. "1920x1080".
    """
    width, height = pyautogui.size()
    return f"{width}x{height}"

@mcp.tool()
def get_cursor_position() -> str:
    """Get the current mouse cursor coordinates (X, Y) on the screen.
    
    Returns:
        str: Coordinates format, e.g. "x=540, y=980".
    """
    x, y = pyautogui.position()
    return f"x={x}, y={y}"

@mcp.tool()
def launch_application(app_path: str) -> str:
    """Launch any Windows executable file (.exe) using its absolute path.
    
    Args:
        app_path (str): The absolute file path to the executable.
        
    Returns:
        str: Status message indicating success or failure.
    """
    if not os.path.exists(app_path):
        return f"[ERROR] File not found at path: {app_path}"
    try:
        subprocess.Popen(app_path)
        return f"Successfully launched: {app_path}"
    except Exception as e:
        return f"[ERROR] Failed to launch application: {str(e)}"

@mcp.tool()
def capture_desktop() -> str:
    """Take a full screenshot of the primary Windows display and save it.
    
    The image is saved to 'C:\\AI_Facepost\\desktop_state.png' so the agent can inspect it.
    
    Returns:
        str: Absolute path to the saved screenshot file.
    """
    save_path = "C:\\AI_Facepost\\desktop_state.png"
    try:
        # Ensure target folder exists
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        screenshot = pyautogui.screenshot()
        screenshot.save(save_path)
        return f"Screenshot successfully saved to: {save_path}"
    except Exception as e:
        return f"[ERROR] Failed to capture screenshot: {str(e)}"

@mcp.tool()
def click_coordinate(x: int, y: int, clicks: int = 1, button: str = "left") -> str:
    """Click the mouse at specific pixel coordinates (x, y) on the screen.
    
    Args:
        x (int): Horizontal coordinate in pixels.
        y (int): Vertical coordinate in pixels.
        clicks (int, optional): Number of clicks. Defaults to 1.
        button (str, optional): Mouse button, either 'left', 'right', or 'middle'. Defaults to 'left'.
        
    Returns:
        str: Confirmation message.
    """
    try:
        pyautogui.click(x=x, y=y, clicks=clicks, button=button)
        return f"Successfully clicked {button} mouse button {clicks} time(s) at coordinate ({x}, {y})"
    except Exception as e:
        return f"[ERROR] Click failed: {str(e)}"

@mcp.tool()
def move_to_coordinate(x: int, y: int, duration: float = 0.5) -> str:
    """Smoothly move the mouse cursor to a specific coordinate (x, y) over a duration.
    
    Args:
        x (int): Horizontal destination coordinate.
        y (int): Vertical destination coordinate.
        duration (float, optional): Move speed in seconds. Defaults to 0.5.
        
    Returns:
        str: Confirmation message.
    """
    try:
        pyautogui.moveTo(x, y, duration=duration)
        return f"Moved cursor to coordinate ({x}, {y})"
    except Exception as e:
        return f"[ERROR] Cursor move failed: {str(e)}"

@mcp.tool()
def type_text(text: str, interval: float = 0.05) -> str:
    """Simulate keyboard input by typing a string of text.
    
    Args:
        text (str): The text string to type out.
        interval (float, optional): Pause delay between key presses in seconds. Defaults to 0.05.
        
    Returns:
        str: Confirmation message.
    """
    try:
        pyautogui.write(text, interval=interval)
        return f"Successfully typed text: '{text}'"
    except Exception as e:
        return f"[ERROR] Typing simulation failed: {str(e)}"

@mcp.tool()
def press_key(key: str) -> str:
    """Simulate pressing a specific keyboard key (e.g. 'enter', 'tab', 'backspace', 'esc', 'down').
    
    Args:
        key (str): The standard key name. Options include: 'enter', 'tab', 'backspace', 'esc', 
                   'up', 'down', 'left', 'right', 'pgup', 'pgdn', 'win', 'space'.
                   
    Returns:
        str: Confirmation message.
    """
    try:
        pyautogui.press(key)
        return f"Pressed key: '{key}'"
    except Exception as e:
        return f"[ERROR] Key press failed: {str(e)}"

@mcp.tool()
def mouse_scroll(clicks: int) -> str:
    """Scroll the mouse wheel.
    
    Args:
        clicks (int): Number of scroll clicks. Positive to scroll up, negative to scroll down.
        
    Returns:
        str: Confirmation message.
    """
    try:
        pyautogui.scroll(clicks)
        direction = "up" if clicks > 0 else "down"
        return f"Scrolled mouse wheel {direction} by {abs(clicks)} clicks."
    except Exception as e:
        return f"[ERROR] Scroll failed: {str(e)}"

@mcp.tool()
def find_image_on_screen(template_path: str, confidence: float = 0.8) -> str:
    """Locate a sub-image template (like a button icon) on the screen.
    
    Requires 'opencv-python' library to support confidence checking.
    
    Args:
        template_path (str): Absolute path to the template image (.png / .jpg).
        confidence (float, optional): Match accuracy (0.0 to 1.0). Defaults to 0.8.
        
    Returns:
        str: Coordinates of the center of the image, e.g. "x=120, y=340", or not found.
    """
    if not os.path.exists(template_path):
        return f"[ERROR] Template file not found: {template_path}"
    try:
        pos = pyautogui.locateCenterOnScreen(template_path, confidence=confidence)
        if pos:
            return f"Found at x={pos.x}, y={pos.y}"
        return "Image not found on current screen."
    except Exception as e:
        return f"[ERROR] Image lookup failed: {str(e)}. (Ensure opencv-python is installed for confidence filtering)"

if __name__ == "__main__":
    mcp.run(transport="stdio")
