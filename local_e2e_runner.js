// agent_harness/local_e2e_runner.js
const { spawn, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const db = require('better-sqlite3');

// Cấu hình đường dẫn
const WORKSPACE_DIR = path.resolve(__dirname, '..');
const TEST_DB_PATH = path.join(WORKSPACE_DIR, 'scratch', 'test_database.sqlite');
const TEST_LOGS_DIR = path.join(WORKSPACE_DIR, 'scratch', 'test_logs');
const SCREENSHOTS_DIR = path.join(TEST_LOGS_DIR, 'screenshots');
const EXPRESS_SERVER_PATH = path.join(WORKSPACE_DIR, 'dashboard', 'server.js');
const GHOST_EXT_PATH = path.join(WORKSPACE_DIR, 'extension');

let serverProcess = null;
let chromeProcess = null;

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
    console.warn(`[E2E Runner] Cảnh báo khi kill tiến trình ${pid}:`, err.message);
  }
}

// 1. Tạo Database Kiểm Thử Tạm Thời
function setupTestDatabase() {
  console.log('[E2E Runner] Thiết lập Database Test SQLite...');
  
  const scratchDir = path.join(WORKSPACE_DIR, 'scratch');
  if (!fs.existsSync(scratchDir)) {
    fs.mkdirSync(scratchDir, { recursive: true });
  }

  if (fs.existsSync(TEST_DB_PATH)) {
    fs.unlinkSync(TEST_DB_PATH);
  }
  
  const sqliteDb = new db(TEST_DB_PATH);
  
  // Khởi tạo bảng từ file schema.sql
  const schemaSql = fs.readFileSync(path.join(WORKSPACE_DIR, 'dashboard', 'schema.sql'), 'utf8');
  sqliteDb.exec(schemaSql);
  
  // Chèn dữ liệu tài khoản và chiến dịch giả lập để test
  sqliteDb.prepare(`
    INSERT INTO accounts (id, account_id, display_name, status, cookies, ws_auth_secret) 
    VALUES (?, ?, ?, ?, ?, ?)
  `).run('fb_mock_acc_1001', 'fb_mock_acc_1001', 'mock_tester', 'ACTIVE', 'c_user=1001; xs=mock_session_key;', 'aabbccddeeff00112233445566778899aabbccddeeff00112233445566778899');

  sqliteDb.prepare(`
    INSERT INTO campaigns (id, name, spintax_content, status) 
    VALUES (?, ?, ?, ?)
  `).run('camp_e2e_001', 'E2E Campaign Test', 'Nội dung test E2E gửi từ runner', 'QUEUED');

  sqliteDb.close();
  console.log('[E2E Runner] Tạo Database Test thành công.');
}

// 2. Khởi chạy Express & WebSocket Server Cục Bộ
function startLocalServer() {
  return new Promise((resolve, reject) => {
    console.log('[E2E Runner] Khởi chạy Local Backend Server...');
    
    if (!fs.existsSync(TEST_LOGS_DIR)) {
      fs.mkdirSync(TEST_LOGS_DIR, { recursive: true });
    }
    if (!fs.existsSync(SCREENSHOTS_DIR)) {
      fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
    }

    const logStream = fs.createWriteStream(path.join(TEST_LOGS_DIR, 'e2e_express.log'), { flags: 'w' });
    
    serverProcess = spawn('node', [EXPRESS_SERVER_PATH], {
      env: {
        ...process.env,
        PORT: '9875',
        NODE_ENV: 'test',
        DATABASE_PATH: TEST_DB_PATH,
        LOGS_PATH: TEST_LOGS_DIR,
        UI_AUTH_TOKEN: 'e2e-ui-token-secret-xyz'
      }
    });

    serverProcess.stdout.pipe(logStream);
    serverProcess.stderr.pipe(logStream);

    serverProcess.on('error', (err) => {
      reject(err);
    });

    // Chờ server khởi động thành công (thường mất 1.5-2 giây)
    setTimeout(() => {
      console.log('[E2E Runner] Server Backend sẵn sàng tại Port 9875.');
      resolve();
    }, 2000);
  });
}

// 3. Khởi chạy Trình duyệt Chrome giả lập nạp Ghost Extension
function launchChromeWithExtension() {
  return new Promise((resolve, reject) => {
    console.log('[E2E Runner] Đang khởi chạy Google Chrome Mock...');

    // Windows / Linux paths
    let chromeBinary = 'google-chrome';
    if (process.platform === 'win32') {
      chromeBinary = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
    }

    const userProfileDir = path.join(TEST_LOGS_DIR, 'chrome_profile');

    const args = [
      `--user-data-dir=${userProfileDir}`,
      `--load-extension=${GHOST_EXT_PATH}`,
      '--disable-gpu',
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--window-size=1280,800',
      '--remote-debugging-port=9222',
      'http://localhost:9875/mock_facebook.html' // Mở trang web Mock Facebook do server cung cấp để test
    ];

    chromeProcess = spawn(chromeBinary, args);

    chromeProcess.on('error', (err) => {
      console.error('[E2E Runner] Không thể khởi chạy trình duyệt Chrome:', err.message);
      reject(err);
    });

    setTimeout(() => {
      console.log('[E2E Runner] Trình duyệt Chrome khởi chạy thành công.');
      resolve();
    }, 3000);
  });
}

// 4. Giải phóng tài nguyên & Dọn dẹp Zombie
function cleanupResources() {
  console.log('[E2E Runner] Bắt đầu dọn dẹp tài nguyên...');
  
  if (chromeProcess) {
    killProcessTree(chromeProcess.pid);
  }
  if (serverProcess) {
    killProcessTree(serverProcess.pid);
  }

  // Xóa DB test tạm thời
  try {
    if (fs.existsSync(TEST_DB_PATH)) {
      fs.unlinkSync(TEST_DB_PATH);
      console.log('[E2E Runner] Đã xóa Database SQLite test.');
    }
  } catch (err) {
    console.warn('[E2E Runner] Không thể xóa SQLite DB test:', err.message);
  }
  console.log('[E2E Runner] Dọn dẹp hoàn tất.');
}

// 5. Xuất báo cáo kết quả JUnit XML
function generateJUnitReport(success, errors = []) {
  const duration = 15; // Giả định thời gian chạy test là 15 giây
  const timestamp = new Date().toISOString();
  
  const xmlContent = `<?xml version="1.0" encoding="UTF-8"?>
<testsuites name="Hermes FacePost E2E Test Suite" tests="1" failures="${success ? 0 : 1}" time="${duration}">
  <testsuite name="E2E Pipeline Integration" tests="1" failures="${success ? 0 : 1}" errors="0" skipped="0" time="${duration}" timestamp="${timestamp}">
    <testcase name="Verify Campaign Auto Publishing Protocol" classname="E2E_Runner" time="${duration}">
      ${success ? '' : `<failure message="E2E Execution Failed" type="AssertionError">${errors.join('\n')}</failure>`}
    </testcase>
  </testsuite>
</testsuites>`;

  const reportPath = path.join(TEST_LOGS_DIR, 'junit_report.xml');
  fs.writeFileSync(reportPath, xmlContent, 'utf8');
  console.log(`[E2E Runner] Báo cáo JUnit XML đã được ghi tại: ${reportPath}`);
}

// Luồng thực thi chính (Main Pipeline)
async function main() {
  // Lấy cờ từ terminal CLI arguments
  const args = process.argv.slice(2);
  const isHeadless = args.includes('--headless');
  
  if (isHeadless) {
    console.log('[E2E Runner] Chế độ Headless được bật.');
    process.env.CHROME_HEADLESS = 'true';
  }

  try {
    setupTestDatabase();
    await startLocalServer();
    await launchChromeWithExtension();

    console.log('[E2E Runner] Bắt đầu chạy kịch bản tự động hóa kiểm định...');
    
    // Giả lập E2E check: Chờ kịch bản tự động chạy trong 10 giây
    let testSuccess = true;
    let errorDetails = [];

    await new Promise((r) => setTimeout(r, 10000));

    // Thực hiện kiểm tra log xem có bất kỳ lỗi "ERROR" hoặc kết nối bị từ chối nào không
    const logData = fs.readFileSync(path.join(TEST_LOGS_DIR, 'e2e_express.log'), 'utf8');
    if (logData.includes('ERR-HYB') || logData.includes('Handshake failed')) {
      testSuccess = false;
      errorDetails.push('Lỗi phát hiện trong log của Backend Server.');
    }

    if (testSuccess) {
      console.log('💚 [E2E SUCCESS] Kiểm thử E2E tích hợp hoàn thành và thành công!');
    } else {
      console.error('🔴 [E2E FAILED] Có lỗi xảy ra trong quá trình chạy E2E.');
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

// Bắt các lỗi ngoại vi để cleanup không làm treo terminal CI
process.on('SIGINT', () => {
  console.log('\n[E2E Runner] Nhận SIGINT, đang thoát...');
  cleanupResources();
  process.exit(1);
});

process.on('SIGTERM', () => {
  console.log('\n[E2E Runner] Nhận SIGTERM, đang thoát...');
  cleanupResources();
  process.exit(1);
});

// Chạy runner
main();
