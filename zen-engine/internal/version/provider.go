package version

import "context"

// Provider mengembalikan versi rules yang sedang aktif (published).
// Misal: 17 -> decisionKey "payroll_v17.jdm.json"
type Provider interface {
	ActiveVersion(ctx context.Context) (int, error)
}
