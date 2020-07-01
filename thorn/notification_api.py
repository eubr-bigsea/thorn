# -*- coding: utf-8 -*-}
from thorn.app_auth import requires_auth
from flask import request, current_app, g as flask_globals
from flask_restful import Resource
from sqlalchemy import or_

import math
import logging
from thorn.schema import *
from flask_babel import gettext

log = logging.getLogger(__name__)

# region Protected\s*
# endregion


class NotificationListApi(Resource):
    """ REST API for listing class Notification """

    def __init__(self):
        self.human_name = gettext('Notification')

    @requires_auth
    def get(self):
        if request.args.get('fields'):
            only = [f.strip() for f in request.args.get('fields').split(',')]
        else:
            only = ('id', ) if request.args.get(
                'simple', 'false') == 'true' else None
        notifications = Notification.query.all()

        page = request.args.get('page') or '1'
        if page is not None and page.isdigit():
            page_size = int(request.args.get('size', 20))
            page = int(page)
            pagination = notifications.paginate(page, page_size, True)
            result = {
                'data': NotificationListResponseSchema(
                    many=True, only=only).dump(pagination.items).data,
                'pagination': {
                    'page': page, 'size': page_size,
                    'total': pagination.total,
                    'pages': int(math.ceil(1.0 * pagination.total / page_size))}
            }
        else:
            result = {
                'data': NotificationListResponseSchema(
                    many=True, only=only).dump(
                    notifications).data}

        if log.isEnabledFor(logging.DEBUG):
            log.debug(gettext('Listing %(name)s', name=self.human_name))
        return result

    @requires_auth
    def post(self):
        result = {'status': 'ERROR',
                  'message': gettext("Missing json in the request body")}
        return_code = 400
        
        if request.json is not None:
            request_schema = NotificationCreateRequestSchema()
            response_schema = NotificationItemResponseSchema()
            form = request_schema.load(request.json)
            if form.errors:
                result = {'status': 'ERROR',
                          'message': gettext("Validation error"),
                          'errors': translate_validation(form.errors)}
            else:
                try:
                    if log.isEnabledFor(logging.DEBUG):
                        log.debug(gettext('Adding %s'), self.human_name)
                    notification = form.data
                    db.session.add(notification)
                    db.session.commit()
                    result = response_schema.dump(notification).data
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


class NotificationDetailApi(Resource):
    """ REST API for a single instance of class Notification """
    def __init__(self):
        self.human_name = gettext('Notification')

    @requires_auth
    def get(self, notification_id):

        if log.isEnabledFor(logging.DEBUG):
            log.debug(gettext('Retrieving %s (id=%s)'), self.human_name,
                      notification_id)

        notification = Notification.query.get(notification_id)
        return_code = 200
        if notification is not None:
            result = {
                'status': 'OK',
                'data': [NotificationItemResponseSchema().dump(
                    notification).data]
            }
        else:
            return_code = 404
            result = {
                'status': 'ERROR',
                'message': gettext(
                    '%(name)s not found (id=%(id)s)',
                    name=self.human_name, id=notification_id)
            }

        return result, return_code

    @requires_auth
    def delete(self, notification_id):
        return_code = 200
        if log.isEnabledFor(logging.DEBUG):
            log.debug(gettext('Deleting %s (id=%s)'), self.human_name,
                      notification_id)
        notification = Notification.query.get(notification_id)
        if notification is not None:
            try:
                db.session.delete(notification)
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
                                   name=self.human_name, id=notification_id)
            }
        return result, return_code

    @requires_auth
    def patch(self, notification_id):
        result = {'status': 'ERROR', 'message': gettext('Insufficient data.')}
        return_code = 404

        if log.isEnabledFor(logging.DEBUG):
            log.debug(gettext('Updating %s (id=%s)'), self.human_name,
                      notification_id)
        if request.json:
            request_schema = partial_schema_factory(
                NotificationCreateRequestSchema)
            # Ignore missing fields to allow partial updates
            form = request_schema.load(request.json, partial=True)
            response_schema = NotificationItemResponseSchema()
            if not form.errors:
                try:
                    form.data.id = notification_id
                    notification = db.session.merge(form.data)
                    db.session.commit()

                    if notification is not None:
                        return_code = 200
                        result = {
                            'status': 'OK',
                            'message': gettext(
                                '%(n)s (id=%(id)s) was updated with success!',
                                n=self.human_name,
                                id=notification_id),
                            'data': [response_schema.dump(
                                notification).data]
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
                                       id=notification_id),
                    'errors': form.errors
                }
        return result, return_code
