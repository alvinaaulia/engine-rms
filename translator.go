package main

func operatorMap(op string) string {
	switch op {
	case "=":
		return "=="
	case "IN":
		return "in"
	case "NOT_IN":
		return "not in"
	case "CONTAINS":
		return "contains"
	case "==", "!=", ">", ">=", "<", "<=":
		return op
	default:
		return op
	}
}
