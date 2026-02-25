<?php

namespace App\Services;

use App\Models\RuleAuditLog;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

class AuditLogger
{
    public static function log(
        Request $request,
        string $actionType,
        ?int $ruleVersionId = null,
        ?array $before = null,
        ?array $after = null,
        ?string $notes = null
    ): RuleAuditLog {
        return RuleAuditLog::create([
            'rule_version_id' => $ruleVersionId,
            'user_id' => Auth::guard('sanctum')->id(),
            'action_type' => $actionType,
            'before_json' => $before,
            'after_json' => $after,
            'notes' => $notes,
            'ip_address' => $request->ip(),
            'action_date' => now(),
        ]);
    }
}
