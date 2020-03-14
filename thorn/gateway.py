# -*- coding: utf-8 -*-}
import logging

import requests
from flask import request
from flask.views import MethodView
from flask_babel import gettext

log = logging.getLogger(__name__)


class ApiGateway(MethodView):
    """ API Gateway """

    def __init__(self):
        self.human_name = gettext('API Gateway')

    def get(self, path):
        print('#' * 20)
        print('get')
        print(request.args)
        print(path)
        print(request.headers)
        headers = request.headers
        print('#' * 20)
        url = 'https://dev.ctweb.inweb.org.br/stand/clusters?token=123456'
        resp = requests.get(url, headers=headers, stream=True)
        return resp.raw.read(), resp.status_code, resp.headers.items()

    def post(self, path):
        headers = request.headers
        url = 'https://dev.ctweb.inweb.org.br/stand/clusters?token=123456'
        resp = requests.post(url, data=request.data,
                             headers=headers, stream=True)
        return resp.raw.read(), resp.status_code, resp.headers.items()

    def delete(self, path):
        headers = request.headers
        url = 'http://localhost:3323/{}?token=123456'.format(path)
        resp = requests.delete(url, headers=headers, stream=False)
        if resp.status_code == 405:
            return 'Invalid method', resp.status_code, resp.headers.items()
        else:
            return resp.raw.read(), resp.status_code, resp.headers.items()

    def patch(self, path):
        headers = request.headers
        url = 'http://localhost:3323/{}?token=123456'.format(path)
        resp = requests.patch(url, json=request.json,
                              headers=headers, stream=True)
        return resp.raw.read(), resp.status_code, resp.headers.items()
