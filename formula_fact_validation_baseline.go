//go:build differential_baseline

package main

// This build profile reproduces the pre-remediation validator behavior for the
// auditable baseline experiment. It is never used by the production build.
func validateFormulaFactRuntimeType(_ interface{}, _, _ string) error {
	return nil
}
