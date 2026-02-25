package version

import (
	"context"
	"os"
	"strconv"
)

type DBProvider struct{}

func NewDBProvider() *DBProvider { return &DBProvider{} }

func (p *DBProvider) ActiveVersion(ctx context.Context) (int, error) {
	// TODO: ganti jadi query DB, misal:
	// SELECT active_version FROM rule_sets WHERE name='payroll' LIMIT 1;

	// Skeleton: pakai ENV ACTIVE_RULE_VERSION
	v := os.Getenv("ACTIVE_RULE_VERSION")
	if v == "" {
		return 1, nil // default
	}
	n, err := strconv.Atoi(v)
	if err != nil {
		return 0, err
	}
	return n, nil
}
