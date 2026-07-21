const API_BASE = '/trainerhub/api';

let state = {
    users: [],
    trainers: [],
    patterns: [],
    games: [],
    stats: {},
    userFilter: '',
    userStatusFilter: '',
    trainerFilter: '',
    trainerTypeFilter: '',
    patternFilter: '',
    patternStatusFilter: ''
};

async function apiCall(endpoint, method='GET', body=null) {
    const token = localStorage.getItem('trainerhub_admin_token');
    const opts = {
        method,
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    };
    if (body) opts.body = JSON.stringify(body);
    try {
        const r = await fetch(`${API_BASE}/${endpoint}`, opts);
        if (r.status === 401) { logout(); return { success: false, error: 'Unauthorized' }; }
        return r.json();
    } catch (e) {
        return { success: false, error: e.message };
    }
}

/* Auth */
async function login() {
    const pass = document.getElementById('adminPass').value;
    const data = await apiCall('admin.php?action=login', 'POST', { password: pass });
    if (data.success) {
        localStorage.setItem('trainerhub_admin_token', data.token);
        showApp();
    } else {
        document.getElementById('error').textContent = data.error;
    }
}

function showApp() {
    document.getElementById('loginPage').classList.add('hidden');
    document.getElementById('app').classList.remove('hidden');
    showTab('dashboard');
}

function logout() {
    localStorage.removeItem('trainerhub_admin_token');
    location.reload();
}

/* Navigation */
function showTab(tab) {
    document.querySelectorAll('.tab-section').forEach(t => t.classList.add('hidden'));
    document.querySelectorAll('.nav-item').forEach(t => t.classList.remove('active'));
    document.getElementById(tab).classList.remove('hidden');
    document.querySelector(`.nav-item[data-tab="${tab}"]`).classList.add('active');
    
    if (tab === 'dashboard') loadDashboard();
    if (tab === 'users') loadUsers();
    if (tab === 'trainers') loadTrainers();
    if (tab === 'community') loadCommunityPatterns();
    if (tab === 'leaderboard') loadLeaderboard();
    if (tab === 'system') loadSystem();
}

/* Dashboard */
async function loadDashboard() {
    const data = await apiCall('admin.php?action=stats');
    if (!data.success) return;
    state.stats = data;
    document.getElementById('statsGrid').innerHTML = `
        <div class="stat-card"><i class="fas fa-gamepad"></i><h3>${data.games || 0}</h3><p>Spiele</p></div>
        <div class="stat-card"><i class="fas fa-bolt"></i><h3>${data.trainers || 0}</h3><p>Trainer</p></div>
        <div class="stat-card"><i class="fas fa-users"></i><h3>${data.users || 0}</h3><p>Benutzer</p></div>
        <div class="stat-card"><i class="fas fa-download"></i><h3>${data.downloads || 0}</h3><p>Downloads</p></div>
        <div class="stat-card"><i class="fas fa-crown"></i><h3>${data.premium_users || 0}</h3><p>Premium User</p></div>
        <div class="stat-card"><i class="fas fa-puzzle-piece"></i><h3>${data.community_patterns || 0}</h3><p>Community Patterns</p></div>
    `;
}

async function refreshAll() {
    await apiCall('admin-clear-cache.php', 'POST', {});
    loadDashboard();
}

async function syncStats() {
    const data = await apiCall('admin.php?action=sync_stats', 'POST');
    alert(data.message || data.error);
    loadDashboard();
}

async function clearCache() {
    const data = await apiCall('admin-clear-cache.php', 'POST');
    alert(data.message || data.error);
}

async function purgeLogs() {
    const data = await apiCall('admin.php?action=purge_logs', 'POST');
    alert(data.message || data.error);
}

/* Users */
async function loadUsers() {
    const data = await apiCall('admin.php?action=list_users');
    if (!data.success) return alert(data.error);
    state.users = data.users || [];
    renderUsers();
}

function renderUsers() {
    const q = state.userFilter.toLowerCase();
    const status = state.userStatusFilter;
    const filtered = state.users.filter(u => {
        const matches = !q || (u.email || '').toLowerCase().includes(q) || (u.username || '').toLowerCase().includes(q);
        const statusOk = !status || u.subscription_status === status || (status === 'premium' && u.subscription_status !== 'free');
        return matches && statusOk;
    });
    
    document.getElementById('usersTable').innerHTML = filtered.map(u => {
        const isPremium = u.subscription_status && u.subscription_status !== 'free';
        return `<tr>
            <td>${u.id}</td>
            <td>${escapeHtml(u.email)}</td>
            <td>${escapeHtml(u.username || '-')}</td>
            <td><span class="status-badge ${isPremium ? 'status-premium' : 'status-free'}">${isPremium ? 'Premium' : 'Free'}</span></td>
            <td>${u.created_at ? new Date(u.created_at * 1000).toLocaleDateString() : '-'}</td>
            <td>
                <button class="btn ${isPremium ? 'btn-secondary' : 'btn-primary'}" style="padding:6px 12px; font-size:0.8rem;" onclick="togglePremium(${u.id}, ${!isPremium})">
                    ${isPremium ? 'Premium entfernen' : 'Premium geben'}
                </button>
                <button class="btn btn-secondary" style="padding:6px 12px; font-size:0.8rem; margin-left:6px;" onclick="viewUser(${u.id})">
                    Details
                </button>
            </td>
        </tr>`;
    }).join('');
}

function filterUsers() {
    state.userFilter = document.getElementById('userSearch').value;
    state.userStatusFilter = document.getElementById('userStatusFilter').value;
    renderUsers();
}

async function togglePremium(userId, enable) {
    const action = enable ? 'grant_premium' : 'revoke_premium';
    const days = enable ? prompt('Wie viele Tage Premium?', '30') : null;
    const body = { user_id: userId };
    if (enable && days) body.days = parseInt(days);
    const data = await apiCall(`admin.php?action=${action}`, 'POST', body);
    if (data.success) loadUsers(); else alert(data.error);
}

async function viewUser(userId) {
    const user = state.users.find(u => u.id === userId);
    if (!user) return;
    const logs = await apiCall(`trainer-logs.php?action=list&limit=20`); // needs user filter in backend ideally
    openModal('Benutzerdetails', `
        <p><strong>ID:</strong> ${user.id}</p>
        <p><strong>E-Mail:</strong> ${escapeHtml(user.email)}</p>
        <p><strong>Benutzername:</strong> ${escapeHtml(user.username || '-')}</p>
        <p><strong>Status:</strong> ${user.subscription_status}</p>
        <p><strong>Registriert:</strong> ${new Date(user.created_at * 1000).toLocaleString()}</p>
        <hr style="border-color:var(--border); margin:1rem 0;">
        <h4>Letzte Aktivierungen</h4>
        <div id="userLogPreview" style="color:var(--muted); font-size:0.9rem;">Lade...</div>
    `);
}

function exportUsers() {
    const csv = [['ID','Email','Username','Status','Created'].join(',')].concat(
        state.users.map(u => [u.id, u.email, u.username || '', u.subscription_status, u.created_at].join(','))
    ).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `trainerhub-users-${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
}

/* Trainers */
async function loadTrainers() {
    const data = await apiCall('admin.php?action=list_trainers');
    if (!data.success) return alert(data.error);
    state.trainers = data.trainers || [];
    renderTrainers();
}

function renderTrainers() {
    const q = state.trainerFilter.toLowerCase();
    const type = state.trainerTypeFilter;
    const filtered = state.trainers.filter(t => {
        const matches = !q || (t.game_name || '').toLowerCase().includes(q) || (t.name || '').toLowerCase().includes(q);
        const typeOk = !type || (type === 'premium' ? t.is_premium : !t.is_premium);
        return matches && typeOk;
    });
    document.getElementById('trainersTable').innerHTML = filtered.map(t => `<tr>
        <td>${t.id}</td>
        <td>${escapeHtml(t.game_name)}</td>
        <td>${escapeHtml(t.name)}</td>
        <td><span class="status-badge ${t.is_premium ? 'status-premium' : 'status-free'}">${t.is_premium ? 'Premium' : 'Free'}</span></td>
        <td>${t.patterns.length}</td>
        <td>
            <button class="btn btn-primary" style="padding:6px 12px; font-size:0.8rem;" onclick="showPatterns(${t.id})">Patterns</button>
            <button class="btn btn-secondary" style="padding:6px 12px; font-size:0.8rem; margin-left:6px;" onclick="editTrainer(${t.id})">Edit</button>
            <button class="btn btn-danger" style="padding:6px 12px; font-size:0.8rem; margin-left:6px;" onclick="deleteTrainer(${t.id})">Löschen</button>
        </td>
    </tr>`).join('');
}

function filterTrainers() {
    state.trainerFilter = document.getElementById('trainerSearch').value;
    state.trainerTypeFilter = document.getElementById('trainerTypeFilter').value;
    renderTrainers();
}

async function deleteTrainer(id) {
    if (!confirm('Trainer wirklich löschen?')) return;
    const data = await apiCall('admin.php?action=delete_trainer', 'POST', { trainer_id: id });
    if (data.success) loadTrainers(); else alert(data.error);
}

function openAddTrainerModal() {
    const gameOptions = state.games.map(g => `<option value="${g.id}">${escapeHtml(g.name)}</option>`).join('');
    openModal('Trainer hinzufügen', `
        <div class="form-group"><label>Spiel</label><select id="newTrainerGame">${gameOptions}</select></div>
        <div class="form-group"><label>Name</label><input type="text" id="newTrainerName" placeholder="z.B. Unendlich Geld"></div>
        <div class="form-group"><label>Beschreibung</label><textarea id="newTrainerDesc" rows="3" placeholder="Was macht dieser Trainer?"></textarea></div>
        <div class="form-group"><label>Cheat Typ</label><select id="newTrainerType"><option value="memory_scan">Memory Scan</option><option value="console">Console Command</option><option value="savegame">Savegame Editor</option><option value="smapi">SMAPI Bridge</option></select></div>
        <div class="form-group"><label><input type="checkbox" id="newTrainerPremium" style="width:auto; margin-right:8px;">Premium</label></div>
    `, async () => {
        const body = {
            game_id: parseInt(document.getElementById('newTrainerGame').value),
            name: document.getElementById('newTrainerName').value,
            description: document.getElementById('newTrainerDesc').value,
            cheat_type: document.getElementById('newTrainerType').value,
            is_premium: document.getElementById('newTrainerPremium').checked ? 1 : 0
        };
        const data = await apiCall('admin.php?action=add_trainer', 'POST', body);
        if (data.success) { closeModal(); loadTrainers(); }
        else alert(data.error);
    });
}

function openAddGameModal() {
    openModal('Spiel hinzufügen', `
        <div class="form-row">
            <div class="form-group"><label>Name</label><input type="text" id="newGameName" placeholder="z.B. Stardew Valley"></div>
            <div class="form-group"><label>Slug</label><input type="text" id="newGameSlug" placeholder="stardew-valley"></div>
        </div>
        <div class="form-row">
            <div class="form-group"><label>Prozess-Name</label><input type="text" id="newGameProcess" placeholder="Stardew Valley.exe"></div>
            <div class="form-group"><label>Genre</label><input type="text" id="newGameGenre" placeholder="Farming Sim"></div>
        </div>
        <div class="form-group"><label>Steam App ID</label><input type="number" id="newGameSteamId" placeholder="413150"></div>
    `, async () => {
        const body = {
            name: document.getElementById('newGameName').value,
            slug: document.getElementById('newGameSlug').value,
            process_name: document.getElementById('newGameProcess').value,
            genre: document.getElementById('newGameGenre').value,
            steam_app_id: parseInt(document.getElementById('newGameSteamId').value) || null
        };
        const data = await apiCall('admin.php?action=add_game', 'POST', body);
        if (data.success) { closeModal(); loadDashboard(); }
        else alert(data.error);
    });
}

function editTrainer(id) {
    const t = state.trainers.find(x => x.id === id);
    if (!t) return;
    openModal('Trainer bearbeiten', `
        <div class="form-group"><label>Name</label><input type="text" id="editTrainerName" value="${escapeHtml(t.name)}"></div>
        <div class="form-group"><label>Beschreibung</label><textarea id="editTrainerDesc" rows="3">${escapeHtml(t.description || '')}</textarea></div>
        <div class="form-group"><label><input type="checkbox" id="editTrainerPremium" ${t.is_premium ? 'checked' : ''} style="width:auto; margin-right:8px;">Premium</label></div>
    `, async () => {
        const body = {
            trainer_id: id,
            name: document.getElementById('editTrainerName').value,
            description: document.getElementById('editTrainerDesc').value,
            is_premium: document.getElementById('editTrainerPremium').checked ? 1 : 0
        };
        const data = await apiCall('admin.php?action=edit_trainer', 'POST', body);
        if (data.success) { closeModal(); loadTrainers(); }
        else alert(data.error);
    });
}

/* Patterns modal */
function showPatterns(trainerId) {
    const t = state.trainers.find(x => x.id === trainerId);
    const html = (t.patterns || []).map(p => `
        <div class="card" style="margin-bottom:0.5rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                <strong>${p.game_version || '*'}</strong>
                <button class="btn btn-danger" style="padding:4px 10px; font-size:0.75rem;" onclick="deletePattern(${p.id})">Löschen</button>
            </div>
            <div style="color:var(--muted); font-size:0.85rem; margin-bottom:0.5rem;">${p.value_type} = ${p.value}</div>
            <pre style="color:var(--muted);font-size:0.8rem;margin:0; background:var(--bg); padding:0.5rem; border-radius:6px; overflow:auto;">${escapeHtml(p.pattern)}</pre>
        </div>
    `).join('') || '<p style="color:var(--muted);">Keine Patterns.</p>';
    
    openModal(`Patterns für ${escapeHtml(t.name)}`, `
        ${html}
        <hr style="border-color:var(--border); margin:1.5rem 0;">
        <h4>Neues Pattern</h4>
        <input type="hidden" id="patternTrainerId" value="${trainerId}">
        <div class="form-row">
            <div class="form-group"><label>Game Version</label><input type="text" id="patVersion" value="*"></div>
            <div class="form-group"><label>Offset</label><input type="number" id="patOffset" value="0"></div>
            <div class="form-group"><label>Value Type</label><select id="patType"><option>int32</option><option>float</option><option>int64</option><option>int8</option><option>int16</option><option>double</option></select></div>
        </div>
        <div class="form-group"><label>Byte Pattern</label><input type="text" id="patPattern" placeholder="89 7D ?? 8B 45 ..."></div>
        <div class="form-group"><label>Value</label><input type="text" id="patValue" value="999999"></div>
    `, async () => {
        const body = {
            trainer_id: parseInt(document.getElementById('patternTrainerId').value),
            game_version: document.getElementById('patVersion').value,
            pattern: document.getElementById('patPattern').value,
            offset: parseInt(document.getElementById('patOffset').value),
            value_type: document.getElementById('patType').value,
            value: document.getElementById('patValue').value
        };
        const data = await apiCall('admin.php?action=add_pattern', 'POST', body);
        if (data.success) { closeModal(); loadTrainers(); }
        else alert(data.error);
    }, 'Pattern hinzufügen');
}

async function addPattern() {
    // fallback for inline buttons inside modal
}

async function deletePattern(id) {
    if (!confirm('Pattern löschen?')) return;
    const data = await apiCall('admin.php?action=delete_pattern', 'POST', { pattern_id: id });
    if (data.success) { closeModal(); loadTrainers(); }
    else alert(data.error);
}

/* Community Patterns */
async function loadCommunityPatterns() {
    const data = await apiCall('admin.php?action=list_community_patterns');
    if (!data.success) return alert(data.error);
    state.patterns = data.patterns || [];
    renderPatterns();
}

function renderPatterns() {
    const q = state.patternFilter.toLowerCase();
    const status = state.patternStatusFilter;
    const filtered = state.patterns.filter(p => {
        const matches = !q || (p.game_name || '').toLowerCase().includes(q) || (p.name || '').toLowerCase().includes(q) || (p.pattern || '').toLowerCase().includes(q);
        const statusOk = !status || p.status === status;
        return matches && statusOk;
    });
    document.getElementById('communityTable').innerHTML = filtered.map(p => `<tr>
        <td>${p.id}</td>
        <td>${escapeHtml(p.game_name)}</td>
        <td>${escapeHtml(p.name)}</td>
        <td><code style="background:var(--bg); padding:2px 6px; border-radius:4px;">${escapeHtml(p.pattern).slice(0,40)}${p.pattern.length > 40 ? '...' : ''}</code></td>
        <td>${escapeHtml(p.author)}</td>
        <td>${p.votes || 0}</td>
        <td><span class="status-badge status-${p.status}">${p.status}</span></td>
        <td>
            ${p.status === 'pending' ? `<button class="btn btn-primary" style="padding:6px 12px; font-size:0.8rem;" onclick="approvePattern(${p.id})">Freigeben</button>` : ''}
            <button class="btn btn-danger" style="padding:6px 12px; font-size:0.8rem; margin-left:6px;" onclick="rejectPattern(${p.id})">${p.status === 'pending' ? 'Ablehnen' : 'Löschen'}</button>
        </td>
    </tr>`).join('');
}

function filterPatterns() {
    state.patternFilter = document.getElementById('patternSearch').value;
    state.patternStatusFilter = document.getElementById('patternStatusFilter').value;
    renderPatterns();
}

async function approvePattern(id) {
    const data = await apiCall('admin.php?action=approve_community_pattern', 'POST', { pattern_id: id });
    if (data.success) loadCommunityPatterns(); else alert(data.error);
}

async function rejectPattern(id) {
    if (!confirm('Pattern ablehnen/löschen?')) return;
    const data = await apiCall('admin.php?action=reject_community_pattern', 'POST', { pattern_id: id });
    if (data.success) loadCommunityPatterns(); else alert(data.error);
}

/* Leaderboard */
async function loadLeaderboard() {
    const data = await apiCall('premium.php?action=leaderboard');
    if (!data.success) return alert(data.error);
    document.getElementById('leaderboardTable').innerHTML = data.leaderboard.map((u, i) => `<tr>
        <td><strong style="color:${i < 3 ? 'var(--gold)' : 'var(--muted)'};">#${i + 1}</strong></td>
        <td>${escapeHtml(u.email)}</td>
        <td>${u.reputation}</td>
        <td>${u.approved_patterns}</td>
        <td>${u.total_votes}</td>
        <td>${u.last_active ? new Date(u.last_active * 1000).toLocaleDateString() : '-'}</td>
    </tr>`).join('');
}

/* System */
async function loadSystem() {
    const data = await apiCall('admin.php?action=stats');
    const health = await apiCall('version.php');
    document.getElementById('systemStats').innerHTML = `
        <div class="stat-card"><i class="fas fa-database"></i><h3>${data.db_size || '?'}</h3><p>Datenbankgröße</p></div>
        <div class="stat-card"><i class="fas fa-code-branch"></i><h3>${health.version || '?'}</h3><p>API Version</p></div>
        <div class="stat-card"><i class="fas fa-shield-alt"></i><h3>${health.success ? 'OK' : 'ERR'}</h3><p>API Status</p></div>
    `;
    document.getElementById('systemLogs').innerHTML = '<div style="color:var(--muted);">Logs werden überwacht...</div>';
}

/* Modal */
function openModal(title, body, onConfirm=null, confirmText='Speichern') {
    const overlay = document.getElementById('modalOverlay');
    const content = document.getElementById('modalContent');
    const footer = onConfirm ? `
        <div class="modal-footer">
            <button class="btn btn-secondary" onclick="closeModal()">Abbrechen</button>
            <button class="btn btn-primary" onclick="modalConfirm()">${confirmText}</button>
        </div>
    ` : `
        <div class="modal-footer">
            <button class="btn btn-secondary" onclick="closeModal()">Schließen</button>
        </div>
    `;
    content.innerHTML = `
        <div class="modal-header"><h3>${title}</h3><button class="close-btn" onclick="closeModal()">×</button></div>
        <div class="modal-body">${body}</div>
        ${footer}
    `;
    overlay.classList.add('open');
    window._modalConfirm = onConfirm;
}

function modalConfirm() {
    if (window._modalConfirm) window._modalConfirm();
}

function closeModal() {
    document.getElementById('modalOverlay').classList.remove('open');
    window._modalConfirm = null;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}

async function loadGames() {
    const data = await apiCall('games.php?action=list');
    if (data.success) state.games = data.games || [];
}

function refreshAll() {
    loadDashboard();
    loadUsers();
    loadTrainers();
    loadCommunityPatterns();
    loadLeaderboard();
    loadSystem();
}

/* Init */
if (localStorage.getItem('trainerhub_admin_token')) {
    showApp();
    loadGames();
}
