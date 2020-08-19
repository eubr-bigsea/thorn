# -*- coding: utf-8 -*-}
import json
import logging
import urllib

import jwt
from thorn.app_auth import requires_auth, requires_permission
from flask import request, current_app, Response
from flask_restful import Resource
from thorn.models import User, db, AuthenticationType
from thorn.util import check_password, ldap_authentication, encrypt_password
from flask_babel import force_locale, gettext, get_locale
from thorn.models import *

log = logging.getLogger(__name__)


def _get_global_roles():
    return [r.id for r in Role.query.filter(Role.all_user==True)]

def _get_jwt_token(user):
    return jwt.encode(
        {
            'id': user.id,
            #'name': '{} {}'.format(
            #    user.first_name or '', user.last_name or '').strip(),
            #'email': user.email,
            #'login': user.email,
            #'locale': user.locale,
            #'permissions': [p.name for r in user.roles
            #                for p in r.permissions]
        }, current_app.secret_key).decode('utf8')


def _success(user):
    # Include global roles
    user.roles.extend(Role.query.filter(Role.all_user==True))
    user_data = {
            'id': user.id,
            'email': user.email,
            'login': user.login,
            'locale': user.locale,
            'workspace': {'id': user.workspace.id if user.workspace else None},
            'name': user.first_name + ('' if not user.last_name else ' ' 
                + user.last_name),
            'roles': [{'name': r.name, 'description': r.description, 
                'permissions': [{'id': p.id, 'name': p.name} 
                    for p in r.permissions],
                'id': r.id, 'label': r.label} for r in user.roles]
            }
    return Response(
            json.dumps({'status': 'OK', 'token': _get_jwt_token(user), 
                'user': user_data}), 200,
        mimetype="application/json")


def _create_ldap_user(login: str, ldap_user:dict):
    first_name, last_name = ldap_user.get(
        'displayName', ldap_user.get('nome', ['User']))[0].decode('utf8').split(' ', 1)
    user = User(login=login, email=ldap_user.get('mail', [''])[0],
                notes=gettext('LDAP User'), first_name=first_name,
                last_name=last_name.strip(),
                locale='pt',
                authentication_type=AuthenticationType.LDAP,
                encrypted_password=encrypt_password('dummy'))
    db.session.add(user)
    db.session.commit()
    return user


class AuthenticationApi(Resource):
    """
    Authenticates users.
    """

    def post(self):
        msg = gettext('Invalid login or password.')
        result = Response(json.dumps({'status': 'ERROR', 'message': msg}), 401,
                          mimetype="application/json")
    
        if 'application/json' in request.content_type:
            password = request.json['user']['password']
            login = request.json['user']['email']
        else:
            password = request.form.get('password')
            login = request.form.get('login')

        config = current_app.config['THORN_CONFIG']
        if all([login, password]):
            user = User.query.filter(User.login == login).first()
            ldap_keys = ['LDAP_SERVER', 'LDAP_BASE_DN', 'LDAP_USER_DN']
            query = Configuration.query.filter(Configuration.name.in_(ldap_keys))
            ldap_config = dict( (c.name, c.value) for c in query)
            if user:
                if user.enabled:
                    if user.authentication_type == AuthenticationType.INTERNAL:
                        if check_password(password.encode('utf8'),
                                          user.encrypted_password.encode(
                                              'utf8')):
                            result = _success(user)
                    elif user.authentication_type == AuthenticationType.LDAP:
                        ldap_authentication(ldap_config, login, password)[0][1]
                        result = _success(user)
                    else:
                        log.warn(gettext('Unsupported authentication type'))
                else:
                    msg = gettext('User disabled')
                    result = Response(
                        json.dumps({'status': 'ERROR', 'message': msg}), 401,
                        mimetype="application/json")
            elif 'ldap' in config['providers']:
                ldap_data = ldap_authentication(ldap_config, login, password)
                if ldap_data:
                    ldap_user = ldap_data[0][1]
                    user = _create_ldap_user(login, ldap_user)
                    result = _success(user)
    
        return result


class ValidateTokenApi(Resource):
    """
    Validates JWT tokens.
    """
    @requires_auth
    def get(self):
        return "OK", 200

    def post(self):
        status_code = 401
        user = None
        config = current_app.config['THORN_CONFIG']

        # Check if URL is unprotected
        unprotected = config.get(
            'unprotected_urls', {})
        path = request.headers.get('X-Original-URI', '')
        qs = {}
        if '?' in path:
            path, qs = path.split('?')
            qs = urllib.parse.parse_qs(qs)

        method = request.headers.get('X-Original-Method', 'INVALID')

        if method in unprotected.get(path, []) or unprotected.get(path) == [] \
                or '/public/' in path:
            status_code = 200
            result = {}
        elif request.headers.get('X-Auth-Token') == str(config.get('secret')):
            status_code = 200
            result = { 
                    'X-User-Id': 1,
                    'X-Permissions': ['ADMINISTRATOR'],
                    'X-Locale': 'pt',
                    'X-User-Data': '{};{};{} {};{}'.format(
                        'admin', 'admin@lemonade.org.br',
                        'Admin', 'Lemonade',
                        'pt')
                    }
        elif 'api_token' in qs:
            user = User.query.filter(User.api_token==qs.get('api_token')[0]).first()
            if user is not None and user.enabled and user.status == UserStatus.ENABLED:
                result = self._get_result(user)
                status_code = 200
        else: 
            authorization = request.headers.get('Authorization')
            offset = 7 if authorization and authorization.startswith(
                    'Bearer ') else 0
            result = {'status': 'ERROR', 
                    'msg': gettext('Invalid authentication')}
            if authorization is None:
                authorization = qs.get('token')[0] if 'token' in qs else None
                offset = 0
            if authorization is not None:
                try:
                    decoded = jwt.decode(authorization[offset:],
                                         current_app.secret_key)
                    user = User.query.get(int(decoded.get('id')))
                    if user.enabled and user.status == UserStatus.ENABLED:
                        result = self._get_result(user)
                        status_code = 200
                except Exception as ex:
                    log.error(ex)
        return '', status_code, result

    def _get_result(self, user):
        global_roles = _get_global_roles()
        return {
              'X-User-Id': user.id,
              'X-Permissions': ','.join([p.name for r in user.roles 
                  for p in r.permissions]),
              'X-Roles': ','.join(map(str, [
                  r.id for r in user.roles] + global_roles)),
              'X-Locale': user.locale,
              'X-User-Data': '{};{};{} {};{}'.format(
                  user.login, user.email,
                  user.first_name, user.last_name,
                  user.locale)
              }
    

