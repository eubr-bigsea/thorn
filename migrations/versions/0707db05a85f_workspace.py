"""workspace

Revision ID: 0707db05a85f
Revises: 6cc0f4cce834
Create Date: 2020-05-28 16:43:28.831762

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from thorn.migration_utils import is_sqlite

# revision identifiers, used by Alembic.
revision = '0707db05a85f'
down_revision = '6cc0f4cce834'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('workspace',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('owner_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['owner_id'], ['user.id'], name='fk_user_id'),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('user', sa.Column('workspace_id', sa.Integer(), nullable=True))

    if is_sqlite():
        with op.batch_alter_table('workspace') as batch_op:
            batch_op.create_foreign_key('fk_user_id', 'user', ['workspace_id'], ['id'])
    else:
        op.create_foreign_key('fk_workspace_id', 'user', 'workspace', ['workspace_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    if is_sqlite():
        with op.batch_alter_table('user') as batch_op:
            batch_op.drop_column('workspace_id')
    else:
        op.drop_constraint('fk_workspace_id', 'user', type_='foreignkey')
        op.drop_column('user', 'workspace_id')
    op.drop_table('workspace')

