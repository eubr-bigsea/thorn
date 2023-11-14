# -*- coding: utf-8 -*-}
from thorn.app_auth import requires_auth, requires_permission
from thorn.util import translate_validation
from flask import request, current_app, g as flask_globals, abort
from flask_restful import Resource
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.expression import bindparam, text
import math
import logging
from thorn.schema import *
from flask_babel import gettext
import json
from marshmallow import ValidationError

log = logging.getLogger(__name__)

# region Protected\s*
# endregion\w*


class ConfigurationListApi(Resource):
    """ REST API for listing class Configuration """

    def __init__(self):
        self.human_name = gettext('Configuration')

    @requires_auth
    @requires_permission('ADMINISTRATOR')
    def get(self):
        if request.args.get('fields'):
            only = [f.strip() for f in request.args.get('fields').split(',')]
        else:
            only = ('id', ) if request.args.get(
                'simple', 'false') == 'true' else None
        enabled_filter = request.args.get('enabled')
        if enabled_filter:
            configurations = Configuration.query.filter(
                Configuration.enabled == (enabled_filter != 'false'))
        else:
            configurations = Configuration.query
        sort = request.args.get('sort', 'name')
        if sort not in ['id', 'name']:
            sort = 'name'
        sort_option = getattr(Configuration, sort)
        if request.args.get('asc', 'true') == 'false':
            sort_option = sort_option.desc()
        configurations = configurations.order_by(sort_option)

        q = request.args.get('query')
        if q is not None and q:
            # SqlAlchemy-i18n is not working when a filter
            # is used in where clause with a translation table field.
            # In order to optimize the query, I'm using text() query here
            # to write SQL. Notice that the name operation_translation_1
            # is generated by SqlAlchemy and it is hard coded here.
            q = '%%{}%%'.format(q)
            param_q = bindparam('q', '%%{}%%'.format(q), Unicode)
            configurations = configurations.options(joinedload('current_translation')) \
                    .filter(
                            or_(Configuration.name.like(q), 
                                text(
                                    'configuration_translation_1.description LIKE :q',
                                    bindparams=[param_q]),
                                text(
                                    'configuration_translation_1.category LIKE :q',
                                    bindparams=[param_q])
                                ))
        page = request.args.get('page') or '1'
        if page is not None and page.isdigit():
            page_size = int(request.args.get('size', 20))
            page = int(page)
            pagination = configurations.paginate(page, page_size, False)
            result = {
                'data': ConfigurationListResponseSchema(
                    many=True, only=only).dump(pagination.items),
                'pagination': {
                    'page': page, 'size': page_size,
                    'total': pagination.total,
                    'pages': int(math.ceil(1.0 * pagination.total / page_size))}
            }
        else:
            result = {
                'data': ConfigurationListResponseSchema(
                    many=True, only=only).dump(
                    configurations)}

        if log.isEnabledFor(logging.DEBUG):
            log.debug(gettext('Listing %(name)s', name=self.human_name))
        return result

    @requires_auth
    @requires_permission('ADMINISTRATOR')
    def patch(self):
        result = {'status': 'ERROR', 'message': gettext('Insufficient data.')}
        return_code = 404
        if log.isEnabledFor(logging.DEBUG):
            log.debug(gettext('Updating %s'), self.human_name)
        if request.json:
            request_schema = ConfigurationCreateRequestSchema( many=True)
            # Ignore missing fields to allow partial updates
            try:
                config = request_schema.load(request.json, partial=True)
                response_schema = ConfigurationItemResponseSchema()
                configurations = []
                for config in config:
                    configurations.append(db.session.merge(config))
                db.session.commit()
                return_code = 200
                result = {
                    'status': 'OK',
                    'message': gettext(
                        '%(n)s was updated with success!', n=self.human_name),
                    'data': [response_schema.dump(
                        configurations, many=True)]
                }
                
            except ValidationError as e:
                result = {'status': 'ERROR',
                            'message': gettext("Validation error"),
                            'errors': translate_validation(e.messages)}
            except Exception as e:
                result = {'status': 'ERROR',
                          'message': gettext("Internal error")}
                return_code = 500
                if current_app.debug:
                    result['debug_detail'] = str(e)
                db.session.rollback()
        return result, return_code

class UserInterfaceConfigurationDetailApi(Resource):

    def __init__(self):
        self.human_name = gettext('Configuration')

    def get(self, name):
        config = Configuration.query.filter(Configuration.name==name, 
                Configuration.internal==False).first()
        if config:
            try:
                return {'data': json.loads(config.value)}
            except:
                abort(500)
        else:
            abort(404)
 
