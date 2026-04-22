package domain

import (
	"time"

	"github.com/google/uuid"
)

type ChannelType string

const (
	ChannelVoice   ChannelType = "voice"
	ChannelSMS     ChannelType = "sms"
	ChannelEmail   ChannelType = "email"
	ChannelWebChat ChannelType = "web_chat"
)

type SessionState string

const (
	StateGreeting           SessionState = "greeting"
	StateQualifying         SessionState = "qualifying"
	StatePropertyDiscussion SessionState = "property_discussion"
	StateScheduling         SessionState = "scheduling"
	StateOfferDiscussion    SessionState = "offer_discussion"
	StateHandoffToHuman     SessionState = "handoff_to_human"
	StateClosed             SessionState = "closed"
)

type ProductPath string

const (
	PathInstantOffer      ProductPath = "instant_offer"
	PathListingBoost       ProductPath = "listing_boost"
	PathAgentReferral ProductPath = "agent_referral"
)

type IntentTier string

const (
	TierHighIntent   IntentTier = "high_intent"
	TierMediumIntent IntentTier = "medium_intent"
	TierLookyLoo     IntentTier = "looky_loo"
)

type Session struct {
	ID              uuid.UUID
	LeadID          uuid.UUID
	Channel         ChannelType
	State           SessionState
	Context         map[string]string
	AssignedAgentID *uuid.UUID
	CreatedAt       time.Time
	LastActivity    time.Time
	ExpiredAt       *time.Time
}

type Lead struct {
	ID                     uuid.UUID
	ExternalID             string
	Phone                  string
	Email                  string
	Name                   string
	QualificationScore     float64
	IntentTier             IntentTier
	RecommendedPath        ProductPath
	BuyerAgreementSigned   bool
	BuyerAgreementSignedAt *time.Time
	CreatedAt              time.Time
	UpdatedAt              time.Time
}

type IntentSignal struct {
	ID         uuid.UUID
	LeadID     uuid.UUID
	SessionID  uuid.UUID
	SignalType string
	Value      string
	Strength   float64
	CreatedAt  time.Time
}

type InboundMessage struct {
	SessionID string
	Content   string
	Sender    string
	Channel   ChannelType
	Metadata  map[string]string
}

type OutboundMessage struct {
	SessionID string
	Content   string
	Channel   ChannelType
	ClaimIDs  []string
	Metadata  map[string]string
}

type RoutingDecision struct {
	ID                   uuid.UUID
	LeadID               uuid.UUID
	SessionID            uuid.UUID
	PropertyID           *uuid.UUID
	SelectedPath         ProductPath
	ExpectedValue        int64
	Rationale            string
	RequiresHumanHandoff bool
	CreatedAt            time.Time
}
