"""Seed micro_markets table with 10 metro markets

Revision ID: 20250430_0002
Revises: 20250430_0001
Create Date: 2025-04-30 10:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
import json
from pathlib import Path

# revision identifiers, used by Alembic.
revision = '20250430_0002'
down_revision = '20250430_0001'
branch_labels = None
depends_on = None


def upgrade():
    """Load seed data into micro_markets table"""
    connection = op.get_bind()
    
    # Load seed data from JSON file
    seed_file = Path(__file__).parent.parent.parent / "app/services/success_profile/micromarkets/seed_data/all_metros.json"
    
    try:
        with open(seed_file, 'r') as f:
            seed_records = json.load(f)
        
        # Insert each record
        for record in seed_records:
            # Check if already exists
            stmt = sa.text("""
                SELECT id FROM micro_markets 
                WHERE market_name = :name AND metro = :metro AND state = :state
            """)
            result = connection.execute(stmt, {
                'name': record['market_name'],
                'metro': record['metro'],
                'state': record['state']
            }).first()
            
            if result:
                # Already exists, skip
                continue
            
            # Insert new record
            insert_stmt = sa.text("""
                INSERT INTO micro_markets (
                    market_name, metro, state,
                    center_latitude, center_longitude,
                    polygon_geojson, description,
                    typical_archetypes, demographic_profile,
                    is_active, created_at, updated_at
                ) VALUES (
                    :name, :metro, :state,
                    :lat, :lng,
                    :polygon, :description,
                    :archetypes, :demographics,
                    1, NOW(), NOW()
                )
            """)
            
            connection.execute(insert_stmt, {
                'name': record['market_name'],
                'metro': record['metro'],
                'state': record['state'],
                'lat': record['center_latitude'],
                'lng': record['center_longitude'],
                'polygon': json.dumps(record.get('polygon_geojson', {})),
                'description': record.get('description'),
                'archetypes': json.dumps(record.get('typical_archetypes', [])),
                'demographics': json.dumps(record.get('demographic_profile', {})),
            })
        
        print(f"✓ Seeded {len(seed_records)} micro-markets")
    
    except Exception as e:
        print(f"⚠ Error seeding micro-markets: {e}")
        # Don't fail the migration, continue
        pass


def downgrade():
    """Remove seeded micro-markets"""
    connection = op.get_bind()
    
    # Delete all micro-markets (assuming they're the seeded ones)
    # In a real scenario, might want to be more selective
    delete_stmt = sa.text("DELETE FROM micro_markets WHERE is_active = 1")
    connection.execute(delete_stmt)
