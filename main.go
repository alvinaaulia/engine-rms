package main

import (
	"encoding/json"
	"log"
	"net/http"
)

func executeRules(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	var req ExecuteRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "invalid JSON: "+err.Error(), http.StatusBadRequest)
		return
	}

	resp, err := executeAllRules(req.Rules, req.Facts)
	if err != nil {
		http.Error(w, "rule execution error: "+err.Error(), http.StatusInternalServerError)
		return
	}

	_ = json.NewEncoder(w).Encode(resp)
}

func main() {
	http.HandleFunc("/execute", executeRules)
	log.Println("Go Rule Engine running on :8081")
	log.Fatal(http.ListenAndServe(":8081", nil))
}