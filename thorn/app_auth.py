# -*- coding: utf-8 -*-}
import json
import jwt
import logging
from functools import wraps

from flask import Response, g as flask_g, request, current_app
from thorn.models import User, Role, Permission

CONFIG_KEY = 'THORN_CONFIG'

log = logging.getLogger(__name__)


def authenticate(msg, params):
    """Sends a 403 response that enables basic auth"""
    return Response(json.dumps({'status': 'ERROR', 'message': msg}), 401,
                    mimetype="application/json")


def requires_role(*roles):
    def real_requires_role(f):
        @wraps(f)
        def decorated(*_args, **kwargs):
            belongs = any(r.name for r in flask_g.user.roles if r.name in roles)
            if belongs:
                return f(*_args, **kwargs)
            else:
                return Response(
                    json.dumps({'status': 'ERROR', 'message': 'Role'}), 401,
                    mimetype="application/json")

        return decorated

    return real_requires_role


def requires_permission(*permissions):
    def real_requires_permission(f):
        @wraps(f)
        def decorated(*_args, **kwargs):
            fullfill = any(
                p for r in flask_g.user.roles for p in r.permissions if
                p.name in permissions)
            if fullfill:
                return f(*_args, **kwargs)
            else:
                return Response(
                    json.dumps({'status': 'ERROR', 'message': 'Permission'}),
                    401,
                    mimetype="application/json")

        return decorated

    return real_requires_permission


def requires_auth(f):
    # noinspection PyArgumentList
    @wraps(f)
    def decorated(*_args, **kwargs):
        user_id = 1
        email = 'walter@dcc.ufmg.br'
        first_name = 'Walter'
        last_name = 'Santos'
        locale = 'pt'
        authorization = request.headers.get('Authorization')
        if authorization is not None:
            print('======')
            print(authorization)
            import pdb;pdb.set_trace()
            print(jwt.decode(authorization[7:], current_app.secret_key))

        print('======')

        if request.args.get('token') == '123456':
            r = Role(id=1, name='admin', enabled=1,
                     permissions=[Permission(id=1000, name='ADMINISTRATOR')])
        else:
            r = Role(id=1, name='admin', enabled=1,
                     permissions=[Permission(id=1, name='WORK')])

        setattr(flask_g, 'user', User(
            id=int(user_id),
            email=email,
            first_name=first_name,
            last_name=last_name,
            locale=locale,
            roles=[r]))
        return f(*_args, **kwargs)

    return decorated
