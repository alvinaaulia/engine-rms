<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::create('salary_components', function (Blueprint $table) {
            $table->id('component_id');

            $table->string('component_code', 50)->unique(); // ex: TUNJANGAN_THR
            $table->string('component_name', 150);
            $table->enum('component_type', ['EARNING', 'DEDUCTION']); // untuk gross/net

            $table->text('description')->nullable();
            $table->boolean('is_taxable')->default(false);
            $table->boolean('is_active')->default(true);

            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('salary_components');
    }
};
