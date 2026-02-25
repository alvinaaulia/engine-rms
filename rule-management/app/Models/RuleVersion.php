<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use App\Models\SalaryComponent;


class RuleVersion extends Model
{
    use HasFactory;

    /**
     * Status constants
     */
    const STATUS_DRAFT = 'DRAFT';
    const STATUS_ACTIVE = 'ACTIVE';
    const STATUS_INACTIVE = 'INACTIVE';
    const STATUS_ARCHIVED = 'ARCHIVED';

    const APPROVAL_PENDING = 'PENDING';
    const APPROVAL_APPROVED = 'APPROVED';
    const APPROVAL_REJECTED = 'REJECTED';


    /**
     * The attributes that are mass assignable.
     *
     * @var array<int, string>
     */
    protected $fillable = [
        'rule_id',
        'version',
        'status',
        'approval_status',
        'definition',
        'created_by',
        'approved_by',
        'approved_at',
        'rejected_by',
        'rejected_at',
        'decision_notes',
        'activated_at',
    ];


    /**
     * The attributes that should be cast.
     *
     * @var array<string, string>
     */
    protected $casts = [
        'definition' => 'array',
        'activated_at' => 'datetime',
        'approved_at' => 'datetime',
        'rejected_at' => 'datetime',
    ];

    /**
     * Get the rule that owns the version.
     */
    public function rule(): BelongsTo
    {
        return $this->belongsTo(Rule::class);
    }

    /**
     * Scope a query to only include active versions.
     */
    public function scopeActive($query)
    {
        return $query->where('status', self::STATUS_ACTIVE);
    }

    /**
     * Activate this version.
     */
    public function activate()
    {
        // ===== 1. WAJIB sudah di-approve direktur =====
        if ($this->approval_status !== self::APPROVAL_APPROVED) {
            throw new \RuntimeException(
                "Rule version must be APPROVED before activation."
            );
        }

        // ===== 2. Nonaktifkan versi lain dari rule yang sama =====
        static::where('rule_id', $this->rule_id)
            ->where('status', self::STATUS_ACTIVE)
            ->update(['status' => self::STATUS_INACTIVE]);

        // ===== 3. Aktifkan versi ini =====
        $this->update([
            'status' => self::STATUS_ACTIVE,
            'activated_at' => now(),
        ]);
    }



    /**
     * Check if this version is active.
     */
    public function isActive(): bool
    {
        return $this->status === self::STATUS_ACTIVE;
    }

    /**
     * Check if this version is draft.
     */
    public function isDraft(): bool
    {
        return $this->status === self::STATUS_DRAFT;
    }

    public function getNormalizedDefinitionAttribute(): array
    {
        $definition = $this->definition;

        // Pastikan conditions selalu array
        if (!isset($definition['conditions']) || !is_array($definition['conditions'])) {
            $definition['conditions'] = [];
        }

        foreach ($definition['conditions'] as &$condition) {

            // 1. Field → auto prefix employee.
            // if (isset($condition['field']) && !str_contains($condition['field'], '.')) {
            //     $condition['field'] = 'employee.' . $condition['field'];
            // }

            // 2. Operator → normalisasi
            if (isset($condition['operator'])) {
                if ($condition['operator'] === '=') {
                    $condition['operator'] = '==';
                }
            }

            // 3. Value → tidak perlu diapa-apakan (Go handle quoting)
        }

        // Pastikan action ada
        if (!isset($definition['action'])) {
            $definition['action'] = [
                'type' => 'UNKNOWN',
                'value' => 0
            ];
        }

        return $definition;
    }

    public function components()
    {
        return $this->belongsToMany(
            SalaryComponent::class,
            'rule_version_components',
            'rule_version_id',
            'component_id'
        );
    }

    public function salaryComponents()
    {
        return $this->belongsToMany(
            \App\Models\SalaryComponent::class,
            'rule_version_components',
            'rule_version_id',
            'component_id'
        );
    }
}
