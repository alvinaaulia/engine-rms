package main

func operatorMap(op string) string {
	switch op {
	case "=":
		return "=="
	case "==", "!=", ">", ">=", "<", "<=":
		return op
	default:
		return op
	}
}
