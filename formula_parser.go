package main

import (
	"fmt"
	"math"
	"strconv"
	"strings"
	"unicode"
)

type formulaTokenKind int

const (
	formulaEOF formulaTokenKind = iota
	formulaNumber
	formulaIdentifier
	formulaPlus
	formulaMinus
	formulaMultiply
	formulaDivide
	formulaLeftParen
	formulaRightParen
)

type formulaToken struct {
	kind formulaTokenKind
	text string
}

type formulaNode struct {
	kind  string
	value string
	left  *formulaNode
	right *formulaNode
}

func lexFormula(input string) ([]formulaToken, error) {
	if strings.TrimSpace(input) == "" {
		return nil, validationError("EMPTY_FORMULA", "formula", "formula is required")
	}
	if len(input) > TPRMaxFormulaLength {
		return nil, validationError("FORMULA_TOO_LONG", "formula", "formula exceeds 1000 characters")
	}
	tokens := []formulaToken{}
	for i := 0; i < len(input); {
		r := rune(input[i])
		if unicode.IsSpace(r) {
			i++
			continue
		}
		switch input[i] {
		case '+':
			tokens = append(tokens, formulaToken{formulaPlus, "+"})
			i++
			continue
		case '-':
			tokens = append(tokens, formulaToken{formulaMinus, "-"})
			i++
			continue
		case '*':
			tokens = append(tokens, formulaToken{formulaMultiply, "*"})
			i++
			continue
		case '/':
			tokens = append(tokens, formulaToken{formulaDivide, "/"})
			i++
			continue
		case '(':
			tokens = append(tokens, formulaToken{formulaLeftParen, "("})
			i++
			continue
		case ')':
			tokens = append(tokens, formulaToken{formulaRightParen, ")"})
			i++
			continue
		}
		if (input[i] >= '0' && input[i] <= '9') || input[i] == '.' {
			start := i
			dots := 0
			for i < len(input) && ((input[i] >= '0' && input[i] <= '9') || input[i] == '.') {
				if input[i] == '.' {
					dots++
				}
				i++
			}
			raw := input[start:i]
			if dots > 1 || raw == "." {
				return nil, validationError("INVALID_FORMULA_TOKEN", "formula", fmt.Sprintf("invalid numeric literal %q", raw))
			}
			f, err := strconv.ParseFloat(raw, 64)
			if err != nil || math.IsInf(f, 0) || math.IsNaN(f) {
				return nil, validationError("NUMERIC_OVERFLOW", "formula", "numeric literal is not finite")
			}
			tokens = append(tokens, formulaToken{formulaNumber, raw})
			continue
		}
		if (input[i] >= 'A' && input[i] <= 'Z') || (input[i] >= 'a' && input[i] <= 'z') || input[i] == '_' {
			start := i
			for i < len(input) {
				c := input[i]
				if (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_' || c == '.' {
					i++
					continue
				}
				break
			}
			tokens = append(tokens, formulaToken{formulaIdentifier, input[start:i]})
			continue
		}
		return nil, validationError("INVALID_FORMULA_TOKEN", "formula", fmt.Sprintf("unsupported character %q", input[i]))
	}
	tokens = append(tokens, formulaToken{formulaEOF, ""})
	return tokens, nil
}

type formulaParser struct {
	tokens  []formulaToken
	pos     int
	catalog map[string]TPRFieldReference
	depth   int
}

func parseFormula(input string, catalog map[string]TPRFieldReference) (*formulaNode, error) {
	tokens, err := lexFormula(input)
	if err != nil {
		return nil, err
	}
	p := &formulaParser{tokens: tokens, catalog: catalog}
	node, err := p.expression()
	if err != nil {
		return nil, err
	}
	if p.peek().kind != formulaEOF {
		return nil, validationError("INVALID_FORMULA", "formula", "unexpected trailing token")
	}
	if _, zero, constant := formulaConstant(node); constant && zero && node.kind == "divide" {
		return nil, validationError("DIVISION_BY_ZERO", "formula", "division by zero is not allowed")
	}
	return node, nil
}
func (p *formulaParser) peek() formulaToken { return p.tokens[p.pos] }
func (p *formulaParser) take() formulaToken { t := p.peek(); p.pos++; return t }
func (p *formulaParser) expression() (*formulaNode, error) {
	left, err := p.term()
	if err != nil {
		return nil, err
	}
	for p.peek().kind == formulaPlus || p.peek().kind == formulaMinus {
		op := p.take()
		right, err := p.term()
		if err != nil {
			return nil, err
		}
		kind := "add"
		if op.kind == formulaMinus {
			kind = "subtract"
		}
		left = &formulaNode{kind: kind, left: left, right: right}
	}
	return left, nil
}
func (p *formulaParser) term() (*formulaNode, error) {
	left, err := p.unary()
	if err != nil {
		return nil, err
	}
	for p.peek().kind == formulaMultiply || p.peek().kind == formulaDivide {
		op := p.take()
		right, err := p.unary()
		if err != nil {
			return nil, err
		}
		kind := "multiply"
		if op.kind == formulaDivide {
			kind = "divide"
			if _, zero, constant := formulaConstant(right); constant && zero {
				return nil, validationError("DIVISION_BY_ZERO", "formula", "constant zero divisor is not allowed")
			}
		}
		left = &formulaNode{kind: kind, left: left, right: right}
	}
	return left, nil
}
func (p *formulaParser) unary() (*formulaNode, error) {
	if p.peek().kind == formulaPlus {
		p.take()
		return p.unary()
	}
	if p.peek().kind == formulaMinus {
		p.take()
		n, err := p.unary()
		if err != nil {
			return nil, err
		}
		return &formulaNode{kind: "negate", left: n}, nil
	}
	return p.primary()
}
func (p *formulaParser) primary() (*formulaNode, error) {
	t := p.take()
	switch t.kind {
	case formulaNumber:
		return &formulaNode{kind: "number", value: t.text}, nil
	case formulaIdentifier:
		ref, ok := p.catalog[t.text]
		if !ok {
			return nil, validationError("UNKNOWN_FORMULA_IDENTIFIER", "formula", "formula identifier is not in field catalog")
		}
		if ref.DataType != "numeric" {
			return nil, validationError("NON_NUMERIC_FORMULA_IDENTIFIER", "formula", "formula identifiers must be numeric")
		}
		return &formulaNode{kind: "field", value: t.text}, nil
	case formulaLeftParen:
		p.depth++
		if p.depth > TPRMaxFormulaDepth {
			return nil, validationError("MAX_FORMULA_DEPTH", "formula", "formula nesting exceeds limit")
		}
		n, err := p.expression()
		if err != nil {
			return nil, err
		}
		if p.peek().kind != formulaRightParen {
			return nil, validationError("INVALID_FORMULA", "formula", "unbalanced parentheses")
		}
		p.take()
		p.depth--
		return n, nil
	default:
		return nil, validationError("INVALID_FORMULA", "formula", "operand expected")
	}
}

func formulaConstant(n *formulaNode) (value float64, zero bool, constant bool) {
	if n == nil {
		return 0, false, false
	}
	switch n.kind {
	case "number":
		v, err := strconv.ParseFloat(n.value, 64)
		return v, v == 0, err == nil
	case "negate":
		v, _, ok := formulaConstant(n.left)
		return -v, v == 0, ok
	case "add", "subtract", "multiply", "divide":
		a, _, aok := formulaConstant(n.left)
		b, bzero, bok := formulaConstant(n.right)
		if !aok || !bok {
			return 0, false, false
		}
		switch n.kind {
		case "add":
			a += b
		case "subtract":
			a -= b
		case "multiply":
			a *= b
		case "divide":
			if bzero {
				return 0, true, true
			}
			a /= b
		}
		return a, a == 0, true
	}
	return 0, false, false
}

func emitFormulaGRL(n *formulaNode) (string, error) {
	if n == nil {
		return "", fmt.Errorf("nil formula")
	}
	switch n.kind {
	case "number":
		return n.value, nil
	case "field":
		return safeGRLField(n.value)
	case "negate":
		v, e := emitFormulaGRL(n.left)
		return "(-" + v + ")", e
	case "add", "subtract", "multiply", "divide":
		a, e := emitFormulaGRL(n.left)
		if e != nil {
			return "", e
		}
		b, e := emitFormulaGRL(n.right)
		if e != nil {
			return "", e
		}
		op := map[string]string{"add": "+", "subtract": "-", "multiply": "*", "divide": "/"}[n.kind]
		return "(" + a + " " + op + " " + b + ")", nil
	}
	return "", fmt.Errorf("unknown formula AST node")
}

func safeGRLField(key string) (string, error) {
	if mapped, ok := fieldAliases[key]; ok {
		return mapped, nil
	}
	parts := strings.SplitN(key, ".", 2)
	if len(parts) != 2 {
		return "", validationError("UNKNOWN_FIELD", "field", "invalid field reference")
	}
	name := normalizeDynamicFactKey(parts[1])
	if name == "" {
		return "", validationError("UNKNOWN_FIELD", "field", "non-canonical field reference")
	}
	switch parts[0] {
	case "rates":
		if name != parts[1] {
			return "", validationError("UNKNOWN_FIELD", "field", "rate reference must use canonical lowercase")
		}
		return fmt.Sprintf("rates.Value(%q)", name), nil
	case "components":
		return fmt.Sprintf("components.Value(%q)", name), nil
	}
	return "", validationError("UNKNOWN_FIELD", "field", "field has no safe GRL mapping")
}
