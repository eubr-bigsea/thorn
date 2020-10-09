# -*- coding: utf-8 -*-}
from thorn.app_auth import requires_auth, requires_permission
from flask import request, current_app, g as flask_globals
from flask_restful import Resource
from sqlalchemy import or_
from thorn.util import check_password, ldap_authentication, encrypt_password
import math
import uuid
import datetime
import rq
import random
import string
import logging
from thorn.schema import *
from flask_babel import gettext, get_locale
from thorn.jobs import send_email
import json
from thorn.models import Configuration
from thorn.util import translate_validation

def _get_random_string(length):
    # Random string with the combination of lower and upper case
    letters = string.ascii_letters + string.digits
    return ''.join(random.choice(letters) for i in range(length))

log = logging.getLogger(__name__)

# region Protected\s*
class ChangeLocaleApi(Resource):
    @requires_auth
    def change_locale(self, user_id):
        pass

class GenerateUserTokenApi(Resource):
    @staticmethod
    @requires_auth
    @requires_permission('ADMINISTRATOR')
    def post(user_id):
        user = User.query.get(user_id)
        if not user:
            return {'status': 'ERROR', 'message': 'not found'}, 404
        user.api_token = _get_random_string(15)
        db.session.add(user)
        db.session.commit()
        return {'status': 'OK', 'token': user.api_token, 'message': 
                gettext('A new token was generated.')}, 200


class ApproveUserApi(Resource):
    @staticmethod
    @requires_auth
    @requires_permission('ADMINISTRATOR')
    def post(user_id):
        user = User.query.get(user_id)
        if not user:
            return {'status': 'ERROR', 'message': 'not found'}, 404
        user.confirmed_at = datetime.datetime.now()
        base_url_conf = Configuration.query.filter_by(
                name='SERVER_BASE_URL').first()

        if base_url_conf is None:
            base_url_conf = ''
        success_message = gettext('Registration confirmed')
        job = send_email.queue(
                subject=success_message,
                to=user.email, 
                name=user.first_name + " " + user.last_name,
                template='confirm',
                link=base_url_conf.value,
                queue='thorn',)
        
        user.enabled = True
        user.status = UserStatus.ENABLED
        if user.locale is None:
            user.locale = 'pt'

        db.session.add(user)
        db.session.commit()
        return {'status': 'OK', 'message': success_message}, 200

class ResetPasswordApi(Resource):
    @staticmethod
    def get():
        result = {'status': 'ERROR', 'message': gettext('Record not found')}
        status_code = 404

        user_id = request.args.get('id')
        token = request.args.get('token')
        
        if all([user_id, token]):
            found = User.query.filter(
                    User.id==user_id, 
                    User.reset_password_token==token).count()
            if found > 0: 
                result = {'status': 'OK'}
                status_code = 200
        return result, status_code

    @staticmethod
    def patch():
        result = {'status': 'ERROR', 
                'message': gettext('User not found or invalid token.')}
        status_code = 404
        if request.json and len(request.json.get('token', '')) > 0:
            user = User.query.filter(
                User.id==request.json.get('id'),
                User.reset_password_token==request.json.get('token')).first()
            if user:
                if len(request.json.get('password', '')) > 5:
                    user.encrypted_password = encrypt_password(
                                 request.json.get('password')).decode('utf8')
                    user.reset_password_token = None
                    user.reset_password_sent_at = None
                    db.session.add(user)
                    db.session.commit()

                    result = {'status': 'OK', 
                            'message': gettext(
                                'Password changed with success!')}
                    status_code = 200
                else:
                    result['message'] = gettext('Password too short')

        return result, status_code

    @staticmethod
    def post():
        result = {'status': 'ERROR', 'message': 'User not found.'}
        status_code = 404
        if request.json:
            user = User.query.filter(User.email==request.json.get('email')).first()
            if user:
                config = Configuration.query.filter(or_(
                        Configuration.name=='SUPPORT_EMAIL', 
                        Configuration.name=='SERVER_BASE_URL'))
                support_email = next(c.value for c in config if c.name == 'SUPPORT_EMAIL')
                server_url = next(c.value for c in config if c.name == 'SERVER_BASE_URL')

                user.reset_password_token = uuid.uuid4().hex
                user.reset_password_sent_at = datetime.datetime.now() 
                job = send_email.queue(
                        subject=gettext('Reset password instructions'), 
                        to=user.email, 
                        name='{} {}'.format(user.first_name, user.last_name).strip(),
                        template='reset_password',
                        link='{}/#/change-password/{}/{}'.format(server_url, user.id, 
                            user.reset_password_token),
                        queue='thorn')
                db.session.add(user)
                db.session.commit()
                result = {'status': 'OK', 'message': gettext(
                    'Success! Soon you will receive an email with instructions '
                    'to reset your password.'), 
                    'supportEmail': support_email}
                status_code = 200
        return result, status_code

# class ChangePasswordWithTokenApi(Resource):
#     @staticmethod
#     def get(user_id, token):
#         user = User.query.get(user_id)
#         if not user:
#             return {'status': 'ERROR', 'message': 'not found'}, 404
#         if user.reset_password_token == token:
#             user.enabled = True
#             db.session.add(user)
#             db.session.commit()
#             return {'status': 'OK', 'message': 'FIXME'}, 200 
#         else:
#             return {'status': 'ERROR', 'message': 'Invalid token'}, 401
#     @staticmethod
#     def post(user_id, token):
#         user = User.query.get(user_id)
#         if not user:
#             return {'status': 'ERROR', 'message': 'not found'}, 404
#         if user.reset_password_token == token:
#             user.enabled = True
#             user.reset_password_token = None
#             user.encrypted_password = '11'
#             db.session.add(user)
#             db.session.commit()
#             return {'status': 'OK', 'message': 'FIXME'}, 200 
#         else:
#             return {'status': 'ERROR', 'message': 'Invalid token'}, 401


def has_permission(permission):
    user = flask_globals.user
    return permission in user.permissions
    # return any(p for r in user.roles 
    #         for p in r.permissions if p.name == permission)
# endregion

def _add_user(human_name, administrative=False):
    result = {'status': 'ERROR',
              'message': gettext("Missing json in the request body")}
    return_code = 400
    
    if request.json is not None:
        request_schema = UserCreateRequestSchema()
        response_schema = UserItemResponseSchema()
        # FIXME use defaults
        data = {}
        data.update(request.json)
        data['status'] = UserStatus.ENABLED if administrative else \
                UserStatus.PENDING_APPROVAL
        data['enabled'] = data['status'] == UserStatus.ENABLED
        data['login'] = request.json.get('email')
        # data['reset_password_sent_at'] = None
        if request.json.get('password') is None:
            result = {'status': 'ERROR',
                      'message': gettext("You must inform a valid password.")}
            return_code = 400
            return result, return_code
        data['encrypted_password'] = encrypt_password(
                request.json.get('password'))

        form = request_schema.load(data)
        if form.errors:
            result = {'status': 'ERROR',
                      'message': gettext("Validation error"),
                      'errors': translate_validation(form.errors)}
        else:
            try:
                email_in_use = User.query.with_entities(User.id).filter(
                        User.email==form.data.email, 
                        User.status!=UserStatus.DELETED).scalar() is not None
                if email_in_use:
                    result = {'status': 'ERROR',
                          'message': gettext("Email in use. Please, inform another.")}
                    return_code = 400
                else:
                    if log.isEnabledFor(logging.DEBUG):
                        log.debug(gettext('Adding %s'), human_name)
                    user = form.data
                    mail = {'type': 'REGISTRATION', 'user': user.login}
                    q = MailQueue(json_data=json.dumps(mail), status='PENDING')
                    db.session.add(user)
                    db.session.add(q)
                    db.session.commit()
                    result = {
                        'status': 'OK',
                        'message': gettext('User registered with success!'),
                        'data': response_schema.dump(user).data
                    }
                    return_code = 200
            except Exception as e:
                result = {'status': 'ERROR',
                          'message': gettext("Internal error")}
                return_code = 500
                if current_app.debug:
                    result['debug_detail'] = str(e)

                log.exception(e)
                db.session.rollback()

    return result, return_code

def _change_user(user_id, administrative, human_name):
    result = {'status': 'ERROR', 'message': gettext('Insufficient data.')}
    return_code = 400

    if log.isEnabledFor(logging.DEBUG):
        log.debug(gettext('Updating %s (id=%s)'), human_name,
                  user_id)
    if request.json:
        # roles = request.json.pop('roles', [])

        request_schema = partial_schema_factory(
            UserCreateRequestSchema)
        roles = [Role.query.get_or_404(r.get('id')) for r in 
                request.json.get('roles', [])]

        # Ignore missing fields to allow partial updates
        form = request_schema.load(request.json, partial=True)
        response_schema = UserItemResponseSchema(exclude=('roles.users',))

        if not form.errors:
            try:
                password = request.json.get('current_password')
                new_password= request.json.get('password', '')
                confirm = request.json.get('password_confirmation', '')
                form.data.id = user_id
                user = User.query.get(user_id)
                user.roles = roles
                change_pass_ok = new_password is None \
                        or confirm == new_password \
                        or user.authentication_type == 'LDAP'
                if user.authentication_type != 'LDAP' and not administrative and (
                        not password or not check_password or not check_password(
                        password.encode('utf8'), 
                        user.encrypted_password.encode('utf8'))):
                    result = {'status': 'ERROR', 'message': 
                            gettext('Invalid password or confirmation')}
                    return_code = 401
                else:
                    if new_password is not None and len(new_password) > 0:
                        form.data.encrypted_password = encrypt_password(
                                new_password).decode('utf8')
                    # form.data.roles = list(Role.query.filter(
                    #         Role.id.in_([r['id'] for r in roles])))
                    db.session.merge(form.data)
                    db.session.commit()

                    if user is not None:
                        return_code = 200
                        result = {
                            'status': 'OK',
                            'message': gettext(
                                '%(n)s (id=%(id)s) was updated with success!',
                                n=human_name,
                                id=user_id),
                            'data': [response_schema.dump(
                                user).data]
                        }
            except Exception as e:
                result = {'status': 'ERROR',
                          'message': gettext("Internal error")}
                return_code = 500
                if current_app.debug:
                    result['debug_detail'] = str(e)
                db.session.rollback()
        else:
            result = {
                'status': 'ERROR',
                'message': gettext('Invalid data for %(name)s (id=%(id)s)',
                                   name=human_name,
                                   id=user_id),
                'errors': form.errors
            }
    return result, return_code

    
class ProfileApi(Resource):
    def __init__(self):
        self.human_name = gettext('User')
    @requires_auth
    def get(self):
        user_api = UserDetailApi()
        user_id = int(request.headers.get('X-User-Id'))
        return user_api.get(user_id)

    @requires_auth
    def patch(self):
        user_id = int(request.headers.get('X-User-Id'))
        return _change_user(user_id, False, self.human_name) 


class UserListApi(Resource):
    """ REST API for listing class User """

    def __init__(self):
        self.human_name = gettext('User')

    @requires_auth
    @requires_permission('ADMINISTRATOR')
    def post(self):
        return _add_user(self.human_name, True)

    @requires_auth
    def get(self):
        if request.args.get('fields'):
            only = [f.strip() for f in request.args.get('fields').split(',')]
        else:
            only = ('id', ) if request.args.get(
                'simple', 'false') == 'true' else None
        enabled_filter = request.args.get('enabled')
        if enabled_filter:
            users = User.query.filter(
                User.enabled == (enabled_filter != 'false'))
        else:
            users = User.query

        exclude = [] if has_permission('ADMINISTRATOR') else [
                'email', 'notes', 'updated_at', 'created_at', 'locale', 
                'roles']
        sort = request.args.get('sort', 'name')
        if sort not in ['id', 'email', 'confirmed_at']:
            sort = 'first_name'
        sort_option = getattr(User, sort)
        if request.args.get('asc', 'true') == 'false':
            sort_option = sort_option.desc()
        users = users.order_by(sort_option)

        q = request.args.get('query')
        if q: 
            q = '%{}%'.format(q)
            users = users.filter(or_(
                User.first_name.ilike(q),
                User.last_name.ilike(q),
                User.login.ilike(q),
                User.email.ilike(q)),
            )

        page = request.args.get('page') or '1'
        if page is not None and page.isdigit():
            page_size = int(request.args.get('size', 20))
            page = int(page)
            pagination = users.paginate(page, page_size, True)
            # remove user.roles.users in order to avoid recursion
            exclude.append('roles.users')
            result = {
                'data': UserListResponseSchema(
                    many=True, only=only, exclude=exclude).dump(pagination.items).data,
                'pagination': {
                    'page': page, 'size': page_size,
                    'total': pagination.total,
                    'pages': int(math.ceil(1.0 * pagination.total / page_size))}
            }
        else:
            result = {
                'data': UserListResponseSchema(
                    many=True, only=only, exclude=exclude).dump(
                    users)}

        if log.isEnabledFor(logging.DEBUG):
            log.debug(gettext('Listing %(name)s', name=self.human_name))
        return result

class RegisterApi(Resource):
    def __init__(self):
        self.human_name = gettext('User')
    def post(self):
       return _add_user(self.human_name) 

class UserDetailApi(Resource):
    """ REST API for a single instance of class User """
    def __init__(self):
        self.human_name = gettext('User')

    @requires_auth
    def get(self, user_id):

        if log.isEnabledFor(logging.DEBUG):
            log.debug(gettext('Retrieving %s (id=%s)'), self.human_name,
                      user_id)

        user = User.query.get(user_id)
        return_code = 200
        if user is not None:
            result = {
                'status': 'OK',
                'data': [UserItemResponseSchema(
                    exclude=('roles.users', 'roles.permissions',)).dump(
                    user).data]
            }
        else:
            return_code = 404
            result = {
                'status': 'ERROR',
                'message': gettext(
                    '%(name)s not found (id=%(id)s)',
                    name=self.human_name, id=user_id)
            }

        return result, return_code

    @requires_auth
    @requires_permission('ADMINISTRATOR')
    def delete(self, user_id):
        return_code = 200
        if log.isEnabledFor(logging.DEBUG):
            log.debug(gettext('Deleting %s (id=%s)'), self.human_name,
                      user_id)
        user = User.query.get(user_id)
        if user is not None:
            try:
                user.enabled = False
                db.session.add(user)
                db.session.commit()
                result = {
                    'status': 'OK',
                    'message': gettext('%(name)s deleted with success!',
                                       name=self.human_name)
                }
            except Exception as e:
                result = {'status': 'ERROR',
                          'message': gettext("Internal error")}
                return_code = 500
                if current_app.debug:
                    result['debug_detail'] = str(e)
                db.session.rollback()
        else:
            return_code = 404
            result = {
                'status': 'ERROR',
                'message': gettext('%(name)s not found (id=%(id)s).',
                                   name=self.human_name, id=user_id)
            }
        return result, return_code
    
    @requires_auth
    @requires_permission('ADMINISTRATOR')
    def patch(self, user_id):
        return _change_user(user_id, True, self.human_name)

