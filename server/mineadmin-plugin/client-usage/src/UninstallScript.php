<?php

declare(strict_types=1);

namespace Plugin\Gohey\ClientUsage;

use Hyperf\Command\Concerns\InteractsWithIO;
use Symfony\Component\Console\Output\ConsoleOutput;

class UninstallScript
{
    use InteractsWithIO;

    public function __invoke(): void
    {
        $this->output = new ConsoleOutput();
        $this->info('客户端使用统计插件已卸载（数据表 app_client_usage_logs 保留，如需删除请手动执行 DROP TABLE）');
    }
}
