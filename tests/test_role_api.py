from .conftest import *
from flask import current_app


def test_unauthorized(client):
    rv = client.post('/roles', headers=None)
    assert rv.json['status'] == 'ERROR'
    assert rv.status_code == 401

    rv = client.patch('/roles/1', headers=None)
    assert rv.json['status'] == 'ERROR'
    assert rv.status_code == 401


def test_get_role_return_none(client):
    headers = {'X-Auth-Token': str(client.secret)}

    rv = client.get('/roles/200', headers=headers)
    assert rv.status_code == 404
    assert rv.json['status'] == 'ERROR', rv.json['status']


def test_get_role(client):
    headers = {'X-Auth-Token': str(client.secret)}
    role_id = 101
    rv = client.get(
        f'/roles/{role_id}?fields=title,data',
        headers=headers)

    v3 = rv.json['data'][0]
    assert rv.status_code == 200
    assert v3['name'] == 'everybody'

def test_post_role_invalid_form(client):
    headers = {'X-Auth-Token': str(client.secret)}
    data = {}
    rv = client.post('/roles', headers=headers, json=data)
    
    assert rv.status_code == 400

