package session

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/yashkuceriya/hearth/internal/domain"
	"go.uber.org/zap"
)

type Manager struct {
	db     *sql.DB
	logger *zap.Logger
}

func NewManager(db *sql.DB, logger *zap.Logger) *Manager {
	return &Manager{db: db, logger: logger}
}

func (m *Manager) Create(ctx context.Context, leadID uuid.UUID, channel domain.ChannelType) (*domain.Session, error) {
	s := &domain.Session{
		ID:           uuid.New(),
		LeadID:       leadID,
		Channel:      channel,
		State:        domain.StateGreeting,
		Context:      make(map[string]string),
		CreatedAt:    time.Now().UTC(),
		LastActivity: time.Now().UTC(),
	}

	ctxJSON, err := json.Marshal(s.Context)
	if err != nil {
		return nil, fmt.Errorf("marshal context: %w", err)
	}

	_, err = m.db.ExecContext(ctx,
		`INSERT INTO sessions (id, lead_id, channel, state, context, created_at, last_activity)
         VALUES ($1, $2, $3, $4, $5, $6, $7)`,
		s.ID, s.LeadID, s.Channel, s.State, ctxJSON, s.CreatedAt, s.LastActivity,
	)
	if err != nil {
		return nil, fmt.Errorf("insert session: %w", err)
	}

	m.logger.Info("session created", zap.String("id", s.ID.String()), zap.String("lead", leadID.String()))
	return s, nil
}

func (m *Manager) Get(ctx context.Context, sessionID uuid.UUID) (*domain.Session, error) {
	s := &domain.Session{}
	var ctxJSON []byte
	var assignedAgent *string
	var expiredAt *time.Time

	err := m.db.QueryRowContext(ctx,
		`SELECT id, lead_id, channel, state, context, assigned_agent_id, created_at, last_activity, expired_at
         FROM sessions WHERE id = $1`, sessionID,
	).Scan(&s.ID, &s.LeadID, &s.Channel, &s.State, &ctxJSON, &assignedAgent, &s.CreatedAt, &s.LastActivity, &expiredAt)
	if err != nil {
		return nil, fmt.Errorf("get session: %w", err)
	}

	if err := json.Unmarshal(ctxJSON, &s.Context); err != nil {
		return nil, fmt.Errorf("unmarshal context: %w", err)
	}
	s.ExpiredAt = expiredAt

	if assignedAgent != nil {
		id, _ := uuid.Parse(*assignedAgent)
		s.AssignedAgentID = &id
	}

	return s, nil
}

func (m *Manager) UpdateState(ctx context.Context, sessionID uuid.UUID, state domain.SessionState) error {
	_, err := m.db.ExecContext(ctx,
		`UPDATE sessions SET state = $1, last_activity = now() WHERE id = $2`,
		state, sessionID,
	)
	return err
}

func (m *Manager) Resume(ctx context.Context, leadID uuid.UUID, channel domain.ChannelType) (*domain.Session, error) {
	s := &domain.Session{}
	var ctxJSON []byte

	err := m.db.QueryRowContext(ctx,
		`SELECT id, lead_id, channel, state, context, created_at, last_activity
         FROM sessions
         WHERE lead_id = $1 AND expired_at IS NULL
         ORDER BY last_activity DESC
         LIMIT 1`, leadID,
	).Scan(&s.ID, &s.LeadID, &s.Channel, &s.State, &ctxJSON, &s.CreatedAt, &s.LastActivity)
	if err == sql.ErrNoRows {
		return m.Create(ctx, leadID, channel)
	}
	if err != nil {
		return nil, fmt.Errorf("resume session: %w", err)
	}

	if err := json.Unmarshal(ctxJSON, &s.Context); err != nil {
		return nil, fmt.Errorf("unmarshal context: %w", err)
	}

	// Update channel if they switched
	if s.Channel != channel {
		s.Channel = channel
		_, _ = m.db.ExecContext(ctx, `UPDATE sessions SET channel = $1, last_activity = now() WHERE id = $2`, channel, s.ID)
	}

	return s, nil
}
