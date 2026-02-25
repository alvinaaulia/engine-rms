<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\Hash;
use App\Models\User;

class UsersSeeder extends Seeder
{
    public function run(): void
    {
        // ===== HR USER =====
        User::updateOrCreate(
            ['email' => 'hr@company.test'],
            [
                'name' => 'HR User',
                'password' => Hash::make('password'),
                'role' => 'HR',
            ]
        );
        
        User::updateOrCreate(
            ['email' => 'director@company.test'],
            [
                'name' => 'Director User',
                'password' => Hash::make('password'),
                'role' => 'DIRECTOR',
            ]
        );
    }
}
