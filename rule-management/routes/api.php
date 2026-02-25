<?php

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Route;
use App\Http\Controllers\RuleController;
use App\Http\Controllers\SalaryComponentController;
use App\Models\RuleAuditLog;


Route::middleware('auth:sanctum')->group(function () {
    Route::post('/rules', [RuleController::class, 'store']);
    Route::post('/rules/{rule}/activate/{version}', [RuleController::class, 'activate']);
    Route::post('/payroll/run', [RuleController::class, 'execute']);

    Route::get('/components', [SalaryComponentController::class, 'index']);
    Route::post('/components', [SalaryComponentController::class, 'store']);
    Route::get('/components/{component}', [SalaryComponentController::class, 'show']);
    Route::put('/components/{component}', [SalaryComponentController::class, 'update']);
    Route::post('/components/{component}/activate', [SalaryComponentController::class, 'activate']);
    Route::post('/components/{component}/disable', [SalaryComponentController::class, 'disable']);

    Route::post('/rules/versions/{ruleVersion}/submit', [RuleController::class, 'submitVersion']);
    Route::post('/rules/versions/{ruleVersion}/approve', [RuleController::class, 'approveVersion']);
    Route::post('/rules/versions/{ruleVersion}/reject', [RuleController::class, 'rejectVersion']);

    Route::get('/audit-logs', function () {
        return RuleAuditLog::orderByDesc('audit_log_id')->limit(200)->get();
    });
});
