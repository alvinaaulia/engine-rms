<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\DB;
use Illuminate\Validation\ValidationException;

use App\Models\Rule;
use App\Models\RuleVersion;
use App\Models\SalaryComponent;
use App\Models\RuleVersionComponent;

use App\Services\AuditLogger;

class RuleController extends Controller
{
    /**
     * Require DIRECTOR role for approve/reject.
     */
    private function requireDirector(Request $request): void
    {
        $u = $request->user();
        if (!$u || ($u->role ?? null) !== 'DIRECTOR') {
            abort(403, 'Only DIRECTOR can approve/reject rules.');
        }
    }

    /**
     * CREATE rule + first version (DRAFT, approval PENDING).
     * Also maps the rule_version to a salary component based on action.code.
     */
    public function store(Request $request)
    {
        $data = $request->validate([
            'name' => 'required|string|max:150',
            'definition' => 'required|array',

            'definition.conditions' => 'required|array|min:1',
            'definition.action' => 'required|array',
            'definition.action.type' => 'required|string',
            'definition.action.code' => 'required|string|max:50',
            'definition.action.formula' => 'required|string',
        ]);

        // Normalize action code
        $actionCode = strtoupper(trim($data['definition']['action']['code']));
        $data['definition']['action']['code'] = $actionCode;

        // Ensure component exists & active
        $component = SalaryComponent::where('component_code', $actionCode)
            ->where('is_active', true)
            ->first();

        if (!$component) {
            throw ValidationException::withMessages([
                'definition.action.code' => [
                    "Component code '{$actionCode}' tidak ditemukan di salary_components atau tidak aktif."
                ],
            ]);
        }

        return DB::transaction(function () use ($request, $data, $component) {

            // 1) Create rule master
            $rule = Rule::create([
                'name' => $data['name'],
            ]);

            // 2) Create first rule version (DRAFT + PENDING approval)
            $version = RuleVersion::create([
                'rule_id' => $rule->id,
                'version' => 1,
                'status' => RuleVersion::STATUS_DRAFT,
                'approval_status' => RuleVersion::APPROVAL_PENDING,
                'definition' => $data['definition'],
                'created_by' => $request->user()?->id,
            ]);

            // 3) Map rule_version -> component_id
            RuleVersionComponent::create([
                'rule_version_id' => $version->id,
                'component_id' => $component->component_id,
            ]);

            // ===== AUDIT =====
            AuditLogger::log(
                $request,
                'RULE_CREATE',
                $version->id,
                null,
                ['rule_id' => $rule->id, 'rule_name' => $rule->name],
                "Created rule master"
            );

            AuditLogger::log(
                $request,
                'RULE_VERSION_CREATE',
                $version->id,
                null,
                [
                    'rule_id' => $rule->id,
                    'version' => $version->version,
                    'status' => $version->status,
                    'approval_status' => $version->approval_status,
                    'definition' => $version->definition,
                    'component_code' => $component->component_code,
                    'component_id' => $component->component_id,
                ],
                "Created first rule version (DRAFT, approval PENDING)"
            );

            return response()->json([
                'message' => 'Rule saved (DRAFT, PENDING approval) and mapped to component',
                'rule_id' => $rule->id,
                'rule_version_id' => $version->id,
                'version' => $version->version,
                'status' => $version->status,
                'approval_status' => $version->approval_status,
                'component_code' => $component->component_code,
                'component_id' => $component->component_id,
            ], 201);
        });
    }

    /**
     * OPTIONAL: Submit a DRAFT rule version for approval.
     * Sets approval_status to PENDING and clears prior decision fields.
     */
    public function submitVersion(Request $request, RuleVersion $ruleVersion)
    {
        if ($ruleVersion->status !== RuleVersion::STATUS_DRAFT) {
            abort(422, 'Only DRAFT versions can be submitted.');
        }

        $before = $ruleVersion->toArray();

        $ruleVersion->update([
            'approval_status' => RuleVersion::APPROVAL_PENDING,
            'decision_notes' => null,
            'approved_by' => null,
            'approved_at' => null,
            'rejected_by' => null,
            'rejected_at' => null,
        ]);

        AuditLogger::log(
            $request,
            'RULE_VERSION_SUBMIT',
            $ruleVersion->id,
            $before,
            $ruleVersion->fresh()->toArray(),
            'Submitted rule version for director approval'
        );

        return response()->json([
            'message' => 'Rule version submitted for approval',
            'rule_version' => $ruleVersion->fresh(),
        ]);
    }

    /**
     * DIRECTOR: Approve a rule version.
     */
    public function approveVersion(Request $request, RuleVersion $ruleVersion)
    {
        $this->requireDirector($request);

        $data = $request->validate([
            'notes' => ['nullable', 'string', 'max:1000'],
        ]);

        $before = $ruleVersion->toArray();

        $ruleVersion->update([
            'approval_status' => RuleVersion::APPROVAL_APPROVED,
            'approved_by' => $request->user()->id,
            'approved_at' => now(),
            'rejected_by' => null,
            'rejected_at' => null,
            'decision_notes' => $data['notes'] ?? null,
        ]);

        AuditLogger::log(
            $request,
            'RULE_VERSION_APPROVE',
            $ruleVersion->id,
            $before,
            $ruleVersion->fresh()->toArray(),
            'Director approved rule version'
        );

        return response()->json([
            'message' => 'Rule version approved',
            'rule_version' => $ruleVersion->fresh(),
        ]);
    }

    /**
     * DIRECTOR: Reject a rule version (notes required).
     */
    public function rejectVersion(Request $request, RuleVersion $ruleVersion)
    {
        $this->requireDirector($request);

        $data = $request->validate([
            'notes' => ['required', 'string', 'max:1000'],
        ]);

        $before = $ruleVersion->toArray();

        $ruleVersion->update([
            'approval_status' => RuleVersion::APPROVAL_REJECTED,
            'rejected_by' => $request->user()->id,
            'rejected_at' => now(),
            'approved_by' => null,
            'approved_at' => null,
            'decision_notes' => $data['notes'],
        ]);

        AuditLogger::log(
            $request,
            'RULE_VERSION_REJECT',
            $ruleVersion->id,
            $before,
            $ruleVersion->fresh()->toArray(),
            'Director rejected rule version'
        );

        return response()->json([
            'message' => 'Rule version rejected',
            'rule_version' => $ruleVersion->fresh(),
        ]);
    }

    /**
     * Activate a version of a rule.
     * Enforced by RuleVersion::activate() -> must be APPROVED.
     */
    public function activate(Request $request, Rule $rule, int $version)
    {
        $rv = RuleVersion::where('rule_id', $rule->id)
            ->where('version', $version)
            ->firstOrFail();

        $before = $rv->toArray();

        // This should throw if not approved
        $rv->activate();

        $after = $rv->fresh()->toArray();

        AuditLogger::log(
            $request,
            'RULE_VERSION_ACTIVATE',
            $rv->id,
            $before,
            $after,
            'Activated approved rule version'
        );

        return response()->json([
            'message' => 'Rule version activated',
            'rule_id' => $rule->id,
            'version' => $version,
            'rule_version' => $rv->fresh(),
        ]);
    }

    /**
     * Disable a rule version (set INACTIVE).
     */
    public function disableVersion(Request $request, RuleVersion $ruleVersion)
    {
        $before = $ruleVersion->toArray();

        if ($ruleVersion->status === RuleVersion::STATUS_ACTIVE) {
            $ruleVersion->update(['status' => RuleVersion::STATUS_INACTIVE]);
        }

        $after = $ruleVersion->fresh()->toArray();

        AuditLogger::log(
            $request,
            'RULE_VERSION_DISABLE',
            $ruleVersion->id,
            $before,
            $after,
            "Disabled rule version (set to INACTIVE)"
        );

        return response()->json([
            'message' => 'Rule version disabled (INACTIVE)',
            'rule_version' => $ruleVersion->fresh(),
        ]);
    }

    /**
     * Execute payroll rules:
     * - fetch ACTIVE rule_versions
     * - validate referenced components are active
     * - send to Go engine
     * - return components + summary
     */
    public function execute(Request $request)
    {
        $data = $request->validate([
            'facts' => 'required|array',
            'facts.employee' => 'required|array',
            'facts.attendance' => 'required|array',
            'facts.rates' => 'required|array',
        ]);

        $rules = RuleVersion::where('status', RuleVersion::STATUS_ACTIVE)->get();

        if ($rules->isEmpty()) {
            return response()->json([
                'message' => 'No ACTIVE rules found.',
                'sent' => [
                    'rules' => [],
                    'facts' => $data['facts'],
                ],
                'engine_response' => [
                    'components' => [],
                    'summary' => null,
                ],
            ], 200);
        }

        // Validate action.code exists & active in salary_components
        $codes = $rules->map(function ($rv) {
            $def = is_array($rv->definition) ? $rv->definition : [];
            $code = $def['action']['code'] ?? null;
            return is_string($code) ? strtoupper(trim($code)) : null;
        })->filter()->unique()->values();

        $activeCodes = SalaryComponent::whereIn('component_code', $codes)
            ->where('is_active', true)
            ->pluck('component_code')
            ->map(fn($x) => strtoupper(trim($x)))
            ->toArray();

        $missingOrInactive = $codes->diff($activeCodes)->values()->all();

        if (!empty($missingOrInactive)) {
            throw ValidationException::withMessages([
                'rules' => [
                    'Terdapat action.code yang tidak terdaftar atau tidak aktif pada salary_components: ' .
                    implode(', ', $missingOrInactive),
                ],
            ]);
        }

        $definitions = $rules->map(function ($rv) {
            $def = $rv->definition;
            if (isset($def['action']['code']) && is_string($def['action']['code'])) {
                $def['action']['code'] = strtoupper(trim($def['action']['code']));
            }
            return $def;
        })->values()->all();

        $payload = [
            'rules' => $definitions,
            'facts' => $data['facts'],
        ];

        $response = Http::post('http://localhost:8081/execute', $payload);

        AuditLogger::log(
            $request,
            'RULE_EXECUTE',
            null,
            ['sent' => $payload],
            ['engine_response' => $response->json(), 'status' => $response->status()],
            "Executed payroll rules"
        );

        return response()->json([
            'sent' => $payload,
            'engine_response' => $response->json(),
            'status' => $response->status(),
            'raw' => $response->body(),
        ], $response->successful() ? 200 : 500);
    }
}
