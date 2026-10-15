import json
import logging
import re
import time
import urllib
import requests
import jwt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from flask import Response, current_app, request
from flask_babel import gettext
from flask_restful import Resource

from thorn.app_auth import is_service_token, requires_auth
from thorn.models import (AuthenticationType, Configuration, Role, User, 
                          UserStatus, db)
from thorn.util import check_password, encrypt_password, ldap_authentication

from thorn.cache_config import cache
log = logging.getLogger(__name__)

# Public routes live under /api/v1/<service>/public/ ; match the segment
# anchored at the service prefix, not anywhere in the path.
PUBLIC_PATH = re.compile(r'^/api/v1/[^/]+/public/')
TOKEN_TTL_SECONDS = 12 * 3600  # shortcut: fixed default, make configurable if needed
JWKS_REFRESH_MIN_INTERVAL = 60  # also the back-off after a failed download
JWKS_TTL = 3600  # how long the downloaded JWKS counts as fresh
OPENID_SETTINGS_TTL = 60  # DB read of the OpenID configuration rows


def _is_public_path(path):
    if '..' in path or '%' in path:
        return False
    return PUBLIC_PATH.match(path) is not None


def _clean(value):
    """Make a value safe for the ';'-delimited X-User-Data header."""
    return str(value or '').replace(';', ',').replace('\n', ' ').replace(
        '\r', ' ')


def _find_jwk(jwks, kid):
    for jwk in (jwks or {}).get('keys', []):
        if jwk.get('kid') == kid:
            return jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
    return None


def _download_jwks(json_conf):
    """Returns (jwks, issuer) from the OpenID discovery document."""
    discovery = requests.get(json_conf['authority'], timeout=5).json()
    jwks = requests.get(discovery['jwks_uri'], timeout=5).json()
    return jwks, discovery.get('issuer')


def _cache_call(method, *args, default=None, **kwargs):
    """Cache errors (e.g. Redis down) must degrade, never fail the login."""
    try:
        return getattr(cache, method)(*args, **kwargs)
    except Exception as ex:  # noqa: BLE001
        log.warning('Cache %s failed: %s', method, ex)
        return default


def _get_openid_settings():
    """OPENID_CONFIG / OPENID_JWT_PUB_KEY rows, cached to spare the DB."""
    settings = _cache_call('get', 'OPENID_SETTINGS')
    if settings is None:
        query = Configuration.query.filter(Configuration.name.in_(
            ['OPENID_CONFIG', 'OPENID_JWT_PUB_KEY']))
        settings = dict((c.name, c.value) for c in query)
        _cache_call('set', 'OPENID_SETTINGS', settings,
                    timeout=OPENID_SETTINGS_TTL)
    return settings


def invalidate_openid_cache():
    """Call after the OpenID configuration changes."""
    _cache_call('delete', 'OPENID_SETTINGS')
    _cache_call('delete', 'OPENID_JWKS_FRESH')


def _get_signing_key(json_conf, kid):
    """Returns (public key, issuer) for the token's kid.

    The JWKS is kept without expiry and refreshed when older than JWKS_TTL,
    when the kid is unknown (rotation) or the issuer is not known yet. A
    failed refresh keeps serving the last known keys, and downloads are
    limited to one per JWKS_REFRESH_MIN_INTERVAL.
    """
    jwks = _cache_call('get', 'OPENID_JWKS')
    pkey = _find_jwk(jwks, kid)
    issuer = json_conf.get('issuer') or _cache_call('get', 'OPENID_ISSUER')
    stale = not _cache_call('get', 'OPENID_JWKS_FRESH')
    if (stale or pkey is None or issuer is None) and _cache_call(
            'add', 'OPENID_JWKS_LOCK', True,
            timeout=JWKS_REFRESH_MIN_INTERVAL, default=True):
        try:
            log.info('Downloading JWKS')
            jwks, discovered = _download_jwks(json_conf)
            _cache_call('set', 'OPENID_JWKS', jwks, timeout=0)
            _cache_call('set', 'OPENID_ISSUER', discovered, timeout=0)
            _cache_call('set', 'OPENID_JWKS_FRESH', True, timeout=JWKS_TTL)
            pkey = _find_jwk(jwks, kid)
            issuer = json_conf.get('issuer') or discovered
        except Exception:  # noqa: BLE001
            log.exception('JWKS download failed; using cached keys')
    if pkey is None:
        raise ValueError(f'Unknown key id {kid}')
    return pkey, issuer


def _get_global_roles():
    return [r.id for r in Role.query.filter(Role.all_user == True)]  # noqa: E712

def _get_global_permissions():
  return [p.name for r in Role.query.filter(Role.all_user == True) for p in r.permissions]


def _get_jwt_token(user):
    return jwt.encode(
        {
            'id': user.id,
            'exp': int(time.time()) + TOKEN_TTL_SECONDS,
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

    login = openid_user.get('username') or sub
    email = openid_user.get('email', login) or login
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
    login = openid_user.get('username') or sub
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
    # user.roles = list(Role.query.filter(Role.name=='everybody'))
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
        result = {}

        # Check if URL is unprotected
        unprotected = config.get(
            'unprotected_urls', {})
        path = request.headers.get('X-Original-URI', '')
        qs = {}
        if '?' in path:
            path, qs = path.split('?', 1)
            qs = urllib.parse.parse_qs(qs)

        method = request.headers.get('X-Original-Method', 'INVALID')

        if method in unprotected.get(path, []) or unprotected.get(path) == [] \
                or _is_public_path(path):
            status_code = 200
        elif is_service_token(request.headers.get('X-Auth-Token')):
            status_code = 200
            result = { 
                    'X-User-Id': 1,
                    'X-Permissions': ['ADMINISTRATOR'],
                    'X-User-Locale': 'pt',
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
            openId_config = _get_openid_settings()

            has_open_id_config = ('OPENID_CONFIG' in openId_config)
            
            create_open_id_user=True
            open_id_success = False
            if has_open_id_config:
                json_conf = json.loads(openId_config['OPENID_CONFIG'])
                algorithms = ["RS256"]
                if json_conf.get('enabled', False):
                    log.info('Using OpenID token')
                    if ('OPENID_JWT_PUB_KEY' in openId_config and 
                        len(openId_config.get('OPENID_JWT_PUB_KEY', '')) > 5):
                        log.info('Using provided OpenID Pub Key')
                        cert = (openId_config['OPENID_JWT_PUB_KEY'].encode(
                            'utf8'))
                        pkey = serialization.load_pem_public_key(cert, 
                                backend=default_backend())
                        issuer = json_conf.get('issuer')
                    else:
                        
                        pkey, issuer = _get_signing_key(
                            json_conf,
                            jwt.get_unverified_header(token)['kid'])
                    if issuer is None:
                        # shortcut: PEM key without discovery cannot learn the
                        # issuer; set "issuer" in OPENID_CONFIG to enforce it.
                        log.warning('OpenID issuer not verified')
                    decoded = jwt.decode(token.encode('utf8'), key=pkey, 
                                audience=json_conf.get('client_id'),
                                issuer=issuer,
                                algorithms=algorithms,
                                options={'verify_exp': verify_exp})
                    login = decoded.get('username') or decoded.get('sub')
                    user = User.query.filter(
                        User.login==login).first()
                    
                    if user:
                        # Only enabled OpenID users may log in this way;
                        # never let an IdP token take over another user type.
                        if (user.enabled
                                and user.status == UserStatus.ENABLED
                                and user.authentication_type ==
                                AuthenticationType.OPENID):
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
                    # Tokens issued before expiry existed never lapse: refuse.
                    if 'exp' not in decoded:
                        raise jwt.MissingRequiredClaimError('exp')
                    user = User.query.get(int(decoded.get('id')))
                    if user.enabled and user.status == UserStatus.ENABLED:
                        result = self._get_result(user)
                        status_code = 200

        except Exception as ex:
            log.exception(ex)
        return status_code,result

    def _get_result(self, user):
        global_roles = _get_global_roles()
        global_permissions = _get_global_permissions()     
        permissions = ','.join(set(
		[p.name for r in user.roles for p in r.permissions] + 
		global_permissions
	)) 
        return {
              'X-User-Id': user.id,
              'X-Permissions': permissions,
              'X-Roles': ','.join(map(str, [
                  r.id for r in user.roles] + global_roles)),
              'X-User-Locale': user.locale,
              'X-User-Data': ';'.join([
                  _clean(user.login), _clean(user.email),
                  _clean(f'{user.first_name or ""} {user.last_name or ""}'
                         .strip()),
                  _clean(user.locale)])
              }
    

