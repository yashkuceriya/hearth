// Package migrations embeds SQL migration files so they travel with the binary.
package migrations

import "embed"

//go:embed *.up.sql
var FS embed.FS
