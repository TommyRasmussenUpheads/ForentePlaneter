"""baseline schema

Revision ID: 0001_baseline
Revises:
Create Date: 2026-05-14

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Baseline migration — database already created via init.sql
    # This migration marks the starting point for future migrations.
    # Run this after a fresh docker compose down -v to recreate everything.
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")

    # Enums
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE user_role AS ENUM ('superadmin','admin','elder_race','player');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE game_status AS ENUM ('lobby','active','ended');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE planet_type AS ENUM ('home','neighbor','npc','elder_race');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE ship_type AS ENUM
            ('fighter','cruiser','bomber','planet_defense','expedition','transport','diplomat');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE mission_type AS ENUM ('attack','transport','expedition','diplomacy','return');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE mission_status AS ENUM ('in_flight','arrived','returning','completed','cancelled');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE blockade_status AS ENUM ('none','blockaded');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE honor_mark AS ENUM ('honored','betrayed');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE build_status AS ENUM ('queued','building','completed','cancelled');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)

    # Users
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            username VARCHAR(32) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role user_role NOT NULL DEFAULT 'player',
            totp_secret TEXT,
            email_verified BOOLEAN NOT NULL DEFAULT FALSE,
            is_active BOOLEAN NOT NULL DEFAULT FALSE,
            honor_points INT NOT NULL DEFAULT 0,
            honor_from_trade INT NOT NULL DEFAULT 0,
            honor_from_deals INT NOT NULL DEFAULT 0,
            betrayals_marked INT NOT NULL DEFAULT 0,
            fp_member BOOLEAN NOT NULL DEFAULT FALSE,
            invites_remaining INT NOT NULL DEFAULT 100,
            invited_by UUID REFERENCES users(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_login TIMESTAMPTZ
        )
    """)

    # Invitations
    op.execute("""
        CREATE TABLE IF NOT EXISTS invitations (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            token UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
            invited_by UUID NOT NULL REFERENCES users(id),
            invited_email VARCHAR(255),
            used_by UUID REFERENCES users(id),
            used_at TIMESTAMPTZ,
            expires_at TIMESTAMPTZ NOT NULL,
            reward_applied BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # Email verifications
    op.execute("""
        CREATE TABLE IF NOT EXISTS email_verifications (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID NOT NULL REFERENCES users(id),
            token UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
            expires_at TIMESTAMPTZ NOT NULL,
            verified_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # Game round
    op.execute("""
        CREATE TABLE IF NOT EXISTS game_round (
            id SERIAL PRIMARY KEY,
            status game_status NOT NULL DEFAULT 'lobby',
            current_tick INT NOT NULL DEFAULT 0,
            duration_days INT NOT NULL DEFAULT 30,
            started_at TIMESTAMPTZ,
            ends_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # Alliances
    op.execute("""
        CREATE TABLE IF NOT EXISTS alliances (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            name VARCHAR(64) UNIQUE NOT NULL,
            tag VARCHAR(8) UNIQUE NOT NULL,
            leader_id UUID NOT NULL REFERENCES users(id),
            founded_tick INT NOT NULL DEFAULT 0,
            is_public BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS alliance_members (
            alliance_id UUID NOT NULL REFERENCES alliances(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            joined_tick INT NOT NULL DEFAULT 0,
            PRIMARY KEY (alliance_id, user_id)
        )
    """)

    # Solar systems and planets
    op.execute("""
        CREATE TABLE IF NOT EXISTS solar_systems (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            name VARCHAR(64) NOT NULL,
            hex_q INT NOT NULL,
            hex_r INT NOT NULL,
            owner_id UUID REFERENCES users(id),
            is_npc BOOLEAN NOT NULL DEFAULT FALSE,
            is_elder_race BOOLEAN NOT NULL DEFAULT FALSE,
            is_unknown_region BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (hex_q, hex_r)
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS system_routes (
            id SERIAL PRIMARY KEY,
            from_system_id UUID NOT NULL REFERENCES solar_systems(id),
            to_system_id UUID NOT NULL REFERENCES solar_systems(id),
            travel_ticks INT NOT NULL DEFAULT 6,
            CHECK (from_system_id != to_system_id)
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS planets (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            solar_system_id UUID NOT NULL REFERENCES solar_systems(id),
            name VARCHAR(64) NOT NULL,
            planet_type planet_type NOT NULL,
            owner_id UUID REFERENCES users(id),
            orbit_slot SMALLINT NOT NULL,
            travel_ticks SMALLINT NOT NULL DEFAULT 0,
            blockade_status blockade_status NOT NULL DEFAULT 'none',
            metal BIGINT NOT NULL DEFAULT 0,
            energy BIGINT NOT NULL DEFAULT 0,
            gas BIGINT NOT NULL DEFAULT 0,
            metal_production INT NOT NULL DEFAULT 0,
            energy_production INT NOT NULL DEFAULT 0,
            gas_production INT NOT NULL DEFAULT 0,
            score BIGINT NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # Ships
    op.execute("""
        CREATE TABLE IF NOT EXISTS ship_stats (
            ship_type ship_type PRIMARY KEY,
            attack INT NOT NULL DEFAULT 0,
            defense INT NOT NULL DEFAULT 0,
            travel_modifier FLOAT NOT NULL DEFAULT 1.0,
            cargo_capacity INT NOT NULL DEFAULT 0,
            is_immune BOOLEAN NOT NULL DEFAULT FALSE,
            is_mobile BOOLEAN NOT NULL DEFAULT TRUE,
            dies_first BOOLEAN NOT NULL DEFAULT FALSE,
            dies_last BOOLEAN NOT NULL DEFAULT FALSE,
            build_ticks INT NOT NULL DEFAULT 1,
            cost_metal INT NOT NULL DEFAULT 0,
            cost_energy INT NOT NULL DEFAULT 0,
            cost_gas INT NOT NULL DEFAULT 0,
            unlock_condition TEXT
        )
    """)
    op.execute("""
        INSERT INTO ship_stats VALUES
        ('fighter',         10,  3, 1.0,      0, FALSE, TRUE,  FALSE, FALSE, 2,  50,  20,  10, NULL),
        ('cruiser',          6, 12, 1.0,      0, FALSE, TRUE,  FALSE, FALSE, 4, 120,  30,  20, NULL),
        ('bomber',          20,  1, 1.0,      0, FALSE, TRUE,  FALSE, FALSE, 3,  40, 150,  20, NULL),
        ('planet_defense',   1, 20, 0.0,      0, FALSE, FALSE, FALSE, FALSE, 5,  60,  20, 120, NULL),
        ('transport',        0, 30, 1.0,  10000, FALSE, TRUE,  TRUE,  FALSE, 4, 200,  40,  30, NULL),
        ('expedition',       0,  0, 0.5,      0, FALSE, TRUE,  FALSE, TRUE,  6,  80, 100,  60, NULL),
        ('diplomat',         0,  0, 0.167,    0, TRUE,  TRUE,  FALSE, FALSE, 8, 100, 150,  80, 'first_intersystem_travel')
        ON CONFLICT DO NOTHING
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS ships (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            owner_id UUID NOT NULL REFERENCES users(id),
            planet_id UUID REFERENCES planets(id),
            ship_type ship_type NOT NULL,
            quantity INT NOT NULL DEFAULT 1,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # Build queue
    op.execute("""
        CREATE TABLE IF NOT EXISTS build_queue (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            planet_id UUID NOT NULL REFERENCES planets(id) ON DELETE CASCADE,
            owner_id UUID NOT NULL REFERENCES users(id),
            ship_type ship_type NOT NULL,
            quantity INT NOT NULL DEFAULT 1,
            ticks_remaining INT NOT NULL,
            ticks_total INT NOT NULL,
            status build_status NOT NULL DEFAULT 'queued',
            queue_position INT NOT NULL DEFAULT 1,
            metal_cost INT NOT NULL DEFAULT 0,
            energy_cost INT NOT NULL DEFAULT 0,
            gas_cost INT NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # Fleet missions
    op.execute("""
        CREATE TABLE IF NOT EXISTS fleet_missions (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            owner_id UUID NOT NULL REFERENCES users(id),
            origin_planet_id UUID NOT NULL REFERENCES planets(id),
            target_planet_id UUID NOT NULL REFERENCES planets(id),
            mission_type mission_type NOT NULL,
            status mission_status NOT NULL DEFAULT 'in_flight',
            depart_tick INT NOT NULL,
            arrive_tick INT NOT NULL,
            return_tick INT,
            cargo_metal BIGINT NOT NULL DEFAULT 0,
            cargo_energy BIGINT NOT NULL DEFAULT 0,
            cargo_gas BIGINT NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS fleet_mission_ships (
            mission_id UUID NOT NULL REFERENCES fleet_missions(id) ON DELETE CASCADE,
            ship_type ship_type NOT NULL,
            quantity INT NOT NULL,
            PRIMARY KEY (mission_id, ship_type)
        )
    """)

    # Combat, diplomacy, FP, honor, tick, notifications
    op.execute("""
        CREATE TABLE IF NOT EXISTS combat_log (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            tick_number INT NOT NULL,
            planet_id UUID NOT NULL REFERENCES planets(id),
            attacker_id UUID NOT NULL REFERENCES users(id),
            defender_id UUID REFERENCES users(id),
            attacker_won BOOLEAN NOT NULL,
            attacker_atk_total INT NOT NULL,
            defender_atk_total INT NOT NULL,
            planet_changed_owner BOOLEAN NOT NULL DEFAULT FALSE,
            losses_json JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS ambassadors (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            from_user_id UUID NOT NULL REFERENCES users(id),
            to_user_id UUID NOT NULL REFERENCES users(id),
            home_planet_id UUID NOT NULL REFERENCES planets(id),
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            opened_tick INT NOT NULL,
            closed_tick INT,
            CHECK (from_user_id != to_user_id)
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS direct_messages (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            ambassador_id UUID NOT NULL REFERENCES ambassadors(id) ON DELETE CASCADE,
            sender_id UUID NOT NULL REFERENCES users(id),
            content TEXT NOT NULL,
            sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS fp_threads (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            author_id UUID NOT NULL REFERENCES users(id),
            title VARCHAR(128) NOT NULL,
            category VARCHAR(32) NOT NULL DEFAULT 'general',
            is_open BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS fp_posts (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            thread_id UUID NOT NULL REFERENCES fp_threads(id) ON DELETE CASCADE,
            author_id UUID NOT NULL REFERENCES users(id),
            content TEXT NOT NULL,
            is_agreement BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS honor_awards (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            from_user_id UUID NOT NULL REFERENCES users(id),
            to_user_id UUID NOT NULL REFERENCES users(id),
            source_type VARCHAR(16) NOT NULL,
            source_id UUID NOT NULL,
            mark honor_mark NOT NULL DEFAULT 'honored',
            awarded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CHECK (from_user_id != to_user_id)
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS tick_log (
            id SERIAL PRIMARY KEY,
            tick_number INT NOT NULL UNIQUE,
            round_id INT REFERENCES game_round(id),
            started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            ended_at TIMESTAMPTZ,
            planets_processed INT NOT NULL DEFAULT 0,
            missions_resolved INT NOT NULL DEFAULT 0,
            combats_resolved INT NOT NULL DEFAULT 0,
            status VARCHAR(16) NOT NULL DEFAULT 'running'
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            type VARCHAR(32) NOT NULL,
            title VARCHAR(128) NOT NULL,
            body TEXT,
            is_read BOOLEAN NOT NULL DEFAULT FALSE,
            related_id UUID,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # Indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_planets_owner ON planets(owner_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_planets_system ON planets(solar_system_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_ships_owner ON ships(owner_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_ships_planet ON ships(planet_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_missions_owner ON fleet_missions(owner_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_missions_arrive ON fleet_missions(arrive_tick, status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_missions_target ON fleet_missions(target_planet_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_build_planet ON build_queue(planet_id, status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_combat_tick ON combat_log(tick_number)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_systems_hex ON solar_systems(hex_q, hex_r)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_honor_pair ON honor_awards(from_user_id, to_user_id)")


def downgrade() -> None:
    # Drop in reverse dependency order
    for tbl in [
        "notifications", "tick_log", "honor_awards", "fp_posts", "fp_threads",
        "direct_messages", "ambassadors", "combat_log", "fleet_mission_ships",
        "fleet_missions", "build_queue", "ships", "ship_stats", "planets",
        "system_routes", "solar_systems", "alliance_members", "alliances",
        "game_round", "email_verifications", "invitations", "users",
    ]:
        op.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")
    for enum in [
        "build_status", "honor_mark", "blockade_status", "mission_status",
        "mission_type", "ship_type", "planet_type", "game_status", "user_role",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum} CASCADE")
