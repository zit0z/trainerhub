"""SweetCheat Desktop API Client"""
import json
import logging
import urllib.request
import urllib.error
import urllib.parse
import ssl

logger = logging.getLogger('SweetCheat.API')

class SweetCheatAPI:
    def __init__(self, base_url='https://sayfespace.online/sweetcheat/api', api_key=None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.user = None
        self._ctx = ssl.create_default_context()

    def set_key(self, api_key):
        self.api_key = api_key

    def _request(self, endpoint, method='GET', data=None, headers=None):
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        h = headers or {}
        h['Accept'] = 'application/json'
        if self.api_key:
            h['Authorization'] = f'Bearer {self.api_key}'
        body = None
        if data is not None:
            body = json.dumps(data).encode('utf-8')
            h['Content-Type'] = 'application/json'
        try:
            req = urllib.request.Request(url, data=body, method=method, headers=h)
            with urllib.request.urlopen(req, context=self._ctx, timeout=15) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            try:
                return json.loads(e.read().decode('utf-8'))
            except Exception:
                return {'success': False, 'error': f'HTTP {e.code}'}
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

    def favorites(self):
        return self._request('favorites.php')

    def add_favorite(self, game_id=None, trainer_id=None):
        return self._request('favorites.php', method='POST', data={'game_id': game_id, 'trainer_id': trainer_id})

    def remove_favorite(self, game_id=None, trainer_id=None):
        return self._request('favorites.php', method='DELETE', data={'game_id': game_id, 'trainer_id': trainer_id})
