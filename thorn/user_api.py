# -*- coding: utf-8 -*-}
from thorn.app_auth import requires_auth, requires_permission
from flask import request, current_app, g as flask_globals
from flask_restful import Resource
from sqlalchemy import or_

import math
import uuid
import datetime
import rq
import logging
from thorn.schema import *
from flask_babel import gettext, get_locale
from thorn.jobs import send_email

log = logging.getLogger(__name__)

# region Protected\s*
class ChangeLocaleApi(Resource):
    @requires_auth
    def change_locale(self, user_id):
        pass

class ApproveUserApi(Resource):
    @staticmethod
    @requires_auth
    @requires_permission('ADMINISTRATOR')
    def post(user_id):
        user = User.query.get(user_id)
        if not user:
            return {'status': 'ERROR', 'msg': 'not found'}, 404
        user.confirmed_at = datetime.datetime.now()
        job = send_email.queue(
                subject=gettext('Registration confirmed'), 
                to='waltersf@gmail.com', 
                name='Walter dos Santos Filho',
                template='confirm',
                url='https://fixme.lemonade.org.br',
                queue='thorn',)
        user.enabled = True
        db.session.add(user)
        db.session.commit()
        return {'status': 'OK', 'msg': 'fixme'}, 200
class ResetPasswordApi(Resource):
    @staticmethod
    @requires_auth
    def post(user_id):
        user = User.query.get(user_id)
        if not user:
            return {'status': 'ERROR', 'msg': 'not found'}, 404
        user.reset_password_token = uuid.uuid4().hex
        user.reset_password_sent_at = datetime.datetime.now() 
        job = send_email.queue(
                subject=gettext('Reset password instructions'), 
                to='waltersf@gmail.com', 
                name='Walter dos Santos Filho',
                template='reset_password',
                link='https://fixme.lemonade.org.br/fixme',
                queue='thorn')
        db.session.add(user)
        db.session.commit()
        return {'status': 'OK'}
        
class ChangePasswordWithTokenApi(Resource):
    @staticmethod
    def get(user_id, token):
        user = User.query.get(user_id)
        if not user:
            return {'status': 'ERROR', 'msg': 'not found'}, 404
        if user.reset_password_token == token:
            user.enabled = True
            db.session.add(user)
            db.session.commit()
            return {'status': 'OK', 'msg': 'FIXME'}, 200 
        else:
            return {'status': 'ERROR', 'msg': 'Invalid token'}, 401
    @staticmethod
    def post(user_id, token):
        user = User.query.get(user_id)
        if not user:
            return {'status': 'ERROR', 'msg': 'not found'}, 404
        if user.reset_password_token == token:
            user.enabled = True
            user.reset_password_token = None
            user.encrypted_password = '11'
            db.session.add(user)
            db.session.commit()
            return {'status': 'OK', 'msg': 'FIXME'}, 200 
        else:
            return {'status': 'ERROR', 'msg': 'Invalid token'}, 401


def has_permission(permission):
    user = flask_globals.user
    return permission in user.permissions
    # return any(p for r in user.roles 
    #         for p in r.permissions if p.name == permission)
# endregion


class UserListApi(Resource):
    """ REST API for listing class User """

    def __init__(self):
        self.human_name = gettext('User')

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
        page = request.args.get('page') or '1'
        if page is not None and page.isdigit():
            page_size = int(request.args.get('size', 20))
            page = int(page)
            pagination = users.paginate(page, page_size, True)
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

    @requires_auth
    def post(self):
        result = {'status': 'ERROR',
                  'message': gettext("Missing json in the request body")}
        return_code = 400
        
        if request.json is not None:
            request_schema = UserCreateRequestSchema()
            response_schema = UserItemResponseSchema()
            form = request_schema.load(request.json)
            if form.errors:
                result = {'status': 'ERROR',
                          'message': gettext("Validation error"),
                          'errors': translate_validation(form.errors)}
            else:
                try:
                    if log.isEnabledFor(logging.DEBUG):
                        log.debug(gettext('Adding %s'), self.human_name)
                    user = form.data
                    db.session.add(user)
                    db.session.commit()
                    result = response_schema.dump(user)
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
                'data': [UserItemResponseSchema().dump(
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
    def patch(self, user_id):
        result = {'status': 'ERROR', 'message': gettext('Insufficient data.')}
        return_code = 400

        if log.isEnabledFor(logging.DEBUG):
            log.debug(gettext('Updating %s (id=%s)'), self.human_name,
                      user_id)
        if request.json:
            request_schema = partial_schema_factory(
                UserCreateRequestSchema)
            # Ignore missing fields to allow partial updates
            form = request_schema.load(request.json, partial=True)
            response_schema = UserItemResponseSchema()
            if not form.errors:
                try:
                    form.data.id = user_id
                    user = db.session.merge(form.data)
                    db.session.commit()

                    if user is not None:
                        return_code = 200
                        result = {
                            'status': 'OK',
                            'message': gettext(
                                '%(n)s (id=%(id)s) was updated with success!',
                                n=self.human_name,
                                id=user_id),
                            'data': [response_schema.dump(
                                user)]
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
                                       name=self.human_name,
                                       id=user_id),
                    'errors': form.errors
                }
        return result, return_code
