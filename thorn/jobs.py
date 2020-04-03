# coding=utf-8
import datetime
import json
import os
import logging.config
import os
import smtplib
import yaml
from flask import current_app
from flask_babel import gettext as babel_gettext, force_locale
from thorn import rq
from thorn.models import *
import jinja2
logging.config.fileConfig('logging_config.ini')
logger = logging.getLogger(__name__)

JOB_MODULE = True

def get_config():
    config_file = os.environ.get('THORN_CONFIG')
    if config_file is None:
        raise ValueError(
            'You must inform the THORN_CONF env variable')

    with open(config_file) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    return config['thorn']


# def ctx_gettext(locale):
#     def translate(msg, **variables):
#         with app.app.test_request_context():
#             with force_locale(locale):
#                 return babel_gettext(msg, **variables)
# 
#     return translate
# 

@rq.job("thorn", description="Send email", result_ttl=86400)
def send_email(**kwargs):
    smtp_configs = [
        'SMTP_SERVER', 'SMTP_USER',
        'SMTP_PASSWORD', 'SMTP_PORT'
    ]
    try:
        query = None
        with current_app.app_context():
            query = Configuration.query.filter(
                Configuration.name.in_(smtp_configs))
        configs = dict( (c.name, c.value) for c in query)
    
        smtp_user = configs.get('SMTP_USER')
        smtp_passwd = configs.get('SMTP_PASSWORD')
        smtp_server = configs.get('SMTP_SERVER')
        smtp_port = configs.get('SMTP_PORT')
    
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('SMTP configuration: %s:%s (%s %s%s)',
                    smtp_server, smtp_port, smtp_user, smtp_passwd[0], 
                    (len(smtp_passwd) - 1) * '*')

        base_dir = os.path.dirname(os.path.abspath(__file__))
        templateLoader = jinja2.FileSystemLoader(
                searchpath='{}/templates/mail'.format(base_dir))
        templateEnv = jinja2.Environment(
                extensions=['jinja2.ext.i18n'],
                loader=templateLoader)

        templ = templateEnv.get_template('{}.html'.format(kwargs.get('template')))
        with force_locale(kwargs.get('locale', 'pt')):
            kwargs['gettext'] = babel_gettext
            body = templ.render(kwargs)
        
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        server.ehlo()
        server.login(smtp_user, smtp_passwd)
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.header import Header
        from email.utils import formataddr

        to = kwargs.get('to').split()
        sender = 'LEMONADE <lemonade.suporte@gmail.com>'
        msg = MIMEMultipart('alternative')
        msg['From']    = sender
        msg['Subject'] = kwargs.get('subject')
        msg['To']      = ','.join(to)
        msg.attach(MIMEText(body, 'html'))

        print(body)
        to_list = to
        server.sendmail(sender, to_list, msg.as_string())
    
        print('*' * 50)
    except Exception:
        logger.exception('Error in metric job')
        db.session.rollback()
        raise



