CREATE TABLE routing_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID NOT NULL REFERENCES leads(id),
    session_id UUID NOT NULL REFERENCES sessions(id),
    property_id UUID,
    selected_path product_path NOT NULL,
    expected_value BIGINT,
    rationale TEXT,
    requires_human_handoff BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_routing_lead ON routing_decisions(lead_id, created_at DESC);

CREATE TABLE interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id),
    direction VARCHAR(10) NOT NULL CHECK (direction IN ('inbound', 'outbound')),
    channel channel_type NOT NULL,
    content TEXT NOT NULL,
    sender VARCHAR(50) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    compliance_check_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_interactions_session ON interactions(session_id, created_at);
