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
from thorn import rq
from flask import Flask, request
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_babel import get_locale, Babel
from flask_cors import CORS
from flask_restful import Api
from thorn.gateway import ApiGateway
from thorn.models import db, User
from thorn.permission_api import PermissionListApi
from thorn.user_api import UserListApi, \
    ResetPasswordApi, ApproveUserApi, UserDetailApi, ProfileApi, \
    RegisterApi
from thorn.auth_api import ValidateTokenApi, AuthenticationApi
from thorn.role_api import RoleListApi, RoleDetailApi
from thorn.notification_api import NotificationListApi, NotificationDetailApi, \
    NotificationSummaryApi
from thorn.configuration_api import ConfigurationListApi
import rq_dashboard

sqlalchemy_utils.i18n.get_locale = get_locale

app = Flask(__name__)
app.config['BABEL_TRANSLATION_DIRECTORIES'] = os.path.abspath('thorn/i18n/locales') 
babel = Babel(app)

logging.config.fileConfig('logging_config.ini')

app.secret_key = '0e36528dc34844e79963436a7af9258f'
# Flask Admin 
admin = Admin(app, name='Lemonade', template_mode='bootstrap3')

# CORS
CORS(app, resources={r"/*": {"origins": "*"}})
api = Api(app)

# RQ dashboard
app.config.from_object(rq_dashboard.default_settings)
app.register_blueprint(rq_dashboard.blueprint, url_prefix="/rq")

mappings = {
    '/approve/<int:user_id>': ApproveUserApi,
    '/auth/validate': ValidateTokenApi,
    '/auth/login': AuthenticationApi,
    '/configurations': ConfigurationListApi,
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


def main(is_main_module):
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
        app.config['SQLALCHEMY_POOL_SIZE'] = 10
        app.config['SQLALCHEMY_POOL_RECYCLE'] = 240
        app.config['RQ_REDIS_URL'] = config['servers']['redis_url']
        app.config['RQ_DASHBOARD_REDIS_URL'] = app.config['RQ_REDIS_URL']

        app.config.update(config.get('config', {}))
        app.config['THORN_CONFIG'] = config

        db.init_app(app)
        rq.init_app(app)

        port = int(config.get('port', 5000))
        logger.debug('Running in %s mode', config.get('environment'))

        if is_main_module:
            if config.get('environment', 'dev') == 'dev':
                admin.add_view(ModelView(User, db.session))
                app.run(debug=True, port=port)
            else:
                eventlet.wsgi.server(eventlet.listen(('', port)), app)
                # http_server = WSGIServer(('0.0.0.0', port), app)
                # http_server.serve_forever()
    else:
        logger.error('Please, set THORN_CONFIG environment variable')
        exit(1)


main(__name__ == '__main__')
