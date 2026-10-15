from types import SimpleNamespace

from thorn import auth_api


def _user():
    return SimpleNamespace(login='ana', email='ana@x.org', first_name='Ana',
                           last_name='Silva', notes=None)


def _run(monkeypatch, claims):
    saved = []
    session = SimpleNamespace(add=saved.append, commit=lambda: None)
    monkeypatch.setattr(auth_api, 'db', SimpleNamespace(session=session))
    user = _user()
    auth_api._update_open_id_user_information(user, claims)
    return user


def test_missing_name_claims_keep_stored_names(monkeypatch):
    user = _run(monkeypatch, {'sub': 's', 'username': 'ana',
                              'email': 'ana@x.org'})
    assert (user.first_name, user.last_name) == ('Ana', 'Silva')


def test_name_claims_update_stored_names(monkeypatch):
    user = _run(monkeypatch, {'sub': 's', 'username': 'ana',
                              'email': 'ana@x.org', 'given_name': 'Maria',
                              'family_name': 'Souza'})
    assert (user.first_name, user.last_name) == ('Maria', 'Souza')


class _Resp:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


CONF = {'authority': 'https://idp.example/oauth2/token'}


def test_userinfo_fills_missing_names(monkeypatch):
    def fake_get(url, **kwargs):
        if url.endswith('/.well-known/openid-configuration'):
            return _Resp({'userinfo_endpoint': 'https://idp.example/userinfo'})
        assert kwargs['headers']['Authorization'] == 'Bearer tok'
        return _Resp({'given_name': 'Ana', 'family_name': 'Silva'})
    monkeypatch.setattr(auth_api.requests, 'get', fake_get)
    claims = auth_api._with_userinfo_names(CONF, 'tok', {'sub': 's'})
    assert (claims['given_name'], claims['family_name']) == ('Ana', 'Silva')


def test_userinfo_failure_keeps_claims(monkeypatch):
    def boom(url, **kwargs):
        raise ConnectionError()
    monkeypatch.setattr(auth_api.requests, 'get', boom)
    claims = {'sub': 's'}
    assert auth_api._with_userinfo_names(CONF, 'tok', claims) == claims
