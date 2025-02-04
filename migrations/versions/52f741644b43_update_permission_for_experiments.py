"""Update permission for experiments

Revision ID: 52f741644b43
Revises: 923425234ade
Create Date: 2025-02-04 08:56:15.060331

"""
from alembic import op, context
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker


# revision identifiers, used by Alembic.
revision = '52f741644b43'
down_revision = '923425234ade'
branch_labels = None
depends_on = None


def upgrade():

    ctx = context.get_context()
    session = sessionmaker(bind=ctx.bind)()
    connection = session.connection()
    connection.execute("""
        UPDATE permission SET applicable_to = 'EXPERIMENT'
        WHERE applicable_to LIKE 'EXPERIMENT%%';
    """)
    breakpoint()
    connection.execute("""
        UPDATE permission_translation 
        SET description = 'Executar experimentos SQL'
        WHERE id = 24 and locale = 'pt';
    """)
    connection.execute("""
        UPDATE permission SET applicable_to = 'PIPELINE'
        WHERE applicable_to LIKE 'PIPELINE%%';
    """)
    session.commit()


def downgrade():
    ctx = context.get_context()
    session = sessionmaker(bind=ctx.bind)()
    connection = session.connection()
    connection.execute("""
        UPDATE permission SET applicable_to = name
        WHERE applicable_to LIKE 'EXPERIMENT%%';
    """)
    connection.execute("""
        UPDATE permission SET applicable_to = name
        WHERE applicable_to LIKE 'PIPELINE%%';
    """)
    session.commit()
