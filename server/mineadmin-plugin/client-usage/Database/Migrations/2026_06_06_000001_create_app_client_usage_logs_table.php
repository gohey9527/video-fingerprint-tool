<?php

declare(strict_types=1);

use Hyperf\Database\Migrations\Migration;
use Hyperf\Database\Schema\Blueprint;
use Hyperf\Database\Schema\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('app_client_usage_logs', function (Blueprint $table) {
            $table->engine = 'InnoDB';
            $table->comment('桌面客户端使用记录');
            $table->bigIncrements('id');
            $table->string('username', 64)->comment('登录用户名');
            $table->string('client_id', 64)->comment('客户端标识');
            $table->string('client_platform', 16)->comment('windows/macos/linux');
            $table->string('client_version', 32)->default('')->comment('客户端版本');
            $table->string('event_type', 32)->comment('login/logout/generate_video');
            $table->string('event_detail', 512)->default('')->comment('附加信息');
            $table->string('ip_address', 45)->nullable()->comment('来源 IP');
            $table->string('user_agent', 255)->nullable()->comment('User-Agent');
            $table->dateTime('created_at')->useCurrent()->comment('记录时间');

            $table->index('username');
            $table->index('client_id');
            $table->index('client_platform');
            $table->index('event_type');
            $table->index(['created_at']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('app_client_usage_logs');
    }
};
