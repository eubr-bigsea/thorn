import logging

import bcrypt
import ldap
from flask_babel import gettext

log = logging.getLogger(__name__)


def encrypt_password(password: str):
    return bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt(12))


def check_password(password: str, hashed: str):
    check = bcrypt.checkpw(password, hashed)
    return check


# noinspection PyUnresolvedReferences
def ldap_authentication(ldap_config: dict, login: str, password: str):
    if not ('LDAP_BASE_DN' in ldap_config and 'LDAP_SERVER' in ldap_config 
            and 'LDAP_USER_DN' in ldap_config):
        log.error(gettext('LDAP server is not correctly configured.'))
        return None

    ldap_server = ldap_config.get('LDAP_SERVER')
    base_dn = ldap_config.get('LDAP_BASE_DN')
    user_dn = ldap_config.get('LDAP_USER_DN').format(login=login)

    connect = ldap.initialize('ldap://' + ldap_server)
    connect.set_option(ldap.OPT_NETWORK_TIMEOUT, 5.0)
    try:
        connect.set_option(ldap.OPT_REFERRALS, 0)
        connect.simple_bind_s(user_dn, password)
        result = connect.search_s(
            base_dn, ldap.SCOPE_SUBTREE,
            'uid=' + login)
        connect.unbind_s()
        return result
    except ldap.INVALID_CREDENTIALS:
        pass
    except ldap.SERVER_DOWN:
        log.error(gettext('LDAP server is down.'))
    except ldap.LDAPError as lde:
        connect.unbind_s()
        log.error(gettext('LDAP server reported an error.'))


def translate_validation(validation_errors):
    for field, errors in list(validation_errors.items()):
        validation_errors[field] = [gettext(error) for error in errors]
    return validation_errors
