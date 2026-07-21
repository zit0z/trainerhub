const API_BASE = '/trainerhub/api';

let state = {
    users: [],
    trainers: [],
    patterns: [],
    games: [],
    stats: {},
    currentView: 'dashboard',
    userFilter: '',
    userStatusFilter: '',
    trainerFilter: '',
    patternFilter: ''
};

function init() {
    const token = localStorage.getItem('trainerhub_admin_token');
    if (token) {
        showApp();
    }
    window.addEventListener('hashchange', handleHash);
}

function handleHash() {
    const hash = window.location.hash.replace('#', '') || 'dashboard';
    if (['dashboard','users','trainers','patterns','leaderboard','system'].includes(hash)) {
        switchView(hash, false);
    }
}

function doLogin() {
    const pass = document.getElementById('adminPass').value;
    document.getElementById('loginError').textContent = '';

    fetch(`${API_BASE}/admin.php?action=login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: pass })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            localStorage.setItem('trainerhub_admin_token', data.token);
            showApp();
        } else {
            document.getElementById('loginError').textContent = data.error || 'Login fehlgeschlagen';
        }
    })
    .catch(e => {
        document.getElementById('loginError').textContent = 'Fehler: ' + e.message;
    });
}

function showApp() {
    document.getElementById('loginOverlay').style.display = 'none';
    document.getElementById('adminLayout').style.display = 'grid';
    const hash = window.location.hash.replace('#', '') || 'dashboard';
    switchView(hash, false);
}

function logout() {
    localStorage.removeItem('trainerhub_admin_token');
    location.reload();
}

function apiCall(endpoint, method='GET', body=null) {
    const token = localStorage.getItem('trainerhub_admin_token');
    const opts = {
        method,
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    };
    if (body) opts.body = JSON.stringify(body);
    return fetch(`${API_BASE}/${endpoint}`, opts)
        .then(r => {
            if (r.status === 401) { logout(); return { success: false, error: 'Unauthorized' }; }
            return r.json();
        })
        .catch(e => ({ success: false, error: e.message }));
}

function switchView(view, updateHash=true) {
    const targetView = document.getElementById(`view-${view}`);
    if (!targetView) {
        console.error('View not found:', view);
        return;
    }

    document.querySelectorAll('.view').forEach(v => v.classList.add('hidden'));
    targetView.classList.remove('hidden');

    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    const navItem = document.querySelector(`.nav-item[data-view="${view}"]`);
    if (navItem) navItem.classList.add('active');

    state.currentView = view;
    if (updateHash) window.location.hash = view;

    if (view === 'dashboard') loadStats();
    if (view === 'users') loadUsers();
    if (view === 'trainers') loadTrainers();
    if (view === 'patterns') loadPatterns();
    if (view === 'leaderboard') loadLeaderboard();
    if (view === 'system') loadSystem();
}

function showToast(msg, type='success') {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.className = `toast ${type} show`;
    setTimeout(() => t.classList.remove('show'), 3000);
}

/* Dashboard */
async function loadStats() {
    const data = await apiCall('admin.php?action=stats');
    if (!data.success) return;
    state.stats = data;
    document.getElementById('statsGrid').innerHTML = `
        <div class="stat-card"><i class="fas fa-gamepad"></i><h3>${data.games || 0}</h3><p>Spiele</p></div>
        <div class="stat-card"><i class="fas fa-code"></i><h3>${data.trainers || 0}</h3><p>Trainer</p></div>
        <div class="stat-card"><i class="fas fa-users"></i><h3>${data.users || 0}</h3><p>Benutzer</p></div>
        <div class="stat-card"><i class="fas fa-crown"></i><h3>${data.premium_users || 0}</h3><p>Premium</p></div>
        <div class="stat-card"><i class="fas fa-bolt"></i><h3>${data.activations_today || 0}</h3><p>Aktivierungen heute</p></div>
        <div class="stat-card"><i class="fas fa-project-diagram"></i><h3>${data.patterns || 0}</h3><p>Patterns</p></div>
    `;
}

function clearCache() {
    apiCall('admin-clear-cache.php', 'POST').then(d => {
        showToast(d.success ? 'Cache geleert' : d.error, d.success ? 'success' : 'error');
    });
}

function syncStats() {
    loadStats();
    showToast('Stats aktualisiert');
}

function purgeLogs() {
    if (!confirm('Alle Logs älter als 30 Tage löschen?')) return;
    apiCall('admin.php?action=purge_logs', 'POST').then(d => {
        showToast(d.success ? 'Logs gepurgt' : d.error, d.success ? 'success' : 'error');
    });
}

/* Users */
async function loadUsers() {
    const data = await apiCall('admin.php?action=list_users');
    if (!data.success) return;
    state.users = data.users || [];
    renderUsers();
}

function filterUsers() {
    state.userFilter = document.getElementById('userFilter').value.toLowerCase();
    state.userStatusFilter = document.getElementById('userStatusFilter').value;
    renderUsers();
}

function renderUsers() {
    const filtered = state.users.filter(u => {
        const matchText = !state.userFilter ||
            (u.email || '').toLowerCase().includes(state.userFilter) ||
            (u.username || '').toLowerCase().includes(state.userFilter);
        const matchStatus = !state.userStatusFilter || u.subscription_status === state.userStatusFilter;
        return matchText && matchStatus;
    });

    const tbody = document.getElementById('usersTable');
    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:var(--muted); padding:2rem;">Keine Benutzer gefunden</td></tr>';
        return;
    }

    tbody.innerHTML = filtered.map(u => {
        const statusClass = u.subscription_status === 'premium' || u.subscription_status === 'active' ? 'badge-premium' : 'badge-free';
        const exp = u.subscription_expires_at ? new Date(u.subscription_expires_at * 1000).toLocaleDateString('de-DE') : '—';
        return `
            <tr>
                <td>${u.id}</td>
                <td>
                    <div>${escapeHtml(u.username || '-')}</div>
                    <div style="color:var(--muted); font-size:0.8rem;">${escapeHtml(u.email)}</div>
                </td>
                <td><span class="badge-inline ${statusClass}">${u.subscription_status}</span></td>
                <td>${exp}</td>
                <td>${new Date(u.created_at * 1000).toLocaleDateString('de-DE')}</td>
                <td>
                    <button class="btn btn-primary" style="padding:6px 12px; font-size:0.75rem;" onclick="editUser(${u.id})"><i class="fas fa-edit"></i> Edit</button>
                </td>
            </tr>
        `;
    }).join('');
}

function openUserModal() {
    document.getElementById('userModalTitle').textContent = 'Benutzer erstellen';
    document.getElementById('editUserId').value = '';
    document.getElementById('editUserEmail').value = '';
    document.getElementById('editUserUsername').value = '';
    document.getElementById('editUserStatus').value = 'free';
    document.getElementById('editUserDays').value = '30';
    document.getElementById('editUserPassword').value = '';
    document.getElementById('userModal').classList.add('active');
}

function editUser(id) {
    const u = state.users.find(x => x.id === id);
    if (!u) return;
    document.getElementById('userModalTitle').textContent = 'Benutzer bearbeiten';
    document.getElementById('editUserId').value = u.id;
    document.getElementById('editUserEmail').value = u.email;
    document.getElementById('editUserUsername').value = u.username || '';
    document.getElementById('editUserStatus').value = u.subscription_status;
    document.getElementById('editUserDays').value = '30';
    document.getElementById('editUserPassword').value = '';
    document.getElementById('userModal').classList.add('active');
}

function closeUserModal() {
    document.getElementById('userModal').classList.remove('active');
}

function saveUser() {
    const id = document.getElementById('editUserId').value;
    const body = {
        email: document.getElementById('editUserEmail').value,
        username: document.getElementById('editUserUsername').value,
        subscription_status: document.getElementById('editUserStatus').value,
        premium_days: parseInt(document.getElementById('editUserDays').value) || 30
    };
    const pass = document.getElementById('editUserPassword').value;
    if (pass) body.password = pass;

    const action = id ? `admin.php?action=edit_user&id=${id}` : 'admin.php?action=create_user';
    apiCall(action, 'POST', body).then(d => {
        showToast(d.success ? 'Gespeichert' : d.error, d.success ? 'success' : 'error');
        if (d.success) {
            closeUserModal();
            loadUsers();
        }
    });
}

/* Trainers */
async function loadTrainers() {
    const data = await apiCall('admin.php?action=list_trainers');
    if (!data.success) return;
    state.trainers = data.trainers || [];
    renderTrainers();
}

function filterTrainers() {
    state.trainerFilter = document.getElementById('trainerFilter').value.toLowerCase();
    renderTrainers();
}

function renderTrainers() {
    const filtered = state.trainers.filter(t => {
        return !state.trainerFilter ||
            (t.name || '').toLowerCase().includes(state.trainerFilter) ||
            (t.game_name || '').toLowerCase().includes(state.trainerFilter);
    });

    const tbody = document.getElementById('trainersTable');
    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:var(--muted); padding:2rem;">Keine Trainer gefunden</td></tr>';
        return;
    }

    tbody.innerHTML = filtered.map(t => `
        <tr>
            <td>${t.id}</td>
            <td>${escapeHtml(t.name)}</td>
            <td>${escapeHtml(t.game_name || '-')}</td>
            <td>${t.cheat_type || t.type || 'memory'}</td>
            <td>${t.is_active ? '<span style="color:var(--success);">●</span> Aktiv' : '<span style="color:var(--danger);">●</span> Inaktiv'}</td>
            <td>
                <button class="btn btn-primary" style="padding:6px 12px; font-size:0.75rem;" onclick="editTrainer(${t.id})"><i class="fas fa-edit"></i> Edit</button>
            </td>
        </tr>
    `).join('');
}

function openTrainerModal() {
    document.getElementById('trainerModalTitle').textContent = 'Trainer hinzufügen';
    document.getElementById('editTrainerId').value = '';
    document.getElementById('editTrainerName').value = '';
    document.getElementById('editTrainerGameId').value = '';
    document.getElementById('editTrainerType').value = 'memory';
    document.getElementById('editTrainerDescription').value = '';
    document.getElementById('trainerModal').classList.add('active');
}

function editTrainer(id) {
    const t = state.trainers.find(x => x.id === id);
    if (!t) return;
    document.getElementById('trainerModalTitle').textContent = 'Trainer bearbeiten';
    document.getElementById('editTrainerId').value = t.id;
    document.getElementById('editTrainerName').value = t.name;
    document.getElementById('editTrainerGameId').value = t.game_id;
    document.getElementById('editTrainerType').value = t.cheat_type || t.type || 'memory';
    document.getElementById('editTrainerDescription').value = t.description || '';
    document.getElementById('trainerModal').classList.add('active');
}

function closeTrainerModal() {
    document.getElementById('trainerModal').classList.remove('active');
}

function saveTrainer() {
    const id = document.getElementById('editTrainerId').value;
    const body = {
        name: document.getElementById('editTrainerName').value,
        game_id: parseInt(document.getElementById('editTrainerGameId').value) || null,
        type: document.getElementById('editTrainerType').value,
        description: document.getElementById('editTrainerDescription').value
    };
    const action = id ? `admin.php?action=edit_trainer&id=${id}` : 'admin.php?action=create_trainer';
    apiCall(action, 'POST', body).then(d => {
        showToast(d.success ? 'Gespeichert' : d.error, d.success ? 'success' : 'error');
        if (d.success) {
            closeTrainerModal();
            loadTrainers();
        }
    });
}

/* Patterns */
async function loadPatterns() {
    const data = await apiCall('admin.php?action=list_patterns');
    if (!data.success) return;
    state.patterns = data.patterns || [];
    renderPatterns();
}

function filterPatterns() {
    state.patternFilter = document.getElementById('patternFilter').value.toLowerCase();
    renderPatterns();
}

function renderPatterns() {
    const filtered = state.patterns.filter(p => {
        return !state.patternFilter ||
            (p.name || '').toLowerCase().includes(state.patternFilter) ||
            (p.game_name || '').toLowerCase().includes(state.patternFilter);
    });

    const tbody = document.getElementById('patternsTable');
    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; color:var(--muted); padding:2rem;">Keine Patterns gefunden</td></tr>';
        return;
    }

    tbody.innerHTML = filtered.map(p => `
        <tr>
            <td>${p.id}</td>
            <td>${escapeHtml(p.game_name || '-')}</td>
            <td>${escapeHtml(p.name)}</td>
            <td>${escapeHtml(p.author_name || '-')}</td>
            <td>${p.votes || 0}</td>
            <td>${p.status === 'approved' ? '<span style="color:var(--success);">✓</span>' : '<span style="color:var(--warning);">Ausstehend</span>'}</td>
            <td>
                <button class="btn btn-primary" style="padding:6px 12px; font-size:0.75rem;" onclick="approvePattern(${p.id})">${p.status === 'approved' ? 'Zurücksetzen' : 'Freischalten'}</button>
            </td>
        </tr>
    `).join('');
}

function approvePattern(id) {
    apiCall(`admin.php?action=approve_pattern&id=${id}`, 'POST').then(d => {
        showToast(d.success ? 'Pattern aktualisiert' : d.error, d.success ? 'success' : 'error');
        if (d.success) loadPatterns();
    });
}

/* Leaderboard */
async function loadLeaderboard() {
    const data = await apiCall('premium.php?action=leaderboard');
    if (!data.success) return;
    const tbody = document.getElementById('leaderboardTable');
    const rows = (data.leaderboard || []).slice(0, 50);
    if (rows.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:var(--muted); padding:2rem;">Keine Einträge</td></tr>';
        return;
    }
    tbody.innerHTML = rows.map((u, i) => `
        <tr>
            <td>#${i + 1}</td>
            <td>${escapeHtml(u.email)}</td>
            <td>${u.reputation || 0}</td>
            <td>${u.approved_patterns || 0}</td>
            <td>${u.total_votes || 0}</td>
        </tr>
    `).join('');
}

/* System */
async function loadSystem() {
    const data = await apiCall('admin.php?action=system');
    const container = document.getElementById('systemInfo');
    if (!data.success) {
        container.innerHTML = `<p style="color:var(--danger);">Fehler: ${data.error}</p>`;
        return;
    }
    container.innerHTML = `
        <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap:1rem;">
            <div class="stat-card"><i class="fas fa-database"></i><h3>${data.db_size || '?'}</h3><p>Datenbankgröße</p></div>
            <div class="stat-card"><i class="fas fa-hdd"></i><h3>${data.disk_free || '?'}</h3><p>Freier Speicher</p></div>
            <div class="stat-card"><i class="fas fa-clock"></i><h3>${data.uptime || '?'}</h3><p>Server-Uptime</p></div>
        </div>
    `;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Auto-login if token exists
if (localStorage.getItem('trainerhub_admin_token')) {
    showApp();
}
