"""SweetCheat Desktop API Client"""
import json
import logging
import ssl
import urllib.request
import urllib.error
import urllib.parse

logger = logging.getLogger('SweetCheat.API')

# Try to use requests if available (more robust on Windows), fallback to urllib
try:
    import requests
    HAS_REQUESTS = True
except Exception:
    HAS_REQUESTS = False

class SweetCheatAPI:
    def __init__(self, base_url='https://sayfespace.online/trainerhub/api', api_key=None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.user = None
        self._ctx = ssl.create_default_context()

    def set_key(self, api_key):
        self.api_key = api_key

    def _headers(self):
        h = {
            'Accept': 'application/json',
            'User-Agent': 'SweetCheat-Desktop/0.8.5',
        }
        if self.api_key:
            h['Authorization'] = f'Bearer {self.api_key}'
        return h

    def _request(self, endpoint, method='GET', data=None):
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        logger.info(f"API {method} {url}")
        headers = self._headers()
        body = None
        if data is not None:
            body = json.dumps(data).encode('utf-8')
            headers['Content-Type'] = 'application/json'

        if HAS_REQUESTS:
            try:
                resp = requests.request(method, url, data=body, headers=headers, timeout=15)
                logger.info(f"API response {resp.status_code}")
                try:
                    return resp.json()
                except Exception:
                    return {'success': False, 'error': resp.text, 'status': resp.status_code}
            except Exception as e:
                logger.error(f'requests error: {e}')
                return {'success': False, 'error': str(e)}

        # Fallback urllib
        try:
            req = urllib.request.Request(url, data=body, method=method, headers=headers)
            with urllib.request.urlopen(req, context=self._ctx, timeout=15) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            try:
                return json.loads(e.read().decode('utf-8'))
            except Exception:
                return {'success': False, 'error': f'HTTP {e.code}', 'status': e.code}
        except Exception as e:
            logger.error(f'API request failed: {e}')
            return {'success': False, 'error': str(e)}

    def login(self, email, password):
        payload = {'email': email, 'password': password}
        result = self._request('auth.php?action=login', method='POST', data=payload)
        if result.get('success') and result.get('api_key'):
            self.api_key = result['api_key']
            self.user = result.get('user')
        return result

    def status(self):
        return self._request('billing.php?action=status')

    def games(self, search=None, per_page=100):
        q = f'games.php?per_page={per_page}'
        if search:
            q += f'&search={urllib.parse.quote(search)}'
        return self._request(q)

    def trainers(self, game_slug):
        return self._request(f'trainers.php?game={urllib.parse.quote(game_slug)}')

    def activate_log(self, trainer_id, success=1, action='activate'):
        return self._request('trainer-logs.php?action=add', method='POST',
                             data={'trainer_id': trainer_id, 'success': success, 'action': action})

    def settings_get(self):
        return self._request('user-settings.php?action=get')

    def settings_update(self, username, theme):
        return self._request('user-settings.php?action=update_profile', method='POST',
                             data={'username': username, 'theme': theme})

    def rotate_key(self):
        return self._request('user-settings.php?action=rotate_key', method='POST', data={})

    def change_password(self, current, new):
        return self._request('user-settings.php?action=change_password', method='POST',
                             data={'current_password': current, 'new_password': new})

    def favorites(self):
        return self._request('favorites.php')

    def add_favorite(self, game_id=None, trainer_id=None):
        return self._request('favorites.php', method='POST', data={'game_id': game_id, 'trainer_id': trainer_id})

    def remove_favorite(self, game_id=None, trainer_id=None):
        return self._request('favorites.php', method='DELETE', data={'game_id': game_id, 'trainer_id': trainer_id})
