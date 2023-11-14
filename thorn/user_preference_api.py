# -*- coding: utf-8 -*-}
import math
import logging

from thorn.app_auth import requires_auth, requires_permission
from flask import request, current_app, g as flask_globals
from flask_restful import Resource
from sqlalchemy import or_
from http import HTTPStatus
from marshmallow.exceptions import ValidationError

from thorn.schema import *
from thorn.util import translate_validation
from flask_babel import gettext

log = logging.getLogger(__name__)
# region Protected\s*
# endregion

class UserPreferenceListApi(Resource):
    """ REST API for listing class UserPreference """

    def __init__(self):
        self.human_name = gettext('UserPreference')

    @requires_auth
    def get(self):
        if request.args.get('fields'):
            only = [f.strip() for f in request.args.get('fields').split(',')]
        else:
            only = ('id', ) if request.args.get(
                'simple', 'false') == 'true' else None
        user_preferences = UserPreference.query.all()

        page = request.args.get('page') or '1'
        if page is not None and page.isdigit():
            page_size = int(request.args.get('size', 20))
            page = int(page)
            pagination = user_preferences.paginate(page, page_size, False)
            result = {
                'data': UserPreferenceListResponseSchema(
                    many=True, only=only).dump(pagination.items),
                'pagination': {
                    'page': page, 'size': page_size,
                    'total': pagination.total,
                    'pages': int(math.ceil(1.0 * pagination.total / page_size))}
            }
        else:
            result = {
                'data': UserPreferenceListResponseSchema(
                    many=True, only=only).dump(
                    user_preferences)}

        if log.isEnabledFor(logging.DEBUG):
            log.debug(gettext('Listing %(name)s', name=self.human_name))
        return result

    @requires_auth
    def post(self):
        result = {'status': 'ERROR',
                  'message': gettext("Missing json in the request body")}
        return_code = HTTPStatus.BAD_REQUEST
        
        if request.json is not None:
            request_schema = UserPreferenceCreateRequestSchema()
            response_schema = UserPreferenceItemResponseSchema()
            user_preference = request_schema.load(request.json)
            try:
                if log.isEnabledFor(logging.DEBUG):
                    log.debug(gettext('Adding %s'), self.human_name)
                user_preference = user_preference
                db.session.add(user_preference)
                db.session.commit()
                result = response_schema.dump(user_preference)
                return_code = HTTPStatus.CREATED
            except ValidationError as e:
                result= {
                   'status': 'ERROR', 
                   'message': gettext('Invalid data for %(name)s.)',
                                      name=self.human_name),
                   'errors': translate_validation(e.messages)
                }
            except Exception as e:
                result = {'status': 'ERROR',
                          'message': gettext("Internal error")}
                return_code = 500
                if current_app.debug:
                    result['debug_detail'] = str(e)

                log.exception(e)
                db.session.rollback()

        return result, return_code


class UserPreferenceDetailApi(Resource):
    """ REST API for a single instance of class UserPreference """
    def __init__(self):
        self.human_name = gettext('UserPreference')

    @requires_auth
    def get(self, user_preference_id):

        if log.isEnabledFor(logging.DEBUG):
            log.debug(gettext('Retrieving %s (id=%s)'), self.human_name,
                      user_preference_id)

        user_preference = UserPreference.query.get(user_preference_id)
        return_code = HTTPStatus.OK
        if user_preference is not None:
            result = {
                'status': 'OK',
                'data': [UserPreferenceItemResponseSchema().dump(
                    user_preference)]
            }
        else:
            return_code = HTTPStatus.NOT_FOUND
            result = {
                'status': 'ERROR',
                'message': gettext(
                    '%(name)s not found (id=%(id)s)',
                    name=self.human_name, id=user_preference_id)
            }

        return result, return_code

    @requires_auth
    def delete(self, user_preference_id):
        return_code = HTTPStatus.NO_CONTENT
        if log.isEnabledFor(logging.DEBUG):
            log.debug(gettext('Deleting %s (id=%s)'), self.human_name,
                      user_preference_id)
        user_preference = UserPreference.query.get(user_preference_id)
        if user_preference is not None:
            try:
                db.session.delete(user_preference)
                db.session.commit()
                result = {
                    'status': 'OK',
                    'message': gettext('%(name)s deleted with success!',
                                       name=self.human_name)
                }
            except Exception as e:
                result = {'status': 'ERROR',
                          'message': gettext("Internal error")}
                return_code = HTTPStatus.INTERNAL_SERVER_ERROR
                if current_app.debug:
                    result['debug_detail'] = str(e)
                db.session.rollback()
        else:
            return_code = HTTPStatus.NOT_FOUND
            result = {
                'status': 'ERROR',
                'message': gettext('%(name)s not found (id=%(id)s).',
                                   name=self.human_name, id=user_preference_id)
            }
        return result, return_code

    @requires_auth
    def patch(self, user_preference_id):
        result = {'status': 'ERROR', 'message': gettext('Insufficient data.')}
        return_code = HTTPStatus.NOT_FOUND

        if log.isEnabledFor(logging.DEBUG):
            log.debug(gettext('Updating %s (id=%s)'), self.human_name,
                      user_preference_id)
        if request.json:
            request_schema = partial_schema_factory(
                UserPreferenceCreateRequestSchema)
            # Ignore missing fields to allow partial updates
            user_preference = request_schema.load(request.json, partial=True)
            response_schema = UserPreferenceItemResponseSchema()
            try:
                user_preference.id = user_preference_id
                user_preference = db.session.merge(user_preference)
                db.session.commit()

                if user_preference is not None:
                    return_code = HTTPStatus.OK
                    result = {
                        'status': 'OK',
                        'message': gettext(
                            '%(n)s (id=%(id)s) was updated with success!',
                            n=self.human_name,
                            id=user_preference_id),
                        'data': [response_schema.dump(
                            user_preference)]
                    }
            except ValidationError as e:
                result= {
                   'status': 'ERROR', 
                   'message': gettext('Invalid data for %(name)s (id=%(id)s)',
                                      name=self.human_name,
                                      id=user_preference_id),
                   'errors': translate_validation(e.messages)
                }
            except Exception as e:
                result = {'status': 'ERROR',
                          'message': gettext("Internal error")}
                return_code = 500
                if current_app.debug:
                    result['debug_detail'] = str(e)
                db.session.rollback()
        return result, return_code
