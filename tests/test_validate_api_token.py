def _validate(client, **headers):
    return client.post('/auth/validate', headers={
        'X-Original-URI': '/api/v1/limonero/datasources',
        'X-Original-Method': 'GET', **headers})


def test_api_token_in_authorization_header(client):
    for value in ('Bearer SOME TOKEN', 'SOME TOKEN'):
        response = _validate(client, Authorization=value)
        assert response.status_code == 200
        assert response.headers['X-User-Id']


def test_api_token_in_query_string(client):
    response = client.post('/auth/validate', headers={
        'X-Original-URI': '/api/v1/limonero/datasources?api_token=SOME%20TOKEN',
        'X-Original-Method': 'GET'})
    assert response.status_code == 200


def test_unknown_api_token_is_rejected(client):
    assert _validate(client, Authorization='Bearer nope').status_code == 401
