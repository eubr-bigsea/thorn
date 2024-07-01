""" new_permissions  

Revision ID: 923425234ade
Revises: c79673214a30

"""
import datetime

import bcrypt
from alembic import context
from alembic import op
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import table, column
from thorn.migration_utils import (is_mysql, upgrade_actions,
        get_psql_enum_alter_commands, is_sqlite)


# revision identifiers, used by Alembic.
revision = '923425234ade'
down_revision = 'c79673214a30'
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
        (21, 'PIPELINE', 'PIPELINE', True),
        (22, 'PIPELINE_RUN', 'PIPELINE_RUN', True),
        (23, 'EXPERIMENT', 'EXPERIMENT', True),
        (24, 'EXPERIMENT_SQL', 'EXPERIMENT_SQL', True),
        (25, 'EXPERIMENT_VISUALIZATION', 'EXPERIMENT_VISUALIZATION', True),
        (26, 'EXPERIMENT_EXPLORER', 'EXPERIMENT_EXPLORER', True),
        (27, 'EXPERIMENT_MODEL', 'EXPERIMENT_MODEL', True),
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
        (21, 'pt', 'Gerenciar pipelines'),
        (21, 'en', 'Manage pipelines'),
        (22, 'pt', 'Gerenciar execução de pipelines'),
        (22, 'en', 'Manage pipeline runs'),
        (23, 'pt', 'Executar experimentos'),
        (23, 'en', 'Execute experiments'),
        (24, 'pt', 'Executar experimentos'),
        (24, 'en', 'Execute SQL experiments'),
        (25, 'pt', 'Executar experimentos de visualização'),
        (25, 'en', 'Execute visualization experiments'),
        (26, 'pt', 'Executar exprimentos de exploração de dados'),
        (26, 'en', 'Execute data exploration experiments'),
        (27, 'pt', 'Executar experimentos de aprendizado de máquina'),
        (27, 'en', 'Execute machine learning experiments'),
    ]
    rows = [dict(list(zip(columns, row))) for row in data]
    op.bulk_insert(tb, rows)

def get_commands():
    if is_mysql():
        cmd = '''ALTER TABLE permission CHANGE 
             applicable_to `applicable_to` enum('SYSTEM','DASHBOARD','DATA_SOURCE',
             'JOB', 'APP', 'DEPLOYMENT', 'API',
             'WORKFLOW','VISUALIZATION','USER',
    		'PIPELINE',
    		'PIPELINE_RUN',
    		'EXPERIMENT',
    		'EXPERIMENT_EXPLORER',
    		'EXPERIMENT_VISUALIZATION',
    		'EXPERIMENT_MODEL',
    		'EXPERIMENT_SQL'
             )'''
    elif is_sqlite():
        cmd = 'SELECT 1'
    else: get_psql_enum_alter_commands(
                 ['permission', 'asset'], ['applicable_to', 'type'], 'AssetTypeEnumType', 
                   ['SYSTEM','DASHBOARD','DATA_SOURCE', 'JOB', 'APP', 'DEPLOYMENT', 'API',
                     'WORKFLOW','VISUALIZATION','USER', 
		'PIPELINE',
    		'PIPELINE_RUN',
    		'EXPERIMENT',
    		'EXPERIMENT_EXPLORER',
    		'EXPERIMENT_VISUALIZATION',
    		'EXPERIMENT_MODEL',
    		'EXPERIMENT_SQL', ], 'USER') 

    all_commands = [ (cmd, 'SELECT 1'),
        (_insert_permissions, 'DELETE FROM permission WHERE id BETWEEN 21 AND 27'),
        (_insert_permission_translations,
         'DELETE FROM permission_translation WHERE id BETWEEN 21 AND 27'),
    ]
    return all_commands


def upgrade():
    ctx = context.get_context()
    session = sessionmaker(bind=ctx.bind)()
    connection = session.connection()
    all_commands = get_commands()

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
    all_commands = get_commands()

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
