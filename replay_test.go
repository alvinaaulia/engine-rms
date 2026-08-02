package main

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"reflect"
	"strings"
	"testing"
)

func temporalReplayFixture(t *testing.T) ReplayRequest {
	t.Helper()
	facts := semanticFacts()
	facts["source"] = map[string]interface{}{
		"resolved_rate_version_ids": []interface{}{json.Number("7")},
		"resolved_tax_version_ids":  []interface{}{json.Number("9")},
	}
	rule := semanticRule("BONUS", "rates.bonus_rate", "HIGH")
	rule.Meta.RuleVersionID = 42
	ruleset := adaptedRuleSet(t, []Rule{rule})
	rulesetMap := map[string]interface{}{}
	raw, err := json.Marshal(ruleset)
	if err != nil {
		t.Fatal(err)
	}
	decoder := json.NewDecoder(strings.NewReader(string(raw)))
	decoder.UseNumber()
	if err := decoder.Decode(&rulesetMap); err != nil {
		t.Fatal(err)
	}
	factsHash, err := canonicalSHA256(facts)
	if err != nil {
		t.Fatal(err)
	}
	rulesHash, err := canonicalSHA256(rulesetMap)
	if err != nil {
		t.Fatal(err)
	}
	return ReplayRequest{
		Mode: "TEMPORAL_REPLAY", ExecutionUUID: "execution-1", RequestID: "request-1",
		ManifestVersion: temporalManifestVersion, TPRIRSchemaVersion: TPRSchemaVersion,
		FactsSnapshot: facts, RuleSetSnapshot: rulesetMap,
		ComponentTypesSnapshot: map[string]string{"BONUS": "EARNING"},
		ExpectedHashes:         ReplayExpectedHashes{FactsSHA256: factsHash, RuleSetSHA256: rulesHash},
		VersionIdentities: ReplayVersionIdentities{
			RuleVersionIDs: []int{42}, RateVersionIDs: []int{7}, TaxVersionIDs: []int{9},
			BindingStatus: map[string]string{"rule": "BOUND", "rate": "BOUND", "tax": "BOUND"},
		},
		TranslatorVersion: temporalTranslatorVersion, EngineVersion: temporalEngineVersion,
		RoundingPolicy: TPRRoundingPolicy{Scale: 6, Mode: "HALF_UP"},
	}
}

func TestTemporalReplayIsDeterministicAndSnapshotBound(t *testing.T) {
	req := temporalReplayFixture(t)
	first, err := executeTemporalReplay(context.Background(), req)
	if err != nil {
		t.Fatal(err)
	}
	req.ExpectedHashes.GeneratedGRLSHA256 = first.GeneratedGRLSHA256
	req.ExpectedHashes.OriginalOutputSHA256 = first.OutputSHA256
	second, err := executeTemporalReplay(context.Background(), req)
	if err != nil {
		t.Fatal(err)
	}
	if first.OutputSHA256 != second.OutputSHA256 || !reflect.DeepEqual(first.Components, second.Components) || first.Summary != second.Summary {
		t.Fatalf("replay is not deterministic: first=%#v second=%#v", first, second)
	}
	if second.MatchesOriginalHash == nil || !*second.MatchesOriginalHash {
		t.Fatal("replay did not verify the original output hash")
	}
	if got := second.Summary.NetSalary; got != "5001000.000000" {
		t.Fatalf("unexpected fixed-six net salary %q", got)
	}
	if !reflect.DeepEqual(second.Provenance.RuleVersionIDs, []int{42}) ||
		!reflect.DeepEqual(second.Provenance.RateVersionIDs, []int{7}) ||
		!reflect.DeepEqual(second.Provenance.TaxVersionIDs, []int{9}) {
		t.Fatalf("version provenance was not snapshot-bound: %#v", second.Provenance)
	}
}

func TestTemporalReplayRejectsCorruptionAndUnsupportedVersions(t *testing.T) {
	tests := []struct {
		name string
		edit func(*ReplayRequest)
		code string
	}{
		{"facts hash corruption", func(req *ReplayRequest) { req.ExpectedHashes.FactsSHA256 = strings.Repeat("0", 64) }, "REPLAY_HASH_MISMATCH"},
		{"unsupported manifest", func(req *ReplayRequest) { req.ManifestVersion = "2.0" }, "REPLAY_SCHEMA_UNSUPPORTED"},
		{"missing rate identity", func(req *ReplayRequest) { req.VersionIdentities.RateVersionIDs = nil }, "REPLAY_VERSION_MISSING"},
		{"wrong engine", func(req *ReplayRequest) { req.EngineVersion = "current-engine" }, "REPLAY_SCHEMA_UNSUPPORTED"},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			req := temporalReplayFixture(t)
			test.edit(&req)
			_, err := executeTemporalReplay(context.Background(), req)
			assertValidationCode(t, err, test.code)
		})
	}
}

func TestCanonicalSHA256DoesNotHTMLEscapeComparisonOperators(t *testing.T) {
	value := map[string]interface{}{"operator": ">", "formula": "attendance.late_minutes > 0"}
	actual, err := canonicalSHA256(value)
	if err != nil {
		t.Fatal(err)
	}
	expected := sha256Text(`{"formula":"attendance.late_minutes > 0","operator":">"}`)
	if actual != expected {
		t.Fatalf("canonical hash escaped comparison operators: got %s want %s", actual, expected)
	}
}

func TestTemporalReplayRuntimeCorrelationAndResearchTrace(t *testing.T) {
	original := temporalReplayFixture(t)
	original.ExecutionUUID = "11111111-1111-4111-8111-111111111111"
	original.RequestID = "22222222-2222-4222-8222-222222222222"
	baseline, err := executeTemporalReplay(context.Background(), original)
	if err != nil {
		t.Fatal(err)
	}

	replay := original
	replay.RequestID = "33333333-3333-4333-8333-333333333333"
	replay.OriginalRequestID = original.RequestID
	replay.ReplayUUID = "44444444-4444-4444-8444-444444444444"
	replay.LaravelCorrelationID = "55555555-5555-4555-8555-555555555555"
	replay.ResearchTrace = true
	replay.ExpectedHashes.OriginalOutputSHA256 = baseline.OutputSHA256
	actual, err := executeTemporalReplay(context.Background(), replay)
	if err != nil {
		t.Fatal(err)
	}
	if actual.RequestID != replay.RequestID || actual.ReplayUUID != replay.ReplayUUID || actual.LaravelCorrelationID != replay.LaravelCorrelationID {
		t.Fatalf("runtime correlation was not returned: %#v", actual)
	}
	if actual.Provenance.RequestID != original.RequestID || actual.OutputSHA256 != baseline.OutputSHA256 {
		t.Fatalf("runtime IDs changed historical output provenance/hash: %#v", actual.Provenance)
	}
	if len(actual.CorrelationEvents) < 7 || actual.TranslatorTraceID == "" || actual.GRULEExecutionID == "" {
		t.Fatalf("runtime events are incomplete: %#v", actual.CorrelationEvents)
	}
	if len(actual.RoundingTrace) == 0 || actual.RoundingTrace[0].RoundedResult == "" {
		t.Fatalf("research rounding trace is missing: %#v", actual.RoundingTrace)
	}
}

func TestReplayHandlerRejectsMismatchedHTTPCorrelation(t *testing.T) {
	req := temporalReplayFixture(t)
	raw, err := json.Marshal(req)
	if err != nil {
		t.Fatal(err)
	}
	httpRequest := httptest.NewRequest(http.MethodPost, "/replay", strings.NewReader(string(raw)))
	httpRequest.Header.Set("X-Request-ID", "different-request")
	recorder := httptest.NewRecorder()
	replayRules(recorder, httpRequest)
	if recorder.Code != http.StatusBadRequest || !strings.Contains(recorder.Body.String(), "REPLAY_MANIFEST_INVALID") {
		t.Fatalf("unexpected response: status=%d body=%s", recorder.Code, recorder.Body.String())
	}
}

func TestCurrentExecutionSupportsIndependentScaleTwoRoundingPolicy(t *testing.T) {
	req := temporalReplayFixture(t)
	req.FactsSnapshot["rates"].(map[string]interface{})["bonus_rate"] = json.Number("1000.125001")
	raw, err := json.Marshal(req.RuleSetSnapshot)
	if err != nil {
		t.Fatal(err)
	}
	var ruleset TPRRuleSet
	if err := json.Unmarshal(raw, &ruleset); err != nil {
		t.Fatal(err)
	}
	ruleset.RoundingPolicy.Scale = 2
	result, err := ExecuteTPRRuleSet(context.Background(), &ruleset, req.FactsSnapshot, req.ComponentTypesSnapshot)
	if err != nil {
		t.Fatal(err)
	}
	if len(result.Components) != 1 || result.Components[0].Amount != 1000.13 {
		t.Fatalf("scale-2 HALF_UP was not applied: %#v", result.Components)
	}
}
