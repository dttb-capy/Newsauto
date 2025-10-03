"""add_quality_scores_to_content

Revision ID: f69452393f99
Revises: 
Create Date: 2025-10-03 18:16:53.741372+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f69452393f99'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add quality scoring columns to content_items table
    op.add_column('content_items', sa.Column('quality_score', sa.Float(), nullable=True, server_default='0.0'))
    op.add_column('content_items', sa.Column('hallucination_score', sa.Float(), nullable=True))
    op.add_column('content_items', sa.Column('factual_score', sa.Float(), nullable=True))
    op.add_column('content_items', sa.Column('sentiment_score', sa.Float(), nullable=True))
    op.add_column('content_items', sa.Column('confidence_score', sa.Float(), nullable=True, server_default='1.0'))
    op.add_column('content_items', sa.Column('needs_review', sa.Boolean(), nullable=True, server_default='0'))
    op.add_column('content_items', sa.Column('quality_flags', sa.JSON(), nullable=True))
    op.add_column('content_items', sa.Column('quality_checked_at', sa.DateTime(), nullable=True))

    # Create index for filtering by quality
    op.create_index('ix_content_items_quality_score', 'content_items', ['quality_score'])
    op.create_index('ix_content_items_needs_review', 'content_items', ['needs_review'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_content_items_needs_review', 'content_items')
    op.drop_index('ix_content_items_quality_score', 'content_items')

    # Drop columns
    op.drop_column('content_items', 'quality_checked_at')
    op.drop_column('content_items', 'quality_flags')
    op.drop_column('content_items', 'needs_review')
    op.drop_column('content_items', 'confidence_score')
    op.drop_column('content_items', 'sentiment_score')
    op.drop_column('content_items', 'factual_score')
    op.drop_column('content_items', 'hallucination_score')
    op.drop_column('content_items', 'quality_score')