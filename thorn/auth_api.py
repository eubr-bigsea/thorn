import json
import logging
import urllib
import requests
import jwt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from flask import Response, current_app, request
from flask_babel import gettext
from flask_restful import Resource

from thorn.app_auth import requires_auth
from thorn.models import (AuthenticationType, Configuration, Role, User, 
                          UserStatus, db)
from thorn.util import check_password, encrypt_password, ldap_authentication

from thorn.cache_config import cache
log = logging.getLogger(__name__)


def _get_global_roles():
    return [r.id for r in Role.query.filter(Role.all_user==True)]  # noqa: E712

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
        }, current_app.secret_key)


def _success(user):
    # Include global roles
    user.roles.extend(Role.query.filter(Role.all_user==True))  # noqa: E712
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
        'displayName', 
        ldap_user.get('nome', ['User']))[0].decode('utf8').split(' ', 1)
    user = User(login=login, email=ldap_user.get('mail', [''])[0],
                notes=gettext('LDAP User'), first_name=first_name,
                last_name=last_name.strip(),
                locale='pt',
                authentication_type=AuthenticationType.LDAP,
                encrypted_password=encrypt_password('dummy'))
    db.session.add(user)
    db.session.commit()
    return user
def _update_open_id_user_information(user: User, openid_user: dict):
    sub = openid_user.get('sub')
    notes = f'{{"sub": "{sub}", "OpenId": true}}'
    login = openid_user.get('username')
    email = openid_user.get('email')
    first_name = openid_user.get('given_name')
    last_name = openid_user.get('family_name')

    
    if any([user.login != login, 
           user.email != email, 
           user.first_name != first_name, 
           user.last_name != last_name]):
        user.login = login
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.notes = notes
        db.session.add(user)
        db.session.commit()

def _create_open_id_user(openid_user:dict):
    sub = openid_user.get('sub')
    notes = f'{{"sub": "{sub}", "OpenId": true}}'
    login = openid_user.get('username')
    email = openid_user.get('email') or login
    first_name = openid_user.get('given_name')
    last_name = openid_user.get('family_name')

    user = User(login=login, 
                first_name=first_name,
                last_name=last_name,
                locale='pt',
                email=email,
                notes=notes,
                authentication_type=AuthenticationType.OPENID,
                encrypted_password=encrypt_password('dummy'))
    user.roles = list(Role.query.filter(Role.name=='everybody'))
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
            query = Configuration.query.filter(
                Configuration.name.in_(ldap_keys))
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
            user = User.query.filter(
                User.api_token==qs.get('api_token')[0]).first()
            if user is not None and user.enabled \
                    and user.status not in [UserStatus.DELETED, 
                        UserStatus.PENDING_APPROVAL]:
                result = self._get_result(user)
                status_code = 200
        else: 
            authorization = (request.headers.get('Authorization') or 
                request.headers.get('X-Authentication'))
            offset = 7 if authorization and authorization.startswith(
                    'Bearer ') else 0
            result = {'status': 'ERROR', 
                    'msg': gettext('Invalid authentication')}
            #breakpoint()
            if authorization is None:
                authorization = qs.get('token')[0] if 'token' in qs else None
                offset = 0
            if authorization is not None:
                status_code, result = self._validate_authorization_token(
                    authorization[offset:],
                    request.headers.get('X-THORN-ID') == 'true',
                    verify_exp=not current_app.testing)
            else:
                log.warn(gettext('No suitable authentication method found.'))
        return '', status_code, result

    def _validate_authorization_token(self, authorization, try_old_thorn_token,
                                      verify_exp=True):
        """ Validate tokens in Authorization request header (e.g. JWT tokens)
        """
        token = authorization
        status_code = 401
        result = {}
        try:
            
            # using open id  
            openId_keys = ['OPENID_CONFIG', 'OPENID_JWT_PUB_KEY']
            query = Configuration.query.filter(
                        Configuration.name.in_(openId_keys))
            openId_config = dict((c.name, c.value) for c in query)

            has_open_id_config = ('OPENID_CONFIG' in openId_config)
            
            create_open_id_user=True
            open_id_success = False
            if has_open_id_config:
                json_conf = json.loads(openId_config['OPENID_CONFIG'])
                algorithms = ["RS256"]
                if json_conf['enabled']:
                    log.info('Using OpenID token')
                    if ('OPENID_JWT_PUB_KEY' in openId_config and 
                        len(openId_config.get('OPENID_JWT_PUB_KEY', '')) > 5):
                        log.info('Using provided OpenID Pub Key')
                        cert = (openId_config['OPENID_JWT_PUB_KEY'].encode(
                            'utf8'))
                        pkey = serialization.load_pem_public_key(cert, 
                                backend=default_backend())
                    else:
                        
                        # Try to download 
                        jwks = cache.get('OPENID_JWKS')
                        log.info('Downloading JWS? %s', jwks is None)
                        if jwks is None:
                            r = requests.get(json_conf['authority'])
                            jwks_uri = r.json()['jwks_uri']
                            r = requests.get(jwks_uri)
                            jwks = r.json()
                        else:
                            kid = jwt.get_unverified_header(token)['kid']
                            jwks = cache.get('OPENID_JWKS')

                        # keep the cache warm
                        cache.add('OPENID_JWKS', jwks)
                        print(jwks, token)
                        token_kid = jwt.get_unverified_header(token)['kid']
                        for jwk in jwks['keys']:
                            kid = jwk['kid']
                            if token_kid == kid:
                                pkey = jwt.algorithms.RSAAlgorithm.from_jwk(
                                    json.dumps(jwk))
                                log.info('Found key %s', token_kid)
                                break
                    #breakpoint()
                    decoded = jwt.decode(token.encode('utf8'), key=pkey, 
                                audience=json_conf.get('client_id'),
                                algorithms=algorithms,
                                options={'verify_exp': verify_exp})
                    user = User.query.filter(
                        User.login==decoded.get('username')).first()
                    
                    if user:
                        if user.enabled and user.authentication_type == 'OPENID':
                            _update_open_id_user_information(user, decoded)
                            result = self._get_result(user)
                        
                        status_code = 200
                    elif create_open_id_user: # creates the user
                        user = _create_open_id_user(decoded)
                        result = self._get_result(user)
                        status_code = 200
                    open_id_success = True
            if not open_id_success:
                if try_old_thorn_token: # Old thorn auth
                    decoded = jwt.decode(token, current_app.secret_key, 
                            algorithms=["HS256"])
                    user = User.query.get(int(decoded.get('id')))
                    if user.enabled and user.status == UserStatus.ENABLED:
                        result = self._get_result(user)
                        status_code = 200

        except Exception as ex:
            log.exception(ex)
        return status_code,result

    def _get_result(self, user):
        global_roles = _get_global_roles()
        return {
              'X-User-Id': user.id,
              'X-Permissions': ','.join([p.name for r in user.roles 
                  for p in r.permissions]),
              'X-Roles': ','.join(map(str, [
                  r.id for r in user.roles] + global_roles)),
              'X-Locale': user.locale,
              'X-User-Data': (f'{user.login};{user.email};{user.first_name} '
                        f'{user.last_name};{user.locale}')
              }
    

