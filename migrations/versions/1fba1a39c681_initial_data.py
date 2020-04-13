"""initial data

Revision ID: 1fba1a39c681
Revises: df233bb88c97
Create Date: 2020-03-02 09:28:48.614317

"""
import datetime

import bcrypt
from alembic import context
from alembic import op
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import table, column

# revision identifiers, used by Alembic.
revision = '1fba1a39c681'
down_revision = '2f93dbc61a5d'
branch_labels = None
depends_on = None


def _insert_permissions():
    tb = table(
        'permission',
        column('id', Integer),
        column('name', String),
        column('applicable_to', String),
        column('enabled', String),
    )

    columns = [c.name for c in tb.columns]
    data = [
        (1, 'WORKFLOW_VIEW_ANY', 'WORKFLOW', 1),
        (2, 'WORKFLOW_EDIT_ANY', 'WORKFLOW', 1),
        (3, 'WORKFLOW_EXECUTE_ANY', 'WORKFLOW', 1),
        (4, 'WORKFLOW_VIEW', 'WORKFLOW', 1),
        (5, 'WORKFLOW_EDIT', 'WORKFLOW', 1),
        (6, 'WORKFLOW_EXECUTE', 'WORKFLOW', 1),

        (7, 'DATA_SOURCE_VIEW_ANY', 'DATA_SOURCE', 1),
        (8, 'DATA_SOURCE_EDIT_ANY', 'DATA_SOURCE', 1),
        (9, 'DATA_SOURCE_USE_ANY', 'DATA_SOURCE', 1),
        (10, 'DATA_SOURCE_VIEW', 'DATA_SOURCE', 1),
        (11, 'DATA_SOURCE_EDIT', 'DATA_SOURCE', 1),
        (12, 'DATA_SOURCE_USE', 'DATA_SOURCE', 1),

        (13, 'DASHBOARD_VIEW_ANY', 'DASHBOARD', 1),
        (14, 'DASHBOARD_EDIT_ANY', 'DASHBOARD', 1),
        (15, 'DASHBOARD_VIEW', 'DASHBOARD', 1),
        (16, 'DASHBOARD_EDIT', 'DASHBOARD', 1),

        (100, 'USER_MANAGE', 'USER', 1),
        (101, 'STORAGE_MANAGE', 'SYSTEM', 1),
        (102, 'CLUSTER_MANAGE', 'SYSTEM', 1),

        (1000, 'ADMINISTRATOR', 'SYSTEM', 1),

    ]
    rows = [dict(list(zip(columns, row))) for row in data]
    op.bulk_insert(tb, rows)


def _insert_permission_translations():
    tb = table(
        'permission_translation',
        column('id', Integer),
        column('locale', String),
        column('description', String)
    )

    columns = [c.name for c in tb.columns]
    data = [
        (1, 'pt', 'Visualizar qualquer fluxo de trabalho'),
        (1, 'en', 'View any workflow'),
        (2, 'pt', 'Editar qualquer fluxo de trabalho'),
        (2, 'en', 'Edit any workflow'),
        (3, 'pt', 'Executar qualquer fluxo de trabalho'),
        (3, 'en', 'Execute any workflow'),
        (4, 'pt', 'Visualizar fluxo de trabalho'),
        (4, 'en', 'View workflow'),
        (5, 'pt', 'Editar fluxo de trabalho'),
        (5, 'en', 'Edit workflow'),
        (6, 'pt', 'Executar fluxo de trabalho'),
        (6, 'en', 'Execute workflow'),

        (7, 'pt', 'Visualizar qualquer fonte de dados'),
        (7, 'en', 'View any data source'),
        (8, 'pt', 'Editar qualquer fonte de dados'),
        (8, 'en', 'Edit any data source'),
        (9, 'pt', 'Usar qualquer fonte de dados'),
        (9, 'en', 'Use any data source'),
        (10, 'pt', 'Visualizar fonte de dados'),
        (10, 'en', 'View data source'),
        (11, 'pt', 'Editar fonte de dados'),
        (11, 'en', 'Edit data source'),
        (12, 'pt', 'Usar fonte de dados'),
        (12, 'en', 'Use data source'),

        (13, 'pt', 'Visualizar qualquer dashboard'),
        (13, 'en', 'View any dashboard'),
        (14, 'pt', 'Editar qualquer dashboard'),
        (14, 'en', 'Edit any dashboard'),
        (15, 'pt', 'Visualizar dashboard'),
        (15, 'en', 'View dashboard'),
        (16, 'pt', 'Editar dashboard'),
        (16, 'en', 'Edit dashboard'),

        (100, 'pt', 'Gerenciar usuários'),
        (100, 'en', 'Manage users'),
        (101, 'pt', 'Gerenciar armazenamentos'),
        (101, 'en', 'Manage stores'),
        (102, 'pt', 'Gerenciar clusters'),
        (102, 'en', 'Manage clusters'),

        (1000, 'en', 'Administrator'),
        (1000, 'pt', 'Administrador'),

    ]
    rows = [dict(list(zip(columns, row))) for row in data]
    op.bulk_insert(tb, rows)


def _insert_admin():
    tb = table(
        'user',
        column('id', Integer),
        column('login', String),
        column('email', String),
        column('encrypted_password', String),
        column('created_at', DateTime),
        column('first_name', String),
        column('last_name', String),
        column('locale', String),
        column('enabled', Integer),
        column('authentication_type', String),
    )

    columns = [c.name for c in tb.columns]
    hashed = bcrypt.hashpw('admin'.encode('utf8'),
                           bcrypt.gensalt(12)).decode('utf8')
    data = [
        (1, 'admin@lemonade.org.br', 'admin@lemonade.org.br',
         hashed, datetime.datetime.now(), 'Admin', '', 'pt', 1, 'INTERNAL'),
    ]
    rows = [dict(list(zip(columns, row))) for row in data]
    op.bulk_insert(tb, rows)


def _insert_roles():
    tb = table(
        'role',
        column('id', Integer),
        column('name', String),
        column('all_user', Integer),
        column('enabled', Integer),
    )
    columns = [c.name for c in tb.columns]
    data = [
        (1, 'admin', 0, 1),
        (100, 'public', 1, 1),
    ]
    rows = [dict(list(zip(columns, row))) for row in data]
    op.bulk_insert(tb, rows)


def _insert_role_translations():
    tb = table(
        'role_translation',
        column('id', Integer),
        column('locale', String),
        column('description', String)
    )
    columns = [c.name for c in tb.columns]
    data = [
        (1, 'pt', 'Administrador'),
        (1, 'en', 'Administrator'),
        (100, 'pt', 'Público'),
        (100, 'en', 'Public'),
    ]
    rows = [dict(list(zip(columns, row))) for row in data]
    op.bulk_insert(tb, rows)


def _insert_user_roles():
    tb = table(
        'user_role',
        column('user_id', Integer),
        column('role_id', Integer),
    )
    columns = [c.name for c in tb.columns]
    data = [
        (1, 1),
    ]
    rows = [dict(list(zip(columns, row))) for row in data]
    op.bulk_insert(tb, rows)


def _insert_role_permission():
    tb = table(
        'role_permission',
        column('role_id', Integer),
        column('permission_id', Integer),
    )
    columns = [c.name for c in tb.columns]
    data = [
        (1, 1000),
    ]
    rows = [dict(list(zip(columns, row))) for row in data]
    op.bulk_insert(tb, rows)



all_commands = [
    (_insert_permissions, 'DELETE FROM permission WHERE id BETWEEN 1 AND 16 OR '
                          'id BETWEEN 100 AND 102 OR id BETWEEN 1000 AND 1000'),
    (_insert_permission_translations,
     'DELETE FROM permission_translation WHERE id BETWEEN 1 AND 16 OR '
     'id BETWEEN 100 AND 102 OR id BETWEEN 1000 AND 1000'),

    (_insert_admin, 'DELETE FROM user WHERE id BETWEEN 1 AND 1 '),
    (_insert_roles, 'DELETE FROM role WHERE id BETWEEN 1 AND 1 OR id '
                    'BETWEEN 100 AND 100'),
    (_insert_role_translations,
     'DELETE FROM role_translation WHERE id BETWEEN 1 AND 1 OR id '
     'BETWEEN 100 AND 100'),
    (_insert_user_roles, 'DELETE FROM user_role WHERE user_id BETWEEN 1 AND 1'),

    (_insert_role_permission, 'DELETE FROM role_permission WHERE role_id = 1 '
                              'AND permission_id = 1000')
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
