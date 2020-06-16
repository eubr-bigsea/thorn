""" new_permissions  

Revision ID: 9c908beaa51a
Revises: 10120f95d77f
Create Date: 2020-06-15 18:38:29.256375

"""
import datetime

import bcrypt
from alembic import context
from alembic import op
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import table, column

# revision identifiers, used by Alembic.
revision = '9c908beaa51a'
down_revision = '10120f95d77f'
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
        (17, 'JOB_VIEW_ANY', 'JOB', 1),
        (18, 'JOB_EDIT_ANY', 'JOB', 1),
        (19, 'APP_EDIT', 'APP', 1),
        (20, 'APP_USE', 'APP', 1),

        (103, 'DEPLOYMENT_MANAGE', 'DEPLOYMENT', 1),
        (104, 'RUN_WORKFLOW_API', 'JOB', 1),
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
        (17, 'pt', 'Visualizar qualquer execução de fluxo'),
        (17, 'en', 'View any job'),
        (18, 'pt', 'Editar qualquer execução'),
        (18, 'en', 'Edit any job'),
        (19, 'pt', 'Editar aplicações (trilhas)'),
        (19, 'en', 'Edit apps'),
        (20, 'pt', 'Usar aplicações (trilhas)'),
        (20, 'en', 'Use apps'),
        (103, 'pt', 'Gerenciar implantação de fluxos de trabalho'),
        (103, 'en', 'Manageg workflow deployment'),
        (104, 'pt', 'Executar fluxo de trabalho pela API'),
        (104, 'en', 'Execute workflow using API'),
    ]
    rows = [dict(list(zip(columns, row))) for row in data]
    op.bulk_insert(tb, rows)


all_commands = [
    ('''ALTER TABLE permission CHANGE 
         applicable_to `applicable_to` enum('SYSTEM','DASHBOARD','DATA_SOURCE',
         'JOB', 'APP', 'DEPLOYMENT', 'API',
         'WORKFLOW','VISUALIZATION','USER')'''
        , 'SELECT 1'
    ),
    (_insert_permissions, 'DELETE FROM permission WHERE id BETWEEN 17 AND 20 OR '
                          'id BETWEEN 103 AND 104 '),
    (_insert_permission_translations,
     'DELETE FROM permission_translation WHERE id BETWEEN 17 AND 20 OR '
                          'id BETWEEN 103 AND 104 ' ),

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
            if isinstance(cmd[1], str) and cmd[1]:
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
