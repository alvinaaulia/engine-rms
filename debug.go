package main

import (
	"encoding/json"
	"log"
)

func debugPrint(v interface{}) {
	b, _ := json.MarshalIndent(v, "", "  ")
	log.Println(string(b))
}
