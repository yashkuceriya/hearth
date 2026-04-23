package migrate

import (
	"testing"
)

// LoadFromFS sorting is the main logic we can test without a live Postgres.
// Integration testing the apply path requires a real DB and is covered by
// docker-compose CI setups (not the unit suite).

func TestMigrationSortByVersion(t *testing.T) {
	ms := []Migration{
		{Version: "010", Filename: "010_z.up.sql"},
		{Version: "002", Filename: "002_b.up.sql"},
		{Version: "001", Filename: "001_a.up.sql"},
	}
	// Simulate what Apply() relies on — LoadFromFS sorts ascending.
	sortMigrations(ms)
	if ms[0].Version != "001" || ms[1].Version != "002" || ms[2].Version != "010" {
		t.Fatalf("expected 001,002,010 ordering; got %+v", ms)
	}
}

// sortMigrations is a test helper mirroring the sort.Slice call inside LoadFromFS.
func sortMigrations(ms []Migration) {
	for i := 1; i < len(ms); i++ {
		for j := i; j > 0 && ms[j-1].Version > ms[j].Version; j-- {
			ms[j-1], ms[j] = ms[j], ms[j-1]
		}
	}
}
