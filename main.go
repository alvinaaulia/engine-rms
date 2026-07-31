package main

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"log"
	"net/http"
	"time"
)

const maxExecuteRequestBytes int64 = 1 << 20

func writeAPIError(w http.ResponseWriter, status int, err error) {
	w.WriteHeader(status)
	if validation, ok := err.(*ValidationError); ok {
		_ = json.NewEncoder(w).Encode(validation)
		return
	}
	_ = json.NewEncoder(w).Encode(ValidationError{ErrorCode: "EXECUTION_ERROR", Path: "request", Message: err.Error()})
}

func executeRules(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	if r.Method != http.MethodPost {
		writeAPIError(w, http.StatusMethodNotAllowed, validationError("METHOD_NOT_ALLOWED", "request.method", "only POST is supported"))
		return
	}
	r.Body = http.MaxBytesReader(w, r.Body, maxExecuteRequestBytes)

	var req ExecuteRequest
	decoder := json.NewDecoder(r.Body)
	decoder.UseNumber()
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&req); err != nil {
		var maxBytesError *http.MaxBytesError
		if errors.As(err, &maxBytesError) {
			writeAPIError(w, http.StatusRequestEntityTooLarge, validationError("REQUEST_TOO_LARGE", "request", "request body exceeds 1 MiB"))
			return
		}
		writeAPIError(w, http.StatusBadRequest, validationError("INVALID_JSON", "request", "invalid or oversized JSON request"))
		return
	}
	if err := decoder.Decode(&struct{}{}); err != io.EOF {
		writeAPIError(w, http.StatusBadRequest, validationError("INVALID_JSON", "request", "request must contain exactly one JSON object"))
		return
	}

	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()
	var resp ExecuteResponse
	var err error
	if req.RuleSet != nil {
		if req.SchemaVersion == "" {
			err = validationError("MISSING_SCHEMA_VERSION", "schema_version", "top-level schema_version is required for TPR payloads")
		} else if req.SchemaVersion != TPRSchemaVersion || req.RuleSet.SchemaVersion != req.SchemaVersion {
			err = validationError("UNSUPPORTED_SCHEMA_VERSION", "schema_version", "schema versions must both be 1.0")
		} else {
			resp, err = ExecuteTPRRuleSet(ctx, req.RuleSet, req.Facts, req.ComponentTypes)
		}
	} else {
		resp, err = executeAllRulesWithComponentTypes(req.Rules, req.Facts, req.ComponentTypes)
	}
	if err != nil {
		status := http.StatusUnprocessableEntity
		if _, ok := err.(*ValidationError); !ok || req.RuleSet == nil {
			status = http.StatusInternalServerError
		}
		writeAPIError(w, status, err)
		return
	}

	_ = json.NewEncoder(w).Encode(resp)
}

func main() {
	http.HandleFunc("/execute", executeRules)
	log.Println("Go Rule Engine running on :8081")
	server := &http.Server{Addr: ":8081", ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 10 * time.Second, WriteTimeout: 15 * time.Second, IdleTimeout: 60 * time.Second}
	log.Fatal(server.ListenAndServe())
}
