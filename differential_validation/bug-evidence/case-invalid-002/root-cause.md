# Root cause

The formula fact path was checked for existence, but its runtime scalar type was not validated. An invalid `employee.basic_salary` type was therefore accepted by the reconstructed implementation. The fixed production build calls `validateFormulaFactRuntimeType`; the frozen expected result was unchanged.
