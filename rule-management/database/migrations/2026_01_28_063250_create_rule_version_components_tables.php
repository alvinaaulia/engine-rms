<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::create('rule_version_components', function (Blueprint $table) {
            $table->id();
            $table->foreignId('rule_version_id')->constrained('rule_versions')->cascadeOnDelete();
            $table->foreignId('component_id')->constrained('salary_components', 'component_id')->restrictOnDelete();
            $table->timestamps();

            $table->unique(['rule_version_id', 'component_id'], 'uq_rvc_rule_version_component');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('rule_version_components');
    }
};