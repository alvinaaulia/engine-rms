package main

import "strings"

func calculateSummary(emp Employee, comps []Component, componentTypes map[string]string) Summary {
	add := zeroPayrollDecimal()
	ded := zeroPayrollDecimal()

	for _, c := range comps {
		amount := payrollDecimalFromFloat(c.Amount).Rounded(payrollMoneyScale)
		switch componentTypeForCode(componentTypes, c.Code) {
		case "DEDUCTION":
			ded = ded.Add(amount)
		case "EARNING":
			if isBasicSalaryComponent(c.Code) {
				continue
			}
			add = add.Add(amount)
		}
	}

	basicSalary := payrollDecimalFromFloat(emp.BasicSalary).Rounded(payrollMoneyScale)
	gross := basicSalary.Add(add).Rounded(payrollMoneyScale)
	net := gross.Sub(ded).Rounded(payrollMoneyScale)

	return Summary{
		BasicSalary:     basicSalary.Float64(),
		GrossSalary:     gross.Float64(),
		TotalDeductions: ded.Rounded(payrollMoneyScale).Float64(),
		NetSalary:       net.Float64(),
	}
}

func componentTypeForCode(componentTypes map[string]string, code string) string {
	normalizedCode := strings.ToUpper(strings.TrimSpace(code))
	if normalizedCode == "" {
		return ""
	}

	for key, value := range componentTypes {
		if strings.ToUpper(strings.TrimSpace(key)) == normalizedCode {
			return strings.ToUpper(strings.TrimSpace(value))
		}
	}

	return ""
}

func isBasicSalaryComponent(code string) bool {
	normalized := strings.ToUpper(strings.TrimSpace(code))
	return normalized == "BASIC_SALARY" || normalized == "GAJI_POKOK"
}
