// Package migrate applies SQL migration files to Postgres.
//
// Forward-only. Each file is applied in filename order (001, 002, …). Files
// are resolved via embed.FS so the binary is self-contained. Applied versions
// are recorded in schema_migrations. If a filename starts with a version we've
// already applied, it's skipped; if a file's hash differs from the recorded
// hash, we crash — migrations are immutable once applied.
package migrate

import (
	"crypto/sha256"
	"database/sql"
	"embed"
	"encoding/hex"
	"fmt"
	"io/fs"
	"sort"
	"strings"

	"go.uber.org/zap"
)

type Migration struct {
	Version  string
	Filename string
	SQL      string
	Hash     string
}

// LoadFromFS scans the given embed.FS root directory for *.up.sql files and
// returns them in version order.
func LoadFromFS(efs embed.FS, root string) ([]Migration, error) {
	var out []Migration
	err := fs.WalkDir(efs, root, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() || !strings.HasSuffix(path, ".up.sql") {
			return nil
		}
		body, err := efs.ReadFile(path)
		if err != nil {
			return err
		}
		base := path[strings.LastIndex(path, "/")+1:]
		version := base[:strings.Index(base, "_")]
		h := sha256.Sum256(body)
		out = append(out, Migration{
			Version:  version,
			Filename: base,
			SQL:      string(body),
			Hash:     hex.EncodeToString(h[:]),
		})
		return nil
	})
	if err != nil {
		return nil, err
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Version < out[j].Version })
	return out, nil
}

// Apply runs any migrations not yet recorded in schema_migrations. Idempotent.
func Apply(db *sql.DB, migrations []Migration, logger *zap.Logger) error {
	if _, err := db.Exec(`
		CREATE TABLE IF NOT EXISTS schema_migrations (
			version     text PRIMARY KEY,
			filename    text NOT NULL,
			hash        text NOT NULL,
			applied_at  timestamptz NOT NULL DEFAULT now()
		)
	`); err != nil {
		return fmt.Errorf("create schema_migrations: %w", err)
	}

	applied := map[string]string{}
	rows, err := db.Query(`SELECT version, hash FROM schema_migrations`)
	if err != nil {
		return fmt.Errorf("read schema_migrations: %w", err)
	}
	for rows.Next() {
		var v, h string
		if err := rows.Scan(&v, &h); err != nil {
			rows.Close()
			return err
		}
		applied[v] = h
	}
	rows.Close()

	for _, m := range migrations {
		prev, ok := applied[m.Version]
		if ok {
			if prev != m.Hash {
				return fmt.Errorf("migration %s was modified after apply (hash mismatch)", m.Filename)
			}
			continue
		}
		logger.Info("applying migration", zap.String("file", m.Filename))
		tx, err := db.Begin()
		if err != nil {
			return err
		}
		if _, err := tx.Exec(m.SQL); err != nil {
			tx.Rollback()
			return fmt.Errorf("apply %s: %w", m.Filename, err)
		}
		if _, err := tx.Exec(
			`INSERT INTO schema_migrations (version, filename, hash) VALUES ($1, $2, $3)`,
			m.Version, m.Filename, m.Hash,
		); err != nil {
			tx.Rollback()
			return err
		}
		if err := tx.Commit(); err != nil {
			return err
		}
	}
	return nil
}
