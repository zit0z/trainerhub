// SweetCheat Shared Web UI Helpers
(function() {
    const API_BASE = 'api';

    function getKey() { return localStorage.getItem('sweetcheat_api_key'); }
    function authHeaders() { const k = getKey(); return k ? {'Authorization': 'Bearer '+k} : {}; }

    // Toast notifications
    function showToast(message, type = 'info', duration = 3000) {
        let container = document.getElementById('toastContainer');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toastContainer';
            container.style.cssText = 'position:fixed; top:20px; right:20px; z-index:9999; display:flex; flex-direction:column; gap:10px;';
            document.body.appendChild(container);
        }
        const el = document.createElement('div');
        const colors = { info: 'var(--accent)', success: '#00e676', error: '#ff3864', warn: '#ffab00' };
        el.style.cssText = `background:var(--bg-card); border:1px solid ${colors[type]||colors.info}; color:var(--text); padding:12px 18px; border-radius:var(--radius); box-shadow:0 8px 24px rgba(0,0,0,0.4); display:flex; align-items:center; gap:10px; min-width:220px; animation:slideIn .3s ease;`;
        el.innerHTML = `<i class="fas ${type==='success'?'fa-check-circle':type==='error'?'fa-exclamation-circle':type==='warn'?'fa-exclamation-triangle':'fa-info-circle'}" style="color:${colors[type]||colors.info};"></i><span>${message}</span>`;
        container.appendChild(el);
        setTimeout(() => { el.style.opacity='0'; el.style.transform='translateX(120%)'; setTimeout(()=>el.remove(), 300); }, duration);
    }
    window.showToast = showToast;

    // Theme toggle
    function initTheme() {
        const saved = localStorage.getItem('sweetcheat_theme') || 'dark';
        document.documentElement.setAttribute('data-theme', saved);
        window.toggleTheme = function() {
            const current = document.documentElement.getAttribute('data-theme') || 'dark';
            const next = current === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', next);
            localStorage.setItem('sweetcheat_theme', next);
            showToast(next === 'dark' ? 'Dark Mode aktiviert' : 'Light Mode aktiviert', 'info', 1500);
        };
    }
    initTheme();

    // Keyboard shortcuts
    document.addEventListener('keydown', e => {
        if (e.ctrlKey || e.metaKey) {
            switch(e.key) {
                case 'k':
                    e.preventDefault();
                    const search = document.getElementById('gameSearch') || document.getElementById('globalSearch');
                    if (search) search.focus();
                    break;
                case 'd':
                    e.preventDefault();
                    window.location.href = 'dashboard';
                    break;
                case 'g':
                    e.preventDefault();
                    window.location.href = 'games';
                    break;
                case 'f':
                    e.preventDefault();
                    window.location.href = 'favorites';
                    break;
            }
        }
        if (e.key === 'Escape') {
            const overlay = document.querySelector('.overlay.open');
            if (overlay) overlay.classList.remove('open');
        }
    });

    // Mobile nav toggle
    window.toggleMobileNav = function() {
        const sidebar = document.querySelector('.nav-sidebar');
        if (sidebar) sidebar.classList.toggle('open');
    };

    // Global search dropdown
    let searchTimeout;
    window.globalSearch = async function(input) {
        clearTimeout(searchTimeout);
        const dropdown = document.getElementById('searchDropdown');
        if (!dropdown) return;
        const q = input.value.trim();
        if (q.length < 2) { dropdown.innerHTML = ''; dropdown.classList.remove('open'); return; }
        searchTimeout = setTimeout(async () => {
            try {
                const [gamesRes, trainersRes] = await Promise.all([
                    fetch(`${API_BASE}/games.php?search=${encodeURIComponent(q)}&per_page=5`, {headers: authHeaders()}),
                    fetch(`${API_BASE}/trainers.php?search=${encodeURIComponent(q)}&per_page=5`, {headers: authHeaders()})
                ]);
                const games = await gamesRes.json();
                const trainers = await trainersRes.json();
                let html = '';
                if (games.games?.length) {
                    html += '<div style="padding:8px 12px; color:var(--text-muted); font-size:12px; text-transform:uppercase;">Spiele</div>';
                    html += games.games.map(g => `<a href="trainers?game=${g.slug}" style="display:flex; align-items:center; gap:10px; padding:8px 12px; color:var(--text); text-decoration:none; hover:background:rgba(255,255,255,0.05);"><i class="fas fa-gamepad" style="color:var(--accent);"></i>${escapeHtml(g.name)}</a>`).join('');
                }
                if (trainers.trainers?.length) {
                    html += '<div style="padding:8px 12px; color:var(--text-muted); font-size:12px; text-transform:uppercase;">Trainer</div>';
                    html += trainers.trainers.map(t => `<a href="trainers?game=${t.game_slug}" style="display:flex; align-items:center; gap:10px; padding:8px 12px; color:var(--text); text-decoration:none;"><i class="fas fa-bolt" style="color:#ff3864;"></i>${escapeHtml(t.name)}</a>`).join('');
                }
                if (!html) html = '<div style="padding:12px; color:var(--text-muted); text-align:center;">Keine Treffer</div>';
                dropdown.innerHTML = html;
                dropdown.classList.add('open');
            } catch(e) { console.error(e); }
        }, 200);
    };

    // Onboarding tour
    window.startTour = function(steps) {
        let step = 0;
        const overlay = document.createElement('div');
        overlay.id = 'tourOverlay';
        overlay.style.cssText = 'position:fixed; inset:0; background:rgba(0,0,0,0.7); z-index:10000; display:flex; align-items:center; justify-content:center;';
        const box = document.createElement('div');
        box.style.cssText = 'background:var(--bg-card); border:1px solid var(--accent); border-radius:var(--radius); padding:24px; max-width:360px; text-align:center;';
        function render() {
            const s = steps[step];
            box.innerHTML = `
                <div style="font-size:2rem; color:var(--accent); margin-bottom:12px;"><i class="fas ${s.icon||'fa-info-circle'}"></i></div>
                <h3 style="margin:0 0 8px; font-family:'Rajdhani',sans-serif;">${s.title}</h3>
                <p style="color:var(--text-muted); margin-bottom:20px;">${s.text}</p>
                <div style="display:flex; justify-content:center; gap:10px;">
                    ${step > 0 ? '<button class="btn btn-secondary btn-sm" onclick="window._prevTour()">Zurück</button>' : ''}
                    <button class="btn btn-primary btn-sm" onclick="window._nextTour()">${step === steps.length-1 ? 'Fertig' : 'Weiter'}</button>
                </div>
                <div style="margin-top:12px; font-size:12px; color:var(--text-muted);">${step+1}/${steps.length}</div>
            `;
        }
        window._nextTour = () => { step++; if (step >= steps.length) { overlay.remove(); delete window._nextTour; delete window._prevTour; } else render(); };
        window._prevTour = () => { step--; render(); };
        overlay.appendChild(box);
        document.body.appendChild(overlay);
        render();
    };

    function escapeHtml(text) { const div = document.createElement('div'); div.textContent = text || ''; return div.innerHTML; }
    window.escapeHtml = escapeHtml;
})();
