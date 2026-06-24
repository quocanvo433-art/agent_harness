# Hermes FacePost-Group — Spec 04: Anti-Detection & Proxy Architecture
**Version:** 2.1 (MV3-Compatible)  
**Updated:** 2026-06-18  
**Status:** 🔴 CRITICAL — Replacing broken MV3-incompatible implementation  
**Related:** `facepost_01_overview.md`, `facepost_02_content_engine.md`, `facepost_03_scheduler.md`

---

## 1. Tổng quan & Cảnh báo an ninh phòng thủ (Anti-Detection Warnings)

Hệ thống chống phát hiện tự động của Hermes được thiết kế nhằm mục đích che giấu các dấu hiệu tự động hóa (automation signatures) khi tương tác với nền tảng Facebook. Tránh tối đa việc tài khoản bị khóa hoặc hạn chế do hệ thống giám sát hành vi tự động FBT (Facebook Behavioral Tracking) quét.

### 1.1. React Value Injection (`react_state_patcher.js`)
* **Hạn chế kỹ thuật:** Không sử dụng thuộc tính `element._valueTracker` trực tiếp đối với trình soạn thảo bài viết của Facebook (thẻ `div[contenteditable="true"]`). Đối với div contenteditable, thuộc tính này hoàn toàn không tồn tại và việc gán ép sẽ gây lỗi đồng bộ trạng thái của React, dẫn đến việc nút đăng bài bị vô hiệu hóa (xám nút).
* **Giải pháp chuẩn hóa:** Phải can thiệp trực tiếp vào DOM bằng cách tạo một `TextNode` mới chứa văn bản cần nhập, xóa các node con cũ, chèn `TextNode` vào phần tử và di chuyển con trỏ (Selection/Caret) về cuối. Sau đó, bắt buộc kích hoạt sự kiện `InputEvent` với cờ `bubbles: true` để kích hoạt vòng lặp bắt sự kiện của React (React Event Loop).

### 1.2. Giả lập hành vi người dùng (`human_simulator.js`)
* **Hạn chế kỹ thuật:** Không sử dụng `setInterval` hoặc `setTimeout` với thời gian trễ cố định (Fixed delay). Đây là dấu hiệu nhận biết bot cơ bản nhất mà hệ thống giám sát hành vi của Facebook (FBT) sẽ nhận diện để khóa tài khoản ngay lập tức.
* **Giải pháp chuẩn hóa:** 
  - Toàn bộ thao tác gõ phím bắt buộc phải sử dụng dải trễ biến thiên ngẫu nhiên (Jittering) từ 40ms đến 270ms dựa trên phân phối chuẩn Gaussian.
  - Thao tác di chuột bắt buộc phải tính toán qua thuật toán đường cong **Cubic Bezier** với ít nhất hai điểm điều khiển ngẫu nhiên để mô phỏng chính xác biên độ rung tay của con người.
  - Thường xuyên thực hiện cuộn trang ngẫu nhiên (random scroll) lên xuống để tạo hành vi duyệt web tự nhiên giống như người dùng thật.

### 1.3. Quản lý Proxy (`local_proxy_relay.py` & `ChromeLauncher.js`)
* **Hạn chế kỹ thuật:** Không sử dụng các lệnh can thiệp thay đổi Registry hệ thống Windows ở cấp độ Global OS Proxy khi hệ thống chạy đa luồng. Việc thay đổi proxy hệ thống liên tục trên môi trường chạy song song nhiều tài khoản sẽ gây hiện tượng dẫm chân lên nhau giữa các tiến trình Chrome, dẫn đến rò rỉ địa chỉ IP chéo giữa các tài khoản.
* **Giải pháp chuẩn hóa:** Triển khai mô hình **Per-Account Local Proxy Relay**. Mỗi profile Chrome được mở lên thông qua `ChromeLauncher.js` sẽ truyền một tham số cô lập `--proxy-server=socks5h://127.0.0.1:PORT_RIÊNG`. Toàn bộ phần xác thực (User/Pass) sẽ do relay Python xử lý ngầm ở mức độ local, đảm bảo luồng mạng của các tài khoản tách biệt hoàn toàn.

---

## Mục Lục

1. [Vấn Đề Proxy Trong Manifest V3](#2-vấn-đề-proxy-trong-manifest-v3)
2. [Giải Pháp A — Native Messaging Host (DEPRECATED)](#3-giải-pháp-a--native-messaging-host-deprecated)
3. [Giải Pháp B — Server-Side Chrome Launch (PRIMARY)](#4-giải-pháp-b--server-side-chrome-launch-primary)
4. [React State Patcher (Nâng Cấp)](#5-react-state-patcher-nâng-cấp)
5. [Human Simulator (Nâng Cấp)](#6-human-simulator-nâng-cấp)
6. [Behavioral Fingerprint Evasion Checklist](#7-behavioral-fingerprint-evasion-checklist)
7. [Windows Installation Guide](#8-windows-installation-guide)

---

## 2. Vấn Đề Proxy Trong Manifest V3

### 2.1 Tóm Tắt Vấn Đề (Bug A1 + A2 + B5 — CRITICAL)

Chrome Extension Manifest V3 đã loại bỏ hai API cốt lõi mà `ProxyRotator` (phiên bản cũ) phụ thuộc:
- `chrome.proxy` — Bị xóa hoàn toàn khỏi Service Worker context trong MV3.
- `chrome.webRequest` với `['blocking']` listener — Bị cấm và được thay thế bằng `declarativeNetRequest`.

Hệ quả là toàn bộ lớp `ProxyRotator` trước đây không hoạt động khi chạy trong MV3 extension. Extension không thể tự động thiết lập proxy và không thể chèn thông tin xác thực (auth credentials) cho proxy yêu cầu user/password.

### 2.2 Tại Sao `chrome.proxy` Không Còn Dùng Được

* **Trong Manifest V2:** Background page là một HTML page thực, chạy JS liên tục, do đó `chrome.proxy` API hoạt động bình thường.
* **Trong Manifest V3:** Background là Service Worker — không có persistent state và bị tắt sau ~30 giây không hoạt động. `chrome.proxy.settings` không tồn tại trong Service Worker context. Gọi `chrome.proxy.settings.set()` sẽ gây lỗi: "Cannot read properties of undefined".
* **Nguyên nhân kỹ thuật:** Service Worker không có DOM context và proxy settings là global, không hỗ trợ thiết lập per-tab/per-account một cách cô lập. Từ Chrome 127, Chrome đã vô hiệu hóa hoàn toàn extension chạy MV2 manifest trong production channel.

### 2.3 Tại Sao `chrome.webRequest` Blocking Bị Xóa

* **Mục đích cũ (MV2):** Dùng `onAuthRequired` với đầu vào `['blocking']` để chèn thông tin xác thực khi proxy yêu cầu:
* **Nguyên nhân loại bỏ trong MV3:** `['blocking']` listener chạy đồng bộ trên network thread của trình duyệt, gây tăng độ trễ cho mọi request. MV3 thay thế bằng `declarativeNetRequest` chạy trực tiếp trên C++ engine của Chrome nhưng không hỗ trợ chèn thông tin xác thực động (dynamic auth credentials). `onAuthRequired` chỉ cho phép quan sát (observe), không thể trả về credentials, dẫn đến lỗi `ERR_PROXY_AUTH_FAILED` hoặc xuất hiện popup xin credentials.

---

## 3. Giải Pháp A — Native Messaging Host (DEPRECATED)

### 3.1 Kiến Trúc Tổng Quan

```
┌─────────────────────────────────────────────────────────────────┐
│  Chrome Extension (MV3)                                         │
│  ┌─────────────────┐    ┌──────────────────────────────────┐   │
│  │  popup.js /     │───>│  background.js (Service Worker)  │   │
│  │  content.js     │    │  chrome.runtime.sendNativeMessage │   │
│  └─────────────────┘    └──────────────┬─────────────────── ┘   │
└─────────────────────────────────────────┼───────────────────────┘
                                          │ stdin/stdout JSON pipe
                        ┌─────────────────▼─────────────────┐
                        │  hermes_proxy_host.py              │
                        │  (Native Host — runs as subprocess) │
                        │                                    │
                        │  • Đọc proxyConfig từ stdin        │
                        │  • Set Windows Internet Settings   │
                        │    via winreg hoặc netsh           │
                        │  • Per-process proxy via env vars  │
                        │  • Return status via stdout        │
                        └─────────────────┬─────────────────┘
                                          │
                        ┌─────────────────▼─────────────────┐
                        │  Windows OS Proxy Settings         │
                        │  (HKCU\Software\Microsoft\        │
                        │   Windows\CurrentVersion\         │
                        │   Internet Settings)               │
                        └───────────────────────────────────┘
```

1. Extension gửi message tới `background.js`.
2. `background.js` gọi `chrome.runtime.sendNativeMessage('com.hermes.proxy_host', proxyConfig)`.
3. Chrome khởi chạy tiến trình `hermes_proxy_host.py` (nếu chưa chạy).
4. Native host nhận JSON từ stdin, cấu hình proxy ở cấp độ Windows OS.
5. Native host trả về kết quả JSON qua stdout.

### 3.2 Native Host Manifest — `com.hermes.proxy_host.json`

File này phải đặt tại một đường dẫn cố định và đăng ký vào Windows Registry:

```json
{
  "name": "com.hermes.proxy_host",
  "description": "Hermes Proxy Manager — Native Messaging Host",
  "path": "C:\\Program Files\\Hermes\\hermes_proxy_host.bat",
  "type": "stdio",
  "allowed_origins": [
    "chrome-extension://REPLACE_WITH_YOUR_EXTENSION_ID/"
  ]
}
```

* **Lưu ý:** `"path"` trỏ tới wrapper script `.bat` khởi chạy Python.

Wrapper bat file (`hermes_proxy_host.bat`):
```batch
@echo off
"C:\Python311\python.exe" "C:\Program Files\Hermes\hermes_proxy_host.py" %*
```

### 3.3 `background.js` — Extension Side

```javascript
// background.js — Service Worker (MV3)
const NATIVE_HOST_ID = 'com.hermes.proxy_host';

class ProxyRotatorMV3 {
  constructor() {
    this.currentProxy = null;
    this.accountProxyMap = new Map();
    this.port = null;
  }

  async loadProxyAssignments() {
    const data = await chrome.storage.local.get('proxyAssignments');
    if (data.proxyAssignments) {
      this.accountProxyMap = new Map(Object.entries(data.proxyAssignments));
    }
  }

  async saveProxyAssignments() {
    const obj = Object.fromEntries(this.accountProxyMap);
    await chrome.storage.local.set({ proxyAssignments: obj });
  }

  async assignProxy(accountId, proxyConfig) {
    this.accountProxyMap.set(accountId, proxyConfig);
    await this.saveProxyAssignments();
  }

  async activateProxyForAccount(accountId) {
    const proxyConfig = this.accountProxyMap.get(accountId);
    if (!proxyConfig) {
      return { success: false, error: 'NO_PROXY_ASSIGNED' };
    }

    const command = {
      action: 'SET_PROXY',
      accountId: accountId,
      proxy: {
        scheme: proxyConfig.scheme || 'socks5',
        host: proxyConfig.host,
        port: proxyConfig.port,
        username: proxyConfig.username || null,
        password: proxyConfig.password || null
      },
      timestamp: Date.now()
    };

    return await this._sendToNativeHost(command);
  }

  async disableProxy() {
    const command = {
      action: 'DISABLE_PROXY',
      timestamp: Date.now()
    };
    return await this._sendToNativeHost(command);
  }

  _sendToNativeHost(message) {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('Native host timeout after 10s'));
      }, 10000);

      chrome.runtime.sendNativeMessage(
        NATIVE_HOST_ID,
        message,
        (response) => {
          clearTimeout(timeout);
          if (chrome.runtime.lastError) {
            reject(new Error(chrome.runtime.lastError.message));
            return;
          }
          resolve(response);
        }
      );
    });
  }
}

const proxyRotator = new ProxyRotatorMV3();

(async () => {
  await proxyRotator.loadProxyAssignments();
})();

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  handleMessage(message, sender).then(sendResponse).catch((err) => {
    sendResponse({ success: false, error: err.message });
  });
  return true;
});

async function handleMessage(message, sender) {
  switch (message.type) {
    case 'ASSIGN_PROXY':
      await proxyRotator.assignProxy(message.accountId, message.proxyConfig);
      return { success: true };
    case 'ACTIVATE_PROXY':
      return await proxyRotator.activateProxyForAccount(message.accountId);
    case 'DISABLE_PROXY':
      return await proxyRotator.disableProxy();
    default:
      return { success: false, error: 'UNKNOWN_MESSAGE_TYPE' };
  }
}
```

---

## 4. Giải Pháp B — Server-Side Chrome Launch (PRIMARY)

### 4.1 Kiến Trúc Cốt Lõi

Thay vì cấu hình proxy trực tiếp trên Extension, hệ thống sử dụng Node.js server khởi chạy (launch) một phiên Chrome riêng biệt cho từng tài khoản với cờ `--proxy-server`. Mỗi tài khoản sử dụng:
* Một thư mục dữ liệu (Chrome profile directory) riêng biệt.
* Một cấu hình proxy riêng biệt.
* Một cổng gỡ lỗi từ xa CDP (Chrome DevTools Protocol) riêng biệt.

```
Dashboard (Node.js)
├── AccountManager
│   ├── Account A → Chrome PID 1234 (--proxy-server=socks5h://127.0.0.1:10001)
│   ├── Account B → Chrome PID 5678 (--proxy-server=socks5h://127.0.0.1:10002)
│   └── Account C → Chrome PID 9012 (--proxy-server=socks5h://127.0.0.1:10003)
│
└── ChromeLauncher
    ├── launchWithProxy(profilePath, proxyConfig) → Khởi chạy Chrome instance
    ├── attachExtension(chromePath) → Nạp Hermes extension
    └── getPage(accountId) → Trả về Page object qua Puppeteer/Playwright
```

### 4.2 Cảnh Báo An Ninh và Lỗ Hổng Kiến Trúc

#### [GAP-04-01] Ngăn ngừa rò rỉ DNS (DNS Leak)
* **Nguyên nhân:** Cấu hình tham số khởi động Chrome `--proxy-server=socks5://127.0.0.1:PORT` bắt buộc Chrome thực hiện phân giải DNS cục bộ (Local DNS Resolution) trên máy chạy bot trước khi gửi kết nối qua proxy. ISP và mạng vật lý của máy chạy bot sẽ nhìn thấy toàn bộ truy vấn tên miền (như `facebook.com`), làm lộ dấu vết tự động hóa ngay lập tức.
* **Biện pháp khắc phục:** Bắt buộc thay đổi giao thức thành **`socks5h://`** (ví dụ: `socks5h://127.0.0.1:PORT`) để ủy quyền toàn bộ việc phân giải DNS từ xa (Remote DNS Resolution) cho proxy server đảm nhận.

#### [GAP-04-02] Ngăn ngừa rò rỉ địa chỉ IP thật qua WebRTC (WebRTC IP Leak)
* **Nguyên nhân:** WebRTC mặc định kích hoạt sẽ gửi trực tiếp các gói UDP STUN/TURN đi xuyên qua proxy để tìm IP LAN/WAN thật của card mạng vật lý, khiến Facebook dễ dàng lấy IP thật qua API `RTCPeerConnection`.
* **Biện pháp khắc phục:** Bổ sung cờ khởi động Chrome: `--force-webrtc-ip-handling-policy=disable_non_proxied_udp` và vô hiệu hóa mdns WebRTC để chặn WebRTC rò rỉ IP.

#### [GAP-04-03] Tránh phát hiện giả mạo Canvas & WebGL thô sơ
* **Nguyên nhân:** Ghi đè prototype (`HTMLCanvasElement.prototype.toDataURL` hoặc WebGL parameters) trực tiếp bằng JavaScript trong content script sẽ bị các hệ thống WAF (Cloudflare, Akamai) phát hiện thông qua kiểm tra hàm `.toString()` (sẽ trả về mã nguồn JS thay vì `[native code]`).
* **Biện pháp khắc phục:** Sử dụng các thư viện stealth chuyên dụng (như `puppeteer-extra-plugin-stealth` che giấu proxy hoàn chỉnh) hoặc can thiệp ngẫu nhiên hóa canvas từ mã nguồn C++ của trình duyệt (Brave).

#### [GAP-04-04] Ẩn cờ tự động hóa `navigator.webdriver`
* **Nguyên nhân:** Gán trực tiếp `webdriver` bằng `Object.defineProperty(navigator, 'webdriver', ...)` sẽ tạo thuộc tính trực tiếp trên đối tượng `navigator` thay vì trên `Navigator.prototype` (làm lệch prototype chain, khiến `navigator.hasOwnProperty('webdriver')` trả về `true` thay vì `false`).
* **Biện pháp khắc phục:** Sử dụng cờ native `--disable-blink-features=AutomationControlled` của Chrome để ẩn cờ webdriver một cách native. Nếu ghi đè bằng JS, bắt buộc phải ghi trên prototype: `Object.defineProperty(Navigator.prototype, 'webdriver', { get: () => false });`.

#### [GAP-04-05] Ngăn ngừa rò rỉ và bypass Proxy qua IPv6 (IPv6 Leakage)
* **Nguyên nhân:** Trình duyệt Chrome mặc định ưu tiên định tuyến IPv6 khi truy cập Facebook. Nếu proxy chỉ hỗ trợ IPv4, Chrome sẽ tự động kết nối trực tiếp đến Facebook qua địa chỉ IPv6 thực của máy chạy bot, bypass hoàn toàn proxy IPv4.
* **Biện pháp khắc phục:** Vô hiệu hóa IPv6 ở cấp độ Hệ điều hành (OS Level) của máy chạy bot, hoặc cấu hình DNS Server nội bộ lọc bỏ hoàn toàn các bản ghi AAAA của Facebook.

#### [GAP-04-06] Ẩn biến toàn cục ChromeDriver
* **Nguyên nhân:** Nếu sử dụng ChromeDriver, các biến toàn cục đặc trưng chứa chuỗi `cdc_` sẽ xuất hiện trên đối tượng `window`, khiến hệ thống phát hiện trình duyệt đang bị điều khiển.
* **Biện pháp khắc phục:** Tránh sử dụng ChromeDriver. Khởi chạy Chrome độc lập bằng `child_process.spawn` và kết nối trực tiếp bằng CDP WebSocket.

#### [GAP-04-07] Quản lý vòng đời tiến trình & Socket Leak trong `local_proxy_relay.py`
* **Nguyên nhân:** Việc spawn luồng (`threading.Thread`) vô hạn cho mỗi kết nối mà không giới hạn số lượng sẽ gây cạn kiệt tài nguyên hệ thống khi trình duyệt tải nhiều asset song song. Ngoài ra, thiếu thiết lập `timeout` cho sockets sẽ khiến luồng bị treo vô hạn ở trạng thái `CLOSE_WAIT`.
* **Biện pháp khắc phục:** Thiết lập `socket.settimeout(30.0)` cho cả socket client và remote, đồng thời cấu trúc lại relay proxy sử dụng mô hình bất động bộ `asyncio` để tối ưu hóa hiệu năng thay vì sử dụng mô hình đa luồng (`threading`) không kiểm soát.

### 4.3 Triển Khai `local_proxy_relay.py` — Per-Account Proxy Relay

```python
# local_proxy_relay.py — Standalone Per-Account SOCKS5 Proxy Relay
import socket
import threading
import struct
import logging
import argparse
import sys
import json
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('LocalProxyRelay')

class LocalProxyRelay:
  """
  Tạo một SOCKS5 relay server độc lập chạy per-process cho từng tài khoản.
  Relay lắng nghe tại 127.0.0.1:0 (OS tự gán cổng ngẫu nhiên khả dụng)
  và chuyển tiếp dữ liệu qua Remote SOCKS5 Proxy có xác thực.
  """
  def __init__(self, remote_host: str, remote_port: int,
         username: Optional[str] = None, password: Optional[str] = None):
    self.remote_host = remote_host
    self.remote_port = remote_port
    self.username = username
    self.password = password
    self.server_socket: Optional[socket.socket] = None
    self.local_port: int = 0
    self.is_active = False

  def start(self):
    self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # Thiết lập timeout cho server socket tránh treo luồng chấp nhận kết nối
    self.server_socket.settimeout(10.0)
    self.server_socket.bind(('127.0.0.1', 0))
    self.local_port = self.server_socket.getsockname()[1]
    self.server_socket.listen(128)
    self.is_active = True
    
    print(json.dumps({"status": "READY", "local_port": self.local_port}))
    sys.stdout.flush()

    logger.info(f"Relay running at 127.0.0.1:{self.local_port} -> {self.remote_host}:{self.remote_port}")

    while self.is_active:
      try:
        client_sock, addr = self.server_socket.accept()
        client_sock.settimeout(30.0) # Ngăn chặn Socket Leak
        t = threading.Thread(
          target=self._handle_client,
          args=(client_sock,),
          daemon=True
        )
        t.start()
      except socket.timeout:
        continue
      except Exception as e:
        if self.is_active:
          logger.error(f"Error accepting connection: {e}")
        break

  def _handle_client(self, client_sock: socket.socket):
    import socks
    try:
      # SOCKS5 Greeting
      greeting = client_sock.recv(262)
      if not greeting or greeting[0] != 0x05:
        client_sock.close()
        return
      client_sock.sendall(b"\x05\x00")

      # CONNECT Request
      request = client_sock.recv(4)
      if not request or len(request) < 4:
        client_sock.close()
        return

      cmd = request[1]
      atyp = request[3]

      if cmd != 0x01:
        client_sock.sendall(b"\x05\x07\x00\x01\x00\x00\x00\x00\x00\x00")
        client_sock.close()
        return

      # Parse Destination Address
      if atyp == 0x01:  # IPv4
        ip = client_sock.recv(4)
        dest_host = socket.inet_ntoa(ip)
      elif atyp == 0x03:  # Domain
        domain_len = client_sock.recv(1)[0]
        dest_host = client_sock.recv(domain_len).decode('utf-8')
      elif atyp == 0x04:  # IPv6
        ipv6 = client_sock.recv(16)
        dest_host = socket.inet_ntop(socket.AF_INET6, ipv6)
      else:
        client_sock.close()
        return

      dest_port = struct.unpack('>H', client_sock.recv(2))[0]

      # Kết nối qua Remote SOCKS5 Proxy
      remote = socks.socksocket()
      remote.settimeout(30.0) # Ngăn chặn Socket Leak
      remote.set_proxy(
        socks.SOCKS5,
        self.remote_host,
        self.remote_port,
        username=self.username,
        password=self.password
      )
      remote.connect((dest_host, dest_port))
      client_sock.sendall(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")

      def forward(src, dst):
        try:
          while True:
            data = src.recv(8192)
            if not data:
              break
            dst.sendall(data)
        except Exception:
          pass
        finally:
          try: src.close()
          except: pass
          try: dst.close()
          except: pass

      t1 = threading.Thread(target=forward, args=(client_sock, remote), daemon=True)
      t2 = threading.Thread(target=forward, args=(remote, client_sock), daemon=True)
      t1.start()
      t2.start()

    except Exception as e:
      try:
        client_sock.sendall(b"\x05\x01\x00\x01\x00\x00\x00\x00\x00\x00")
      except:
        pass
      finally:
        client_sock.close()

  def stop(self):
    self.is_active = False
    if self.server_socket:
      try:
        self.server_socket.close()
      except Exception as e:
        logger.error(f"Error closing socket: {e}")

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description="Hermes Local Proxy Relay")
  parser.add_argument("--remote-host", required=True, help="Remote SOCKS5 host")
  parser.add_argument("--remote-port", type=int, required=True, help="Remote SOCKS5 port")
  parser.add_argument("--username", help="Remote SOCKS5 username")
  parser.add_argument("--password", help="Remote SOCKS5 password")
  args = parser.parse_args()

  relay = LocalProxyRelay(
    remote_host=args.remote_host,
    remote_port=args.remote_port,
    username=args.username,
    password=args.password
  )
  try:
    relay.start()
  except KeyboardInterrupt:
    relay.stop()
```

### 4.4 Triển Khai `ChromeLauncher.js` — Node.js Implementation

```javascript
// ChromeLauncher.js
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const puppeteer = require('puppeteer-core');

const CHROME_EXECUTABLE = process.env.CHROME_PATH
  || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';

const EXTENSION_PATH = process.env.HERMES_EXTENSION_PATH
  || path.join(__dirname, '..', 'extension');

const CDP_PORT_START = 9222;

class ChromeLauncher {
  constructor() {
    this.instances = new Map();
    this._portCounter = CDP_PORT_START;
  }

  async launchWithProxy(accountId, profilePath, proxyConfig) {
    if (this.instances.has(accountId)) {
      console.log(`[ChromeLauncher] Account ${accountId} is already running`);
      return this.instances.get(accountId);
    }

    fs.mkdirSync(profilePath, { recursive: true });
    const cdpPort = this._portCounter++;

    console.log(`[ChromeLauncher] Spawning local proxy relay for ${accountId}...`);
    const relayProcess = spawn('python3', [
      path.join(__dirname, 'local_proxy_relay.py'),
      '--remote-host', proxyConfig.host,
      '--remote-port', proxyConfig.port.toString(),
      ...(proxyConfig.username ? ['--username', proxyConfig.username] : []),
      ...(proxyConfig.password ? ['--password', proxyConfig.password] :     [])
    ]);

    const localPort = await new Promise((resolve, reject) => {
      let output = '';
      const onData = (data) => {
        output += data.toString();
        const lines = output.split('\n');
        for (const line of lines) {
          if (line.trim().startsWith('{')) {
            try {
              const parsed = JSON.parse(line.trim());
              if (parsed.status === 'READY' && parsed.local_port) {
                relayProcess.stdout.off('data', onData);
                resolve(parsed.local_port);
                return;
              }
            } catch (e) {
              // Ignore invalid JSON lines
            }
          }
        }
      };

      relayProcess.stdout.on('data', onData);
      relayProcess.on('error', (err) => reject(new Error(`Relay failed to start: ${err.message}`)));
      relayProcess.on('exit', (code) => {
        if (code !== 0) reject(new Error(`Relay process exited with code ${code}`));
      });
    });

    // GAP-04-01: Sử dụng socks5h:// để ngăn ngừa rò rỉ DNS
    const proxyArg = `socks5h://127.0.0.1:${localPort}`;

    const chromeArgs = [
      `--user-data-dir=${profilePath}`,
      `--proxy-server=${proxyArg}`,
      `--load-extension=${EXTENSION_PATH}`,
      `--disable-extensions-except=${EXTENSION_PATH}`,
      `--remote-debugging-port=${cdpPort}`,
      
      // GAP-04-04: Tắt webdriver một cách native từ mã nguồn Chrome
      '--disable-blink-features=AutomationControlled',
      '--disable-automation',
      
      // GAP-04-02: Ngăn ngừa rò rỉ IP thật qua WebRTC
      '--force-webrtc-ip-handling-policy=disable_non_proxied_udp',
      
      '--no-first-run',
      '--no-default-browser-check',
      '--disable-infobars',
      '--disable-background-timer-throttling',
      '--disable-renderer-backgrounding',
      '--disable-backgrounding-occluded-windows',
      'about:blank'
    ];

    console.log(`[ChromeLauncher] Launching Chrome for ${accountId} on port ${cdpPort}`);

    const chromeProcess = spawn(CHROME_EXECUTABLE, chromeArgs, {
      detached: false,
      stdio: 'pipe'
    });

    chromeProcess.stderr.on('data', (data) => {
      const msg = data.toString();
      if (msg.includes('ERROR') || msg.includes('FATAL')) {
        console.error(`[Chrome/${accountId}] ${msg.trim()}`);
      }
    });

    chromeProcess.on('exit', (code) => {
      this.closeInstance(accountId).catch(() => {});
    });

    await this._waitForChromeReady(cdpPort);

    const browser = await puppeteer.connect({
      browserURL: `http://localhost:${cdpPort}`,
      defaultViewport: this._getRandomViewport()
    });

    const instance = new ChromeInstance(accountId, chromeProcess, browser, cdpPort, proxyConfig, relayProcess);
    this.instances.set(accountId, instance);

    return instance;
  }

  async closeInstance(accountId) {
    const instance = this.instances.get(accountId);
    if (!instance) return;

    await instance.browser.close().catch(() => {});
    instance.process.kill('SIGTERM');
    if (instance.relayProcess) {
      instance.relayProcess.kill('SIGTERM');
    }
    this.instances.delete(accountId);
    console.log(`[ChromeLauncher] Closed instance for ${accountId}`);
  }

  async closeAll() {
    const ids = [...this.instances.keys()];
    await Promise.all(ids.map(id => this.closeInstance(id)));
  }

  async _waitForChromeReady(port, timeoutMs = 15000) {
    const start = Date.now();
    const http = require('http');

    while (Date.now() - start < timeoutMs) {
      try {
        await new Promise((resolve, reject) => {
          const req = http.get(`http://localhost:${port}/json/version`, resolve);
          req.on('error', reject);
          req.setTimeout(500, () => req.destroy());
        });
        return;
      } catch {
        await new Promise(r => setTimeout(r, 300));
      }
    }
    throw new Error(`Chrome did not start on port ${port} within ${timeoutMs}ms`);
  }

  _getRandomViewport() {
    const widths = [1280, 1366, 1440, 1536, 1920];
    const heights = [720, 768, 800, 864, 900, 1080];
    return {
      width: widths[Math.floor(Math.random() * widths.length)],
      height: heights[Math.floor(Math.random() * heights.length)]
    };
  }
}

class ChromeInstance {
  constructor(accountId, process, browser, cdpPort, proxyConfig, relayProcess = null) {
    this.accountId = accountId;
    this.process = process;
    this.browser = browser;
    this.cdpPort = cdpPort;
    this.proxyConfig = proxyConfig;
    this.relayProcess = relayProcess;
    this._activePage = null;
  }

  async getPage() {
    if (!this._activePage || this._activePage.isClosed()) {
      const pages = await this.browser.pages();
      this._activePage = pages[0] || await this.browser.newPage();
      await this._applyAntiDetection(this._activePage);
    }
    return this._activePage;
  }

  async navigateToFacebook() {
    const page = await this.getPage();
    if (!page.url().includes('facebook.com')) {
      await page.goto('https://www.facebook.com', {
        waitUntil: 'networkidle2',
        timeout: 30000
      });
    }
    return page;
  }

  async _applyAntiDetection(page) {
    await page.evaluateOnNewDocument(() => {
      // GAP-04-04: Xóa cờ webdriver trên Navigator.prototype thay vì gán trực tiếp
      Object.defineProperty(Navigator.prototype, 'webdriver', { get: () => false });

      Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5]
      });

      Object.defineProperty(navigator, 'languages', {
        get: () => ['vi-VN', 'vi', 'en-US', 'en']
      });

      window.chrome = { runtime: {} };

      // Spoof hardware specifications
      Object.defineProperty(navigator, 'hardwareConcurrency', {
        get: () => [4, 6, 8, 12][Math.floor(Math.random() * 4)]
      });

      Object.defineProperty(navigator, 'deviceMemory', {
        get: () => [4, 8, 16][Math.floor(Math.random() * 3)]
      });

      Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
      Object.defineProperty(screen, 'colorDepth', { get: () => 24 });

      // Canvas fingerprint noise injection
      const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
      HTMLCanvasElement.prototype.toDataURL = function(type) {
        const result = originalToDataURL.apply(this, arguments);
        return result.replace(/.$/, Math.random() > 0.5 ? '1' : '0');
      };

      // WebGL vendor/renderer spoofing
      const getParameter = WebGLRenderingContext.prototype.getParameter;
      WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) return 'Intel Inc.';
        if (parameter === 37446) return 'Intel(R) UHD Graphics 630';
        return getParameter.apply(this, arguments);
      };
    });
  }
}

module.exports = { ChromeLauncher, ChromeInstance };
```

---

## 5. React State Patcher (Nâng Cấp)

### 5.1 Cơ chế ValueTracker của React

React theo dõi giá trị của `<input>` và `<textarea>` thông qua một đối tượng nội bộ là `_valueTracker`. Khi có sự kiện input xảy ra, React so sánh giá trị DOM hiện tại với giá trị được lưu trữ trong `_valueTracker`. Nếu có sự khác biệt, React mới kích hoạt sự kiện cập nhật trạng thái (`onChange`).

Để chèn giá trị từ bên ngoài một cách thành công và kích hoạt được React State Update:
1. Thiết lập giá trị của `_valueTracker` về rỗng (hoặc giá trị cũ).
2. Dùng bộ setter gốc của trình duyệt (`Object.getOwnPropertyDescriptor().set`) để thay đổi giá trị thuộc tính `value` của DOM Node.
3. Phát sự kiện `input` và `change` với cờ `bubbles: true`.

**Đối với thẻ `div[contenteditable="true"]` của Facebook:** Không sử dụng thuộc tính `_valueTracker`. Việc gán giá trị phải được thực hiện bằng cách tạo TextNode trực tiếp và kích hoạt sự kiện `InputEvent` dạng `insertText` với cờ `bubbles: true`.

### 5.2 Triển Khai `react_state_patcher.js`

```javascript
// react_state_patcher.js
'use strict';

(function HermesReactStatePatcher() {
  'use strict';

  function injectValueToInput(element, value, triggerEvents = true) {
    if (!element) return;

    const tracker = element._valueTracker;
    if (tracker) {
      tracker.setValue(''); // Reset tracker
    }

    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
      window.HTMLInputElement.prototype, 'value'
    ).set;
    const nativeTextareaValueSetter = Object.getOwnPropertyDescriptor(
      window.HTMLTextAreaElement.prototype, 'value'
    ).set;

    if (element.tagName === 'TEXTAREA') {
      nativeTextareaValueSetter.call(element, value);
    } else {
      nativeInputValueSetter.call(element, value);
    }

    if (triggerEvents) {
      element.dispatchEvent(new Event('input', { bubbles: true }));
      element.dispatchEvent(new Event('change', { bubbles: true }));
    }
  }

  function injectValueToContentEditable(element, text) {
    if (!element || element.contentEditable !== 'true') return;

    // Cấm sử dụng _valueTracker đối với contenteditable
    if (element._valueTracker) {
      console.error('[ReactStatePatcher] Cấm sử dụng _valueTracker cho contenteditable div.');
    }

    element.focus();
    element.innerHTML = '';

    const textNode = document.createTextNode(text);
    element.appendChild(textNode);

    const selection = window.getSelection();
    if (selection) {
      const range = document.createRange();
      range.selectNodeContents(element);
      range.collapse(false);
      selection.removeAllRanges();
      selection.addRange(range);
    }

    const inputEvent = new InputEvent('input', {
      bubbles: true,
      cancelable: true,
      inputType: 'insertText',
      data: text
    });
    element.dispatchEvent(inputEvent);
  }

  function smartInject(element, value) {
    if (!element) return;

    const tag = element.tagName.toLowerCase();
    const isContentEditable = element.contentEditable === 'true';

    if (isContentEditable) {
      injectValueToContentEditable(element, value);
    } else if (tag === 'input' || tag === 'textarea') {
      injectValueToInput(element, value);
    }
  }

  function watchContentEditable(element, expectedValue, onCleared) {
    let isInjecting = false;

    const observer = new MutationObserver((mutations) => {
      if (isInjecting) return;

      for (const mutation of mutations) {
        if (mutation.type === 'childList' || mutation.type === 'characterData') {
          const currentText = element.textContent || '';

          if (currentText === '' && expectedValue !== '') {
            isInjecting = true;
            setTimeout(() => {
              injectValueToContentEditable(element, expectedValue);
              isInjecting = false;
              if (onCleared) onCleared(element);
            }, 50);
          }
        }
      }
    });

    observer.observe(element, {
      childList: true,
      subtree: true,
      characterData: true
    });

    return observer;
  }

  function waitForComposer(timeoutMs = 10000) {
    return new Promise((resolve, reject) => {
      const immediate = findComposerElement();
      if (immediate) return resolve(immediate);

      const timeout = setTimeout(() => {
        bodyObserver.disconnect();
        reject(new Error('Composer not found within timeout'));
      }, timeoutMs);

      const bodyObserver = new MutationObserver(() => {
        const composer = findComposerElement();
        if (composer) {
          clearTimeout(timeout);
          bodyObserver.disconnect();
          resolve(composer);
        }
      });

      bodyObserver.observe(document.body, {
        childList: true,
        subtree: true
      });
    });
  }

  function findComposerElement() {
    const byRole = document.querySelector('[role="textbox"][contenteditable="true"]');
    if (byRole) return byRole;

    const byPlaceholder = document.querySelector('[contenteditable="true"][data-lexical-editor]');
    if (byPlaceholder) return byPlaceholder;

    const modal = document.querySelector('[data-testid="react-composer-post-button"]');
    if (modal) {
      const parent = modal.closest('[role="dialog"]') || document.body;
      const editable = parent.querySelector('[contenteditable="true"]');
      if (editable) return editable;
    }

    return null;
  }

  function resolveSpintax(template) {
    let result = template;
    let iterations = 0;
    const MAX_ITERATIONS = 100;

    while (iterations < MAX_ITERATIONS) {
      const innermost = /\{([^{}]+)\}/g;
      const match = innermost.exec(result);

      if (!match) break;

      const options = match[1].split('|');
      const chosen = options[Math.floor(Math.random() * options.length)];

      result = result.slice(0, match.index) + chosen + result.slice(match.index + match[0].length);
      iterations++;
    }

    return result;
  }

  window.HermesStatePatcher = {
    injectValueToInput,
    injectValueToContentEditable,
    smartInject,
    watchContentEditable,
    waitForComposer,
    findComposerElement,
    resolveSpintax
  };
})();
```

---

## 6. Human Simulator (Nâng Cấp)

### 6.1 Giải Thuật Mô Phỏng Hành Vi Con Người (Human Simulation)

#### A. Thời gian trễ gõ phím ngẫu nhiên Gaussian (Gaussian Keyboard Delay)
Hệ thống sử dụng phép biến đổi Box-Muller (Box-Muller transform) để tạo ra thời gian trễ gõ phím phân phối chuẩn.
* **Thông số cấu hình:** Trung bình `mean = 155ms`, độ lệch chuẩn `stdDev = 50ms`.
* **Khoảng chặn (Clamping range):** Giới hạn từ `40ms` đến `270ms` để loại bỏ các trường hợp trễ quá nhanh hoặc quá chậm một cách bất thường.
* **Thời gian dừng nghỉ theo cấu trúc câu:** 
  - Gặp dấu phẩy (`,`) ➔ Tạm dừng thêm khoảng `2 * getGaussianDelay()`.
  - Gặp các dấu kết thúc câu (`.`, `!`, `?`) ➔ Tạm dừng thêm khoảng `4 * getGaussianDelay()`.
* **Mô phỏng lỗi gõ phím (Typo Rate):** Xác suất lỗi gõ phím là 15% cho các từ có độ dài lớn hơn 3 ký tự. Khi xảy ra lỗi:
  1. Gõ từ bị lỗi (ví dụ: tráo đổi ký tự liền kề hoặc thay thế bằng phím liền kề trên bàn phím QWERTY).
  2. Tạm dừng ngẫu nhiên (`2 * getGaussianDelay()`) thể hiện phản xạ của con người khi nhận ra lỗi.
  3. Gõ liên tục phím `Backspace` với tốc độ nhanh hơn bình thường (`0.6 * getGaussianDelay()`).
  4. Gõ lại đoạn văn bản đúng.

#### B. Chuyển động chuột Cubic Bezier (Bezier Mouse Movements)
Để di chuyển chuột từ tọa độ xuất phát $P_0(x_0, y_0)$ đến tọa độ đích $P_3(x_3, y_3)$, thuật toán xây dựng một đường cong Cubic Bezier được xác định bởi công thức:
$$B(t) = (1-t)^3 P_0 + 3(1-t)^2 t P_1 + 3(1-t) t^2 P_2 + t^3 P_3$$
Với $t \in [0, 1]$.
* **Điểm điều khiển ($P_1, P_2$):** Được sinh ngẫu nhiên lệch khỏi đường thẳng nối $P_0$ và $P_3$ trong khoảng tỷ lệ tương đối nhằm tạo ra quỹ đạo cong tự nhiên, có sai số nhỏ để mô phỏng chính xác độ rung tay vật lý.
* **Số bước di chuyển (Steps):** Lấy ngẫu nhiên từ `20` đến `40` bước.
* **Thời gian trễ giữa mỗi bước:** Dao động ngẫu nhiên từ `5ms` đến `25ms`.

#### C. Cuộn trang ngẫu nhiên (Random Scroll)
Trước khi thực hiện các hành động bấm (click) hoặc gõ phím, hệ thống mô phỏng thao tác đọc lướt:
* Thực hiện cuộn lên/xuống ngẫu nhiên từ `2` đến `5` lần.
* Khoảng cách cuộn mỗi lần từ `-150px` đến `450px` (cuộn âm tương đương cuộn ngược lên trên).
* Cuộn mượt (smooth scrolling) thông qua việc chia nhỏ khoảng cách cuộn thành nhiều bước nhỏ từ `8` đến `20` bước, trễ mỗi bước `15ms` - `35ms`.
* Dừng đọc nội dung ngẫu nhiên sau mỗi lần cuộn từ `400ms` đến `1200ms`.

#### D. Sao chép và dán nội dung an toàn (Safe Paste Simulation)
Hành động dán (paste) tức thời văn bản dài ngay khi focus vào ô soạn thảo là dấu hiệu tự động hóa dễ bị phát hiện. Giải pháp thay thế là:
* **Pre-Paste Thinking Delay:** Click focus vào ô soạn thảo, tạm dừng ngẫu nhiên từ `1000ms` đến `3000ms`.
* **Ctrl+V / Cmd+V Keyboard Events:** Phát các sự kiện bàn phím mô phỏng tổ hợp phím dán:
  1. `keydown` phím `Control` (hoặc `Meta` đối với macOS).
  2. `keydown` phím `v`.
  3. Phát sự kiện `paste` với ClipboardData chứa nội dung văn bản.
  4. Thực hiện chèn text qua React State Patcher hoặc DOM Manipulation.
  5. `keyup` phím `v`.
  6. `keyup` phím `Control`.
* **Post-Paste Review Delay:** Tạm dừng ngẫu nhiên từ `1500ms` đến `4000ms` sau khi dán xong để mô phỏng hành vi soát lỗi của người dùng.

### 6.2 Triển Khai `human_simulator.js`

```javascript
// human_simulator.js
'use strict';

(function HermesHumanSimulator() {
  'use strict';

  const rand = (min, max) => min + Math.random() * (max - min);
  const randInt = (min, max) => Math.floor(rand(min, max + 1));
  const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

  function gaussianRand(mean, stdDev) {
    let u, v, s;
    do {
      u = Math.random() * 2 - 1;
      v = Math.random() * 2 - 1;
      s = u * u + v * v;
    } while (s >= 1 || s === 0);

    const mul = Math.sqrt(-2 * Math.log(s) / s);
    return mean + stdDev * u * mul;
  }

  function getGaussianDelay() {
    let delay;
    do {
      delay = gaussianRand(155, 50);
    } while (delay < 40 || delay > 270);
    return delay;
  }

  function cubicBezierPoint(t, p0, p1, p2, p3) {
    const u = 1 - t;
    return u*u*u*p0 + 3*u*u*t*p1 + 3*u*t*t*p2 + t*t*t*p3;
  }

  function generateBezierPath(fromX, fromY, toX, toY, steps = 25) {
    const midX = (fromX + toX) / 2;
    const midY = (fromY + toY) / 2;
    const cp1x = midX + (Math.random() - 0.5) * Math.abs(toX - fromX) * 0.8;
    const cp1y = fromY + (Math.random() - 0.5) * 60;
    const cp2x = midX + (Math.random() - 0.5) * Math.abs(toX - fromX) * 0.8;
    const cp2y = toY + (Math.random() - 0.5) * 60;

    const points = [];
    for (let i = 0; i <= steps; i++) {
      const t = i / steps;
      points.push({
        x: Math.round(cubicBezierPoint(t, fromX, cp1x, cp2x, toX)),
        y: Math.round(cubicBezierPoint(t, fromY, cp1y, cp2y, toY))
      });
    }
    return points;
  }

  async function humanMouseMove(page, fromX, fromY, toX, toY) {
    const path = generateBezierPath(fromX, fromY, toX, toY);
    for (const point of path) {
      await page.mouse.move(point.x, point.y);
      await sleep(5 + Math.random() * 20);
    }
  }

  async function humanMouseMoveDOM(fromX, fromY, toX, toY) {
    const path = generateBezierPath(fromX, fromY, toX, toY);
    for (const point of path) {
      const el = document.elementFromPoint(point.x, point.y);
      if (el) el.dispatchEvent(new MouseEvent('mousemove', {
        clientX: point.x, clientY: point.y, bubbles: true
      }));
      await sleep(5 + Math.random() * 20);
    }
  }

  function cubicBezier(t, p0, p1, p2, p3) {
    const mt = 1 - t;
    return {
      x: mt*mt*mt*p0.x + 3*mt*mt*t*p1.x + 3*mt*t*t*p2.x + t*t*t*p3.x,
      y: mt*mt*mt*p0.y + 3*mt*mt*t*p1.y + 3*mt*t*t*p2.y + t*t*t*p3.y
    };
  }

  let currentMousePos = { x: 0, y: 0 };
  document.addEventListener('mousemove', (e) => {
    currentMousePos = { x: e.clientX, y: e.clientY };
  }, { passive: true });

  async function moveCursorTo(targetElement, options = {}) {
    const rect = targetElement.getBoundingClientRect();
    const end = {
      x: rect.left + rect.width / 2 + rand(-rect.width * 0.1, rect.width * 0.1),
      y: rect.top + rect.height / 2 + rand(-rect.height * 0.1, rect.height * 0.1)
    };
    const start = { ...currentMousePos };
    const dx = end.x - start.x;
    const dy = end.y - start.y;
    const p1 = { x: start.x + rand(dx * 0.1, dx * 0.4) + rand(-80, 80), y: start.y + rand(dy * 0.1, dy * 0.4) + rand(-80, 80) };
    const p2 = { x: end.x - rand(dx * 0.1, dx * 0.3) + rand(-60, 60), y: end.y - rand(dy * 0.1, dy * 0.3) + rand(-60, 60) };
    const steps = options.steps || randInt(20, 40);

    for (let i = 0; i <= steps; i++) {
      const t = i / steps;
      const point = cubicBezier(t, start, p1, p2, end);
      document.dispatchEvent(new MouseEvent('mousemove', { bubbles: true, clientX: Math.round(point.x), clientY: Math.round(point.y) }));
      await sleep(rand(10, 25));
    }
    currentMousePos = { ...end };
  }

  async function randomScrollToElement(element) {
    const rect = element.getBoundingClientRect();
    const viewportHeight = window.innerHeight;
    if (rect.top < 0 || rect.bottom > viewportHeight) {
      window.scrollTo(0, window.scrollY + rect.top - viewportHeight / 2);
      await sleep(rand(300, 800));
    }
  }

  async function randomScroll() {
    const scrollCount = randInt(2, 5);
    for (let i = 0; i < scrollCount; i++) {
      const distance = rand(-150, 450);
      const steps = randInt(8, 20);
      const stepDistance = distance / steps;
      for (let s = 0; s < steps; s++) {
        window.scrollBy(0, stepDistance);
        await sleep(rand(15, 35));
      }
      await sleep(rand(400, 1200));
    }
  }

  async function humanClick(element) {
    await randomScrollToElement(element);
    await moveCursorTo(element);
    await sleep(rand(80, 250));
    const rect = element.getBoundingClientRect();
    const clickX = rect.left + rect.width / 2;
    const clickY = rect.top + rect.height / 2;
    const eventOptions = { bubbles: true, cancelable: true, clientX: Math.round(clickX), clientY: Math.round(clickY) };
    element.dispatchEvent(new MouseEvent('mousedown', eventOptions));
    await sleep(rand(50, 150));
    element.dispatchEvent(new MouseEvent('mouseup', eventOptions));
    element.dispatchEvent(new MouseEvent('click', eventOptions));
    await sleep(rand(100, 400));
  }

  async function typeChar(element, char) {
    const delay = getGaussianDelay();
    await sleep(delay);
    await typeCharacter(element, char, 0);
  }

  async function humanType(element, text, options = {}) {
    const typoRate = options.typoRate !== undefined ? options.typoRate : 0.15;

    await humanClick(element);
    await sleep(rand(200, 500));

    const words = text.split(/(\s+)/);

    for (let wordIdx = 0; wordIdx < words.length; wordIdx++) {
      const word = words[wordIdx];
      const isWhitespace = /^\s+$/.test(word);

      if (isWhitespace) {
        for (const char of word) {
          await typeCharacter(element, char, getGaussianDelay());
        }

        const prevWord = words[wordIdx - 1] || '';
        if (prevWord.endsWith('.') || prevWord.endsWith('!') || prevWord.endsWith('?')) {
          await sleep(getGaussianDelay() * 4);
        } else if (prevWord.endsWith(',')) {
          await sleep(getGaussianDelay() * 2);
        }
        continue;
      }

      const makeTypo = word.length > 3 && Math.random() < typoRate;

      if (makeTypo) {
        const typoWord = injectTypo(word);
        for (const char of typoWord) {
          await typeCharacter(element, char, getGaussianDelay() * 0.9);
        }

        await sleep(getGaussianDelay() * 2);

        const backspaceCount = typoWord.length - Math.floor(rand(0, word.length * 0.3));
        for (let b = 0; b < backspaceCount; b++) {
          await pressKey(element, 'Backspace');
          await sleep(getGaussianDelay() * 0.6);
        }

        const remainderStart = word.length - backspaceCount;
        const remainder = remainderStart < 0 ? word : word.slice(Math.max(0, remainderStart));
        for (const char of remainder) {
          await typeCharacter(element, char, getGaussianDelay());
        }
      } else {
        for (const char of word) {
          await typeCharacter(element, char, getGaussianDelay());
        }
      }

      if (Math.random() < 0.05 && word.length > 4) {
        await sleep(getGaussianDelay() * 3);
      }
    }
  }

  async function typeCharacter(element, char, delayMs = 50) {
    const isContentEditable = element.contentEditable === 'true';

    if (isContentEditable) {
      document.execCommand('insertText', false, char);
    } else {
      const nativeSetter = Object.getOwnPropertyDescriptor(
        element.tagName === 'TEXTAREA'
          ? window.HTMLTextAreaElement.prototype
          : window.HTMLInputElement.prototype,
        'value'
      ).set;

      const tracker = element._valueTracker;
      if (tracker) tracker.setValue('');

      nativeSetter.call(element, element.value + char);
    }

    element.dispatchEvent(new KeyboardEvent('keydown', { key: char, bubbles: true }));
    element.dispatchEvent(new KeyboardEvent('keypress', { key: char, bubbles: true }));
    element.dispatchEvent(new InputEvent('input', {
      bubbles: true,
      inputType: 'insertText',
      data: char
    }));
    element.dispatchEvent(new KeyboardEvent('keyup', { key: char, bubbles: true }));

    await sleep(Math.max(10, delayMs));
  }

  async function pressKey(element, key) {
    element.dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true }));

    if (key === 'Backspace') {
      const isContentEditable = element.contentEditable === 'true';
      if (isContentEditable) {
        document.execCommand('delete', false);
      } else {
        const tracker = element._valueTracker;
        if (tracker) tracker.setValue('');
        const nativeSetter = Object.getOwnPropertyDescriptor(
          element.tagName === 'TEXTAREA'
            ? window.HTMLTextAreaElement.prototype
            : window.HTMLInputElement.prototype,
          'value'
        ).set;
        nativeSetter.call(element, element.value.slice(0, -1));
      }

      element.dispatchEvent(new InputEvent('input', {
        bubbles: true,
        inputType: 'deleteContentBackward'
      }));
    }

    element.dispatchEvent(new KeyboardEvent('keyup', { key, bubbles: true }));
    await sleep(rand(30, 80));
  }

  function injectTypo(word) {
    if (word.length < 2) return word;

    const strategy = Math.floor(Math.random() * 3);
    const pos = randInt(0, word.length - 2);

    switch (strategy) {
      case 0:
        return word.slice(0, pos) + word[pos + 1] + word[pos] + word.slice(pos + 2);
      case 1:
        return word.slice(0, pos + 1) + word[pos] + word.slice(pos + 1);
      case 2:
        const KEYBOARD_ADJACENT = {
          'a':'sq', 'b':'vn', 'c':'xv', 'd':'sf', 'e':'wr',
          'f':'dg', 'g':'fh', 'h':'gj', 'i':'uo', 'j':'hk',
          'k':'jl', 'l':'k', 'm':'n', 'n':'mb', 'o':'ip',
          'p':'o', 'q':'wa', 'r':'et', 's':'ad', 't':'ry',
          'u':'yi', 'v':'cb', 'w':'qe', 'x':'zc', 'y':'tu', 'z':'x'
        };
        const charLower = word[pos].toLowerCase();
        const adjacent = KEYBOARD_ADJACENT[charLower];
        if (adjacent) {
          const typoChar = adjacent[randInt(0, adjacent.length - 1)];
          return word.slice(0, pos) + typoChar + word.slice(pos + 1);
        }
        return word;
      default:
        return word;
    }
  }

  async function simulateSearch(searchInput, keyword) {
    console.log(`[HumanSimulator] Starting search simulation for: "${keyword}"`);
    
    await moveCursorTo(searchInput, { steps: randInt(25, 45) });
    await sleep(rand(100, 300));
    
    const rect = searchInput.getBoundingClientRect();
    const eventOptions = { bubbles: true, cancelable: true, clientX: Math.round(rect.left + rect.width / 2), clientY: Math.round(rect.top + rect.height / 2) };
    searchInput.dispatchEvent(new MouseEvent('mousedown', eventOptions));
    await sleep(rand(50, 150));
    searchInput.dispatchEvent(new MouseEvent('mouseup', eventOptions));
    searchInput.dispatchEvent(new MouseEvent('click', eventOptions));
    searchInput.focus();

    const postClickDelay = rand(500, 1500);
    await sleep(postClickDelay);

    for (const char of keyword) {
      const delay = getGaussianDelay();
      await typeCharacter(searchInput, char, delay);
    }

    await sleep(rand(300, 600));
    await pressKey(searchInput, 'Enter');
  }

  async function waitSearchCooldown() {
    const cooldownMs = rand(30000, 90000);
    await sleep(cooldownMs);
  }

  async function waitPostCooldown() {
    const cooldownMs = rand(30000, 90000);
    await sleep(cooldownMs);
  }

  async function humanPaste(element, text) {
    await humanClick(element);
    
    const preDelay = rand(1000, 3000);
    await sleep(preDelay);

    element.dispatchEvent(new KeyboardEvent('keydown', { key: 'Control', code: 'ControlLeft', ctrlKey: true, bubbles: true }));
    element.dispatchEvent(new KeyboardEvent('keydown', { key: 'v', code: 'KeyV', ctrlKey: true, bubbles: true }));

    const isContentEditable = element.contentEditable === 'true';
    if (isContentEditable) {
      element.focus();
      document.execCommand('insertText', false, text);
    } else {
      const nativeSetter = Object.getOwnPropertyDescriptor(
        element.tagName === 'TEXTAREA'
          ? window.HTMLTextAreaElement.prototype
          : window.HTMLInputElement.prototype,
        'value'
      ).set;

      const tracker = element._valueTracker;
      if (tracker) tracker.setValue('');

      nativeSetter.call(element, text);
    }

    const pasteEvent = new ClipboardEvent('paste', {
      bubbles: true,
      cancelable: true,
      clipboardData: new DataTransfer()
    });
    pasteEvent.clipboardData.setData('text/plain', text);
    element.dispatchEvent(pasteEvent);

    element.dispatchEvent(new InputEvent('input', {
      bubbles: true,
      inputType: 'insertFromPaste',
      data: text
    }));

    element.dispatchEvent(new KeyboardEvent('keyup', { key: 'v', code: 'KeyV', ctrlKey: true, bubbles: true }));
    element.dispatchEvent(new KeyboardEvent('keyup', { key: 'Control', code: 'ControlLeft', ctrlKey: false, bubbles: true }));

    const postDelay = rand(1500, 4000);
    await sleep(postDelay);
  }

  window.HermesHumanSimulator = {
    moveCursorTo,
    randomScrollToElement,
    humanClick,
    humanType,
    typeCharacter,
    typeChar,
    pressKey,
    sleep,
    rand,
    randInt,
    gaussianRand,
    cubicBezierPoint,
    generateBezierPath,
    humanMouseMove,
    humanMouseMoveDOM,
    simulateSearch,
    waitSearchCooldown,
    waitPostCooldown,
    humanPaste
  };

  console.log('[HermesHumanSimulator] Initialized');
})();
```

---

## 7. Behavioral Fingerprint Evasion Checklist

| # | Kỹ Thuật Facebook Detect | Cách Bypass | Implementation |
|---|--------------------------|-------------|----------------|
| **1** | **`navigator.webdriver` flag** | Set về `false` thông qua `Navigator.prototype` | `evaluateOnNewDocument` (Stealth mode) |
| **2** | **Quỹ đạo di chuột (Mouse pattern)** | Sử dụng chuyển động cong Cubic Bezier tự nhiên | `HermesHumanSimulator.moveCursorTo()` |
| **3** | **Tốc độ gõ phím & Nhịp điệu** | Sử dụng thời gian trễ Gaussian, mô phỏng lỗi gõ phím | `HermesHumanSimulator.humanType()` |
| **4** | **Headless Chrome detection** | Thiết lập giả lập plugins, window.chrome | `evaluateOnNewDocument` |
| **5** | **Canvas fingerprinting** | Inject nhiễu ngẫu nhiên vào dữ liệu canvas pixel | Hook `HTMLCanvasElement.prototype.toDataURL` |
| **6** | **WebGL fingerprinting** | Giả mạo vendor/renderer strings | Hook `WebGLRenderingContext.prototype.getParameter` |
| **7** | **Phân tích thời gian (Timing analysis)** | Sử dụng Jittering delay ngẫu nhiên, không dùng interval | Thay thế `setInterval` bằng `setTimeout` với trễ ngẫu nhiên |
| **8** | **Tọa độ click** | Tính sai số click lệch khỏi tâm phần tử | `HermesHumanSimulator.humanClick()` |
| **9** | **Hành vi phiên làm việc** | Tích hợp cuộn ngẫu nhiên, dừng nghỉ mô phỏng hành vi đọc | `HermesHumanSimulator.randomScroll()` |
| **10** | **Rò rỉ địa chỉ IP** | Sử dụng per-account proxy relay và cấu thức proxy `socks5h://` | `ProxyRotatorMV3` / `ChromeLauncher` / `local_proxy_relay` |
| **11** | **Giãn cách phiên (Cooldown)** | Thiết lập giãn cách từ 30s đến 90s giữa các tác vụ | `HermesHumanSimulator.waitSearchCooldown()` & `waitPostCooldown()` |
| **12** | **Dán nội dung tức thời** | Giả lập thao tác Ctrl+V kết hợp thời gian trễ trước/sau | `HermesHumanSimulator.humanPaste()` |

---

## 8. Windows Installation Guide

### 8.1 Yêu Cầu Hệ Thống

* **OS:** Windows 10 (build 1903+) hoặc Windows 11.
* **Python:** Phiên bản 3.11 hoặc mới hơn.
* **Chrome:** Phiên bản 120+.
* **Quyền hạn:** Quyền Administrator để cài đặt và đăng ký registry.

### 8.2 Hướng Dẫn Từng Bước

**Bước 1: Cài đặt Python và Dependencies**
1. Cài đặt Python 3.11 (đảm bảo chọn "Add Python to PATH").
2. Chạy lệnh cài đặt thư viện:
```batch
pip install pywin32 requests[socks] PySocks
```

**Bước 2: Cấu hình và Đăng ký Native Host**
1. Khởi chạy command prompt ở quyền Administrator.
2. Đăng ký Native Messaging Host thông qua tệp `.bat` cài đặt đi kèm để tạo Registry Key tại: `HKCU\Software\Google\Chrome\NativeMessagingHosts\com.hermes.proxy_host`.

---

*Document Version: 2.1 | Spec updated for production implementation | Author: Spec Team*
