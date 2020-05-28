"""adjusts in roles

Revision ID: 6cc0f4cce834
Revises: 9429d9e2ef7f
Create Date: 2020-05-28 15:39:06.252751

"""
import datetime

import bcrypt
from alembic import context
from alembic import op
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import table, column



# revision identifiers, used by Alembic.
revision = '6cc0f4cce834'
down_revision = 'b0e2b55721bd'
branch_labels = None
depends_on = None

def _insert_role_translation():
    tb = table(
        'role_translation',
        column('id', Integer),
        column('locale', String),
        column('label', String),
        column('description', String),
    )
    columns = [c.name for c in tb.columns]
    data = [
        (101, 'pt', 'Todos', 'Todos os usuários autenticados do sistema'),
        (101, 'en', 'Everyone', 'All authenticated users in the system'),
    ]
    rows = [dict(list(zip(columns, row))) for row in data]
    op.bulk_insert(tb, rows)


def _insert_role():
    tb = table(
        'role',
        column('id', Integer),
        column('name', String),
        column('all_user', Integer),
        column('enabled', Integer),
        column('system', Integer),
    )
    columns = [c.name for c in tb.columns]
    data = [
        (101, 'everybody', 1, 1, 1),
    ]
    rows = [dict(list(zip(columns, row))) for row in data]
    op.bulk_insert(tb, rows)


all_commands = [
    (_insert_role, 'DELETE FROM role WHERE id = 101'),
    (_insert_role_translation, 'DELETE FROM role_translation WHERE id = 101'),
    ('UPDATE role SET `system` = 1 WHERE id in (1, 100)', 
        'UPDATE role set `system` = 1  WHERE id in (1, 100)'),
    (""" update role_translation 
         SET label = 'Administrador', 
         description='Administra todo o sistema, tem todas as permissões' 
         WHERE id = 1 and locale = 'pt' """, None),
    (""" update role_translation 
         SET label = 'Administrator', 
         description='System admin, has all permissions' 
         WHERE id = 1 and locale = 'en' """, None),
    (""" update role_translation 
         SET label = 'Público', 
         description='Qualquer usuário, autenticado ou não' 
         WHERE id = 100 and locale = 'pt' """, None),
    (""" update role_translation 
         SET label = 'Public', 
         description='Any user, authenticated or not' 
         WHERE id = 100 and locale = 'en' """, None),

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
                    if cmd[1]:
                        connection.execute(row)
            elif cmd[1]:
                cmd[1]()
    except:
        session.rollback()
        raise
    session.commit()
