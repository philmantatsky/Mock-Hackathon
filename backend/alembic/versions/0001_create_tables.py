"""create tables

Revision ID: 0001
Revises:
Create Date: 2026-10-08 16:04:53.271970

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('households',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('phone_hash', sa.String(length=64), nullable=True),
    sa.Column('first_initial', sa.String(length=1), nullable=True),
    sa.Column('birth_month', sa.SmallInteger(), nullable=True),
    sa.Column('birth_year', sa.SmallInteger(), nullable=True),
    sa.Column('household_size', sa.SmallInteger(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_households')),
    sa.UniqueConstraint('phone_hash', name=op.f('uq_households_phone_hash'))
    )
    locations = op.create_table('locations',
    sa.Column('id', sa.String(length=64), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('address', sa.String(length=300), nullable=True),
    sa.Column('active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_locations'))
    )
    # Demo pantries, the same two the frontend mocks use, so a fresh database
    # can accept visits straight away.
    op.bulk_insert(locations, [
        {'id': 'loc-1', 'name': 'Eastside Community Pantry', 'address': '120 Main St'},
        {'id': 'loc-2', 'name': 'Riverside Church Pantry', 'address': None},
    ])
    op.create_table('visits',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('location_id', sa.String(length=64), nullable=False),
    sa.Column('method', sa.String(length=16), nullable=False),
    sa.Column('visited_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('phone_hash', sa.String(length=64), nullable=True),
    sa.Column('first_initial', sa.String(length=1), nullable=True),
    sa.Column('birth_month', sa.SmallInteger(), nullable=True),
    sa.Column('birth_year', sa.SmallInteger(), nullable=True),
    sa.Column('household_size', sa.SmallInteger(), nullable=True),
    sa.Column('language', sa.String(length=8), nullable=True),
    sa.Column('household_id', sa.Uuid(), nullable=True),
    sa.CheckConstraint("(method = 'phone' AND phone_hash IS NOT NULL AND first_initial IS NULL AND birth_month IS NULL AND birth_year IS NULL) OR (method = 'no_phone' AND phone_hash IS NULL AND first_initial IS NOT NULL AND birth_month IS NOT NULL AND birth_year IS NOT NULL AND household_size IS NOT NULL) OR (method = 'anonymous' AND phone_hash IS NULL AND first_initial IS NULL AND birth_month IS NULL AND birth_year IS NULL AND household_size IS NULL)", name=op.f('ck_visits_identity_matches_method')),
    sa.CheckConstraint("method IN ('phone', 'no_phone', 'anonymous')", name=op.f('ck_visits_method_valid')),
    sa.CheckConstraint('birth_month BETWEEN 1 AND 12', name=op.f('ck_visits_birth_month_range')),
    sa.CheckConstraint('household_size >= 1', name=op.f('ck_visits_household_size_positive')),
    sa.ForeignKeyConstraint(['household_id'], ['households.id'], name=op.f('fk_visits_household_id_households')),
    sa.ForeignKeyConstraint(['location_id'], ['locations.id'], name=op.f('fk_visits_location_id_locations')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_visits'))
    )
    op.create_index(op.f('ix_visits_household_id'), 'visits', ['household_id'], unique=False)
    op.create_index(op.f('ix_visits_phone_hash'), 'visits', ['phone_hash'], unique=False)
    op.create_table('review_items',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('visit_id', sa.Uuid(), nullable=False),
    sa.Column('candidate_household_id', sa.Uuid(), nullable=False),
    sa.Column('score', sa.Float(), nullable=False),
    sa.Column('status', sa.String(length=16), server_default=sa.text("'pending'"), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("status IN ('pending', 'merged', 'separate')", name=op.f('ck_review_items_status_valid')),
    sa.ForeignKeyConstraint(['candidate_household_id'], ['households.id'], name=op.f('fk_review_items_candidate_household_id_households')),
    sa.ForeignKeyConstraint(['visit_id'], ['visits.id'], name=op.f('fk_review_items_visit_id_visits')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_review_items')),
    sa.UniqueConstraint('visit_id', name=op.f('uq_review_items_visit_id'))
    )


def downgrade() -> None:
    op.drop_table('review_items')
    op.drop_index(op.f('ix_visits_phone_hash'), table_name='visits')
    op.drop_index(op.f('ix_visits_household_id'), table_name='visits')
    op.drop_table('visits')
    op.drop_table('locations')
    op.drop_table('households')
