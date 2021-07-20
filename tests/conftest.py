import json
import os
import pytest
import datetime
import flask_migrate
from thorn.app import create_app
from thorn.models import (AuthenticationType, User, Role, UserStatus, db)


def get_users():
    u1 = User(
        id =2,
        login='manager',
        email='man@lemonade.org.br',
        enabled=True,
        status=UserStatus.ENABLED,
        authentication_type =AuthenticationType.INTERNAL,
        encrypted_password='xyuasdasdkjkl',
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now(),
        first_name='Manager',
        last_name='Man',
        locale='pt',
        confirmed_at=datetime.datetime.now(),
        api_token='SOME TOKEN',
        roles=[])
    u2 = User(
        id=3,
        login='manager2',
        email='man2@lemonade.org.br',
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
        api_token='SOME TOKEN',
        roles=[])

    return [u1, u2]

@pytest.fixture(scope='session')
def app():
    return create_app()

@pytest.fixture(scope='session')
def client(app):
    path = os.path.dirname(os.path.abspath(__name__))
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{path}/test.db'
    app.config['TESTING'] = True
    # import pdb; pdb.set_trace()
    with app.test_client() as client:
        with app.app_context():
            flask_migrate.downgrade(revision="base")
            flask_migrate.upgrade(revision='head')
            for user in get_users():
                db.session.add(user)
            client.secret = app.config['THORN_CONFIG']['secret']
            db.session.commit()
        yield client
