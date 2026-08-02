package main

import (
	"bytes"
	"context"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"sort"
	"strconv"
	"strings"
	"time"
)

const (
	temporalManifestVersion   = "1.0"
	temporalTranslatorVersion = "laravel-go-tpr-translator-1.0"
	temporalEngineVersion     = "go-grule-tpr-engine-1.0"
)

type ReplayExpectedHashes struct {
	FactsSHA256          string `json:"facts_sha256"`
	RuleSetSHA256        string `json:"ruleset_sha256"`
	GeneratedGRLSHA256   string `json:"generated_grl_sha256,omitempty"`
	OriginalOutputSHA256 string `json:"original_output_sha256,omitempty"`
}

type ReplayVersionIdentities struct {
	RuleVersionIDs []int             `json:"rule_version_ids"`
	RateVersionIDs []int             `json:"rate_version_ids"`
	TaxVersionIDs  []int             `json:"tax_version_ids"`
	BindingStatus  map[string]string `json:"binding_status"`
}

type ReplayRequest struct {
	Mode                   string                  `json:"mode"`
	ExecutionUUID          string                  `json:"execution_uuid"`
	ReplayUUID             string                  `json:"replay_uuid,omitempty"`
	RequestID              string                  `json:"request_id"`
	OriginalRequestID      string                  `json:"original_request_id,omitempty"`
	LaravelCorrelationID   string                  `json:"laravel_correlation_id,omitempty"`
	ManifestVersion        string                  `json:"manifest_version"`
	TPRIRSchemaVersion     string                  `json:"tpr_ir_schema_version"`
	FactsSnapshot          map[string]interface{}  `json:"facts_snapshot"`
	RuleSetSnapshot        map[string]interface{}  `json:"ruleset_snapshot"`
	ComponentTypesSnapshot map[string]string       `json:"component_types_snapshot"`
	ExpectedHashes         ReplayExpectedHashes    `json:"expected_hashes"`
	VersionIdentities      ReplayVersionIdentities `json:"version_identities"`
	TranslatorVersion      string                  `json:"translator_version"`
	EngineVersion          string                  `json:"engine_version"`
	RoundingPolicy         TPRRoundingPolicy       `json:"rounding_policy"`
	ResearchTrace          bool                    `json:"research_trace,omitempty"`
	HTTPRequestID          string                  `json:"-"`
}

type ReplayComponent struct {
	Code                      string   `json:"code"`
	Type                      string   `json:"type"`
	Amount                    string   `json:"amount"`
	SourceRuleID              string   `json:"source_rule_id"`
	SourceRuleVersionID       int      `json:"source_rule_version_id"`
	ContributorRuleIDs        []string `json:"contributor_rule_ids"`
	ContributorRuleVersionIDs []int    `json:"contributor_rule_version_ids"`
}

type ReplaySummary struct {
	BasicSalary     string `json:"basic_salary"`
	GrossSalary     string `json:"gross_salary"`
	TotalDeductions string `json:"total_deductions"`
	NetSalary       string `json:"net_salary"`
}

type ReplayProvenance struct {
	RuleVersionIDs    []int  `json:"rule_version_ids"`
	RateVersionIDs    []int  `json:"rate_version_ids"`
	TaxVersionIDs     []int  `json:"tax_version_ids"`
	RuleSetSHA256     string `json:"ruleset_sha256"`
	FactsSHA256       string `json:"facts_sha256"`
	TranslatorVersion string `json:"translator_version"`
	EngineVersion     string `json:"engine_version"`
	RequestID         string `json:"request_id"`
	ExecutionUUID     string `json:"execution_uuid"`
}

type ReplayResponse struct {
	Mode                 string                   `json:"mode"`
	ExecutionUUID        string                   `json:"execution_uuid"`
	ReplayUUID           string                   `json:"replay_uuid,omitempty"`
	RequestID            string                   `json:"request_id"`
	LaravelCorrelationID string                   `json:"laravel_correlation_id,omitempty"`
	TranslatorTraceID    string                   `json:"translator_trace_id,omitempty"`
	GRULEExecutionID     string                   `json:"grule_execution_id,omitempty"`
	Components           []ReplayComponent        `json:"components"`
	Summary              ReplaySummary            `json:"summary"`
	Provenance           ReplayProvenance         `json:"provenance"`
	GeneratedGRL         string                   `json:"generated_grl"`
	GeneratedGRLSHA256   string                   `json:"generated_grl_sha256"`
	OutputSHA256         string                   `json:"output_sha256"`
	MatchesOriginalHash  *bool                    `json:"matches_original_hash,omitempty"`
	CorrelationEvents    []ReplayCorrelationEvent `json:"correlation_events,omitempty"`
	RoundingTrace        []ReplayRoundingTrace    `json:"rounding_trace,omitempty"`
}

type ReplayCorrelationEvent struct {
	EventID              string `json:"event_id"`
	OccurredAt           string `json:"occurred_at"`
	Stage                string `json:"stage"`
	Event                string `json:"event"`
	RequestID            string `json:"request_id"`
	ExecutionUUID        string `json:"execution_uuid"`
	ReplayUUID           string `json:"replay_uuid"`
	LaravelCorrelationID string `json:"laravel_correlation_id"`
	TranslatorTraceID    string `json:"translator_trace_id"`
	GRULEExecutionID     string `json:"grule_execution_id"`
}

type ReplayRoundingTrace struct {
	ComponentCode       string `json:"component_code"`
	SourceRule          string `json:"source_rule"`
	RawCandidateDecimal string `json:"raw_candidate_decimal"`
	ScaleBeforeRounding int    `json:"scale_before_rounding"`
	RoundingMode        string `json:"rounding_mode"`
	RoundingQuantum     string `json:"rounding_quantum"`
	RoundedResult       string `json:"rounded_result"`
	OperationTimestamp  string `json:"operation_timestamp"`
}

func replayRules(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	if r.Method != http.MethodPost {
		writeAPIError(w, http.StatusMethodNotAllowed, validationError("METHOD_NOT_ALLOWED", "request.method", "only POST is supported"))
		return
	}
	r.Body = http.MaxBytesReader(w, r.Body, maxExecuteRequestBytes)
	decoder := json.NewDecoder(r.Body)
	decoder.UseNumber()
	decoder.DisallowUnknownFields()
	var req ReplayRequest
	if err := decoder.Decode(&req); err != nil {
		writeAPIError(w, http.StatusBadRequest, validationError("REPLAY_MANIFEST_INVALID", "request", "invalid replay envelope"))
		return
	}
	if err := decoder.Decode(&struct{}{}); err != io.EOF {
		writeAPIError(w, http.StatusBadRequest, validationError("REPLAY_MANIFEST_INVALID", "request", "request must contain exactly one JSON object"))
		return
	}
	req.HTTPRequestID = strings.TrimSpace(r.Header.Get("X-Request-ID"))
	if req.HTTPRequestID == "" {
		req.HTTPRequestID = req.RequestID
	}
	if req.HTTPRequestID != req.RequestID {
		writeAPIError(w, http.StatusBadRequest, validationError("REPLAY_MANIFEST_INVALID", "headers.X-Request-ID", "HTTP and body request correlation IDs must match"))
		return
	}
	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()
	response, err := executeTemporalReplay(ctx, req)
	if err != nil {
		writeAPIError(w, http.StatusUnprocessableEntity, err)
		return
	}
	w.Header().Set("X-Request-ID", response.RequestID)
	_ = json.NewEncoder(w).Encode(response)
}

func executeTemporalReplay(ctx context.Context, req ReplayRequest) (ReplayResponse, error) {
	if req.Mode != "TEMPORAL_REPLAY" {
		return ReplayResponse{}, validationError("REPLAY_MANIFEST_INVALID", "mode", "mode must be TEMPORAL_REPLAY")
	}
	if strings.TrimSpace(req.ExecutionUUID) == "" || strings.TrimSpace(req.RequestID) == "" {
		return ReplayResponse{}, validationError("REPLAY_MANIFEST_INVALID", "execution_uuid", "execution and request correlation IDs are required")
	}
	if req.ReplayUUID != "" && req.LaravelCorrelationID == "" {
		return ReplayResponse{}, validationError("REPLAY_MANIFEST_INVALID", "laravel_correlation_id", "Laravel correlation ID is required for an instrumented replay")
	}
	originalRequestID := req.OriginalRequestID
	if originalRequestID == "" {
		originalRequestID = req.RequestID
	}
	translatorTraceID := newReplayUUID()
	gruleExecutionID := newReplayUUID()
	events := make([]ReplayCorrelationEvent, 0, 7)
	recordEvent := func(stage, event string) {
		events = append(events, ReplayCorrelationEvent{
			EventID: newReplayUUID(), OccurredAt: time.Now().UTC().Format(time.RFC3339Nano), Stage: stage, Event: event,
			RequestID: req.RequestID, ExecutionUUID: req.ExecutionUUID, ReplayUUID: req.ReplayUUID,
			LaravelCorrelationID: req.LaravelCorrelationID, TranslatorTraceID: translatorTraceID, GRULEExecutionID: gruleExecutionID,
		})
	}
	recordEvent("GO_HTTP", "REQUEST_RECEIVED")
	if req.ManifestVersion != temporalManifestVersion || req.TPRIRSchemaVersion != TPRSchemaVersion {
		return ReplayResponse{}, validationError("REPLAY_SCHEMA_UNSUPPORTED", "manifest_version", "manifest and TPR-IR versions are unsupported")
	}
	if req.TranslatorVersion != temporalTranslatorVersion || req.EngineVersion != temporalEngineVersion {
		return ReplayResponse{}, validationError("REPLAY_SCHEMA_UNSUPPORTED", "translator_version", "translator or engine compatibility version is unsupported")
	}
	if req.RoundingPolicy.Scale != int(payrollMoneyScale) || req.RoundingPolicy.Mode != "HALF_UP" {
		return ReplayResponse{}, validationError("REPLAY_SCHEMA_UNSUPPORTED", "rounding_policy", "replay requires scale 6 HALF_UP")
	}
	if req.FactsSnapshot == nil || req.RuleSetSnapshot == nil || req.ComponentTypesSnapshot == nil {
		return ReplayResponse{}, validationError("REPLAY_MANIFEST_INVALID", "facts_snapshot", "facts, ruleset, and component types snapshots are required")
	}
	recordEvent("TPR_IR_VALIDATOR", "SCHEMA_VALIDATED")

	factsHash, err := canonicalSHA256(req.FactsSnapshot)
	if err != nil || factsHash != req.ExpectedHashes.FactsSHA256 {
		return ReplayResponse{}, &ValidationError{ErrorCode: "REPLAY_HASH_MISMATCH", Path: "facts_sha256", Message: "facts snapshot hash mismatch", Details: map[string]interface{}{"expected_sha256": req.ExpectedHashes.FactsSHA256, "actual_sha256": factsHash}}
	}
	rulesetHash, err := canonicalSHA256(req.RuleSetSnapshot)
	if err != nil || rulesetHash != req.ExpectedHashes.RuleSetSHA256 {
		return ReplayResponse{}, &ValidationError{ErrorCode: "REPLAY_HASH_MISMATCH", Path: "ruleset_sha256", Message: "ruleset snapshot hash mismatch", Details: map[string]interface{}{"expected_sha256": req.ExpectedHashes.RuleSetSHA256, "actual_sha256": rulesetHash}}
	}
	recordEvent("TPR_IR_VALIDATOR", "HASHES_VALIDATED")

	rulesetBytes, err := json.Marshal(req.RuleSetSnapshot)
	if err != nil {
		return ReplayResponse{}, validationError("REPLAY_MANIFEST_INVALID", "ruleset_snapshot", "ruleset snapshot is not serializable")
	}
	var ruleset TPRRuleSet
	rulesetDecoder := json.NewDecoder(strings.NewReader(string(rulesetBytes)))
	rulesetDecoder.UseNumber()
	if err := rulesetDecoder.Decode(&ruleset); err != nil {
		return ReplayResponse{}, validationError("REPLAY_MANIFEST_INVALID", "ruleset_snapshot", "ruleset snapshot is invalid")
	}
	if ruleset.SchemaVersion != req.TPRIRSchemaVersion {
		return ReplayResponse{}, validationError("REPLAY_SCHEMA_UNSUPPORTED", "ruleset_snapshot.schema_version", "ruleset schema does not match the manifest")
	}

	ruleIDs := ruleVersionIDsFromSnapshot(&ruleset)
	rateIDs, err := versionIDsFromFacts(req.FactsSnapshot, "resolved_rate_version_ids")
	if err != nil {
		return ReplayResponse{}, err
	}
	taxIDs, err := versionIDsFromFacts(req.FactsSnapshot, "resolved_tax_version_ids")
	if err != nil {
		return ReplayResponse{}, err
	}
	if err := verifyVersionBinding("rule", ruleIDs, req.VersionIdentities.RuleVersionIDs, req.VersionIdentities.BindingStatus); err != nil {
		return ReplayResponse{}, err
	}
	if err := verifyVersionBinding("rate", rateIDs, req.VersionIdentities.RateVersionIDs, req.VersionIdentities.BindingStatus); err != nil {
		return ReplayResponse{}, err
	}
	if err := verifyVersionBinding("tax", taxIDs, req.VersionIdentities.TaxVersionIDs, req.VersionIdentities.BindingStatus); err != nil {
		return ReplayResponse{}, err
	}

	recordEvent("GRL_TRANSLATOR", "TRANSLATION_STARTED")
	generatedGRL, err := buildTPRGRL(&ruleset)
	if err != nil {
		return ReplayResponse{}, validationError("REPLAY_EXECUTION_FAILED", "generated_grl", err.Error())
	}
	recordEvent("GRL_TRANSLATOR", "TRANSLATION_FINISHED")
	recordEvent("GRULE", "EXECUTION_STARTED")
	result, err := ExecuteTPRRuleSet(ctx, &ruleset, req.FactsSnapshot, req.ComponentTypesSnapshot)
	if err != nil {
		if validation, ok := err.(*ValidationError); ok {
			validation.ErrorCode = "REPLAY_EXECUTION_FAILED"
			return ReplayResponse{}, validation
		}
		return ReplayResponse{}, validationError("REPLAY_EXECUTION_FAILED", "ruleset_snapshot", err.Error())
	}
	recordEvent("GRULE", "EXECUTION_FINISHED")
	generatedHash := sha256Text(generatedGRL)
	if req.ExpectedHashes.GeneratedGRLSHA256 != "" && generatedHash != req.ExpectedHashes.GeneratedGRLSHA256 {
		return ReplayResponse{}, validationError("REPLAY_HASH_MISMATCH", "generated_grl_sha256", "generated GRL hash mismatch")
	}

	components := make([]ReplayComponent, 0, len(result.Components))
	roundingTrace := make([]ReplayRoundingTrace, 0, len(result.Components))
	for _, component := range result.Components {
		contributorIDs := uniqueSortedStrings(component.SourceRuleIDs)
		contributorVersions := uniqueSortedInts(component.SourceRuleVersionIDs)
		components = append(components, ReplayComponent{
			Code:                      strings.ToUpper(strings.TrimSpace(component.Code)),
			Type:                      componentTypeForCode(req.ComponentTypesSnapshot, component.Code),
			Amount:                    payrollDecimalFromFloat(component.Amount).StringFixed(payrollMoneyScale),
			SourceRuleID:              component.SourceRuleID,
			SourceRuleVersionID:       component.SourceRuleVersionID,
			ContributorRuleIDs:        contributorIDs,
			ContributorRuleVersionIDs: contributorVersions,
		})
		if req.ResearchTrace {
			raw := strconv.FormatFloat(component.Amount, 'f', -1, 64)
			roundingTrace = append(roundingTrace, ReplayRoundingTrace{
				ComponentCode: strings.ToUpper(strings.TrimSpace(component.Code)), SourceRule: component.SourceRuleID,
				RawCandidateDecimal: raw, ScaleBeforeRounding: decimalScale(raw), RoundingMode: req.RoundingPolicy.Mode,
				RoundingQuantum: "0.000001", RoundedResult: payrollDecimalFromFloat(component.Amount).StringFixed(payrollMoneyScale),
				OperationTimestamp: time.Now().UTC().Format(time.RFC3339Nano),
			})
		}
	}
	sort.Slice(components, func(i, j int) bool { return components[i].Code < components[j].Code })
	summary := ReplaySummary{
		BasicSalary:     payrollDecimalFromFloat(result.Summary.BasicSalary).StringFixed(payrollMoneyScale),
		GrossSalary:     payrollDecimalFromFloat(result.Summary.GrossSalary).StringFixed(payrollMoneyScale),
		TotalDeductions: payrollDecimalFromFloat(result.Summary.TotalDeductions).StringFixed(payrollMoneyScale),
		NetSalary:       payrollDecimalFromFloat(result.Summary.NetSalary).StringFixed(payrollMoneyScale),
	}
	provenance := ReplayProvenance{
		RuleVersionIDs: ruleIDs, RateVersionIDs: rateIDs, TaxVersionIDs: taxIDs,
		RuleSetSHA256: rulesetHash, FactsSHA256: factsHash,
		TranslatorVersion: temporalTranslatorVersion, EngineVersion: temporalEngineVersion,
		RequestID: originalRequestID, ExecutionUUID: req.ExecutionUUID,
	}
	output := map[string]interface{}{"components": components, "summary": summary, "provenance": provenance}
	outputHash, err := canonicalSHA256(output)
	if err != nil {
		return ReplayResponse{}, validationError("REPLAY_EXECUTION_FAILED", "output_sha256", "cannot hash replay output")
	}
	var matches *bool
	if req.ExpectedHashes.OriginalOutputSHA256 != "" {
		value := outputHash == req.ExpectedHashes.OriginalOutputSHA256
		matches = &value
	}
	recordEvent("GO_HTTP", "RESPONSE_GENERATED")
	return ReplayResponse{
		Mode: req.Mode, ExecutionUUID: req.ExecutionUUID, ReplayUUID: req.ReplayUUID, RequestID: req.RequestID,
		LaravelCorrelationID: req.LaravelCorrelationID, TranslatorTraceID: translatorTraceID, GRULEExecutionID: gruleExecutionID,
		Components: components, Summary: summary, Provenance: provenance,
		GeneratedGRL: generatedGRL, GeneratedGRLSHA256: generatedHash,
		OutputSHA256: outputHash, MatchesOriginalHash: matches, CorrelationEvents: events, RoundingTrace: roundingTrace,
	}, nil
}

func newReplayUUID() string {
	value := make([]byte, 16)
	if _, err := rand.Read(value); err != nil {
		return fmt.Sprintf("00000000-0000-4000-8000-%012x", time.Now().UnixNano()&0xffffffffffff)
	}
	value[6] = (value[6] & 0x0f) | 0x40
	value[8] = (value[8] & 0x3f) | 0x80
	return fmt.Sprintf("%08x-%04x-%04x-%04x-%012x", value[0:4], value[4:6], value[6:8], value[8:10], value[10:16])
}

func decimalScale(value string) int {
	if index := strings.IndexByte(value, '.'); index >= 0 {
		return len(value) - index - 1
	}
	return 0
}

func canonicalSHA256(value interface{}) (string, error) {
	raw, err := json.Marshal(value)
	if err != nil {
		return "", err
	}
	var generic interface{}
	decoder := json.NewDecoder(strings.NewReader(string(raw)))
	decoder.UseNumber()
	if err := decoder.Decode(&generic); err != nil {
		return "", err
	}
	var canonical bytes.Buffer
	encoder := json.NewEncoder(&canonical)
	encoder.SetEscapeHTML(false)
	if err := encoder.Encode(generic); err != nil {
		return "", err
	}
	sum := sha256.Sum256(bytes.TrimSuffix(canonical.Bytes(), []byte("\n")))
	return hex.EncodeToString(sum[:]), nil
}

func sha256Text(value string) string {
	sum := sha256.Sum256([]byte(value))
	return hex.EncodeToString(sum[:])
}

func ruleVersionIDsFromSnapshot(ruleset *TPRRuleSet) []int {
	ids := make([]int, 0, len(ruleset.Rules))
	for _, rule := range ruleset.Rules {
		if rule.VersionID > 0 {
			ids = append(ids, rule.VersionID)
		}
	}
	return uniqueSortedInts(ids)
}

func versionIDsFromFacts(facts map[string]interface{}, key string) ([]int, error) {
	source, ok := facts["source"].(map[string]interface{})
	if !ok {
		return nil, validationError("REPLAY_VERSION_MISSING", "facts_snapshot.source", "version identity source is missing")
	}
	value, exists := source[key]
	if !exists {
		return nil, validationError("REPLAY_VERSION_MISSING", "facts_snapshot.source."+key, "version identity is missing")
	}
	rawIDs, ok := value.([]interface{})
	if !ok {
		return nil, validationError("REPLAY_VERSION_MISSING", "facts_snapshot.source."+key, "version identity must be an array")
	}
	ids := make([]int, 0, len(rawIDs))
	for _, raw := range rawIDs {
		var parsed int
		switch typed := raw.(type) {
		case json.Number:
			value, err := typed.Int64()
			if err != nil {
				return nil, validationError("REPLAY_VERSION_MISSING", "facts_snapshot.source."+key, "version identity must be a positive integer")
			}
			parsed = int(value)
		case float64:
			parsed = int(typed)
		case int:
			parsed = typed
		default:
			return nil, validationError("REPLAY_VERSION_MISSING", "facts_snapshot.source."+key, "version identity must be a positive integer")
		}
		if parsed <= 0 {
			return nil, validationError("REPLAY_VERSION_MISSING", "facts_snapshot.source."+key, "version identity must be positive")
		}
		ids = append(ids, parsed)
	}
	return uniqueSortedInts(ids), nil
}

func verifyVersionBinding(kind string, derived, expected []int, statuses map[string]string) error {
	status := statuses[kind]
	if status == "NOT_APPLICABLE" {
		if len(derived) != 0 || len(expected) != 0 {
			return validationError("REPLAY_VERSION_MISSING", "version_identities."+kind, "NOT_APPLICABLE binding must have no version IDs")
		}
		return nil
	}
	if status != "BOUND" || len(derived) == 0 || len(expected) == 0 {
		return validationError("REPLAY_VERSION_MISSING", "version_identities."+kind, "BOUND version identity is missing")
	}
	if fmt.Sprint(uniqueSortedInts(derived)) != fmt.Sprint(uniqueSortedInts(expected)) {
		return validationError("REPLAY_VERSION_MISSING", "version_identities."+kind, "version identity does not match the hashed snapshot")
	}
	return nil
}

func uniqueSortedInts(values []int) []int {
	seen := map[int]bool{}
	result := []int{}
	for _, value := range values {
		if value > 0 && !seen[value] {
			seen[value] = true
			result = append(result, value)
		}
	}
	sort.Ints(result)
	return result
}

func uniqueSortedStrings(values []string) []string {
	seen := map[string]bool{}
	result := []string{}
	for _, value := range values {
		if value != "" && !seen[value] {
			seen[value] = true
			result = append(result, value)
		}
	}
	sort.Strings(result)
	return result
}
