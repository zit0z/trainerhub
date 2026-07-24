(async function() {
    function getKey() {
        return localStorage.getItem('trainerhub_api_key') || localStorage.getItem('sweetcheat_api_key') || '';
    }
    function updateHeader(username) {
        const token = getKey();
        const menu = document.getElementById('headerUserMenu');
        if (!menu) return;
        const user = username || localStorage.getItem('sc_username') || 'User';
        const initial = String(user).charAt(0).toUpperCase();
        if (token) {
            menu.innerHTML = `<div style="display:flex; align-items:center; gap:10px;">
                <div style="width:34px; height:34px; border-radius:999px; background:var(--accent); color:var(--bg); display:flex; align-items:center; justify-content:center; font-weight:700; font-family:'Rajdhani',sans-serif;">${initial}</div>
                <div class="header-dropdown" style="position:relative;">
                    <button class="btn btn-secondary btn-sm" onclick="this.nextElementSibling.classList.toggle('open')">${user} <i class="fas fa-caret-down"></i></button>
                    <div class="header-dropdown-menu" style="display:none; position:absolute; right:0; top:110%; background:var(--bg-card); border:1px solid var(--border); border-radius:12px; padding:8px; min-width:160px; z-index:100; box-shadow:var(--shadow);">
                        <a href="profile" style="display:block; padding:10px 14px; color:var(--text); border-radius:8px;"><i class="fas fa-user"></i> Profil</a>
                        <a href="settings" style="display:block; padding:10px 14px; color:var(--text); border-radius:8px;"><i class="fas fa-cog"></i> Einstellungen</a>
                        <a href="dashboard" style="display:block; padding:10px 14px; color:var(--text); border-radius:8px;"><i class="fas fa-th-large"></i> Dashboard</a>
                        <div style="height:1px; background:var(--border); margin:6px 0;"></div>
                        <a href="#" onclick="logout(); return false;" style="display:block; padding:10px 14px; color:#ff3864; border-radius:8px;"><i class="fas fa-sign-out-alt"></i> Logout</a>
                    </div>
                </div>
            </div>`;
        } else {
            menu.innerHTML = `<a href="login" class="btn btn-secondary btn-sm">Login</a>
                <a href="register" class="btn btn-primary btn-sm">Registrieren</a>`;
        }
    }

    let username = localStorage.getItem('sc_username');
    const token = getKey();
    if (token && !username) {
        try {
            const res = await fetch('api/user-settings.php', {headers:{'Authorization':'Bearer '+token}});
            const data = await res.json();
            if (data.success && data.user) {
                username = data.user.username || data.user.email;
                localStorage.setItem('sc_username', username);
            }
        } catch(e) {}
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => updateHeader(username));
    } else {
        updateHeader(username);
    }
})();
