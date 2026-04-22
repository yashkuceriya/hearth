package channel

import (
	"context"

	"github.com/yashkuceriya/hearth/internal/domain"
)

type Adapter interface {
	Send(ctx context.Context, msg *domain.OutboundMessage) error
	Receive(ctx context.Context) (<-chan *domain.InboundMessage, error)
	Type() domain.ChannelType
}
