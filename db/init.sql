-- ============================================================
-- Forente Planeter — Database Schema
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Enums ────────────────────────────────────────────────────

CREATE TYPE user_role AS ENUM ('superadmin', 'admin', 'elder_race', 'player');
CREATE TYPE game_status AS ENUM ('lobby', 'active', 'ended');
CREATE TYPE planet_type AS ENUM ('home', 'neighbor', 'npc', 'elder_race');
CREATE TYPE ship_type AS ENUM ('fighter', 'cruiser', 'bomber', 'planet_defense', 'expedition', 'transport', 'diplomat');
CREATE TYPE mission_type AS ENUM ('attack', 'transport', 'expedition', 'diplomacy', 'return');
CREATE TYPE mission_status AS ENUM ('in_flight', 'arrived', 'returning', 'completed', 'cancelled');
CREATE TYPE blockade_status AS ENUM ('none', 'blockaded');
CREATE TYPE honor_mark AS ENUM ('honored', 'betrayed');
CREATE TYPE build_status AS ENUM ('queued', 'building', 'completed', 'cancelled');

-- ── Game round ───────────────────────────────────────────────

CREATE TABLE game_round (
    id              SERIAL PRIMARY KEY,
    status          game_status NOT NULL DEFAULT 'lobby',
    current_tick    INT NOT NULL DEFAULT 0,
    duration_days   INT NOT NULL DEFAULT 30,
    started_at      TIMESTAMPTZ,
    ends_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Users ────────────────────────────────────────────────────

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username        VARCHAR(32) UNIQUE NOT NULL,
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    role            user_role NOT NULL DEFAULT 'player',
    totp_secret     TEXT,                          -- for superadmin 2FA
    honor_points    INT NOT NULL DEFAULT 0,
    honor_from_trade    INT NOT NULL DEFAULT 0,
    honor_from_deals    INT NOT NULL DEFAULT 0,
    betrayals_marked    INT NOT NULL DEFAULT 0,
    fp_member       BOOLEAN NOT NULL DEFAULT FALSE, -- unlocked after first inter-system ship
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login      TIMESTAMPTZ
);

-- ── Honor rank (computed, stored for display) ────────────────

CREATE OR REPLACE FUNCTION honor_rank(points INT) RETURNS TEXT AS $$
BEGIN
    RETURN CASE
        WHEN points >= 100 THEN 'Galactic Elder'
        WHEN points >= 50  THEN 'Diplomat'
        WHEN points >= 25  THEN 'Trusted'
        WHEN points >= 10  THEN 'Reliable'
        ELSE 'Unknown'
    END;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ── Alliances ────────────────────────────────────────────────

CREATE TABLE alliances (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(64) UNIQUE NOT NULL,
    tag             VARCHAR(8) UNIQUE NOT NULL,
    leader_id       UUID NOT NULL REFERENCES users(id),
    founded_tick    INT NOT NULL DEFAULT 0,
    is_public       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE alliance_members (
    alliance_id     UUID NOT NULL REFERENCES alliances(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    joined_tick     INT NOT NULL DEFAULT 0,
    PRIMARY KEY (alliance_id, user_id)
);

-- ── Galaxy / Solar systems ───────────────────────────────────

CREATE TABLE solar_systems (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(64) NOT NULL,
    hex_q           INT NOT NULL,              -- axial hex coordinate q
    hex_r           INT NOT NULL,              -- axial hex coordinate r
    owner_id        UUID REFERENCES users(id), -- NULL = NPC system
    is_npc          BOOLEAN NOT NULL DEFAULT FALSE,
    is_elder_race   BOOLEAN NOT NULL DEFAULT FALSE,
    is_unknown_region BOOLEAN NOT NULL DEFAULT FALSE, -- "Do not pass beyond"
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (hex_q, hex_r)
);

-- ── Inter-system routes ──────────────────────────────────────

CREATE TABLE system_routes (
    id              SERIAL PRIMARY KEY,
    from_system_id  UUID NOT NULL REFERENCES solar_systems(id),
    to_system_id    UUID NOT NULL REFERENCES solar_systems(id),
    travel_ticks    INT NOT NULL DEFAULT 6,    -- always 6 for normal, 1 for diplomat
    CHECK (from_system_id != to_system_id)
);

-- ── Planets ──────────────────────────────────────────────────

CREATE TABLE planets (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    solar_system_id UUID NOT NULL REFERENCES solar_systems(id),
    name            VARCHAR(64) NOT NULL,
    planet_type     planet_type NOT NULL,
    owner_id        UUID REFERENCES users(id), -- NULL = unoccupied NPC neighbor
    orbit_slot      SMALLINT NOT NULL,          -- 0=home, 1-3=neighbors
    travel_ticks    SMALLINT NOT NULL DEFAULT 0, -- ticks from home planet (2-4)
    blockade_status blockade_status NOT NULL DEFAULT 'none',

    -- Resources in bank
    metal           BIGINT NOT NULL DEFAULT 0,
    energy          BIGINT NOT NULL DEFAULT 0,
    gas             BIGINT NOT NULL DEFAULT 0,

    -- Production per tick
    metal_production    INT NOT NULL DEFAULT 0,
    energy_production   INT NOT NULL DEFAULT 0,
    gas_production      INT NOT NULL DEFAULT 0,

    -- Score
    score           BIGINT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Ships ────────────────────────────────────────────────────

CREATE TABLE ships (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_id        UUID NOT NULL REFERENCES users(id),
    planet_id       UUID REFERENCES planets(id), -- NULL = in transit
    ship_type       ship_type NOT NULL,
    quantity        INT NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Ship type stats (reference table) ───────────────────────

CREATE TABLE ship_stats (
    ship_type       ship_type PRIMARY KEY,
    attack          INT NOT NULL DEFAULT 0,
    defense         INT NOT NULL DEFAULT 0,
    travel_modifier FLOAT NOT NULL DEFAULT 1.0,  -- expedition = 0.5
    cargo_capacity  INT NOT NULL DEFAULT 0,       -- transport = 10000
    is_immune       BOOLEAN NOT NULL DEFAULT FALSE, -- diplomat = true
    is_mobile       BOOLEAN NOT NULL DEFAULT TRUE,  -- planet_defense = false
    dies_first      BOOLEAN NOT NULL DEFAULT FALSE, -- transport = true
    dies_last       BOOLEAN NOT NULL DEFAULT FALSE, -- expedition = true
    build_ticks     INT NOT NULL DEFAULT 1,
    cost_metal      INT NOT NULL DEFAULT 0,
    cost_energy     INT NOT NULL DEFAULT 0,
    cost_gas        INT NOT NULL DEFAULT 0,
    unlock_condition TEXT                           -- e.g. 'first_intersystem_travel'
);

INSERT INTO ship_stats VALUES
--  type              atk  def  travel  cargo   immune  mobile  dies1st  dieslst  ticks  metal  energy  gas  unlock
('fighter',            10,   3,  1.0,      0,  FALSE,  TRUE,   FALSE,   FALSE,     2,    50,     20,   10,  NULL),
('cruiser',             6,  12,  1.0,      0,  FALSE,  TRUE,   FALSE,   FALSE,     4,   120,     30,   20,  NULL),
('bomber',             20,   1,  1.0,      0,  FALSE,  TRUE,   FALSE,   FALSE,     3,    40,    150,   20,  NULL),
('planet_defense',      1,  20,  0.0,      0,  FALSE,  FALSE,  FALSE,   FALSE,     5,    60,     20,  120,  NULL),
('transport',           0,  30,  1.0,  10000,  FALSE,  TRUE,   TRUE,    FALSE,     4,   200,     40,   30,  NULL),
('expedition',          0,   0,  0.5,      0,  FALSE,  TRUE,   FALSE,   TRUE,      6,    80,    100,   60,  NULL),
('diplomat',            0,   0,  0.167,    0,  TRUE,   TRUE,   FALSE,   FALSE,     8,   100,    150,   80,  'first_intersystem_travel');
-- diplomat travel modifier: 1/6 = ~0.167 (6x speed = 1 tick between systems)

-- ── Build queue ──────────────────────────────────────────────

CREATE TABLE build_queue (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    planet_id       UUID NOT NULL REFERENCES planets(id) ON DELETE CASCADE,
    owner_id        UUID NOT NULL REFERENCES users(id),
    ship_type       ship_type NOT NULL,
    quantity        INT NOT NULL DEFAULT 1,
    ticks_remaining INT NOT NULL,
    ticks_total     INT NOT NULL,
    status          build_status NOT NULL DEFAULT 'queued',
    queue_position  INT NOT NULL DEFAULT 1,
    -- Resources locked at time of order
    metal_cost      INT NOT NULL DEFAULT 0,
    energy_cost     INT NOT NULL DEFAULT 0,
    gas_cost        INT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Fleet missions ───────────────────────────────────────────

CREATE TABLE fleet_missions (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_id            UUID NOT NULL REFERENCES users(id),
    origin_planet_id    UUID NOT NULL REFERENCES planets(id),
    target_planet_id    UUID NOT NULL REFERENCES planets(id),
    mission_type        mission_type NOT NULL,
    status              mission_status NOT NULL DEFAULT 'in_flight',
    depart_tick         INT NOT NULL,
    arrive_tick         INT NOT NULL,
    return_tick         INT,
    -- Cargo (transport missions)
    cargo_metal         BIGINT NOT NULL DEFAULT 0,
    cargo_energy        BIGINT NOT NULL DEFAULT 0,
    cargo_gas           BIGINT NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Ships assigned to a mission
CREATE TABLE fleet_mission_ships (
    mission_id      UUID NOT NULL REFERENCES fleet_missions(id) ON DELETE CASCADE,
    ship_type       ship_type NOT NULL,
    quantity        INT NOT NULL,
    PRIMARY KEY (mission_id, ship_type)
);

-- ── Combat log ───────────────────────────────────────────────

CREATE TABLE combat_log (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tick_number         INT NOT NULL,
    planet_id           UUID NOT NULL REFERENCES planets(id),
    attacker_id         UUID NOT NULL REFERENCES users(id),
    defender_id         UUID REFERENCES users(id),  -- NULL = NPC
    attacker_won        BOOLEAN NOT NULL,
    attacker_atk_total  INT NOT NULL,
    defender_atk_total  INT NOT NULL,
    planet_changed_owner BOOLEAN NOT NULL DEFAULT FALSE,
    losses_json         JSONB NOT NULL DEFAULT '{}', -- {attacker: {fighter: N}, defender: {}}
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Ambassadors / Diplomacy ──────────────────────────────────

CREATE TABLE ambassadors (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    from_user_id        UUID NOT NULL REFERENCES users(id),
    to_user_id          UUID NOT NULL REFERENCES users(id),
    -- Ambassador always lands on home planet of to_user
    home_planet_id      UUID NOT NULL REFERENCES planets(id),
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    opened_tick         INT NOT NULL,
    closed_tick         INT,
    CHECK (from_user_id != to_user_id)
);

-- Direct messages via ambassadors
CREATE TABLE direct_messages (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ambassador_id   UUID NOT NULL REFERENCES ambassadors(id) ON DELETE CASCADE,
    sender_id       UUID NOT NULL REFERENCES users(id),
    content         TEXT NOT NULL,
    sent_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Forente Planetsystem (FP) ────────────────────────────────

CREATE TABLE fp_threads (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    author_id       UUID NOT NULL REFERENCES users(id),
    title           VARCHAR(128) NOT NULL,
    category        VARCHAR(32) NOT NULL DEFAULT 'general', -- general | crisis | proposal | trade
    is_open         BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE fp_posts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    thread_id       UUID NOT NULL REFERENCES fp_threads(id) ON DELETE CASCADE,
    author_id       UUID NOT NULL REFERENCES users(id),
    content         TEXT NOT NULL,
    is_agreement    BOOLEAN NOT NULL DEFAULT FALSE, -- marked as binding agreement
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Honor system ─────────────────────────────────────────────

CREATE TABLE honor_awards (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    from_user_id    UUID NOT NULL REFERENCES users(id),
    to_user_id      UUID NOT NULL REFERENCES users(id),
    source_type     VARCHAR(16) NOT NULL, -- 'trade' | 'deal'
    source_id       UUID NOT NULL,        -- fleet_mission id or fp_post id
    mark            honor_mark NOT NULL DEFAULT 'honored',
    awarded_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Cooldown: max 1 award per pair per 24 ticks enforced in app logic
    CHECK (from_user_id != to_user_id)
);

-- ── Tick log ─────────────────────────────────────────────────

CREATE TABLE tick_log (
    id                  SERIAL PRIMARY KEY,
    tick_number         INT NOT NULL UNIQUE,
    round_id            INT REFERENCES game_round(id),
    started_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at            TIMESTAMPTZ,
    planets_processed   INT NOT NULL DEFAULT 0,
    missions_resolved   INT NOT NULL DEFAULT 0,
    combats_resolved    INT NOT NULL DEFAULT 0,
    status              VARCHAR(16) NOT NULL DEFAULT 'running' -- running | completed | failed
);

-- ── Notifications ────────────────────────────────────────────

CREATE TABLE notifications (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type            VARCHAR(32) NOT NULL, -- 'attack_incoming' | 'ambassador_arrived' | 'blockade' | etc
    title           VARCHAR(128) NOT NULL,
    body            TEXT,
    is_read         BOOLEAN NOT NULL DEFAULT FALSE,
    related_id      UUID,                -- optional FK to related entity
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Indexes ──────────────────────────────────────────────────

CREATE INDEX idx_planets_owner       ON planets(owner_id);
CREATE INDEX idx_planets_system      ON planets(solar_system_id);
CREATE INDEX idx_ships_owner         ON ships(owner_id);
CREATE INDEX idx_ships_planet        ON ships(planet_id);
CREATE INDEX idx_missions_owner      ON fleet_missions(owner_id);
CREATE INDEX idx_missions_arrive     ON fleet_missions(arrive_tick, status);
CREATE INDEX idx_missions_target     ON fleet_missions(target_planet_id);
CREATE INDEX idx_build_planet        ON build_queue(planet_id, status);
CREATE INDEX idx_notifications_user  ON notifications(user_id, is_read);
CREATE INDEX idx_combat_tick         ON combat_log(tick_number);
CREATE INDEX idx_systems_hex         ON solar_systems(hex_q, hex_r);
CREATE INDEX idx_honor_pair          ON honor_awards(from_user_id, to_user_id);

-- ── Missing columns added post-init ──────────────────────────
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS invited_by UUID REFERENCES users(id);
ALTER TABLE users ADD COLUMN IF NOT EXISTS invites_remaining INT NOT NULL DEFAULT 100;

CREATE TABLE IF NOT EXISTS invitations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    token           UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    invited_by      UUID NOT NULL REFERENCES users(id),
    invited_email   VARCHAR(255),
    used_by         UUID REFERENCES users(id),
    used_at         TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ NOT NULL,
    reward_applied  BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS email_verifications (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id),
    token           UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    expires_at      TIMESTAMPTZ NOT NULL,
    verified_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
