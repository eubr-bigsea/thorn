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


class RoleListApi(Resource):
    """ REST API for listing class Role """

    def __init__(self):
        self.human_name = gettext('Role')

    @requires_auth
    def get(self):
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

        sort = request.args.get('sort', 'name')
        if sort not in ['id', 'name']:
            sort = 'name'
        sort_option = getattr(Role, sort)
        if request.args.get('asc', 'true') == 'false':
            sort_option = sort_option.desc()
        roles = roles.order_by(sort_option)

        q = request.args.get('query')
        if q: 
            q = '%{}%'.format(q)
            roles = roles.filter(Role.name.ilike(q))

        page = request.args.get('page') or '1'
        if page is not None and page.isdigit():
            page_size = int(request.args.get('size', 20))
            page = int(page)
            pagination = roles.paginate(page, page_size, True)
            result = {
                'data': RoleListResponseSchema(
                    many=True, only=only).dump(pagination.items).data,
                'pagination': {
                    'page': page, 'size': page_size,
                    'total': pagination.total,
                    'pages': int(math.ceil(1.0 * pagination.total / page_size))}
            }
        else:
            result = {
                'data': RoleListResponseSchema(
                    many=True, only=only).dump(
                    roles).data}

        if log.isEnabledFor(logging.DEBUG):
            log.debug(gettext('Listing %(name)s', name=self.human_name))
        return result


class RoleDetailApi(Resource):
    """ REST API for a single instance of class Role """
    def __init__(self):
        self.human_name = gettext('Role')

    @requires_auth
    def get(self, role_id):

        if log.isEnabledFor(logging.DEBUG):
            log.debug(gettext('Retrieving %s (id=%s)'), self.human_name,
                      role_id)

        role = Role.query.get(role_id)
        return_code = 200
        if role is not None:
            result = {
                'status': 'OK',
                'data': [RoleItemResponseSchema().dump(
                    role).data]
            }
        else:
            return_code = 404
            result = {
                'status': 'ERROR',
                'message': gettext(
                    '%(name)s not found (id=%(id)s)',
                    name=self.human_name, id=role_id)
            }

        return result, return_code

    @requires_auth
    def delete(self, role_id):
        return_code = 200
        if log.isEnabledFor(logging.DEBUG):
            log.debug(gettext('Deleting %s (id=%s)'), self.human_name,
                      role_id)
        role = Role.query.get(role_id)
        if role is not None:
            try:
                if role.system:
                    result = {
                        'status': 'ERROR',
                        'message': gettext('A system role cannot be deleted')
                        }
                    return_code = 400
                else:
                    db.session.delete(role)
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
                                   name=self.human_name, id=role_id)
            }
        return result, return_code

    @requires_auth
    def patch(self, role_id):
        result = {'status': 'ERROR', 'message': gettext('Insufficient data.')}
        return_code = 404

        if log.isEnabledFor(logging.DEBUG):
            log.debug(gettext('Updating %s (id=%s)'), self.human_name,
                      role_id)
        if request.json:
            request_schema = partial_schema_factory(
                RoleCreateRequestSchema)
            permissions = request.json.pop('permissions') \
                    if 'permissions' in request.json else []
            # Ignore missing fields to allow partial updates
            form = request_schema.load(request.json, partial=True)
            response_schema = RoleItemResponseSchema()
            if not form.errors:
                try:
                    form.data.id = role_id
                    role = db.session.merge(form.data)
                    if role.system:
                        result = {'status': 'ERROR', 
                                'message': 'A system role cannot be changed'}
                        return_code = 400
                    else:
                        role.permissions = list(Permission.query.filter(
                                Permission.id.in_([p.get('id', 0) 
                                    for p in permissions])))
                        db.session.commit()

                        if role is not None:
                            return_code = 200
                            result = {
                                'status': 'OK',
                                'message': gettext(
                                    '%(n)s (id=%(id)s) was updated with success!',
                                    n=self.human_name,
                                    id=role_id),
                                'data': [response_schema.dump(
                                    role)]
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
                                       id=role_id),
                    'errors': form.errors
                }
        return result, return_code
