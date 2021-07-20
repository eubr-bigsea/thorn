from .conftest import *
from flask import current_app
from flask_babel import gettext

def test_unauthorized(client):
    rv = client.get('/users', headers=None)
    assert rv.json['status'] == 'ERROR'
    assert rv.status_code == 401

    rv = client.get('/users/1', headers=None)
    assert rv.json['status'] == 'ERROR'
    assert rv.status_code == 401


def test_get_users(client):
    """Retrieve a list of users."""

    headers = {'X-Auth-Token': str(client.secret)}
    rv = client.get('/users', headers=headers)
    assert rv.json['pagination']['total'] == 3
    d1 = rv.json['data'][0]
    assert rv.status_code == 200


def test_get_users_filter(client):
    """Retrieve a list of users."""

    headers = {'X-Auth-Token': str(client.secret)}
    rv = client.get('/users?query=manager', headers=headers)
    assert rv.json['pagination']['total'] == 2
    assert rv.status_code == 200

def test_get_user(client):
    headers = {'X-Auth-Token': str(client.secret)}
    user_id = 2
    rv = client.get(f'/users/{user_id}', headers=headers)
    d1 = rv.json['data'][0]
    
    assert rv.status_code == 200
    assert d1['first_name'] == 'Manager'
    assert d1['login'] == 'manager'


def test_delete_user(client, app):
    user_id = 1000
    with app.app_context():
        u3 = User(
        id=user_id,
        login='manager3',
        email='man3@lemonade.org.br',
        enabled=True,
        status=UserStatus.ENABLED,
        authentication_type =AuthenticationType.INTERNAL,
        encrypted_password='xyuasdasdkjkl',
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now(),
        first_name='Manager2',
        last_name='Man',
        locale='pt',
        confirmed_at=datetime.datetime.now(),
        api_token='SOME TOKEN')

        db.session.add(u3)
        db.session.commit()

    headers = {'X-Auth-Token': str(client.secret)}
    rv = client.delete(f'/users/{user_id}', headers=headers)
    assert rv.status_code == 200
    assert rv.json['status'] == 'OK'
    assert rv.json['message'] == 'User deleted with success!'

    with app.app_context():
        assert User.query.get(4) is None


def test_update_user(client):
    headers = {'X-Auth-Token': str(client.secret)}

    # Missing data
    user_id = 3
    rv = client.patch(f'/users/{user_id}', headers=headers)
    assert rv.status_code == 400

    data = {
        'first_name': 'Someone',
        'enabled': False
    }
    rv = client.patch(
        f'/users/{user_id}', headers=headers, json=data)
    assert rv.status_code == 200
    with current_app.app_context():
        u = User.query.get(user_id)
        assert u.first_name == data['first_name']
        assert u.enabled == data['enabled']


def test_post_user_missing_data(client):
    headers = {'X-Auth-Token': str(client.secret)}

    # Missing data
    data = {
        'email': 'test@lemonade.org.br',
    }
    rv = client.post('/users', headers=headers, json=data)
    assert rv.status_code == 400
    assert rv.json['status'] == 'ERROR'
    assert rv.json['message'] == 'You must inform a valid password.'

def test_post_existing_user(client):
    headers = {'X-Auth-Token': str(client.secret)}

    # Missing data
    data = {
        'email': 'admin@lemonade.org.br',
        'login': 'admin@lemonade.org.br',
        'password': '124333'
    }
    rv = client.post('/users', headers=headers, json=data)
    assert rv.status_code == 400
    assert rv.json['status'] == 'ERROR'
    assert rv.json['message'] ==  gettext(
        "Email in use. Please, inform another.")


def test_post_user_success(client):
    headers = {'X-Auth-Token': str(client.secret)}

    email = 'someone@lemonade.org.br'
    data = {
        'first_name': 'Demo', 'last_name': 'App',
        'password': 'dummy', 'email': email,
        'login': email
    }
    rv = client.post('/users', headers=headers, json=data)
    assert rv.status_code == 200, rv.json

    with current_app.app_context():
        user = User.query.get(rv.json['data']['id'])
        assert user is not None
        for k, v in data.items():
            if k not in ['password']:
                assert getattr(user, k) == v

