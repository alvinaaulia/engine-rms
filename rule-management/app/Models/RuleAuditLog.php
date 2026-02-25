<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class RuleAuditLog extends Model
{
    use HasFactory;

    protected $primaryKey = 'audit_log_id';
    protected $table = 'rule_audit_logs';

    protected $fillable = [
        'rule_version_id',
        'user_id',
        'action_type',
        'before_json',
        'after_json',
        'notes',
        'ip_address',
        'action_date',
    ];

    protected $casts = [
        'before_json' => 'array',
        'after_json' => 'array',
        'action_date' => 'datetime',
    ];
}
