# -*- coding: utf-8 -*-}
from thorn.app_auth import requires_auth
from flask import request, current_app, g as flask_globals
from flask_restful import Resource
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

import math
import logging
from thorn.schema import *
from flask_babel import gettext

log = logging.getLogger(__name__)

# region Protected\s*
# endregion


class PermissionListApi(Resource):
    """ REST API for listing class Permission """

    def __init__(self):
        self.human_name = gettext('Permission')

    @requires_auth
    def get(self):
        if request.args.get('fields'):
            only = [f.strip() for f in request.args.get('fields').split(',')]
        else:
            only = ('id', ) if request.args.get(
                'simple', 'false') == 'true' else None
        enabled_filter = request.args.get('enabled')
        if enabled_filter:
            permissions = Permission.query.filter(
                Permission.enabled == (enabled_filter != 'false'))
        else:
            permissions = Permission.query

        permissions = permissions.options(joinedload(
            Permission.current_translation))
        page = request.args.get('page') or '1'
        if page is not None and page.isdigit():
            page_size = int(request.args.get('size', 20))
            page = int(page)
            pagination = permissions.paginate(page, page_size, True)
            result = {
                'data': PermissionListResponseSchema(
                    many=True, only=only).dump(pagination.items).data,
                'pagination': {
                    'page': page, 'size': page_size,
                    'total': pagination.total,
                    'pages': int(math.ceil(1.0 * pagination.total / page_size))}
            }
        else:
            result = {
                'data': PermissionListResponseSchema(
                    many=True, only=only).dump(
                    permissions).data}

        if log.isEnabledFor(logging.DEBUG):
            log.debug(gettext('Listing %(name)s', name=self.human_name))
        return result
