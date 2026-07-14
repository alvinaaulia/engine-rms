package main

import (
	"encoding/json"
	"math"
	"math/big"
	"strconv"
	"strings"
)

const payrollMoneyScale int32 = 6

type payrollDecimal struct {
	value *big.Rat
}

func zeroPayrollDecimal() payrollDecimal {
	return payrollDecimal{value: new(big.Rat)}
}

func payrollDecimalFromInterface(value interface{}) (payrollDecimal, bool) {
	switch v := value.(type) {
	case float64:
		if math.IsNaN(v) || math.IsInf(v, 0) {
			return zeroPayrollDecimal(), false
		}
		return payrollDecimalFromString(strconv.FormatFloat(v, 'f', -1, 64))
	case float32:
		f := float64(v)
		if math.IsNaN(f) || math.IsInf(f, 0) {
			return zeroPayrollDecimal(), false
		}
		return payrollDecimalFromString(strconv.FormatFloat(f, 'f', -1, 64))
	case int:
		return payrollDecimalFromString(strconv.FormatInt(int64(v), 10))
	case int8:
		return payrollDecimalFromString(strconv.FormatInt(int64(v), 10))
	case int16:
		return payrollDecimalFromString(strconv.FormatInt(int64(v), 10))
	case int32:
		return payrollDecimalFromString(strconv.FormatInt(int64(v), 10))
	case int64:
		return payrollDecimalFromString(strconv.FormatInt(v, 10))
	case uint:
		return payrollDecimalFromString(strconv.FormatUint(uint64(v), 10))
	case uint8:
		return payrollDecimalFromString(strconv.FormatUint(uint64(v), 10))
	case uint16:
		return payrollDecimalFromString(strconv.FormatUint(uint64(v), 10))
	case uint32:
		return payrollDecimalFromString(strconv.FormatUint(uint64(v), 10))
	case uint64:
		return payrollDecimalFromString(strconv.FormatUint(v, 10))
	case json.Number:
		return payrollDecimalFromString(v.String())
	case string:
		return payrollDecimalFromString(v)
	default:
		return zeroPayrollDecimal(), false
	}
}

func payrollDecimalFromFloat(value float64) payrollDecimal {
	decimal, ok := payrollDecimalFromInterface(value)
	if !ok {
		return zeroPayrollDecimal()
	}
	return decimal
}

func payrollDecimalFromString(value string) (payrollDecimal, bool) {
	trimmed := strings.TrimSpace(value)
	if trimmed == "" {
		return zeroPayrollDecimal(), false
	}

	rat := new(big.Rat)
	if _, ok := rat.SetString(trimmed); !ok {
		return zeroPayrollDecimal(), false
	}

	return payrollDecimal{value: rat}, true
}

func (d payrollDecimal) Add(other payrollDecimal) payrollDecimal {
	return payrollDecimal{value: new(big.Rat).Add(d.value, other.value)}
}

func (d payrollDecimal) Sub(other payrollDecimal) payrollDecimal {
	return payrollDecimal{value: new(big.Rat).Sub(d.value, other.value)}
}

func (d payrollDecimal) Rounded(scale int32) payrollDecimal {
	if d.value == nil {
		return zeroPayrollDecimal()
	}

	factor := new(big.Int).Exp(big.NewInt(10), big.NewInt(int64(scale)), nil)
	scaled := new(big.Rat).Mul(d.value, new(big.Rat).SetInt(factor))
	numerator := new(big.Int).Set(scaled.Num())
	denominator := new(big.Int).Set(scaled.Denom())
	quotient, remainder := new(big.Int).QuoRem(numerator, denominator, new(big.Int))

	if remainder.Sign() != 0 {
		twiceRemainder := new(big.Int).Mul(new(big.Int).Abs(remainder), big.NewInt(2))
		if twiceRemainder.Cmp(denominator) >= 0 {
			if scaled.Sign() >= 0 {
				quotient.Add(quotient, big.NewInt(1))
			} else {
				quotient.Sub(quotient, big.NewInt(1))
			}
		}
	}

	return payrollDecimal{value: new(big.Rat).SetFrac(quotient, factor)}
}

func (d payrollDecimal) Float64() float64 {
	if d.value == nil {
		return 0
	}
	value, _ := d.value.Float64()
	return value
}

func normalizePayrollMoney(value interface{}) (float64, bool) {
	decimal, ok := payrollDecimalFromInterface(value)
	if !ok {
		return 0, false
	}
	return decimal.Rounded(payrollMoneyScale).Float64(), true
}
