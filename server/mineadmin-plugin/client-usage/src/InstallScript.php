<?php

declare(strict_types=1);

namespace Plugin\Gohey\ClientUsage;

use Hyperf\Command\Concerns\InteractsWithIO;
use Hyperf\Context\ApplicationContext;
use Hyperf\Contract\ApplicationInterface;
use Symfony\Component\Console\Input\ArrayInput;
use Symfony\Component\Console\Output\ConsoleOutput;
use Symfony\Component\Console\Output\NullOutput;

class InstallScript
{
    use InteractsWithIO;

    public function __invoke(): void
    {
        $this->output = new ConsoleOutput();

        $this->info('========================================');
        $this->info('客户端使用统计插件 (gohey/client-usage)');
        $this->info('========================================');

        $this->runMigrations();

        $this->info('插件安装成功！');
        $this->info('请在 MineAdmin 后台为管理员角色分配权限：');
        $this->info('  - app:clientUsage:list   （查看统计）');
        $this->info('  - app:clientUsage:report （上报，建议分配给所有登录用户）');
        $this->info('========================================');
    }

    protected function runMigrations(): void
    {
        $migrationPath = dirname(__DIR__) . '/Database/Migrations';
        if (! is_dir($migrationPath)) {
            $this->warn('未找到迁移目录，跳过数据库迁移');

            return;
        }

        $app = ApplicationContext::getContainer()->get(ApplicationInterface::class);
        $app->setAutoExit(false);

        $input = new ArrayInput([
            'command' => 'migrate',
            '--path' => $migrationPath,
            '--force' => true,
        ]);

        $app->run($input, new NullOutput());
        $this->info('数据库迁移执行成功');
    }
}
