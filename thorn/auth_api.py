# -*- coding: utf-8 -*-}
import logging
import urllib
import jwt
import json
from flask import request, current_app, Response
from flask_restful import Resource
from thorn.models import User, Role, Permission, db, AuthenticationType
from thorn.util import check_password, ldap_authentication, encrypt_password

log = logging.getLogger(__name__)

class AuthenticationApi(Resource):
    """"""
    def post(self):

        msg = 'Invalid login or password'
        result = Response(json.dumps({'status': 'ERROR', 'message': msg}), 401,
                    mimetype="application/json")
        password = request.form.get('password')
        login = request.form.get('login')
        if all([login, password]):
            user = User.query.filter(User.login == login).first()
            if user:
                if user.enabled:
                     if check_password(password.encode('utf8'), 
                             user.encrypted_password.encode('utf8')):
                         token = jwt.encode(
                                 {
                                     'id': user.id,
                                     'name': '{} {}'.format(
                                         user.first_name, user.last_name).strip(),
                                     'email': user.email, 
                                     'login': user.email, 
                                     'locale': user.locale, 
                                     'permissions': [p.name for r in user.roles 
                                         for p in r.permissions]
                                 }, current_app.secret_key)
                         result = Response(json.dumps({'status': 'OR', 
                             'token': token.decode('utf8')}), 200,
                             mimetype="application/json")
                else:
                    msg = 'User disabled'
                    result = Response(json.dumps({'status': 'ERROR', 'message': msg}), 401,
                                mimetype="application/json")
            else:
                ldap_user = ldap_authentication(login, password)[0][1]
                first_name, last_name = ldap_user.get(
                        'displayName')[0].decode('utf8').split(' ', 1)
                user = User(login=login, email=ldap_user.get('mail', [''])[0],
                        notes='LDAP User', first_name=first_name,
                        last_name=last_name.strip(), 
                        authentication_type=AuthenticationType.LDAP,
                        encrypted_password=encrypt_password('dummy'))
                db.session.add(user)
                db.session.commit()
                token = jwt.encode(
                   {
                       'id': user.id,
                       'name': '{} {}'.format(
                           user.first_name, user.last_name).strip(),
                       'email': user.email, 
                       'login': user.email, 
                       'locale': user.locale,
                       'permissions': [p.name for r in user.roles 
                           for p in r.permissions]
                   }, current_app.secret_key)

                result = Response(json.dumps({'status': 'OR', 
                    'token': token.decode('utf8')}), 200,
                    mimetype="application/json")

        return result

class ValidateTokenApi(Resource):
    """  """

    def post(self):
        status_code = 401
        authorization = request.headers.get('Authorization')
        offset = 7
        if authorization is None:
            if 'X-Original-URI' in request.headers:
                qs = urllib.parse.parse_qs(request.headers['X-Original-URI'])
            authorization = qs.get('token')[0] if 'token' in qs else None
            offset = 0

        if authorization is not None:
            try:
                decoded = jwt.decode(authorization[offset:], current_app.secret_key)
                status_code = 200
            except Exception as ex:
                log.error(ex)

        return '', status_code, {'X-User-Id': decoded.get('id'),
                                 'X-Permissions': decoded.get('permissions'),
                                 'X-User-Data': '{};{};{};{}'.format(
                                     decoded.get('login'), decoded.get('email'),
                                     decoded.get('name'), decoded.get('locale'))
                                 }
