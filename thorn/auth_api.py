# -*- coding: utf-8 -*-}
import json
import logging
import urllib
from gettext import gettext

import jwt
from flask import request, current_app, Response
from flask_restful import Resource
from thorn.models import User, db, AuthenticationType
from thorn.util import check_password, ldap_authentication, encrypt_password

log = logging.getLogger(__name__)


def _get_jwt_token(user):
    return jwt.encode(
        {
            'id': user.id,
            'name': '{} {}'.format(
                user.first_name or '', user.last_name or '').strip(),
            'email': user.email,
            'login': user.email,
            'locale': user.locale,
            'permissions': [p.name for r in user.roles
                            for p in r.permissions]
        }, current_app.secret_key).decode('utf8')


def _success(user):
    user_data = {
            'id': user.id,
            'email': user.email,
            'login': user.login,
            'locale': user.locale,
            'name': user.first_name + ('' if not user.last_name else ' ' 
                + user.last_name),
            'roles': [r.name for r in user.roles]
            }
    return Response(
            json.dumps({'status': 'OK', 'token': _get_jwt_token(user), 
                'user': user_data}), 200,
        mimetype="application/json")


def _create_ldap_user():
    first_name, last_name = ldap_user.get(
        'displayName')[0].decode('utf8').split(' ', 1)
    user = User(login=login, email=ldap_user.get('mail', [''])[0],
                notes=gettext('LDAP User'), first_name=first_name,
                last_name=last_name.strip(),
                authentication_type=AuthenticationType.LDAP,
                encrypted_password=encrypt_password('dummy'))
    db.session.add(user)
    db.session.commit()


class AuthenticationApi(Resource):
    """
    Authenticates users.
    """

    def post(self):
        msg = gettext('Invalid login or password')
        result = Response(json.dumps({'status': 'ERROR', 'message': msg}), 401,
                          mimetype="application/json")

        if 'application/json' in request.content_type:
            password = request.json['user']['password']
            login = request.json['user']['email']
        else:
            password = request.form.get('password')
            login = request.form.get('login')
        if all([login, password]):
            user = User.query.filter(User.login == login).first()
            ldap_config = {}
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
            else:
                ldap_data = ldap_authentication(ldap_config, login, password)
                if ldap_data:
                    ldap_user = ldap_data[0][1]
                    _create_ldap_user(ldap_user)
                    result = Response(json.dumps(
                        {'status': 'OK', 'token': _get_jwt_token(user)}),
                        200, mimetype="application/json")

        return result


class ValidateTokenApi(Resource):
    """
    Validates JWT tokens.
    """

    def post(self):
        status_code = 401
        user = None
        authorization = request.headers.get('Authorization')
        offset = 7 if authorization and authorization.startswith('Bearer ') else 0
        result = {'status': 'ERROR', 'msg': gettext('Invalid authentication')}
        if authorization is None:
            qs = {}
            if 'X-Original-URI' in request.headers:
                qs = urllib.parse.parse_qs(request.headers['X-Original-URI'])
            authorization = qs.get('token')[0] if 'token' in qs else None
            offset = 0

        if authorization is not None:
            try:
                decoded = jwt.decode(authorization[offset:],
                                     current_app.secret_key)
                result = {'X-User-Id': decoded.get('id'),
                          'X-Permissions': decoded.get('permissions'),
                          'X-Locale': decoded.get('locale'),
                          'X-User-Data': '{};{};{};{}'.format(
                              decoded.get('login'), decoded.get('email'),
                              decoded.get('name'), decoded.get('locale'))
                          }
                status_code = 200
            except Exception as ex:
                log.error(ex)
        return '', status_code, result
