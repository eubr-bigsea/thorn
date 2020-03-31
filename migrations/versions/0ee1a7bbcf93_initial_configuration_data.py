"""initial configuration data

Revision ID: 0ee1a7bbcf93
Revises: 339a6b145e56
Create Date: 2020-03-27 11:19:37.266040

"""
import datetime

import bcrypt
from alembic import context
from alembic import op
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import table, column


# revision identifiers, used by Alembic.
revision = '0ee1a7bbcf93'
down_revision = '339a6b145e56'
branch_labels = None
depends_on = None

def _insert_configuration_translation():
    tb = table(
        'configuration_translation',
        column('id', Integer),
        column('locale', String),
        column('description', String),
    )
    columns = [c.name for c in tb.columns]
    data = [
        (1, 'pt', 'Endereço do servidor LDAP'),
        (1, 'en', 'LDAP server address'),
        (2, 'pt', 'Base DN no servidor LDAP'),
        (2, 'en', 'Base DN at LDAP server'),
        (3, 'pt', 'DN para usuário no servidor LDAP'),
        (3, 'en', 'User DN no servidor LDAP'),
        (4, 'pt', 'Endereço (URL) do servidor do Lemonade (se diferente do nome da máquina)'),
        (4, 'en', 'Lemonade server address (URL) (if it is different from the computer\'s name)'),
        (5, 'pt', 'E-mail de suporte para o Lemonade (e-mail de contato)'),
        (5, 'en', 'Lemonade\'s support email (contact email)'),
        (6, 'pt', 'Endereço do servidor para envio de e-mails (SMTP)'),
        (6, 'en', 'Email server address (SMTP)'),
        (7, 'pt', 'Usuário para autenticação no servidor de envio de e-mails'),
        (7, 'en', 'Email server login'),
        (8, 'pt', 'Senha para autenticação no servidor de envio de e-mails'),
        (8, 'en', 'Email server password'),
        (9, 'pt', 'Porta do servidor para envio de e-mails'),
        (9, 'en', 'Email server port'),
    ]
    rows = [dict(list(zip(columns, row))) for row in data]
    op.bulk_insert(tb, rows)


def _insert_configuration():
    tb = table(
        'configuration',
        column('id', Integer),
        column('name', String),
        column('value', String),
        column('enabled', Integer),
        column('internal', Integer),
        column('editor', String),
    )
    columns = [c.name for c in tb.columns]
    data = [
        (1, 'LDAP_SERVER', 'ldap.domain.com', 1, 1, 'TEXT'),
        (2, 'LDAP_BASE_DN', 'dc=domain,dc=com', 1, 1, 'TEXT'),
        (3, 'LDAP_USER_DN', 'uid={login},ou=People,dc=domain,dc=com', 1, 1, 'TEXT'),
        (4, 'SERVER_BASE_URL', 'http://localhost:8000', 1, 0, 'URL'),
        (5, 'SUPPORT_EMAIL', 'supporte@domain', 1, 0, 'EMAIL'),
        (6, 'SMTP_SERVER', 'smtp.domain.com', 1, 1, 'TEXT'),
        (7, 'SMTP_USER', 'lemonade.user', 1, 1, 'TEXT'),
        (8, 'SMTP_PASSWORD', 'secret', 1, 1, 'PASSWORD'),
        (9, 'SMTP_PORT', '465', 1, 1, 'INTEGER'),
    ]
    rows = [dict(list(zip(columns, row))) for row in data]
    op.bulk_insert(tb, rows)


all_commands = [
    (_insert_configuration, 'DELETE FROM configuration'),
    (_insert_configuration_translation, 'DELETE FROM configuration_translation'),
]


def upgrade():
    ctx = context.get_context()
    session = sessionmaker(bind=ctx.bind)()
    connection = session.connection()

    try:
        for cmd in all_commands:
            if isinstance(cmd[0], str):
                connection.execute(cmd[0])
            elif isinstance(cmd[0], list):
                for row in cmd[0]:
                    connection.execute(row)
            else:
                cmd[0]()
    except:
        session.rollback()
        raise
    session.commit()


def downgrade():
    ctx = context.get_context()
    session = sessionmaker(bind=ctx.bind)()
    connection = session.connection()

    try:
        for cmd in reversed(all_commands):
            if isinstance(cmd[1], str):
                connection.execute(cmd[1])
            elif isinstance(cmd[1], list):
                for row in cmd[1]:
                    connection.execute(row)
            else:
                cmd[1]()
    except:
        session.rollback()
        raise
    session.commit()
