(function() {
    function initHeaderMenu() {
        const token = localStorage.getItem('trainerhub_api_key') || localStorage.getItem('sweetcheat_api_key');
        const menuContainer = document.getElementById('headerUserMenu');
        if (!menuContainer) return;
        
        if (!token) {
            menuContainer.innerHTML = `
                <a href="login" class="btn btn-secondary btn-sm">Login</a>
                <a href="register" class="btn btn-primary btn-sm">Registrieren</a>
            `;
            return;
        }
        
        fetch('/trainerhub/api/user-settings.php?action=get', {
            headers: { 'Authorization': 'Bearer ' + token }
        })
        .then(r => r.json())
        .then(data => {
            if (!data.success) {
                menuContainer.innerHTML = `<a href="login" class="btn btn-secondary btn-sm">Login</a>`;
                return;
            }
            const user = data.user;
            menuContainer.innerHTML = `
                <div style="position:relative;" id="hMenuWrap">
                    <button onclick="toggleHMenu()" style="display:flex; align-items:center; gap:10px; background:transparent; border:1px solid var(--border); border-radius:999px; padding:6px 14px 6px 6px; color:var(--text); cursor:pointer; font-size:14px;">
                        <div style="width:30px;height:30px;border-radius:50%;background:var(--bg-elevated);display:flex;align-items:center;justify-content:center;color:var(--accent);">
                            <i class="fas fa-user"></i>
                        </div>
                        <span>${escapeHtml(user.username || user.email)}</span>
                        <i class="fas fa-chevron-down" style="font-size:0.7rem; color:var(--text-muted);"></i>
                    </button>
                    <div id="hMenuDropdown" style="display:none; position:absolute; top:44px; right:0; background:var(--bg-card); border:1px solid var(--border); border-radius:12px; padding:8px 0; min-width:180px; box-shadow:0 10px 30px rgba(0,0,0,0.4); z-index:1001;">
                        <a href="profile" style="display:block; padding:10px 16px; color:var(--text); text-decoration:none; font-size:14px;"><i class="fas fa-user" style="width:20px; color:var(--accent);"></i> Mein Profil</a>
                        <a href="dashboard" style="display:block; padding:10px 16px; color:var(--text); text-decoration:none; font-size:14px;"><i class="fas fa-th-large" style="width:20px; color:var(--accent);"></i> Dashboard</a>
                        <a href="forum" style="display:block; padding:10px 16px; color:var(--text); text-decoration:none; font-size:14px;"><i class="fas fa-comments" style="width:20px; color:var(--accent);"></i> Forum</a>
                        <a href="settings" style="display:block; padding:10px 16px; color:var(--text); text-decoration:none; font-size:14px;"><i class="fas fa-cog" style="width:20px; color:var(--accent);"></i> Einstellungen</a>
                        <div style="height:1px; background:var(--border); margin:8px 0;"></div>
                        <a href="#" onclick="headerLogout(); return false;" style="display:block; padding:10px 16px; color:var(--danger); text-decoration:none; font-size:14px;"><i class="fas fa-sign-out-alt" style="width:20px;"></i> Logout</a>
                    </div>
                </div>
            `;
        })
        .catch(() => {
            menuContainer.innerHTML = `<a href="login" class="btn btn-secondary btn-sm">Login</a>`;
        });
    }
    
    window.toggleHMenu = function() {
        const d = document.getElementById('hMenuDropdown');
        if (!d) return;
        d.style.display = d.style.display === 'block' ? 'none' : 'block';
    };
    
    window.headerLogout = function() {
        localStorage.removeItem('trainerhub_api_key');
        localStorage.removeItem('sweetcheat_api_key');
        window.location.href = '/trainerhub/';
    };
    
    document.addEventListener('click', e => {
        const wrap = document.getElementById('hMenuWrap');
        const drop = document.getElementById('hMenuDropdown');
        if (wrap && drop && !wrap.contains(e.target)) drop.style.display = 'none';
    });
    
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initHeaderMenu);
    } else {
        initHeaderMenu();
    }
})();
