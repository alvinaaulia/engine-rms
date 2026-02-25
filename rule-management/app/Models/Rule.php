<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Rule extends Model
{
    use HasFactory;

    /**
     * The attributes that are mass assignable.
     *
     * @var array<int, string>
     */
    protected $fillable = [
        'name',
        'description',
        'is_active',
    ];

    /**
     * The attributes that should be cast.
     *
     * @var array<string, string>
     */
    protected $casts = [
        'is_active' => 'boolean',
    ];

    /**
     * Get the versions for the rule.
     */
    public function versions(): HasMany
    {
        return $this->hasMany(RuleVersion::class);
    }

    /**
     * Get the active version of the rule.
     */
    public function activeVersion()
    {
        return $this->versions()->where('status', 'ACTIVE')->first();
    }

    /**
     * Get the latest version of the rule.
     */
    public function latestVersion()
    {
        return $this->versions()->latest('version')->first();
    }
}
