-- ai_server/infra/migrations/003_add_step_hypotheses.sql
ALTER TABLE chat_sessions
    ADD COLUMN IF NOT EXISTS step       TEXT    NOT NULL DEFAULT 'input',
    ADD COLUMN IF NOT EXISTS hypotheses JSONB   NOT NULL DEFAULT '[]';
