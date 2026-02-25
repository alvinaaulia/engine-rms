<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::create('rule_audit_logs', function (Blueprint $table) {
            $table->id('audit_log_id');

            $table->unsignedBigInteger('rule_version_id')->nullable();
            $table->unsignedBigInteger('user_id')->nullable();

            $table->enum('action_type', [
                'RULE_CREATE',
                'RULE_VERSION_CREATE',
                'RULE_VERSION_ACTIVATE',
                'RULE_VERSION_DISABLE',
                'RULE_EXECUTE',
                'COMPONENT_CREATE',
                'COMPONENT_UPDATE',
                'COMPONENT_DISABLE',
                'AUTO_RULE_INACTIVATE_BY_COMPONENT'
            ]);

            $table->json('before_json')->nullable();
            $table->json('after_json')->nullable();
            $table->text('notes')->nullable();

            $table->string('ip_address', 45)->nullable();
            $table->timestamp('action_date')->useCurrent();

            $table->timestamps();

            $table->index(['rule_version_id']);
            $table->index(['action_type']);
            $table->index(['action_date']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('rule_audit_logs');
    }
};
