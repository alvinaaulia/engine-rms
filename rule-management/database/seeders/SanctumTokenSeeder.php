<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use App\Models\User;

class SanctumTokenSeeder extends Seeder
{
    public function run(): void
    {
        $hr = User::where('email', 'hr@company.test')->first();
        $director = User::where('email', 'director@company.test')->first();

        if ($hr) {
            $token = $hr->createToken('hr-token')->plainTextToken;
            echo "HR TOKEN:\n$token\n\n";
        }

        if ($director) {
            $token = $director->createToken('director-token')->plainTextToken;
            echo "DIRECTOR TOKEN:\n$token\n\n";
        }
    }
}
