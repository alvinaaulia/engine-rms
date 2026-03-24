package main

func calculateSummary(emp Employee, comps []Component) Summary {
	var add int64
	var ded int64

	for _, c := range comps {
		switch c.Code {
		case "OVERTIME_PAY", "ALLOWANCE", "BONUS":
			add += c.Amount
		case "LATE_DEDUCTION", "UNPAID_LEAVE_DEDUCTION", "TAX_DEDUCTION":
			ded += c.Amount
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