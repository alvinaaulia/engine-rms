# Translation Validation Cases

Dokumen ini dibangkitkan dari test Go `TestTranslationValidationFixtures`. Setiap fixture menyimpan TPR-IR canonical, GRL yang dihasilkan, dan hasil eksekusi atau structured rejection. Salinan machine-readable lengkap berada di `translation_validation_fixtures.json`.

| ID | Fokus | Expected | Hasil |
|---|---|---|---|
| `numeric-comparison` | numeric GTE, formula precedence, and HALF_UP rounding | `SUCCESS` | `SUCCESS` |
| `string-comparison` | strict string EQ literal | `SUCCESS` | `SUCCESS` |
| `boolean-comparison` | strict boolean EQ literal | `SUCCESS` | `SUCCESS` |
| `date-comparison` | date BEFORE mapping | `SUCCESS` | `SUCCESS` |
| `membership` | string IN expands to safe comparisons | `SUCCESS` | `SUCCESS` |
| `nested-condition` | nested OR containing an AND group | `SUCCESS` | `SUCCESS` |
| `add-collect-sum` | two ADD candidates aggregate with multi-rule provenance | `SUCCESS` | `SUCCESS` |
| `set-priority` | SET selects highest salience and preserves source rule | `SUCCESS` | `SUCCESS` |
| `first` | FIRST uses priority descending then stable rule ID | `SUCCESS` | `SUCCESS` |
| `unique-conflict` | UNIQUE rejects two matching candidates | `POTENTIAL_UNIQUE_CONFLICT` | `POTENTIAL_UNIQUE_CONFLICT` |
| `invalid-formula` | formula parser rejects an incomplete expression | `INVALID_FORMULA` | `INVALID_FORMULA` |
| `unknown-field` | canonical validator rejects a field absent from the catalog | `UNKNOWN_FIELD` | `UNKNOWN_FIELD` |

## numeric-comparison

numeric GTE, formula precedence, and HALF_UP rounding.

Canonical TPR-IR:

```json
{
  "schema_version": "1.0",
  "ruleset_id": "legacy-adapter",
  "default_hit_policy": "PRIORITY",
  "component_policies": {
    "NUMERIC": "COLLECT_SUM"
  },
  "rounding_policy": {
    "scale": 6,
    "mode": "HALF_UP"
  },
  "rules": [
    {
      "id": "legacy-fa8276b2af6984a2",
      "priority": 50,
      "metadata": {},
      "condition": {
        "kind": "group",
        "operator": "AND",
        "children": [
          {
            "kind": "leaf",
            "operator": "GTE",
            "field": {
              "namespace": "employee",
              "name": "performance_score",
              "data_type": "numeric",
              "nullable": false
            },
            "literal": {
              "type": "numeric",
              "value": 90
            }
          }
        ]
      },
      "actions": [
        {
          "type": "ADD_COMPONENT",
          "target": {
            "code": "NUMERIC"
          },
          "formula": {
            "language": "TPR-EXPR-1.0",
            "expression": "(rates.bonus_rate + 10) * 1.2345675"
          }
        }
      ]
    }
  ]
}
```

Generated GRL:

```text

rule TPR_c9e77d067ac936a0_0 "TPR-IR 1.0" salience 50 {
when
	(employee.PerformanceScore >= 90)
then
	out.Emit("ADD_COMPONENT", "NUMERIC", ((rates.Value("bonus_rate") + 10) * 1.2345675), 50, "legacy-fa8276b2af6984a2", 0, 0);
	Retract("TPR_c9e77d067ac936a0_0");
}

```

Result:

```json
{
  "components": [
    {
      "code": "NUMERIC",
      "amount": 1246.913175,
      "source_rule": 0,
      "source_rule_id": "legacy-fa8276b2af6984a2",
      "source_rule_ids": [
        "legacy-fa8276b2af6984a2"
      ]
    }
  ],
  "summary": {
    "basic_salary": 5000000,
    "gross_salary": 5001246.913175,
    "total_deductions": 0,
    "net_salary": 5001246.913175
  }
}
```

## string-comparison

strict string EQ literal.

Canonical TPR-IR:

```json
{
  "schema_version": "1.0",
  "ruleset_id": "legacy-adapter",
  "default_hit_policy": "PRIORITY",
  "component_policies": {
    "STRING": "COLLECT_SUM"
  },
  "rounding_policy": {
    "scale": 6,
    "mode": "HALF_UP"
  },
  "rules": [
    {
      "id": "legacy-588679beebdc7883",
      "priority": 50,
      "metadata": {},
      "condition": {
        "kind": "group",
        "operator": "AND",
        "children": [
          {
            "kind": "leaf",
            "operator": "EQ",
            "field": {
              "namespace": "employee",
              "name": "status",
              "data_type": "string",
              "nullable": false
            },
            "literal": {
              "type": "string",
              "value": "aktif"
            }
          }
        ]
      },
      "actions": [
        {
          "type": "ADD_COMPONENT",
          "target": {
            "code": "STRING"
          },
          "formula": {
            "language": "TPR-EXPR-1.0",
            "expression": "10"
          }
        }
      ]
    }
  ]
}
```

Generated GRL:

```text

rule TPR_b61209b9afc266d_0 "TPR-IR 1.0" salience 50 {
when
	(employee.Status == "aktif")
then
	out.Emit("ADD_COMPONENT", "STRING", 10, 50, "legacy-588679beebdc7883", 0, 0);
	Retract("TPR_b61209b9afc266d_0");
}

```

Result:

```json
{
  "components": [
    {
      "code": "STRING",
      "amount": 10,
      "source_rule": 0,
      "source_rule_id": "legacy-588679beebdc7883",
      "source_rule_ids": [
        "legacy-588679beebdc7883"
      ]
    }
  ],
  "summary": {
    "basic_salary": 5000000,
    "gross_salary": 5000010,
    "total_deductions": 0,
    "net_salary": 5000010
  }
}
```

## boolean-comparison

strict boolean EQ literal.

Canonical TPR-IR:

```json
{
  "schema_version": "1.0",
  "ruleset_id": "legacy-adapter",
  "default_hit_policy": "PRIORITY",
  "component_policies": {
    "BOOLEAN": "COLLECT_SUM"
  },
  "rounding_policy": {
    "scale": 6,
    "mode": "HALF_UP"
  },
  "rules": [
    {
      "id": "legacy-70a9bcccbfd23bd9",
      "priority": 50,
      "metadata": {},
      "condition": {
        "kind": "group",
        "operator": "AND",
        "children": [
          {
            "kind": "leaf",
            "operator": "EQ",
            "field": {
              "namespace": "employee",
              "name": "annual_bonus_eligible",
              "data_type": "boolean",
              "nullable": false
            },
            "literal": {
              "type": "boolean",
              "value": true
            }
          }
        ]
      },
      "actions": [
        {
          "type": "ADD_COMPONENT",
          "target": {
            "code": "BOOLEAN"
          },
          "formula": {
            "language": "TPR-EXPR-1.0",
            "expression": "20"
          }
        }
      ]
    }
  ]
}
```

Generated GRL:

```text

rule TPR_66d54c4b64d3866f_0 "TPR-IR 1.0" salience 50 {
when
	(employee.Bool("annual_bonus_eligible") == true)
then
	out.Emit("ADD_COMPONENT", "BOOLEAN", 20, 50, "legacy-70a9bcccbfd23bd9", 0, 0);
	Retract("TPR_66d54c4b64d3866f_0");
}

```

Result:

```json
{
  "components": [
    {
      "code": "BOOLEAN",
      "amount": 20,
      "source_rule": 0,
      "source_rule_id": "legacy-70a9bcccbfd23bd9",
      "source_rule_ids": [
        "legacy-70a9bcccbfd23bd9"
      ]
    }
  ],
  "summary": {
    "basic_salary": 5000000,
    "gross_salary": 5000020,
    "total_deductions": 0,
    "net_salary": 5000020
  }
}
```

## date-comparison

date BEFORE mapping.

Canonical TPR-IR:

```json
{
  "schema_version": "1.0",
  "ruleset_id": "legacy-adapter",
  "default_hit_policy": "PRIORITY",
  "component_policies": {
    "DATE": "COLLECT_SUM"
  },
  "rounding_policy": {
    "scale": 6,
    "mode": "HALF_UP"
  },
  "rules": [
    {
      "id": "legacy-e4601e3dc24261af",
      "priority": 50,
      "metadata": {},
      "condition": {
        "kind": "group",
        "operator": "AND",
        "children": [
          {
            "kind": "leaf",
            "operator": "BEFORE",
            "field": {
              "namespace": "employee",
              "name": "join_date",
              "data_type": "date",
              "nullable": false
            },
            "literal": {
              "type": "date",
              "value": "2021-01-01"
            }
          }
        ]
      },
      "actions": [
        {
          "type": "ADD_COMPONENT",
          "target": {
            "code": "DATE"
          },
          "formula": {
            "language": "TPR-EXPR-1.0",
            "expression": "30"
          }
        }
      ]
    }
  ]
}
```

Generated GRL:

```text

rule TPR_9e0cde8aef562d68_0 "TPR-IR 1.0" salience 50 {
when
	(employee.JoinDate < "2021-01-01")
then
	out.Emit("ADD_COMPONENT", "DATE", 30, 50, "legacy-e4601e3dc24261af", 0, 0);
	Retract("TPR_9e0cde8aef562d68_0");
}

```

Result:

```json
{
  "components": [
    {
      "code": "DATE",
      "amount": 30,
      "source_rule": 0,
      "source_rule_id": "legacy-e4601e3dc24261af",
      "source_rule_ids": [
        "legacy-e4601e3dc24261af"
      ]
    }
  ],
  "summary": {
    "basic_salary": 5000000,
    "gross_salary": 5000030,
    "total_deductions": 0,
    "net_salary": 5000030
  }
}
```

## membership

string IN expands to safe comparisons.

Canonical TPR-IR:

```json
{
  "schema_version": "1.0",
  "ruleset_id": "legacy-adapter",
  "default_hit_policy": "PRIORITY",
  "component_policies": {
    "MEMBERSHIP": "COLLECT_SUM"
  },
  "rounding_policy": {
    "scale": 6,
    "mode": "HALF_UP"
  },
  "rules": [
    {
      "id": "legacy-d94c14efdbfed151",
      "priority": 50,
      "metadata": {},
      "condition": {
        "kind": "group",
        "operator": "AND",
        "children": [
          {
            "kind": "leaf",
            "operator": "IN",
            "field": {
              "namespace": "employee",
              "name": "status",
              "data_type": "string",
              "nullable": false
            },
            "literal": {
              "type": "array<string>",
              "value": [
                "aktif",
                "tetap"
              ]
            }
          }
        ]
      },
      "actions": [
        {
          "type": "ADD_COMPONENT",
          "target": {
            "code": "MEMBERSHIP"
          },
          "formula": {
            "language": "TPR-EXPR-1.0",
            "expression": "40"
          }
        }
      ]
    }
  ]
}
```

Generated GRL:

```text

rule TPR_18741fa1c2172625_0 "TPR-IR 1.0" salience 50 {
when
	((employee.Status == "aktif" || employee.Status == "tetap"))
then
	out.Emit("ADD_COMPONENT", "MEMBERSHIP", 40, 50, "legacy-d94c14efdbfed151", 0, 0);
	Retract("TPR_18741fa1c2172625_0");
}

```

Result:

```json
{
  "components": [
    {
      "code": "MEMBERSHIP",
      "amount": 40,
      "source_rule": 0,
      "source_rule_id": "legacy-d94c14efdbfed151",
      "source_rule_ids": [
        "legacy-d94c14efdbfed151"
      ]
    }
  ],
  "summary": {
    "basic_salary": 5000000,
    "gross_salary": 5000040,
    "total_deductions": 0,
    "net_salary": 5000040
  }
}
```

## nested-condition

nested OR containing an AND group.

Canonical TPR-IR:

```json
{
  "schema_version": "1.0",
  "ruleset_id": "legacy-adapter",
  "default_hit_policy": "PRIORITY",
  "component_policies": {
    "NESTED": "COLLECT_SUM"
  },
  "rounding_policy": {
    "scale": 6,
    "mode": "HALF_UP"
  },
  "rules": [
    {
      "id": "legacy-10ff06069fa90df4",
      "priority": 50,
      "metadata": {},
      "condition": {
        "kind": "group",
        "operator": "OR",
        "children": [
          {
            "kind": "group",
            "operator": "AND",
            "children": [
              {
                "kind": "leaf",
                "operator": "EQ",
                "field": {
                  "namespace": "employee",
                  "name": "has_npwp",
                  "data_type": "boolean",
                  "nullable": false
                },
                "literal": {
                  "type": "boolean",
                  "value": true
                }
              },
              {
                "kind": "leaf",
                "operator": "GTE",
                "field": {
                  "namespace": "employee",
                  "name": "years_of_service",
                  "data_type": "numeric",
                  "nullable": false
                },
                "literal": {
                  "type": "numeric",
                  "value": 5
                }
              }
            ]
          },
          {
            "kind": "leaf",
            "operator": "EQ",
            "field": {
              "namespace": "employee",
              "name": "status",
              "data_type": "string",
              "nullable": false
            },
            "literal": {
              "type": "string",
              "value": "nonaktif"
            }
          }
        ]
      },
      "actions": [
        {
          "type": "ADD_COMPONENT",
          "target": {
            "code": "NESTED"
          },
          "formula": {
            "language": "TPR-EXPR-1.0",
            "expression": "50"
          }
        }
      ]
    }
  ]
}
```

Generated GRL:

```text

rule TPR_cd01f5faf3cf2abd_0 "TPR-IR 1.0" salience 50 {
when
	((employee.HasNpwp == true && employee.YearsOfService >= 5) || employee.Status == "nonaktif")
then
	out.Emit("ADD_COMPONENT", "NESTED", 50, 50, "legacy-10ff06069fa90df4", 0, 0);
	Retract("TPR_cd01f5faf3cf2abd_0");
}

```

Result:

```json
{
  "components": [
    {
      "code": "NESTED",
      "amount": 50,
      "source_rule": 0,
      "source_rule_id": "legacy-10ff06069fa90df4",
      "source_rule_ids": [
        "legacy-10ff06069fa90df4"
      ]
    }
  ],
  "summary": {
    "basic_salary": 5000000,
    "gross_salary": 5000050,
    "total_deductions": 0,
    "net_salary": 5000050
  }
}
```

## add-collect-sum

two ADD candidates aggregate with multi-rule provenance.

Canonical TPR-IR:

```json
{
  "schema_version": "1.0",
  "ruleset_id": "legacy-adapter",
  "default_hit_policy": "PRIORITY",
  "component_policies": {
    "AGGREGATE": "COLLECT_SUM"
  },
  "rounding_policy": {
    "scale": 6,
    "mode": "HALF_UP"
  },
  "rules": [
    {
      "id": "legacy-29234a709f5877c4",
      "priority": 100,
      "metadata": {},
      "condition": {
        "kind": "group",
        "operator": "AND",
        "children": [
          {
            "kind": "leaf",
            "operator": "EQ",
            "field": {
              "namespace": "employee",
              "name": "status",
              "data_type": "string",
              "nullable": false
            },
            "literal": {
              "type": "string",
              "value": "aktif"
            }
          }
        ]
      },
      "actions": [
        {
          "type": "ADD_COMPONENT",
          "target": {
            "code": "AGGREGATE"
          },
          "formula": {
            "language": "TPR-EXPR-1.0",
            "expression": "10"
          }
        }
      ]
    },
    {
      "id": "legacy-d7ec69ad386e494b",
      "priority": 10,
      "metadata": {},
      "condition": {
        "kind": "group",
        "operator": "AND",
        "children": [
          {
            "kind": "leaf",
            "operator": "EQ",
            "field": {
              "namespace": "employee",
              "name": "has_npwp",
              "data_type": "boolean",
              "nullable": false
            },
            "literal": {
              "type": "boolean",
              "value": true
            }
          }
        ]
      },
      "actions": [
        {
          "type": "ADD_COMPONENT",
          "target": {
            "code": "AGGREGATE"
          },
          "formula": {
            "language": "TPR-EXPR-1.0",
            "expression": "20"
          }
        }
      ],
      "legacy_index": 1
    }
  ]
}
```

Generated GRL:

```text

rule TPR_172ef9698b654f1a_0 "TPR-IR 1.0" salience 100 {
when
	(employee.Status == "aktif")
then
	out.Emit("ADD_COMPONENT", "AGGREGATE", 10, 100, "legacy-29234a709f5877c4", 0, 0);
	Retract("TPR_172ef9698b654f1a_0");
}

rule TPR_a8331374de111d95_0 "TPR-IR 1.0" salience 10 {
when
	(employee.HasNpwp == true)
then
	out.Emit("ADD_COMPONENT", "AGGREGATE", 20, 10, "legacy-d7ec69ad386e494b", 0, 1);
	Retract("TPR_a8331374de111d95_0");
}

```

Result:

```json
{
  "components": [
    {
      "code": "AGGREGATE",
      "amount": 30,
      "source_rule": 0,
      "source_rule_id": "legacy-29234a709f5877c4",
      "source_rule_ids": [
        "legacy-29234a709f5877c4",
        "legacy-d7ec69ad386e494b"
      ]
    }
  ],
  "summary": {
    "basic_salary": 5000000,
    "gross_salary": 5000030,
    "total_deductions": 0,
    "net_salary": 5000030
  }
}
```

## set-priority

SET selects highest salience and preserves source rule.

Canonical TPR-IR:

```json
{
  "schema_version": "1.0",
  "ruleset_id": "legacy-adapter",
  "default_hit_policy": "PRIORITY",
  "component_policies": {
    "PRIORITIZED": "PRIORITY"
  },
  "rounding_policy": {
    "scale": 6,
    "mode": "HALF_UP"
  },
  "rules": [
    {
      "id": "legacy-dfc9cf962db9583a",
      "priority": 100,
      "metadata": {},
      "condition": {
        "kind": "group",
        "operator": "AND",
        "children": [
          {
            "kind": "leaf",
            "operator": "EQ",
            "field": {
              "namespace": "employee",
              "name": "status",
              "data_type": "string",
              "nullable": false
            },
            "literal": {
              "type": "string",
              "value": "aktif"
            }
          }
        ]
      },
      "actions": [
        {
          "type": "SET_COMPONENT",
          "target": {
            "code": "PRIORITIZED"
          },
          "formula": {
            "language": "TPR-EXPR-1.0",
            "expression": "100"
          }
        }
      ]
    },
    {
      "id": "legacy-e4891f647c79e430",
      "priority": 10,
      "metadata": {},
      "condition": {
        "kind": "group",
        "operator": "AND",
        "children": [
          {
            "kind": "leaf",
            "operator": "EQ",
            "field": {
              "namespace": "employee",
              "name": "has_npwp",
              "data_type": "boolean",
              "nullable": false
            },
            "literal": {
              "type": "boolean",
              "value": true
            }
          }
        ]
      },
      "actions": [
        {
          "type": "SET_COMPONENT",
          "target": {
            "code": "PRIORITIZED"
          },
          "formula": {
            "language": "TPR-EXPR-1.0",
            "expression": "10"
          }
        }
      ],
      "legacy_index": 1
    }
  ]
}
```

Generated GRL:

```text

rule TPR_db16949d718ce0e5_0 "TPR-IR 1.0" salience 100 {
when
	(employee.Status == "aktif")
then
	out.Emit("SET_COMPONENT", "PRIORITIZED", 100, 100, "legacy-dfc9cf962db9583a", 0, 0);
	Retract("TPR_db16949d718ce0e5_0");
}

rule TPR_b42acb29779ea92c_0 "TPR-IR 1.0" salience 10 {
when
	(employee.HasNpwp == true)
then
	out.Emit("SET_COMPONENT", "PRIORITIZED", 10, 10, "legacy-e4891f647c79e430", 0, 1);
	Retract("TPR_b42acb29779ea92c_0");
}

```

Result:

```json
{
  "components": [
    {
      "code": "PRIORITIZED",
      "amount": 100,
      "source_rule": 0,
      "source_rule_id": "legacy-dfc9cf962db9583a",
      "source_rule_ids": [
        "legacy-dfc9cf962db9583a"
      ]
    }
  ],
  "summary": {
    "basic_salary": 5000000,
    "gross_salary": 5000100,
    "total_deductions": 0,
    "net_salary": 5000100
  }
}
```

## first

FIRST uses priority descending then stable rule ID.

Canonical TPR-IR:

```json
{
  "schema_version": "1.0",
  "ruleset_id": "legacy-adapter",
  "default_hit_policy": "PRIORITY",
  "component_policies": {
    "FIRST_VALUE": "FIRST"
  },
  "rounding_policy": {
    "scale": 6,
    "mode": "HALF_UP"
  },
  "rules": [
    {
      "id": "legacy-0da61247af8ad5ba",
      "priority": 100,
      "metadata": {},
      "condition": {
        "kind": "group",
        "operator": "AND",
        "children": [
          {
            "kind": "leaf",
            "operator": "EQ",
            "field": {
              "namespace": "employee",
              "name": "status",
              "data_type": "string",
              "nullable": false
            },
            "literal": {
              "type": "string",
              "value": "aktif"
            }
          }
        ]
      },
      "actions": [
        {
          "type": "SET_COMPONENT",
          "target": {
            "code": "FIRST_VALUE"
          },
          "formula": {
            "language": "TPR-EXPR-1.0",
            "expression": "70"
          }
        }
      ]
    },
    {
      "id": "legacy-5ee69182f9083932",
      "priority": 10,
      "metadata": {},
      "condition": {
        "kind": "group",
        "operator": "AND",
        "children": [
          {
            "kind": "leaf",
            "operator": "EQ",
            "field": {
              "namespace": "employee",
              "name": "has_npwp",
              "data_type": "boolean",
              "nullable": false
            },
            "literal": {
              "type": "boolean",
              "value": true
            }
          }
        ]
      },
      "actions": [
        {
          "type": "SET_COMPONENT",
          "target": {
            "code": "FIRST_VALUE"
          },
          "formula": {
            "language": "TPR-EXPR-1.0",
            "expression": "80"
          }
        }
      ],
      "legacy_index": 1
    }
  ]
}
```

Generated GRL:

```text

rule TPR_fec95ffe7abba93c_0 "TPR-IR 1.0" salience 100 {
when
	(employee.Status == "aktif")
then
	out.Emit("SET_COMPONENT", "FIRST_VALUE", 70, 100, "legacy-0da61247af8ad5ba", 0, 0);
	Retract("TPR_fec95ffe7abba93c_0");
}

rule TPR_3fcf8f3cfcc45a26_0 "TPR-IR 1.0" salience 10 {
when
	(employee.HasNpwp == true)
then
	out.Emit("SET_COMPONENT", "FIRST_VALUE", 80, 10, "legacy-5ee69182f9083932", 0, 1);
	Retract("TPR_3fcf8f3cfcc45a26_0");
}

```

Result:

```json
{
  "components": [
    {
      "code": "FIRST_VALUE",
      "amount": 70,
      "source_rule": 0,
      "source_rule_id": "legacy-0da61247af8ad5ba",
      "source_rule_ids": [
        "legacy-0da61247af8ad5ba"
      ]
    }
  ],
  "summary": {
    "basic_salary": 5000000,
    "gross_salary": 5000070,
    "total_deductions": 0,
    "net_salary": 5000070
  }
}
```

## unique-conflict

UNIQUE rejects two matching candidates.

Canonical TPR-IR:

```json
{
  "schema_version": "1.0",
  "ruleset_id": "legacy-adapter",
  "default_hit_policy": "PRIORITY",
  "component_policies": {
    "UNIQUE_VALUE": "UNIQUE"
  },
  "rounding_policy": {
    "scale": 6,
    "mode": "HALF_UP"
  },
  "rules": [
    {
      "id": "legacy-6329af26d705472b",
      "priority": 100,
      "metadata": {},
      "condition": {
        "kind": "group",
        "operator": "AND",
        "children": [
          {
            "kind": "leaf",
            "operator": "EQ",
            "field": {
              "namespace": "employee",
              "name": "status",
              "data_type": "string",
              "nullable": false
            },
            "literal": {
              "type": "string",
              "value": "aktif"
            }
          }
        ]
      },
      "actions": [
        {
          "type": "SET_COMPONENT",
          "target": {
            "code": "UNIQUE_VALUE"
          },
          "formula": {
            "language": "TPR-EXPR-1.0",
            "expression": "1"
          }
        }
      ]
    },
    {
      "id": "legacy-e37654dfee51b84b",
      "priority": 10,
      "metadata": {},
      "condition": {
        "kind": "group",
        "operator": "AND",
        "children": [
          {
            "kind": "leaf",
            "operator": "EQ",
            "field": {
              "namespace": "employee",
              "name": "has_npwp",
              "data_type": "boolean",
              "nullable": false
            },
            "literal": {
              "type": "boolean",
              "value": true
            }
          }
        ]
      },
      "actions": [
        {
          "type": "SET_COMPONENT",
          "target": {
            "code": "UNIQUE_VALUE"
          },
          "formula": {
            "language": "TPR-EXPR-1.0",
            "expression": "2"
          }
        }
      ],
      "legacy_index": 1
    }
  ]
}
```

Generated GRL:

```text

rule TPR_6098ab8377db9661_0 "TPR-IR 1.0" salience 100 {
when
	(employee.Status == "aktif")
then
	out.Emit("SET_COMPONENT", "UNIQUE_VALUE", 1, 100, "legacy-6329af26d705472b", 0, 0);
	Retract("TPR_6098ab8377db9661_0");
}

rule TPR_b93bfca1c43f29a1_0 "TPR-IR 1.0" salience 10 {
when
	(employee.HasNpwp == true)
then
	out.Emit("SET_COMPONENT", "UNIQUE_VALUE", 2, 10, "legacy-e37654dfee51b84b", 0, 1);
	Retract("TPR_b93bfca1c43f29a1_0");
}

```

Result:

```json
{
  "components": null,
  "summary": {
    "basic_salary": 0,
    "gross_salary": 0,
    "total_deductions": 0,
    "net_salary": 0
  }
}
```

## invalid-formula

formula parser rejects an incomplete expression.

Canonical TPR-IR:

```json
{
  "schema_version": "1.0",
  "ruleset_id": "legacy-adapter",
  "default_hit_policy": "PRIORITY",
  "component_policies": {
    "INVALID_FORMULA": "COLLECT_SUM"
  },
  "rounding_policy": {
    "scale": 6,
    "mode": "HALF_UP"
  },
  "rules": [
    {
      "id": "legacy-e9f6b03bb12b7a94",
      "priority": 50,
      "metadata": {},
      "condition": {
        "kind": "group",
        "operator": "AND",
        "children": [
          {
            "kind": "leaf",
            "operator": "EQ",
            "field": {
              "namespace": "employee",
              "name": "status",
              "data_type": "string",
              "nullable": false
            },
            "literal": {
              "type": "string",
              "value": "aktif"
            }
          }
        ]
      },
      "actions": [
        {
          "type": "ADD_COMPONENT",
          "target": {
            "code": "INVALID_FORMULA"
          },
          "formula": {
            "language": "TPR-EXPR-1.0",
            "expression": "rates.bonus_rate +"
          }
        }
      ]
    }
  ]
}
```

Generated GRL:

```text
<not emitted: INVALID_FORMULA>
```

Result:

```json
{
  "components": null,
  "summary": {
    "basic_salary": 0,
    "gross_salary": 0,
    "total_deductions": 0,
    "net_salary": 0
  }
}
```

## unknown-field

canonical validator rejects a field absent from the catalog.

Canonical TPR-IR:

```json
{
  "schema_version": "1.0",
  "ruleset_id": "legacy-adapter",
  "default_hit_policy": "PRIORITY",
  "component_policies": {
    "UNKNOWN_FIELD": "COLLECT_SUM"
  },
  "rounding_policy": {
    "scale": 6,
    "mode": "HALF_UP"
  },
  "rules": [
    {
      "id": "legacy-606a82b5563f846c",
      "priority": 50,
      "metadata": {},
      "condition": {
        "kind": "group",
        "operator": "AND",
        "children": [
          {
            "kind": "leaf",
            "operator": "EQ",
            "field": {
              "namespace": "employee",
              "name": "password",
              "data_type": "string",
              "nullable": false
            },
            "literal": {
              "type": "string",
              "value": "aktif"
            }
          }
        ]
      },
      "actions": [
        {
          "type": "ADD_COMPONENT",
          "target": {
            "code": "UNKNOWN_FIELD"
          },
          "formula": {
            "language": "TPR-EXPR-1.0",
            "expression": "10"
          }
        }
      ]
    }
  ]
}
```

Generated GRL:

```text
<not emitted: UNKNOWN_FIELD>
```

Result:

```json
{
  "components": null,
  "summary": {
    "basic_salary": 0,
    "gross_salary": 0,
    "total_deductions": 0,
    "net_salary": 0
  }
}
```

## Verdict

Seluruh 12 fixture menghasilkan outcome yang ditetapkan. Operator, typed literal, nested condition, precedence, salience, hit policy, target, provenance, serta rounding tercakup. Konflik UNIQUE ditolak statis sebagai `POTENTIAL_UNIQUE_CONFLICT`; invalid formula dan unknown field ditolak sebelum GRL dijalankan.
