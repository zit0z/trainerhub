import os
import json
import urllib.request
import urllib.error

API_BASE = os.environ.get('TRAINERHUB_API', 'https://sayfespace.online/sweetcheat/api')
CONFIG_FILE = os.path.join(os.path.expanduser('~'), '.sweetcheat', 'config.json')

class SweetCheatApp:
    def __init__(self):
        self.api_key = None
        self.load_config()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE) as f:
                    self.api_key = json.load(f).get('api_key')
            except: pass

    def save_config(self):
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump({'api_key': self.api_key}, f)

    def api_call(self, endpoint, method='GET', data=None):
        headers = {}
        if self.api_key: headers['Authorization'] = f'Bearer {self.api_key}'
        url = f'{API_BASE}/{endpoint}'
        try:
            if method == 'GET':
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=15) as r:
                    return json.loads(r.read().decode('utf-8'))
            else:
                body = json.dumps(data).encode('utf-8') if data else b''
                req = urllib.request.Request(url, data=body, headers={**headers, 'Content-Type': 'application/json'}, method='POST')
                with urllib.request.urlopen(req, timeout=15) as r:
                    return json.loads(r.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            try:
                return json.loads(e.read().decode('utf-8'))
            except Exception:
                return {'success': False, 'error': f'HTTP {e.code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    def login(self):
        email = input('E-Mail: ').strip()
        password = input('Passwort: ')
        data = self.api_call('auth.php?action=login', 'POST', {'email': email, 'password': password})
        if data.get('success'):
            self.api_key = data['api_key']
            self.save_config()
            print('Login erfolgreich.')
            return True
        print('Fehler:', data.get('error'))
        return False
    
    def run_cli(self):
        print('SweetCheat CLI')
        if not self.api_key and not self.login():
            return
        while True:
            print('\n1. Trainer anzeigen\n2. Beenden')
            c = input('Wahl: ').strip()
            if c == '1':
                d = self.api_call('trainers.php?action=list')
                for t in d.get('trainers', []):
                    print(f"- {t['name']} {'(Premium)' if t.get('locked') else ''}")
            elif c == '2': break
