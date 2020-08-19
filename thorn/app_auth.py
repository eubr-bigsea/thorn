# -*- coding: utf-8 -*-}
import json
import jwt
import logging
from functools import wraps

from collections import namedtuple
from flask import Response, g as flask_g, request, current_app
from thorn.models import User, Role, Permission

CONFIG_KEY = 'THORN_CONFIG'

log = logging.getLogger(__name__)

MSG1 = 'Could not verify your access level for that URL. ' \
       'You have to login with proper credentials provided by Lemonade Thorn'

MSG2 = 'Could not verify your access level for that URL. ' \
       'Invalid authentication token'


SessionUser = namedtuple(
    "SessionUser", "id, login, email, name, first_name, last_name, locale, permissions")

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
            fullfill = len(set(permissions).intersection(
                    set(flask_g.user.permissions))) > 0
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
    @wraps(f)
    def decorated(*_args, **kwargs):
        config = current_app.config[CONFIG_KEY]
        # TODO: User uma configuração / chave no thorn conhecida aqui
        user_id = request.headers.get('x-user-id')
        permissions = request.headers.get('x-permissions', '')
        user_data = request.headers.get('x-user-data')

        if all([user_data, user_id]):
            login, email, name, locale = user_data.split(';')
            setattr(flask_g, 'user', 
                    SessionUser(user_id, login, email, name, locale, '', '',
                permissions.split(',')))
            return f(*_args, **kwargs)
        else:
            return authenticate(MSG1, {'message': 'Invalid authentication'})

    return decorated

