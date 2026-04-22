package compliance

import (
	"context"
	"testing"

	"github.com/yashkuceriya/hearth/internal/domain"
	"go.uber.org/zap"
)

type mockLawyerClient struct {
	fhCompliant      bool
	outboundApproved bool
}

func (m *mockLawyerClient) CheckOutboundMessage(ctx context.Context, sessionID, text, channel string, claimIDs []string) (*ComplianceResult, error) {
	return &ComplianceResult{
		Approved:       m.outboundApproved,
		BlockedReasons: nil,
	}, nil
}

func (m *mockLawyerClient) CheckFairHousing(ctx context.Context, text, channel, sessionID string) (*FairHousingResult, error) {
	return &FairHousingResult{
		Compliant: m.fhCompliant,
	}, nil
}

func TestGateway_ApproveCleanMessage(t *testing.T) {
	gw := NewGateway(&mockLawyerClient{fhCompliant: true, outboundApproved: true}, zap.NewNop())
	msg := &domain.OutboundMessage{
		SessionID: "s1",
		Content:   "This is a clean message about a property.",
		Channel:   domain.ChannelSMS,
	}
	err := gw.Check(context.Background(), msg)
	if err != nil {
		t.Fatalf("expected approval, got error: %v", err)
	}
}

func TestGateway_BlockFairHousingViolation(t *testing.T) {
	gw := NewGateway(&mockLawyerClient{fhCompliant: false, outboundApproved: true}, zap.NewNop())
	msg := &domain.OutboundMessage{
		SessionID: "s2",
		Content:   "violating content",
		Channel:   domain.ChannelSMS,
	}
	err := gw.Check(context.Background(), msg)
	if err == nil {
		t.Fatal("expected error for Fair Housing violation")
	}
}

func TestGateway_BlockUnapprovedOutbound(t *testing.T) {
	gw := NewGateway(&mockLawyerClient{fhCompliant: true, outboundApproved: false}, zap.NewNop())
	msg := &domain.OutboundMessage{
		SessionID: "s3",
		Content:   "message with stale claims",
		Channel:   domain.ChannelEmail,
	}
	err := gw.Check(context.Background(), msg)
	if err == nil {
		t.Fatal("expected error for unapproved outbound message")
	}
}

func TestGateway_NilLawyerPassesThrough(t *testing.T) {
	gw := NewGateway(nil, zap.NewNop())
	msg := &domain.OutboundMessage{
		SessionID: "s4",
		Content:   "test",
		Channel:   domain.ChannelWebChat,
	}
	err := gw.Check(context.Background(), msg)
	if err != nil {
		t.Fatalf("nil lawyer should pass through in dev mode, got: %v", err)
	}
}
