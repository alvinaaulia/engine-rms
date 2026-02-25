<?php

namespace App\Http\Controllers;

use App\Models\SalaryComponent;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use App\Models\RuleVersion;
use App\Services\AuditLogger;


class SalaryComponentController extends Controller
{
    public function index()
    {
        return SalaryComponent::orderBy('component_code')->get();
    }
    public function store(Request $request)
    {
        $data = $request->validate([
            'component_code' => ['required', 'string', 'max:50', 'unique:salary_components,component_code'],
            'component_name' => ['required', 'string', 'max:150'],
            'component_type' => ['required', 'in:EARNING,DEDUCTION'],
            'description' => ['nullable', 'string'],
            'is_taxable' => ['nullable', 'boolean'],
            'is_active' => ['nullable', 'boolean'],
        ]);

        $data['component_code'] = strtoupper(trim($data['component_code']));

        $component = SalaryComponent::create([
            'component_code' => $data['component_code'],
            'component_name' => $data['component_name'],
            'component_type' => $data['component_type'],
            'description' => $data['description'] ?? null,
            'is_taxable' => $data['is_taxable'] ?? false,
            'is_active' => $data['is_active'] ?? true,
        ]);

        AuditLogger::log(
            $request,
            'COMPONENT_CREATE',
            null,
            null,
            ['component' => $component->toArray()],
            "Created salary component {$component->component_code}"
        );

        return response()->json([
            'message' => 'Component created',
            'data' => $component
        ], 201);
    }

    public function show(SalaryComponent $component)
    {
        return $component;
    }

    public function update(Request $request, SalaryComponent $component)
    {
        $data = $request->validate([
            'component_code' => ['sometimes', 'string', 'max:50', 'unique:salary_components,component_code,' . $component->component_id . ',component_id'],
            'component_name' => ['sometimes', 'string', 'max:150'],
            'component_type' => ['sometimes', 'in:EARNING,DEDUCTION'],
            'description' => ['nullable', 'string'],
            'is_taxable' => ['nullable', 'boolean'],
            'is_active' => ['nullable', 'boolean'],
        ]);

        if (isset($data['component_code'])) {
            $data['component_code'] = strtoupper(trim($data['component_code']));
        }

        $wasActive = (bool) $component->is_active;

        return DB::transaction(function () use ($request, $component, $data, $wasActive) {

            $beforeComponent = $component->toArray();

            $component->update($data);
            $component->refresh();

            $afterComponent = $component->toArray();

            AuditLogger::log(
                $request,
                'COMPONENT_UPDATE',
                null, // rule_version_id tidak relevan untuk component
                ['component' => $beforeComponent],
                ['component' => $afterComponent],
                "Updated salary component {$component->component_code}"
            );

            // ===== logic auto-inactivate rules kalau komponen jadi nonaktif =====
            $incomingIsActive = array_key_exists('is_active', $data)
                ? filter_var($data['is_active'], FILTER_VALIDATE_BOOLEAN, FILTER_NULL_ON_FAILURE)
                : null;

            $nowInactive = $wasActive === true
                && array_key_exists('is_active', $data)
                && $incomingIsActive === false;

            $affectedRuleVersions = [];

            if ($nowInactive) {

                $ruleVersionIds = DB::table('rule_version_components')
                    ->where('component_id', $component->component_id)
                    ->pluck('rule_version_id')
                    ->unique()
                    ->values()
                    ->all();

                if (!empty($ruleVersionIds)) {

                    $activeBefore = RuleVersion::whereIn('id', $ruleVersionIds)
                        ->where('status', RuleVersion::STATUS_ACTIVE)
                        ->pluck('id')
                        ->all();

                    if (!empty($activeBefore)) {
                        RuleVersion::whereIn('id', $activeBefore)->update([
                            'status' => RuleVersion::STATUS_INACTIVE,
                            'updated_at' => now(),
                        ]);

                        $affectedRuleVersions = RuleVersion::whereIn('id', $activeBefore)
                            ->get(['id', 'rule_id', 'version', 'status'])
                            ->toArray();

                        AuditLogger::log(
                            $request,
                            'AUTO_RULE_INACTIVATE_BY_COMPONENT',
                            null,
                            [
                                'component_id' => $component->component_id,
                                'component_code' => $component->component_code,
                                'reason' => 'component disabled',
                            ],
                            [
                                'inactivated_rule_version_ids' => $activeBefore
                            ],
                            "Auto-inactivated ACTIVE rule versions due to component disabled"
                        );
                    }
                }
            }

            return response()->json([
                'message' => 'Component updated',
                'component' => $component,
                'auto_inactivated_rule_versions' => $affectedRuleVersions,
            ]);
        });
    }
    public function disable(Request $request, SalaryComponent $component)
    {
        $before = $component->toArray();

        $component->update(['is_active' => false]);
        $component->refresh();

        AuditLogger::log(
            $request,
            'COMPONENT_DISABLE',
            null,
            ['component' => $before],
            ['component' => $component->toArray()],
            "Disabled salary component {$component->component_code}"
        );

        return response()->json([
            'message' => 'Component disabled',
            'component' => $component
        ]);
    }
    public function activate(Request $request, SalaryComponent $component)
    {
        if ((bool) $component->is_active === true) {
            return response()->json([
                'message' => 'Component already active',
                'component' => $component
            ], 200);
        }

        $before = $component->toArray();

        $component->update(['is_active' => true]);
        $component->refresh();

        AuditLogger::log(
            $request,
            'COMPONENT_ACTIVATE',
            null,
            ['component' => $before],
            ['component' => $component->toArray()],
            "Activated salary component {$component->component_code}"
        );

        return response()->json([
            'message' => 'Component activated',
            'component' => $component
        ], 200);
    }
}
