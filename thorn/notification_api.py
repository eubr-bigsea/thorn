# -*- coding: utf-8 -*-}
from thorn.app_auth import requires_auth
from flask import request, current_app, g as flask_globals
from flask_restful import Resource
from sqlalchemy import or_
from thorn.util import translate_validation

import datetime
import math
import logging
import socketio
from thorn.schema import *
from flask_babel import gettext

log = logging.getLogger(__name__)

# region Protected\s*
# endregion


CONFIG_KEY = 'THORN_CONFIG'
NAMESPACE = '/stand'
def _get_number_of_unread_notifications():
    return Notification.query.filter(
        Notification.user_id==flask_globals.user.id,
        Notification.status==NotificationStatus.UNREAD).count()

def _update_notification_count(config):
     mgr = socketio.RedisManager(config['servers']['redis_url'][:-1],
         'job_output')
     mgr.emit('notifications',
             data={'unread': _get_number_of_unread_notifications()},
             room='user:' + flask_globals.user.id,
             namespace=NAMESPACE)
 
class NotificationSummaryApi(Resource):
    @requires_auth
    def get(self):
        return {'unread': _get_number_of_unread_notifications()}

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
        notifications = Notification.query.filter(
            Notification.user_id==flask_globals.user.id)

        page = request.args.get('page') or '1'
        sort = request.args.get('sort', 'created')
        if sort not in ['created', 'id', 'text']:
            sort = 'created'
        sort_option = getattr(Notification, sort)
        if request.args.get('asc', 'true') == 'false':
             sort_option = sort_option.desc()
    
        notifications = notifications.order_by(sort_option)
        q = request.args.get('query')
        if q:
            q = '%' + q + '%'
            notifications = notifications.filter(or_(
                Notification.text.ilike(q),
                Notification.status.ilike(q),
                Notification.type.ilike(q),
            ))
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

        config = current_app.config[CONFIG_KEY]
        token = config['secret']
        if request.headers.get('x-auth-token') != str(token):
            return_code = 401
            result = {'status': 'ERROR'}
        elif request.json is not None:
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
                    notification.created = datetime.datetime.now()
                    db.session.add(notification)
                    db.session.commit()
                    result = response_schema.dump(notification).data

                    # FIXME Thorn use a different number for Redis than stand
                    _update_notification_count(config)
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

        notification = Notification.query.filter(
            Notification.id==notification_id,
            Notification.user_id==flask_globals.user.id).first()
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
        notification = Notification.query.filter(
            Notification.id==notification_id,
            Notification.user_id==flask_globals.user.id).first()
        if notification is not None:
            try:
                db.session.delete(notification)
                db.session.commit()
                config = current_app.config[CONFIG_KEY]
                _update_notification_count(config)
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

        notification = Notification.query.filter(
            Notification.id==notification_id,
            Notification.user_id==flask_globals.user.id).first()
        if notification is None:
            result = {'status': 'ERROR',
                'message': gettext('%(name)s not found (id=%(id)s).',
                                   name=self.human_name, id=notification_id)}

        if request.json and notification is not None:
            request_schema = partial_schema_factory(
                NotificationCreateRequestSchema)

            # Only status is updatable
            payload = {'status': request.json.get('status'),
                'id': request.json.get('id')}
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
                    _update_notification_count(current_app.config[CONFIG_KEY])
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
