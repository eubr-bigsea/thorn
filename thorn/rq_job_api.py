# -*- coding: utf-8 -*-}
from thorn.app_auth import requires_auth, requires_permission
from flask import request, current_app, g as flask_globals
from flask_restful import Resource
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.expression import bindparam, text
import math
import logging
from thorn.schema import *
from thorn import rq
from flask_babel import gettext

log = logging.getLogger(__name__)


class BackgroundJobListApi(Resource):
    """ REST API for listing class BackgroundJob """

    def __init__(self):
        self.human_name = gettext('BackgroundJob')

    @requires_auth
    @requires_permission('ADMINISTRATOR')
    def get(self):
        result = {'status': 'ERROR'}
        status_code = 500
        
        data = []
        for q in rq.queues:
            row = {
                'name': q.name,
                'queued': q.
            }
            data.append(q)
        status_code = 200

        return data, status_code


    @requires_auth
    @requires_permission('ADMINISTRATOR')
    def patch(self):
        result = {'status': 'ERROR', 'message': gettext('Insufficient data.')}
        return_code = 404
        if log.isEnabledFor(logging.DEBUG):
            log.debug(gettext('Updating %s'), self.human_name)
        if request.json:
            request_schema = BackgroundJobCreateRequestSchema( many=True)
            # Ignore missing fields to allow partial updates
            form = request_schema.load(request.json, partial=True)
            response_schema = BackgroundJobItemResponseSchema()
            if not form.errors:
                try:
                    configurations = []
                    for config in form.data:
                        configurations.append(db.session.merge(config))
                    db.session.commit()
                    return_code = 200
                    result = {
                        'status': 'OK',
                        'message': gettext(
                            '%(n)s was updated with success!', n=self.human_name),
                        'data': [response_schema.dump(
                            configurations, many=True).data]
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
                    'message': gettext('Invalid data for %(name)s',
                                       name=self.human_name),
                    'errors': form.errors
                }
        return result, return_code
