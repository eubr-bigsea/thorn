""" Config category  

Revision ID: 731386923937
Revises: 04205e193be1
Create Date: 2020-08-24 19:05:32.471924

"""
from alembic import op
import sqlalchemy as sa
import datetime

from alembic import context
from alembic import op
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import table, column


# revision identifiers, used by Alembic.
revision = '731386923937'
down_revision = '04205e193be1'
branch_labels = None

depends_on = None

all_commands = [
    [
        [
        """ UPDATE configuration_translation
        SET category = 'Autenticação' WHERE locale = 'pt' 
            AND id IN (1, 2, 3)""",
        """ UPDATE configuration_translation
        SET category = 'Authentication' WHERE locale = 'en' 
            AND id IN (1, 2, 3)""",
        """ UPDATE configuration_translation
        SET category = 'Servidor' WHERE locale = 'pt' 
            AND id IN (4)""",
        """ UPDATE configuration_translation
        SET category = 'Server' WHERE locale = 'en' 
            AND id IN (4)""",
        """ UPDATE configuration_translation
        SET category = 'Envio de e-mail' WHERE locale = 'pt' 
            AND id IN (5, 6, 7, 8, 9)""",
        """ UPDATE configuration_translation
        SET category = 'Emails' WHERE locale = 'en' 
            AND id IN (5, 6, 7, 8, 9)""",
        ],
        """UPDATE configuration_translation
           SET category = NULL;"""
    ]

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

