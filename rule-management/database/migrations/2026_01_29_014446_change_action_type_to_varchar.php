<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;

return new class extends Migration {
    public function up(): void
    {
        DB::statement("ALTER TABLE rule_audit_logs MODIFY action_type VARCHAR(60) NOT NULL");
    }

    public function down(): void
    {
        // Kalau mau balik ke enum, harus ditulis ulang. Biasanya tidak perlu.
    }
};
