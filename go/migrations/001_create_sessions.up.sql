CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TYPE channel_type AS ENUM ('voice', 'sms', 'email', 'web_chat');
CREATE TYPE session_state AS ENUM (
    'greeting', 'qualifying', 'property_discussion',
    'scheduling', 'offer_discussion', 'handoff_to_human', 'closed'
);

CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID NOT NULL,
    channel channel_type NOT NULL,
    state session_state NOT NULL DEFAULT 'greeting',
    context JSONB NOT NULL DEFAULT '{}',
    assigned_agent_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_activity TIMESTAMPTZ NOT NULL DEFAULT now(),
    expired_at TIMESTAMPTZ
);

CREATE INDEX idx_sessions_lead_id ON sessions(lead_id);
CREATE INDEX idx_sessions_active ON sessions(last_activity) WHERE expired_at IS NULL;
