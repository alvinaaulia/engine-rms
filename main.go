package main

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"log"
	"net"
	"net/http"
	"os"
	"strings"
	"time"
)

const maxExecuteRequestBytes int64 = 1 << 20

const internalTokenHeader = "X-Rule-Engine-Token"

const (
	defaultRuleExecutionTimeout = 30 * time.Second
	maximumRuleExecutionTimeout = 2 * time.Minute
)

func ruleExecutionTimeout() time.Duration {
	raw := strings.TrimSpace(os.Getenv("RULE_ENGINE_EXECUTION_TIMEOUT"))
	if raw == "" {
		return defaultRuleExecutionTimeout
	}
	timeout, err := time.ParseDuration(raw)
	if err != nil || timeout <= 0 || timeout > maximumRuleExecutionTimeout {
		return defaultRuleExecutionTimeout
	}
	return timeout
}

func requireInternalToken(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		expected := strings.TrimSpace(os.Getenv("RULE_ENGINE_INTERNAL_TOKEN"))
		// Local development remains usable without a token. Non-loopback
		// deployments must configure a token explicitly.
		if expected != "" && subtleConstantTimeEqual(r.Header.Get(internalTokenHeader), expected) == false {
			w.Header().Set("Content-Type", "application/json")
			writeAPIError(w, http.StatusUnauthorized, validationError("UNAUTHORIZED", "headers."+internalTokenHeader, "invalid internal service credential"))
			return
		}
		next(w, r)
	}
}

func subtleConstantTimeEqual(actual, expected string) bool {
	if len(actual) != len(expected) {
		return false
	}
	var mismatch byte
	for i := range actual {
		mismatch |= actual[i] ^ expected[i]
	}
	return mismatch == 0
}

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

	ctx, cancel := context.WithTimeout(r.Context(), ruleExecutionTimeout())
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

func health(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	if r.Method != http.MethodGet {
		writeAPIError(w, http.StatusMethodNotAllowed, validationError("METHOD_NOT_ALLOWED", "request.method", "only GET is supported"))
		return
	}
	w.WriteHeader(http.StatusOK)
	_ = json.NewEncoder(w).Encode(map[string]string{"status": "ready"})
}

func main() {
	http.HandleFunc("/health", health)
	http.HandleFunc("/execute", requireInternalToken(executeRules))
	http.HandleFunc("/replay", requireInternalToken(replayRules))
	addr := strings.TrimSpace(os.Getenv("RULE_ENGINE_ADDR"))
	if addr == "" {
		addr = "127.0.0.1:8081"
	}
	host, _, err := net.SplitHostPort(addr)
	if err != nil {
		log.Fatalf("invalid RULE_ENGINE_ADDR %q: %v", addr, err)
	}
	if strings.TrimSpace(os.Getenv("RULE_ENGINE_INTERNAL_TOKEN")) == "" {
		ip := net.ParseIP(host)
		if host != "localhost" && (ip == nil || !ip.IsLoopback()) {
			log.Fatal("RULE_ENGINE_INTERNAL_TOKEN is required for a non-loopback bind address")
		}
	}
	log.Printf("Go Rule Engine running on %s", addr)
	server := &http.Server{Addr: addr, ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 10 * time.Second, WriteTimeout: 15 * time.Second, IdleTimeout: 60 * time.Second}
	log.Fatal(server.ListenAndServe())
}
