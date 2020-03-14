# -*- coding: utf-8 -*-}
from thorn.app_auth import requires_auth, requires_role
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


class RoleListApi(Resource):
    """ REST API for listing class Role """

    def __init__(self):
        self.human_name = gettext('Role')

    @requires_auth
    @requires_role('admin')
    def get(self):
        print(flask_globals.user)
        if request.args.get('fields'):
            only = [f.strip() for f in request.args.get('fields').split(',')]
        else:
            only = ('id', ) if request.args.get(
                'simple', 'false') == 'true' else None
        enabled_filter = request.args.get('enabled')
        if enabled_filter:
            roles = Role.query.filter(
                Role.enabled == (enabled_filter != 'false'))
        else:
            roles = Role.query

        page = request.args.get('page') or '1'
        if page is not None and page.isdigit():
            page_size = int(request.args.get('size', 20))
            page = int(page)
            pagination = roles.paginate(page, page_size, True)
            result = {
                'data': RoleListResponseSchema(
                    many=True, only=only).dump(pagination.items),
                'pagination': {
                    'page': page, 'size': page_size,
                    'total': pagination.total,
                    'pages': int(math.ceil(1.0 * pagination.total / page_size))}
            }
        else:
            result = {
                'data': RoleListResponseSchema(
                    many=True, only=only).dump(
                    roles)}

        if log.isEnabledFor(logging.DEBUG):
            log.debug(gettext('Listing %(name)s', name=self.human_name))
        return result
