CREATE TABLE IF NOT EXISTS boards (
    id          SERIAL PRIMARY KEY,
    slug        VARCHAR(10) UNIQUE NOT NULL,   -- "g", "a", "b"
    name        TEXT NOT NULL,
    description TEXT,
    nsfw        BOOLEAN DEFAULT false,
    max_threads INT DEFAULT 150,           -- thread massimi prima del pruning
    bump_limit  INT DEFAULT 500            -- dopo N reply il thread smette di bumpare
);

CREATE TABLE IF NOT EXISTS threads (
    id          SERIAL PRIMARY KEY,
    board_id    INT NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
    subject     TEXT,
    locked      BOOLEAN DEFAULT false,
    pinned      BOOLEAN DEFAULT false,     -- thread in cima sempre
    bump_at     TIMESTAMPTZ DEFAULT NOW(), -- usato per ordinare il catalog
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    reply_count INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS posts (
    id          BIGSERIAL PRIMARY KEY,
    thread_id   INT NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
    board_id    INT NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
    name        TEXT DEFAULT 'Anonymous',
    tripcode    TEXT,
    content     TEXT,
    ip_hash     VARCHAR(64) NOT NULL,
    is_op       BOOLEAN DEFAULT false,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    removed_at  TIMESTAMPTZ DEFAULT NULL,
    removal_reason TEXT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS post_files (
    id            SERIAL PRIMARY KEY,
    post_id       BIGINT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    original_name TEXT NOT NULL,
    storage_key   TEXT NOT NULL,
    thumb_key     TEXT NOT NULL,
    width         INT,
    height        INT,
    size_bytes    INT,
    mime_type     VARCHAR(64),
    spoiler       BOOLEAN DEFAULT false
);

CREATE TABLE IF NOT EXISTS bans (
    id         SERIAL PRIMARY KEY,
    board_id   INT REFERENCES boards(id) ON DELETE CASCADE, -- NULL = ban globale
    ip_hash    VARCHAR(64) NOT NULL,
    reason     TEXT,
    expires_at TIMESTAMPTZ, -- NULL = permanente
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS reports (
    id         SERIAL PRIMARY KEY,
    post_id    BIGINT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    reason     TEXT,
    status     VARCHAR(16) DEFAULT 'pending', -- pending | reviewed | dismissed
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_threads_catalog ON threads(board_id, bump_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_thread_view ON posts(thread_id, id ASC);
CREATE INDEX IF NOT EXISTS idx_bans_check ON bans(ip_hash, expires_at);
