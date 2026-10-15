from thorn.auth_api import _discovery_url

FULL = 'https://idp.example/oauth2/token/.well-known/openid-configuration'


def test_discovery_url_from_base():
    assert _discovery_url('https://idp.example/oauth2/token') == FULL
    assert _discovery_url('https://idp.example/oauth2/token/') == FULL


def test_discovery_url_keeps_full_url():
    assert _discovery_url(FULL) == FULL
