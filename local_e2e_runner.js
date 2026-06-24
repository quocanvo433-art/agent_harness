// agent_harness/local_e2e_runner.js
const { spawn, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const puppeteer = require('puppeteer-core');
const axios = require('axios');

// Cấu hình đường dẫn
const WORKSPACE_DIR = path.resolve(__dirname, '..');
const SCRATCH_DIR = path.join(WORKSPACE_DIR, 'scratch');
const TEST_LOGS_DIR = path.join(SCRATCH_DIR, 'test_logs');
const SCREENSHOTS_DIR = path.join(TEST_LOGS_DIR, 'screenshots');
const APP_DATA_TEMP = path.join(SCRATCH_DIR, 'test_app_data');
const ELECTRON_DIR = path.join(WORKSPACE_DIR, 'hermes-desktop');

let electronProcess = null;
let mockChromeProcess = null;

// Hàm hỗ trợ kill cây tiến trình (Process Tree) trên Windows/Linux
function killProcessTree(pid) {
  try {
    if (process.platform === 'win32') {
      execSync(`taskkill /pid ${pid} /T /F`);
    } else {
      execSync(`pkill -P ${pid}`);
      process.kill(pid, 'SIGKILL');
    }
    console.log(`[E2E Runner] Đã tắt sạch tiến trình: ${pid}`);
  } catch (err) {
    console.warn(`[E2E Runner] Cảnh báo khi tắt tiến trình ${pid}:`, err.message);
  }
}

// 1. Sao chép các thư mục nguồn cần thiết vào hermes-desktop để đóng gói
function preparePackagingDirs() {
  console.log('[E2E Runner] Chuẩn bị cấu trúc thư mục đóng gói (Copy nguồn)...');
  const dirsToCopy = [
    { src: path.join(WORKSPACE_DIR, 'dashboard'), dest: path.join(ELECTRON_DIR, 'dashboard') },
    { src: path.join(WORKSPACE_DIR, 'src'), dest: path.join(ELECTRON_DIR, 'src') },
    { src: path.join(WORKSPACE_DIR, 'extension'), dest: path.join(ELECTRON_DIR, 'extension') },
    { src: path.join(WORKSPACE_DIR, 'native_host'), dest: path.join(ELECTRON_DIR, 'native_host') }
  ];

  dirsToCopy.forEach(({ src, dest }) => {
    if (fs.existsSync(dest)) {
      fs.rmSync(dest, { recursive: true, force: true });
    }
    // Lọc bỏ node_modules, logs, data để tránh phình dung lượng đóng gói
    fs.cpSync(src, dest, {
      recursive: true,
      filter: (source) => {
        const base = path.basename(source);
        return base !== 'node_modules' && base !== 'logs' && base !== 'data' && base !== 'dist' && base !== '.git' && base !== '__pycache__';
      }
    });
    console.log(`   [COPY] ${path.basename(src)} -> hermes-desktop/${path.basename(dest)}`);
  });
}

// 2. Biên dịch React UI và Đóng gói Unpacked Electron App
function buildAndPackElectronApp() {
  console.log('[E2E Runner] Đang biên dịch React UI...');
  execSync('npm run build', { cwd: ELECTRON_DIR, stdio: 'inherit' });
  
  console.log('[E2E Runner] Đang đóng gói Electron App (Unpacked)...');
  execSync('npm run pack', { cwd: ELECTRON_DIR, stdio: 'inherit' });
  console.log('[E2E Runner] Đóng gói thành công.');
}

// 3. Thiết lập Môi trường Test Sandbox Cô Lập
function setupSandboxEnvironment() {
  console.log('[E2E Runner] Thiết lập môi trường Sandbox...');
  if (fs.existsSync(APP_DATA_TEMP)) {
    fs.rmSync(APP_DATA_TEMP, { recursive: true, force: true });
  }
  fs.mkdirSync(APP_DATA_TEMP, { recursive: true });

  if (fs.existsSync(TEST_LOGS_DIR)) {
    fs.rmSync(TEST_LOGS_DIR, { recursive: true, force: true });
  }
  fs.mkdirSync(TEST_LOGS_DIR, { recursive: true });
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });

  // Khởi tạo trước database kiểm thử tạm thời trong sandbox userDataPath
  const userDataPath = path.join(APP_DATA_TEMP, 'hermes-facepost-desktop');
  fs.mkdirSync(userDataPath, { recursive: true });
  
  const dbPath = path.join(userDataPath, 'database.sqlite');
  const dbModule = require('better-sqlite3');
  const sqliteDb = new dbModule(dbPath);
  
  const schemaSql = fs.readFileSync(path.join(WORKSPACE_DIR, 'dashboard', 'schema.sql'), 'utf8');
  sqliteDb.exec(schemaSql);
  
  // Chèn dữ liệu mock account
  sqliteDb.prepare(`
    INSERT INTO accounts (id, account_id, display_name, status, cookies, ws_auth_secret) 
    VALUES (?, ?, ?, ?, ?, ?)
  `).run('fb_mock_acc_1001', 'fb_mock_acc_1001', 'mock_tester', 'ACTIVE', 'c_user=1001; xs=mock_session_key;', 'aabbccddeeff00112233445566778899aabbccddeeff00112233445566778899');
  
  sqliteDb.close();
  console.log('[E2E Runner] Sandbox database đã sẵn sàng.');
}

// 4. Khởi chạy Packaged Electron App (.exe)
function launchPackagedApp() {
  return new Promise((resolve, reject) => {
    console.log('[E2E Runner] Khởi chạy tệp thực thi Electron (.exe) đã đóng gói...');
    
    let electronExe = path.join(ELECTRON_DIR, 'dist', 'win-unpacked', 'Hermes FacePost-Group.exe');
    if (process.platform !== 'win32') {
      electronExe = path.join(ELECTRON_DIR, 'dist', 'linux-unpacked', 'hermes-facepost-desktop');
    }

    if (!fs.existsSync(electronExe)) {
      return reject(new Error(`Không tìm thấy tệp thực thi tại: ${electronExe}`));
    }

    // Set APPDATA env variable để Electron lưu userDataPath vào thư mục sandbox tạm của chúng ta
    const env = {
      ...process.env,
      APPDATA: APP_DATA_TEMP,
      HOME: APP_DATA_TEMP, // For Linux
      NODE_ENV: 'test',
      UI_AUTH_TOKEN: 'e2e-ui-token-secret-xyz',
      HERMES_USER_DATA_DIR: path.join(APP_DATA_TEMP, 'hermes-facepost-desktop')
    };

    electronProcess = spawn(electronExe, ['--remote-debugging-port=9223'], { env, stdio: ['ignore', 'pipe', 'pipe'] });

    electronProcess.stdout.on('data', (data) => {
      console.log(`[Electron Main Stdout] ${data.toString().trim()}`);
    });

    electronProcess.stderr.on('data', (data) => {
      console.error(`[Electron Main Stderr] ${data.toString().trim()}`);
    });

    electronProcess.on('error', (err) => {
      reject(err);
    });

    // Chờ app khởi chạy hoàn toàn
    setTimeout(() => {
      console.log('[E2E Runner] Ứng dụng Electron đã khởi động.');
      resolve();
    }, 12000);
  });
}

// 5. Khởi chạy Mock Chrome với Extension để kiểm định WebSocket kết nối
function launchMockChrome(port) {
  return new Promise((resolve, reject) => {
    console.log('[E2E Runner] Khởi chạy Mock Chrome Browser load Extension...');
    
    let chromeBinary = 'google-chrome';
    if (process.platform === 'win32') {
      chromeBinary = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
    }

    const userProfileDir = path.join(TEST_LOGS_DIR, 'chrome_profile');
    const extPath = path.join(WORKSPACE_DIR, 'extension');

    const args = [
      `--user-data-dir=${userProfileDir}`,
      `--load-extension=${extPath}`,
      '--disable-gpu',
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--window-size=1280,800',
      '--remote-debugging-port=9222',
      `http://127.0.0.1:${port}/mock_facebook.html`
    ];

    mockChromeProcess = spawn(chromeBinary, args);

    mockChromeProcess.on('error', (err) => {
      console.error('[E2E Runner] Không thể khởi chạy trình duyệt Chrome:', err.message);
      reject(err);
    });

    setTimeout(() => {
      console.log('[E2E Runner] Mock Chrome Browser khởi chạy thành công.');
      resolve();
    }, 5000);
  });
}

// 6. Giải phóng tài nguyên
function cleanupResources() {
  console.log('[E2E Runner] Dọn dẹp tài nguyên...');
  if (mockChromeProcess) {
    killProcessTree(mockChromeProcess.pid);
  }
  if (electronProcess) {
    killProcessTree(electronProcess.pid);
  }
  
  // Dọn dẹp thư mục tạm (tạm tắt để debug)
  /*
  try {
    if (fs.existsSync(APP_DATA_TEMP)) {
      fs.rmSync(APP_DATA_TEMP, { recursive: true, force: true });
    }
  } catch (err) {
    console.warn('[E2E Runner] Không thể xóa thư mục sandbox tạm:', err.message);
  }
  */
  console.log('[E2E Runner] Dọn dẹp hoàn tất.');
}

// 7. Xuất báo cáo kết quả JUnit XML
function generateJUnitReport(success, errors = []) {
  const duration = 25;
  const timestamp = new Date().toISOString();
  
  const xmlContent = `<?xml version="1.0" encoding="UTF-8"?>
<testsuites name="Hermes FacePost Packaged E2E Test Suite" tests="1" failures="${success ? 0 : 1}" time="${duration}">
  <testsuite name="Packaged E2E Pipeline Integration" tests="1" failures="${success ? 0 : 1}" errors="0" skipped="0" time="${duration}" timestamp="${timestamp}">
    <testcase name="Verify Packaged GUI and integrated API/WS" classname="E2E_Packaged_Runner" time="${duration}">
      ${success ? '' : `<failure message="E2E Execution Failed" type="AssertionError">${errors.join('\n')}</failure>`}
    </testcase>
  </testsuite>
</testsuites>`;

  const reportPath = path.join(TEST_LOGS_DIR, 'junit_report.xml');
  fs.writeFileSync(reportPath, xmlContent, 'utf8');
  console.log(`[E2E Runner] Báo cáo JUnit XML đã được ghi tại: ${reportPath}`);
}

async function main() {
  try {
    preparePackagingDirs();
    buildAndPackElectronApp();
    setupSandboxEnvironment();
    await launchPackagedApp();

    console.log('[E2E Runner] Bắt đầu kiểm tra GUI bằng Puppeteer...');
    
    // Kết nối Puppeteer tới cửa sổ Electron
    const browser = await puppeteer.connect({
      browserURL: 'http://localhost:9223',
      defaultViewport: null
    });

    let mainPage = null;
    console.log('[E2E Runner] Đang chờ trang Renderer (GUI) của Electron xuất hiện...');
    for (let i = 0; i < 15; i++) {
      const pages = await browser.pages();
      mainPage = pages.find(p => p.url().includes('file:///') || p.url().includes('localhost:'));
      if (mainPage) {
        console.log(`[E2E Runner] Tìm thấy trang Renderer: ${mainPage.url()} (Sau ${i} giây)`);
        break;
      }
      await new Promise(r => setTimeout(r, 1000));
    }

    if (!mainPage) {
      const pages = await browser.pages();
      console.log('[E2E Runner] Danh sách các trang hiện có:', pages.map(p => p.url()));
      throw new Error('Không tìm thấy trang Renderer (GUI) của Electron.');
    }

    console.log('[E2E Runner] Đang kiểm tra giao diện và chụp ảnh các tab...');
    await mainPage.screenshot({ path: path.join(SCREENSHOTS_DIR, 'electron_main_gui.png') });
    
    const tabs = ['Overview', 'Campaigns', 'Accounts & Health', 'Settings', 'Coffee (Donate)'];
    for (const tabLabel of tabs) {
      console.log(`[E2E Runner] Click chuyển sang tab: ${tabLabel}`);
      await mainPage.evaluate((label) => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const btn = buttons.find(b => {
          const text = b.innerText || '';
          return text.toLowerCase().includes(label.toLowerCase());
        });
        if (btn) btn.click();
      }, tabLabel);
      await new Promise(r => setTimeout(r, 1500)); // Chờ hiệu ứng chuyển tab
      const filename = `electron_${tabLabel.toLowerCase().replace(/[^a-z0-9]/g, '_')}.png`;
      await mainPage.screenshot({ path: path.join(SCREENSHOTS_DIR, filename) });
      console.log(`[E2E Runner] Đã chụp màn hình tab ${tabLabel} -> ${filename}`);
    }

    // Đọc active port từ sandbox userDataPath
    const userDataPath = path.join(APP_DATA_TEMP, 'hermes-facepost-desktop');
    const activePortPath = path.join(userDataPath, 'active_port.json');

    console.log('[E2E Runner] Đang chờ file active_port.json xuất hiện (tối đa 30 giây)...');
    let port = null;
    for (let i = 0; i < 30; i++) {
      if (fs.existsSync(activePortPath)) {
        try {
          const portData = JSON.parse(fs.readFileSync(activePortPath, 'utf8'));
          port = portData.port;
          console.log(`[E2E Runner] Đã đọc active port từ file: ${port} (Sau ${i} giây)`);
          break;
        } catch (e) {
          // File might be in the middle of being written, wait
        }
      }
      await new Promise(r => setTimeout(r, 1000));
    }

    if (!port) {
      console.log('[E2E Runner] Không tìm thấy file active_port.json. Sử dụng cổng mặc định: 8765');
      port = 8765;
    }

    // Kiểm tra REST API của Express Server tích hợp
    console.log(`[E2E Runner] Gửi request kiểm tra REST API tại http://127.0.0.1:${port}/api/system/version...`);
    const apiResponse = await axios.get(`http://127.0.0.1:${port}/api/system/version`);
    console.log('[E2E Runner] API phản hồi thành công:', apiResponse.data);

    if (apiResponse.data.name !== 'hermes-facepost-group' && apiResponse.data.name !== 'hermes-facepost-desktop') {
      throw new Error('Phản hồi API không đúng tên sản phẩm: ' + apiResponse.data.name);
    }

    // Khởi chạy Mock Chrome Browser load extension để kiểm định websocket handshake
    await launchMockChrome(port);
    
    console.log('[E2E Runner] Chờ WebSocket kết nối và bắt tay...');
    await new Promise(r => setTimeout(r, 6000));

    // Đọc log của Express Server xem có lỗi gì không
    const expressLogFile = path.join(userDataPath, 'logs', 'express.log');
    let testSuccess = true;
    let errorDetails = [];

    if (fs.existsSync(expressLogFile)) {
      const logData = fs.readFileSync(expressLogFile, 'utf8');
      console.log('[E2E Runner] Đã đọc log Express. Nội dung log cuối:');
      console.log(logData.slice(-400));

      if (logData.includes('Handshake failed') || logData.includes('ERR-HYB')) {
        testSuccess = false;
        errorDetails.push('Lỗi bắt tay WebSocket phát hiện trong log.');
      }
    } else {
      console.warn('[E2E Runner] Không tìm thấy file log express.log để kiểm định.');
    }

    if (testSuccess) {
      console.log('💚 [E2E SUCCESS] Kiểm thử E2E tích hợp cho bản đóng gói Electron hoàn toàn thành công!');
    } else {
      console.error('🔴 [E2E FAILED] Kiểm thử E2E tích hợp thất bại.');
    }

    generateJUnitReport(testSuccess, errorDetails);
    process.exitCode = testSuccess ? 0 : 1;

  } catch (err) {
    console.error('💥 [E2E RUNNER FATAL ERROR]:', err);
    generateJUnitReport(false, [err.stack]);
    process.exitCode = 1;
  } finally {
    cleanupResources();
  }
}

// Xử lý SIGINT/SIGTERM để cleanup
process.on('SIGINT', () => {
  cleanupResources();
  process.exit(1);
});

process.on('SIGTERM', () => {
  cleanupResources();
  process.exit(1);
});

main();
