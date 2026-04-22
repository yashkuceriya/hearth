package channel

import (
	"context"
	"fmt"
	"net/http"
	"net/url"
	"strings"

	"github.com/yashkuceriya/hearth/internal/domain"
	"go.uber.org/zap"
)

type SMSAdapter struct {
	accountSID string
	authToken  string
	fromNumber string
	inbound    chan *domain.InboundMessage
	logger     *zap.Logger
}

func NewSMSAdapter(accountSID, authToken, fromNumber string, logger *zap.Logger) *SMSAdapter {
	return &SMSAdapter{
		accountSID: accountSID,
		authToken:  authToken,
		fromNumber: fromNumber,
		inbound:    make(chan *domain.InboundMessage, 100),
		logger:     logger,
	}
}

func (a *SMSAdapter) Type() domain.ChannelType {
	return domain.ChannelSMS
}

func (a *SMSAdapter) Send(ctx context.Context, msg *domain.OutboundMessage) error {
	toNumber := msg.Metadata["to_phone"]
	if toNumber == "" {
		return fmt.Errorf("missing to_phone in metadata")
	}

	endpoint := fmt.Sprintf("https://api.twilio.com/2010-04-01/Accounts/%s/Messages.json", a.accountSID)

	data := url.Values{}
	data.Set("To", toNumber)
	data.Set("From", a.fromNumber)
	data.Set("Body", msg.Content)

	req, err := http.NewRequestWithContext(ctx, "POST", endpoint, strings.NewReader(data.Encode()))
	if err != nil {
		return fmt.Errorf("create request: %w", err)
	}
	req.SetBasicAuth(a.accountSID, a.authToken)
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return fmt.Errorf("send SMS: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		return fmt.Errorf("twilio error: status %d", resp.StatusCode)
	}

	a.logger.Info("SMS sent", zap.String("to", toNumber), zap.String("session", msg.SessionID))
	return nil
}

func (a *SMSAdapter) Receive(ctx context.Context) (<-chan *domain.InboundMessage, error) {
	return a.inbound, nil
}

// HandleWebhook processes incoming Twilio webhook requests.
func (a *SMSAdapter) HandleWebhook(from, body, sessionID string) {
	a.inbound <- &domain.InboundMessage{
		SessionID: sessionID,
		Content:   body,
		Sender:    from,
		Channel:   domain.ChannelSMS,
		Metadata:  map[string]string{"from_phone": from},
	}
}
