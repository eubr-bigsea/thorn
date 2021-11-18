#!/usr/bin/env python
# -*- coding: utf-8 -*-
# noinspection PyBroadException
if __name__ == '__main__':
    import eventlet
    eventlet.monkey_patch(all=True)
    # 
    # See BUG: https://github.com/eventlet/eventlet/issues/592
    import __original_module_threading
    import threading
    __original_module_threading.current_thread.__globals__['_active'] = threading._active
# 
# Eventlet is not being used anymore because there is a severe bug:
# https://github.com/eventlet/eventlet/issues/526

# from gevent import monkey
# monkey.patch_all()

# from gevent.pywsgi import WSGIServer

import logging
import logging.config
import os

import eventlet.wsgi
import sqlalchemy_utils
import yaml
from flask_migrate import Migrate
from thorn import rq
from flask import Flask, request
from flask_babel import get_locale, Babel
from flask_cors import CORS
from flask_restful import Api
from flask_swagger_ui import get_swaggerui_blueprint
from thorn.gateway import ApiGateway
from thorn.models import db, User
from thorn.permission_api import PermissionListApi
from thorn.user_api import UserListApi, \
    ResetPasswordApi, ApproveUserApi, UserDetailApi, ProfileApi, \
    RegisterApi, GenerateUserTokenApi
from thorn.auth_api import ValidateTokenApi, AuthenticationApi
from thorn.role_api import RoleListApi, RoleDetailApi
from thorn.notification_api import NotificationListApi, NotificationDetailApi, \
    NotificationSummaryApi
from thorn.configuration_api import (ConfigurationListApi, 
    UserInterfaceConfigurationDetailApi)

def create_app(is_main_module=False):
    
    app = Flask(__name__)
    app.config['BABEL_TRANSLATION_DIRECTORIES'] = os.path.abspath('thorn/i18n/locales') 
    babel = Babel(app)
    
    logging.config.fileConfig('logging_config.ini')
    
    app.secret_key = '0e36528dc34844e79963436a7af9258f'
    
    # CORS
    CORS(app, resources={r"/*": {"origins": "*"}})

    # Swagger
    swaggerui_blueprint = get_swaggerui_blueprint(
        '/api/docs',  
        '/static/swagger.yaml',
        config={  # Swagger UI config overrides
            'app_name': "Lemonade Thorn"
        },
    )
    
    app.register_blueprint(swaggerui_blueprint)

    api = Api(app)
    
    mappings = {
        '/approve/<int:user_id>': ApproveUserApi,
        '/auth/validate': ValidateTokenApi,
        '/auth/login': AuthenticationApi,
        '/configurations': ConfigurationListApi,
        '/configurations/<name>': UserInterfaceConfigurationDetailApi,
        '/password/reset': ResetPasswordApi,
        '/permissions': PermissionListApi,
        '/notifications': NotificationListApi,
        '/notifications/summary': NotificationSummaryApi,
        '/notifications/<int:notification_id>': NotificationDetailApi,
        '/roles': RoleListApi,
        '/roles/<int:role_id>': RoleDetailApi,
        '/users/me': ProfileApi,
        '/users': UserListApi,
        '/register': RegisterApi,
        '/token/<int:user_id>': GenerateUserTokenApi,
        '/users/<int:user_id>': UserDetailApi,
        #    '/dashboards/<int:dashboard_id>': DashboardDetailApi,
        #    '/visualizations/<int:job_id>/<task_id>': VisualizationDetailApi,
        #    '/visualizations': VisualizationListApi,
    }
    for path, view in list(mappings.items()):
        api.add_resource(view, path)
    
    
    @babel.localeselector
    def get_locale():
        return request.headers.get('X-Locale', 'pt')
    
    sqlalchemy_utils.i18n.get_locale = get_locale
    
    config_file = os.environ.get('THORN_CONFIG')

    os.chdir(os.environ.get('THORN_HOME', '.'))
    logger = logging.getLogger(__name__)
    if config_file:
        with open(config_file) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)['thorn']

        app.config["RESTFUL_JSON"] = {"cls": app.json_encoder}

        server_config = config.get('servers', {})
        app.config['SQLALCHEMY_DATABASE_URI'] = server_config.get(
            'database_url')
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['RQ_REDIS_URL'] = config['servers']['redis_url']
        app.config['RQ_DASHBOARD_REDIS_URL'] = app.config['RQ_REDIS_URL']

        engine_config = config.get('config', {})

        if engine_config:
            final_config = {'pool_pre_ping': True}
            if 'mysql://' in app.config['SQLALCHEMY_DATABASE_URI']:
                if 'SQLALCHEMY_POOL_SIZE' in engine_config: 
                    final_config['pool_size'] = engine_config['SQLALCHEMY_POOL_SIZE'] 
                if 'SQLALCHEMY_POOL_RECYCLE' in engine_config: 
                    final_config['pool_recycle'] = engine_config['SQLALCHEMY_POOL_RECYCLE']
            app.config['SQLALCHEMY_ENGINE_OPTIONS'] = final_config

        app.config['THORN_CONFIG'] = config

        db.init_app(app)
        rq.init_app(app)

        
        migrate = Migrate(app, db)        
        port = int(config.get('port', 5000))
        logger.debug('Running in %s mode', config.get('environment'))

        if is_main_module:
            if config.get('environment', 'dev') == 'dev':
                app.run(debug=True, port=port)
            else:
                eventlet.wsgi.server(eventlet.listen(('', port)), app)
                # http_server = WSGIServer(('0.0.0.0', port), app)
                # http_server.serve_forever()
    else:
        logger.error('Please, set THORN_CONFIG environment variable')
        exit(1)
    return app


if __name__ == '__main__':
    create_app(True)
