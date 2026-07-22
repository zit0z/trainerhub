let adminToken = localStorage.getItem('sweetcheat_admin_token') || '';
let usersData = [];
let auditData = [];

const API = '../api';

function byId(id) { return document.getElementById(id); }

function doLogin() {
    const pass = byId('adminPass').value;
    byId('loginError').textContent = '';
    fetch(`${API}/admin.php?action=login`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({password: pass})
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            adminToken = data.token;
            localStorage.setItem('sweetcheat_admin_token', adminToken);
            showAdminLayout();
            loadDashboard();
        } else {
            byId('loginError').textContent = data.error || 'Login fehlgeschlagen';
        }
    })
    .catch(() => byId('loginError').textContent = 'Netzwerkfehler');
}

function showAdminLayout() {
    byId('loginOverlay').classList.add('hidden');
    byId('adminLayout').classList.remove('hidden');
}

function logout() {
    localStorage.removeItem('sweetcheat_admin_token');
    location.reload();
}

function setView(view) {
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelector(`.nav-item[data-view="${view}"]`).classList.add('active');
    document.querySelectorAll('.admin-section').forEach(s => s.classList.remove('active'));
    byId('view-' + view).classList.add('active');
    if (view === 'dashboard') loadDashboard();
    if (view === 'users') loadUsers();
    if (view === 'audit') loadAudit();
    if (view === 'system') loadSystem();
}

document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', () => setView(btn.dataset.view));
});

async function api(method, url, body) {
    const opts = {
        method,
        headers: {
            'Authorization': 'Bearer ' + adminToken,
            'Content-Type': 'application/json'
        }
    };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(API + url, opts);
    return res.json();
}

async function loadDashboard() {
    const data = await api('GET', '/admin-analytics.php?period=7d');
    if (!data.success) return;
    byId('dashTotalUsers').textContent = data.total_users.toLocaleString('de-DE');
    byId('dashNewUsers').textContent = data.new_users.toLocaleString('de-DE');
    byId('dashPremium').textContent = data.premium_users.toLocaleString('de-DE');
    byId('dashActivations').textContent = data.activations.toLocaleString('de-DE');

    // DB totals
    const gamesRes = await fetch(API + '/games.php?per_page=1');
    const gamesData = await gamesRes.json();
    byId('dbGames').textContent = (gamesData.total || 0).toLocaleString('de-DE');
    const trainRes = await fetch(API + '/trainers.php?action=count');
    const trainData = await trainRes.json();
    byId('dbTrainers').textContent = (trainData.count || 0).toLocaleString('de-DE');
    byId('dbFavorites').textContent = data.favorites.toLocaleString('de-DE');

    renderMainChart(data.chart || []);
    renderTopGames(data.top_games || []);
}

function renderMainChart(chart) {
    const ctx = byId('mainChart').getContext('2d');
    if (window.mainChartInstance) window.mainChartInstance.destroy();
    window.mainChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: chart.map(c => c.date),
            datasets: [
                { label: 'Neue Benutzer', data: chart.map(c => c.users), borderColor: '#00f0ff', backgroundColor: 'rgba(0,240,255,0.1)', fill: true, tension: 0.4 },
                { label: 'Aktivierungen', data: chart.map(c => c.activations), borderColor: '#ff3864', backgroundColor: 'rgba(255,56,100,0.1)', fill: true, tension: 0.4 }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { labels: { color: '#94a3b8' } } },
            scales: {
                x: { ticks: { color: '#94a3b8' }, grid: { color: '#232333' } },
                y: { ticks: { color: '#94a3b8' }, grid: { color: '#232333' }, beginAtZero: true }
            }
        }
    });
}

function renderTopGames(top) {
    const max = top.length ? Math.max(...top.map(t => t.count)) : 1;
    byId('topGames').innerHTML = top.length ? top.map(t => `
        <div class="top-game-row">
            <div style="flex:1;">
                <div class="top-game-name">${escapeHtml(t.name)}</div>
                <div class="progress-bar"><div class="progress-fill" style="width:${(t.count / max * 100)}%"></div></div>
            </div>
            <div class="top-game-count" style="margin-left:16px;">${t.count}</div>
        </div>
    `).join('') : '<div style="color:var(--text-muted);">Keine Daten</div>';
}

async function loadUsers() {
    const data = await api('GET', '/admin.php?action=users');
    usersData = data.users || [];
    renderUsers();
}

function renderUsers() {
    const q = byId('userFilter').value.toLowerCase();
    const status = byId('userStatusFilter').value;
    const filtered = usersData.filter(u => {
        const matches = !q || (u.email || '').toLowerCase().includes(q) || (u.username || '').toLowerCase().includes(q) || String(u.id).includes(q);
        const st = status === '' ? true : (u.subscription_status === status || (status === 'premium' && u.is_premium));
        return matches && st;
    });
    byId('usersTable').innerHTML = filtered.map(u => `
        <tr class="user-row">
            <td>${u.id}</td>
            <td>${escapeHtml(u.email)}</td>
            <td>${escapeHtml(u.username || '-')}</td>
            <td>${u.is_premium || u.subscription_status === 'premium' ? '<span class="badge badge-premium">Premium</span>' : '<span class="badge">Free</span>'}</td>
            <td>${u.subscription_expires_at ? new Date(u.subscription_expires_at * 1000).toLocaleDateString('de-DE') : '-'}</td>
            <td>${new Date(u.created_at * 1000).toLocaleDateString('de-DE')}</td>
            <td>
                <button class="btn btn-secondary btn-sm" onclick="editUser(${u.id})">Bearbeiten</button>
                <button class="btn btn-danger btn-sm" onclick="deleteUser(${u.id})">Löschen</button>
            </td>
        </tr>
    `).join('');
}

function openUserModal() {
    byId('userModalTitle').textContent = 'Benutzer anlegen';
    byId('editUserId').value = '';
    byId('editUserEmail').value = '';
    byId('editUserUsername').value = '';
    byId('editUserStatus').value = 'free';
    byId('editUserExpires').value = '';
    byId('userModal').classList.add('active');
}

function editUser(id) {
    const u = usersData.find(x => x.id === id);
    if (!u) return;
    byId('userModalTitle').textContent = 'Benutzer bearbeiten';
    byId('editUserId').value = u.id;
    byId('editUserEmail').value = u.email;
    byId('editUserUsername').value = u.username || '';
    byId('editUserStatus').value = u.subscription_status || 'free';
    byId('editUserExpires').value = u.subscription_expires_at || '';
    byId('userModal').classList.add('active');
}

function closeUserModal() { byId('userModal').classList.remove('active'); }

async function saveUser() {
    const id = byId('editUserId').value;
    const body = {
        email: byId('editUserEmail').value,
        username: byId('editUserUsername').value,
        subscription_status: byId('editUserStatus').value,
        subscription_expires_at: byId('editUserExpires').value ? parseInt(byId('editUserExpires').value) : null
    };
    const action = id ? 'update_user' : 'create_user';
    if (id) body.id = parseInt(id);
    const data = await api('POST', `/admin.php?action=${action}`, body);
    if (data.success) {
        closeUserModal();
        loadUsers();
    } else {
        alert(data.error || 'Fehler');
    }
}

async function deleteUser(id) {
    if (!confirm('Benutzer wirklich löschen?')) return;
    const data = await api('POST', '/admin.php?action=delete_user', {id});
    if (data.success) loadUsers();
    else alert(data.error || 'Fehler');
}

async function loadAudit() {
    const data = await api('GET', '/admin-audit.php');
    auditData = data.logs || [];
    byId('dbAudit').textContent = (data.total || auditData.length).toLocaleString('de-DE');
    renderAudit();
}

function renderAudit() {
    const q = byId('auditFilter').value.toLowerCase();
    const filtered = auditData.filter(a => {
        return !q || (a.action || '').toLowerCase().includes(q) || String(a.user_id).includes(q) || (a.endpoint || '').toLowerCase().includes(q);
    });
    byId('auditTable').innerHTML = filtered.slice(0, 200).map(a => `
        <tr class="audit-row">
            <td>${new Date(a.created_at * 1000).toLocaleString('de-DE')}</td>
            <td>${a.user_id || '-'}</td>
            <td>${escapeHtml(a.action)}</td>
            <td>${escapeHtml(a.endpoint || '-')}</td>
            <td>${escapeHtml(a.ip || '-')}</td>
            <td style="max-width:300px; overflow:hidden; text-overflow:ellipsis;" title="${escapeHtml(a.details || '')}">${escapeHtml(a.details || '-')}</td>
        </tr>
    `).join('');
}

async function loadSystem() {
    const data = await api('GET', '/admin.php?action=system');
    byId('systemInfo').textContent = JSON.stringify(data, null, 2);
}

function syncStats() { loadDashboard(); }
function clearCache() { api('POST', '/admin-clear-cache.php', {}).then(d => alert(d.success ? 'Cache geleert' : d.error)); }
function testAllAPIs() { api('POST', '/admin.php?action=test_apis', {}).then(d => alert(JSON.stringify(d, null, 2))); }
function purgeAudit() { if (confirm('Audit-Log wirklich leeren?')) api('POST', '/admin-audit.php?action=purge', {}).then(d => { if (d.success) loadAudit(); }); }
function downloadAudit() { window.open(API + '/admin-audit.php?action=csv&token=' + encodeURIComponent(adminToken)); }

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}

// Auto-login on load
if (adminToken) {
    fetch(`${API}/admin.php?action=verify`, {headers: {'Authorization': 'Bearer ' + adminToken}})
        .then(r => r.json())
        .then(d => { if (d.success) { showAdminLayout(); loadDashboard(); } else { localStorage.removeItem('sweetcheat_admin_token'); } });
}
