package main

import "strings"

func calculateSummary(emp Employee, comps []Component) Summary {
	var add float64
	var ded float64

	for _, c := range comps {
		if isDeductionComponent(c.Code) {
			ded += c.Amount
		} else if !isBasicSalaryComponent(c.Code) {
			add += c.Amount
		}
	}

	gross := emp.BasicSalary + add
	net := gross - ded

	return Summary{
		BasicSalary:     emp.BasicSalary,
		GrossSalary:     gross,
		TotalDeductions: ded,
		NetSalary:       net,
	}
}

func isBasicSalaryComponent(code string) bool {
	normalized := strings.ToUpper(strings.TrimSpace(code))
	return normalized == "BASIC_SALARY" || normalized == "GAJI_POKOK"
}

func isDeductionComponent(code string) bool {
	normalized := strings.ToUpper(strings.TrimSpace(code))
	deductionKeywords := []string{
		"DEDUCTION",
		"POTONG",
		"TAX",
		"PPH",
		"BPJS",
		"DENDA",
		"PINJAMAN",
		"LATE",
		"TELAT",
		"TERLAMBAT",
		"UNPAID",
		"TANPA_DIBAYAR",
		"CUTI_TANPA",
	}

	for _, keyword := range deductionKeywords {
		if strings.Contains(normalized, keyword) {
			return true
		}
	}

	return false
}
