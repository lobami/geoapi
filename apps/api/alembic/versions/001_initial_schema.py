"""Initial schema: interventions, areas, reference_places

Revision ID: 001
Revises:
Create Date: 2026-04-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy import inspect, text

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_tables() -> set[str]:
    bind = op.get_bind()
    return set(inspect(bind).get_table_names())


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    existing = _existing_tables()

    if "reference_places" not in existing:
        op.create_table(
            "reference_places",
            sa.Column("key", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("lat", sa.Float(), nullable=False),
            sa.Column("lon", sa.Float(), nullable=False),
            sa.Column("type", sa.String(), nullable=False, server_default="state"),
            sa.Column("aliases", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("geom", Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=True),
            sa.PrimaryKeyConstraint("key"),
        )
        op.create_index("idx_reference_places_geom", "reference_places", ["geom"], postgresql_using="gist")

    if "interventions" not in existing:
        op.create_table(
            "interventions",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("type", sa.String(), nullable=False),
            sa.Column("subtype", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("project_id", sa.String(), nullable=False),
            sa.Column("region", sa.String(), nullable=False),
            sa.Column("operator_id", sa.String(), nullable=False),
            sa.Column("priority", sa.String(), nullable=False),
            sa.Column("source", sa.String(), nullable=False),
            sa.Column("quality_score", sa.Float(), nullable=True),
            sa.Column("date", sa.Date(), nullable=True),
            sa.Column("timestamp", sa.DateTime(timezone=True), nullable=True),
            sa.Column("metadata", sa.JSON(), nullable=True),
            sa.Column("metrics", sa.JSON(), nullable=True),
            sa.Column("lon", sa.Float(), nullable=False),
            sa.Column("lat", sa.Float(), nullable=False),
            sa.Column("geom", Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("idx_interventions_geom", "interventions", ["geom"], postgresql_using="gist")
        op.create_index(op.f("ix_interventions_type"), "interventions", ["type"])
        op.create_index(op.f("ix_interventions_subtype"), "interventions", ["subtype"])
        op.create_index(op.f("ix_interventions_status"), "interventions", ["status"])
        op.create_index(op.f("ix_interventions_project_id"), "interventions", ["project_id"])
        op.create_index(op.f("ix_interventions_region"), "interventions", ["region"])
        op.create_index(op.f("ix_interventions_operator_id"), "interventions", ["operator_id"])
        op.create_index(op.f("ix_interventions_priority"), "interventions", ["priority"])
        op.create_index(op.f("ix_interventions_source"), "interventions", ["source"])

    if "areas" not in existing:
        op.create_table(
            "areas",
            sa.Column("area_id", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("geometry", sa.JSON(), nullable=False),
            sa.Column("geom", Geometry(geometry_type="POLYGON", srid=4326, spatial_index=False), nullable=True),
            sa.PrimaryKeyConstraint("area_id"),
        )
        op.create_index("idx_areas_geom", "areas", ["geom"], postgresql_using="gist")


def downgrade() -> None:
    op.drop_table("areas")
    op.drop_table("interventions")
    op.drop_table("reference_places")
