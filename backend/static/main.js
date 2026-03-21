// ==================== CONFIGURATION ====================
const API_URL = '/api';

// ==================== SIMILARITY ENGINE ====================
function getSimilarity(s1, s2) {
    let longer = s1; let shorter = s2;
    if (s1.length < s2.length) { longer = s2; shorter = s1; }
    const longerLength = longer.length;
    if (longerLength === 0) return 1.0;
    return (longerLength - editDistance(longer, shorter)) / parseFloat(longerLength);
}

function editDistance(s1, s2) {
    s1 = s1.toLowerCase(); s2 = s2.toLowerCase();
    const costs = [];
    for (let i = 0; i <= s1.length; i++) {
        let lastValue = i;
        for (let j = 0; j <= s2.length; j++) {
            if (i === 0) costs[j] = j;
            else {
                if (j > 0) {
                    let newValue = costs[j - 1];
                    if (s1.charAt(i - 1) !== s2.charAt(j - 1))
                        newValue = Math.min(Math.min(newValue, lastValue), costs[j]) + 1;
                    costs[j - 1] = lastValue; lastValue = newValue;
                }
            }
        }
        if (i > 0) costs[s2.length] = lastValue;
    }
    return costs[s2.length];
}

// ==================== STATE MANAGEMENT ====================
let currentAdmin = null;
let logs = [];
let fleet = [];
let currentMode = 'ENTRY';
let isAiReady = false;
let worker = null;

// ==================== DOM CACHE ====================
const DOM = {
    loginModal: null,
    app: null,
    loggedUser: null,
    loginForm: null,
    adminId: null,
    adminPassword: null,
    videoFeed: null,
    scanStatus: null,
    scannedPlate: null,
    busRouteInfo: null,
    busDriverName: null,
    busCapacity: null,
    countInside: null,
    countTotalEntries: null,
    countTotalExits: null,
    inCampusBadge: null,
    outCampusBadge: null,
    liveFleetList: null,
    liveFleetOutList: null,
    busLogTableBody: null,
    fleetTableBody: null,
    currentDateDisplay: null,
    navLinks: null,
    views: null,
    logoutBtn: null,
    exportBtn: null,
    modeEntry: null,
    modeExit: null,
    simulateBtn: null,
    addBusForm: null,
    mirrorAI: null,
    notificationArea: null
};

function initDOM() {
    DOM.loginModal = document.getElementById('loginModal');
    DOM.app = document.getElementById('app');
    DOM.loggedUser = document.getElementById('loggedUser');
    DOM.loginForm = document.getElementById('loginForm');
    DOM.adminId = document.getElementById('adminId');
    DOM.adminPassword = document.getElementById('adminPassword');
    DOM.videoFeed = document.getElementById('videoFeed');
    DOM.scanStatus = document.getElementById('scanStatus');
    DOM.scannedPlate = document.getElementById('scannedPlate');
    DOM.busRouteInfo = document.getElementById('busRouteInfo');
    DOM.busDriverName = document.getElementById('busDriverName');
    DOM.busCapacity = document.getElementById('busCapacity');
    DOM.countInside = document.getElementById('countInside');
    DOM.countTotalEntries = document.getElementById('countTotalEntries');
    DOM.countTotalExits = document.getElementById('countTotalExits');
    DOM.inCampusBadge = document.getElementById('inCampusBadge');
    DOM.outCampusBadge = document.getElementById('outCampusBadge');
    DOM.liveFleetList = document.getElementById('liveFleetList');
    DOM.liveFleetOutList = document.getElementById('liveFleetOutList');
    DOM.busLogTableBody = document.querySelector('#busLogTable tbody');
    DOM.fleetTableBody = document.querySelector('#fleetTable tbody');
    DOM.currentDateDisplay = document.getElementById('currentDateDisplay');
    DOM.navLinks = document.querySelectorAll('.nav-links li');
    DOM.views = document.querySelectorAll('.view');
    DOM.logoutBtn = document.getElementById('logoutBtn');
    DOM.exportBtn = document.getElementById('exportLogs');
    DOM.modeEntry = document.getElementById('modeEntry');
    DOM.modeExit = document.getElementById('modeExit');
    DOM.simulateBtn = document.getElementById('simulateScan');
    DOM.addBusForm = document.getElementById('addBusForm');
    DOM.mirrorAI = document.getElementById('mirrorAI');
    DOM.notificationArea = document.getElementById('notification-area');
}

// ==================== AUTHENTICATION ====================
async function handleLogin(e) {
    if (e) e.preventDefault();
    console.log("Attempting login...");
    const id = DOM.adminId.value.trim();
    const password = DOM.adminPassword.value.trim();
    if (!id || !password) { showNotification('Enter ID and Password', 'error'); return; }
    try {
        const res = await fetch(`${API_URL}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id, password })
        });
        if (res.status === 401) { showNotification('Invalid ID or Password', 'error'); return; }
        const data = await res.json();
        if (res.ok) {
            currentAdmin = data;
            localStorage.setItem('currentAdmin', JSON.stringify(data));
            showDashboard(data);
        } else { showNotification(data.error || 'Server error', 'error'); }
    } catch (err) { showNotification('Backend offline', 'error'); }
}

function showDashboard(user) {
    if (DOM.loginModal) DOM.loginModal.classList.add('hidden');
    if (DOM.app) DOM.app.style.display = 'block';
    if (DOM.loggedUser) DOM.loggedUser.innerText = user.id + (user.role === 'scanner' ? ' (CAMERA)' : ' (ADMIN)');
    showNotification(`Logged in as ${user.id}`, 'success');
    
    // Role based visibility
    if (user.role === 'scanner') {
        document.querySelectorAll('.nav-links li').forEach(li => {
            if (li.getAttribute('data-view') !== 'bus-entry') li.style.display = 'none';
        });
        // Force monitoring view
        const targetView = document.getElementById('bus-entry-view');
        if (targetView) {
            document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
            targetView.classList.add('active');
            
            // HIDE tracking info for scanners
            const tracking = targetView.querySelector('.tracking-column');
            if (tracking) tracking.style.display = 'none';
            // Center the scanner card
            const grid = targetView.querySelector('.dashboard-grid');
            if (grid) grid.style.display = 'block';
        }
    } else {
        document.querySelectorAll('.nav-links li').forEach(li => li.style.display = 'block');
        const tracking = document.querySelector('.tracking-column');
        if (tracking) tracking.style.display = 'grid'; // Restore
    }

    initializeApp();
}

function handleLogout() {
    if (confirm('Are you sure you want to logout?')) {
        localStorage.removeItem('currentAdmin');
        location.reload();
    }
}

function checkAuth() {
    const stored = localStorage.getItem('currentAdmin');
    if (stored) {
        try {
            currentAdmin = JSON.parse(stored);
            showDashboard(currentAdmin);
        } catch (e) { localStorage.removeItem('currentAdmin'); }
    }
}

// ==================== APP INITIALIZATION ====================
async function initializeApp() {
    setupEventListeners();
    updateDate();
    await refreshData();
    initCamera();
    initAI();
    setInterval(refreshData, 10000);
    setInterval(autoScanTask, 5000);
}

function setupEventListeners() {
    if (DOM.logoutBtn) DOM.logoutBtn.onclick = handleLogout;
    if (DOM.exportBtn) DOM.exportBtn.onclick = downloadCSV;
    if (DOM.simulateBtn) DOM.simulateBtn.onclick = performAIPlateScan;
    if (DOM.navLinks) {
        DOM.navLinks.forEach(link => {
            link.onclick = () => {
                const target = link.getAttribute('data-view');
                if (!target) return;
                DOM.navLinks.forEach(l => l.classList.remove('active'));
                link.classList.add('active');
                DOM.views.forEach(v => v.classList.remove('active'));
                const targetView = document.getElementById(`${target}-view`);
                if (targetView) targetView.classList.add('active');
                if (target === 'bus-entry') initCamera();
                refreshData();
            };
        });
    }
    if (DOM.modeEntry) DOM.modeEntry.onclick = () => {
        currentMode = 'ENTRY'; DOM.modeEntry.classList.add('active'); DOM.modeExit.classList.remove('active');
    };
    if (DOM.modeExit) DOM.modeExit.onclick = () => {
        currentMode = 'EXIT'; DOM.modeExit.classList.add('active'); DOM.modeEntry.classList.remove('active');
    };
    if (DOM.addBusForm) {
        DOM.addBusForm.onsubmit = async (e) => {
            e.preventDefault();
            const inputs = e.target.querySelectorAll('input');
            const data = {
                plate: inputs[0].value.toUpperCase().replace(/[^A-Z0-9]/g, ''),
                serial: inputs[1].value.toUpperCase(),
                route: inputs[2].value
            };
            const res = await fetch(`${API_URL}/fleet`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (res.ok) { refreshData(); e.target.reset(); showNotification('Bus added to fleet'); }
            else { showNotification('Failed to add bus', 'error'); }
        };
    }
}

// ==================== DATA OPERATIONS ====================
async function refreshData() {
    try {
        const [fleetRes, logsRes, statsRes] = await Promise.all([
            fetch(`${API_URL}/fleet`),
            fetch(`${API_URL}/logs`),
            fetch(`${API_URL}/stats`)
        ]);
        fleet = await fleetRes.json();
        logs = await logsRes.json();
        const stats = await statsRes.json();
        updateUI(stats);
    } catch (err) { console.error("Data Refresh Error:", err); }
}

function updateUI(stats) {
    if (DOM.countInside) DOM.countInside.innerText = stats.inside;
    if (DOM.countTotalEntries) DOM.countTotalEntries.innerText = stats.entries;
    if (DOM.countTotalExits) DOM.countTotalExits.innerText = stats.exits;
    if (DOM.inCampusBadge) DOM.inCampusBadge.innerText = stats.inside;
    if (DOM.outCampusBadge) DOM.outCampusBadge.innerText = Math.max(0, fleet.length - stats.inside);
    renderLogs(); renderFleetStatus(); renderFleetTable();
}

function renderLogs() {
    if (!DOM.busLogTableBody) return;
    DOM.busLogTableBody.innerHTML = logs.slice(0, 10).map(log => `
        <tr>
            <td><span class="type-badge type-${log.type.toLowerCase()}">${log.type}</span></td>
            <td><span class="plate-badge">${log.plate}</span></td>
            <td>${log.serial || '--'}</td>
            <td>${log.time}</td>
        </tr>
    `).join('');
}

function renderFleetStatus() {
    if (!DOM.liveFleetList || !DOM.liveFleetOutList) return;
    const insidePlates = new Set();
    [...logs].sort((a, b) => a.id - b.id).forEach(l => {
        if (l.type === 'ENTRY') insidePlates.add(l.plate);
        else insidePlates.delete(l.plate);
    });
    const inside = fleet.filter(b => insidePlates.has(b.plate));
    const outside = fleet.filter(b => !insidePlates.has(b.plate));
    DOM.liveFleetList.innerHTML = inside.map(b => `<div class="live-bus-item"><span class="bus-plate">${b.plate}</span><span class="bus-route">${b.route}</span></div>`).join('') || 'None';
    DOM.liveFleetOutList.innerHTML = outside.map(b => `<div class="live-bus-item"><span class="bus-plate">${b.plate}</span><span class="bus-route">${b.route}</span></div>`).join('') || 'All Inside';
}

function renderFleetTable() {
    if (!DOM.fleetTableBody) return;
    DOM.fleetTableBody.innerHTML = fleet.map(b => `
        <tr><td>${b.plate}</td><td>${b.serial}</td><td>${b.route}</td>
        <td><button class="btn-del" onclick="deleteBus('${b.plate}')">🗑️</button></td></tr>
    `).join('');
}

async function deleteBus(plate) {
    if (confirm(`Delete ${plate}?`)) {
        await fetch(`${API_URL}/fleet/${plate}`, { method: 'DELETE' });
        refreshData();
    }
}

// ==================== AI & CAMERA ====================
async function initAI() {
    try {
        worker = await Tesseract.createWorker('eng');
        await worker.setParameters({ tessedit_char_whitelist: '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ' });
        isAiReady = true; console.log("AI Ready.");
    } catch (e) { console.error("AI Init Error:", e); }
}

async function initCamera() {
    console.log("Initializing camera...");
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        let msg = "Camera API not available. This is likely because you are on an insecure 'http' page. Try using 'https' or use Ngrok.";
        console.error(msg);
        if (DOM.scanStatus) DOM.scanStatus.innerText = 'HTTPS Required for Camera';
        alert(msg);
        return;
    }
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment', width: { ideal: 1280 } } });
        console.log("Camera stream obtained.");
        if (DOM.videoFeed) DOM.videoFeed.srcObject = stream;
        if (DOM.scanStatus) DOM.scanStatus.innerText = 'Monitoring...';
    } catch (e) { 
        console.error("Camera access error:", e);
        if (DOM.scanStatus) DOM.scanStatus.innerText = 'Camera Access Denied'; 
    }
}

function autoScanTask() {
    const entryView = document.getElementById('bus-entry-view');
    if (currentAdmin && entryView && entryView.classList.contains('active') && isAiReady) {
        performAIPlateScan();
    }
}

async function performAIPlateScan() {
    if (!isAiReady || (DOM.simulateBtn && DOM.simulateBtn.classList.contains('scanning'))) return;

    const vw = DOM.videoFeed.videoWidth; const vh = DOM.videoFeed.videoHeight;
    const cropW = vw * 0.65; const cropH = vh * 0.30;
    const cropX = (vw - cropW) / 2; const cropY = (vh - cropH) / 2;

    const canvas = document.createElement('canvas');
    canvas.width = cropW; canvas.height = cropH;
    const ctx = canvas.getContext('2d');
    if (DOM.mirrorAI && DOM.mirrorAI.checked) { ctx.translate(canvas.width, 0); ctx.scale(-1, 1); }
    ctx.drawImage(DOM.videoFeed, cropX, cropY, cropW, cropH, 0, 0, cropW, cropH);
    ctx.filter = 'contrast(1.6) grayscale(1) brightness(1.1)';
    ctx.drawImage(canvas, 0, 0);

    if (DOM.simulateBtn) DOM.simulateBtn.classList.add('scanning');
    if (DOM.scanStatus) DOM.scanStatus.innerText = 'AI SCANNING...';

    try {
        const result = await worker.recognize(canvas);
        const text = result.data.text.toUpperCase().replace(/[^A-Z0-9]/g, '').trim();
        if (text.length < 4) return; // Ignore very short noise

        console.log("AI DETECTED:", text);

        let bestMatch = null;
        let highestSimilarity = 0;

        fleet.forEach(bus => {
            // Normalize fleet plate for matching
            const cleanFleetPlate = bus.plate.replace(/[^A-Z0-9]/g, '').toUpperCase();
            const similarity = getSimilarity(text, cleanFleetPlate);

            // Exact contains check bonus
            const bonus = (text.includes(cleanFleetPlate) || cleanFleetPlate.includes(text)) ? 0.3 : 0;
            const finalScore = similarity + bonus;

            if (finalScore > highestSimilarity) {
                highestSimilarity = finalScore;
                bestMatch = bus;
            }
        });

        // Use a stricter threshold (Similarity + Bonus must be >= 0.85)
        if (bestMatch && highestSimilarity >= 0.85) {
            updateScanInfo("Authorized Vehicle Captured", bestMatch);
            // Send the ORIGINAL DB PLATE back for foreign key consistency
            const regRes = await fetch(`${API_URL}/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ plate: bestMatch.plate, type: currentMode })
            });

            if (regRes.ok) {
                refreshData();
                showNotification(`Registered: ${bestMatch.plate} (Confidence: ${Math.round(highestSimilarity * 100)}%)`);
            } else {
                const errorData = await regRes.json();
                console.error("Registration failed:", errorData);
                showNotification(`FAILED to Register: ${errorData.message || 'Check connection'}`, 'error');
            }
        } else if (text.length >= 6) {
            updateScanInfo("UNAUTHORIZED VEHICLE", { plate: text, route: 'NOT IN DATABASE', driver: 'N/A', capacity: 'N/A' });
            showNotification(`Unknown Plate: ${text}`, 'error');
        }
    } catch (e) { console.error("Process Error:", e); }
    finally {
        if (DOM.simulateBtn) DOM.simulateBtn.classList.remove('scanning');
        if (DOM.scanStatus) DOM.scanStatus.innerText = 'Watching...';
    }
}

function updateScanInfo(title, bus) {
    if (document.getElementById('detectedBusTitle')) document.getElementById('detectedBusTitle').innerText = title;
    if (DOM.scannedPlate) DOM.scannedPlate.innerText = bus.plate;
    if (DOM.busRouteInfo) DOM.busRouteInfo.innerText = bus.route;
    if (DOM.busDriverName) DOM.busDriverName.innerText = bus.driver || 'N/A';
    if (DOM.busCapacity) DOM.busCapacity.innerText = bus.capacity || 'N/A';
}

function showNotification(msg, type = 'success') {
    if (!DOM.notificationArea) return;
    const n = document.createElement('div');
    n.className = `notification ${type} show`; n.innerText = msg;
    DOM.notificationArea.appendChild(n);
    setTimeout(() => { n.classList.remove('show'); setTimeout(() => n.remove(), 500); }, 3000);
}

function downloadCSV() {
    const csv = "Action,Plate,Serial,Time\n" + logs.map(l => `${l.type},${l.plate},${l.serial || ''},${l.time}`).join("\n");
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = 'Fleet_Log.csv'; a.click();
}

function updateDate() { if (DOM.currentDateDisplay) DOM.currentDateDisplay.innerText = new Date().toLocaleDateString(); }

document.addEventListener('DOMContentLoaded', () => { initDOM(); if (DOM.loginForm) DOM.loginForm.addEventListener('submit', handleLogin); checkAuth(); });
