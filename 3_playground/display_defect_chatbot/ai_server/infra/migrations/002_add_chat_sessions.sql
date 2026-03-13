-- ai_server/infra/migrations/002_add_chat_sessions.sql
CREATE TABLE IF NOT EXISTS chat_sessions (
    id                  TEXT PRIMARY KEY,
    title               TEXT NOT NULL DEFAULT '',
    product_id          TEXT NOT NULL DEFAULT '',
    defect_description  TEXT NOT NULL DEFAULT '',
    hypothesis          TEXT NOT NULL DEFAULT '',
    agent_results       JSONB NOT NULL DEFAULT '{}',
    chat_messages       JSONB NOT NULL DEFAULT '[]',
    enabled_agents      JSONB NOT NULL DEFAULT '{}',
    long_term_task_id   TEXT,
    long_term_status    TEXT NOT NULL DEFAULT 'PENDING',
    long_term_result    TEXT,
    final_action_plan   TEXT NOT NULL DEFAULT '',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
