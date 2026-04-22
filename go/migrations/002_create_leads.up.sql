CREATE TYPE product_path AS ENUM ('instant_offer', 'listing_boost', 'agent_referral');
CREATE TYPE intent_tier AS ENUM ('high_intent', 'medium_intent', 'looky_loo');

CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(255),
    phone VARCHAR(20),
    email VARCHAR(255),
    name VARCHAR(255),
    qualification_score DOUBLE PRECISION,
    intent_tier intent_tier,
    recommended_product_path product_path,
    buyer_agreement_signed BOOLEAN NOT NULL DEFAULT FALSE,
    buyer_agreement_signed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE intent_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID NOT NULL REFERENCES leads(id),
    session_id UUID NOT NULL REFERENCES sessions(id),
    signal_type VARCHAR(100) NOT NULL,
    value TEXT NOT NULL,
    strength DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_intent_signals_lead ON intent_signals(lead_id, created_at DESC);
