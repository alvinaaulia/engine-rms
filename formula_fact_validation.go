//go:build !differential_baseline

package main

func validateFormulaFactRuntimeType(fact interface{}, dataType, path string) error {
	_, err := strictScalar(fact, dataType, path, true)
	return err
}
