<?php

declare(strict_types=1);

namespace Plugin\Gohey\ClientUsage\Http\Controller;

use Hyperf\Di\Annotation\Inject;
use Hyperf\HttpServer\Annotation\Controller;
use Hyperf\HttpServer\Annotation\GetMapping;
use Hyperf\HttpServer\Annotation\PostMapping;
use Mine\Annotation\Auth;
use Mine\Annotation\Permission;
use Mine\MineController;
use Plugin\Gohey\ClientUsage\Http\Request\ClientUsageReportRequest;
use Plugin\Gohey\ClientUsage\Service\ClientUsageService;
use Psr\Http\Message\ResponseInterface;

#[Controller(prefix: 'admin/app/clientUsage')]
#[Auth]
class ClientUsageController extends MineController
{
    #[Inject]
    protected ClientUsageService $service;

    /**
     * 客户端上报使用记录（桌面端调用）.
     */
    #[PostMapping('report')]
    #[Permission('app:clientUsage:report')]
    public function report(ClientUsageReportRequest $request): ResponseInterface
    {
        $authUser = user();
        $authUsername = (string) ($authUser->username ?? $authUser->getUsername() ?? '');

        $id = $this->service->report(
            $request->validated(),
            $request->getServerParams(),
            $authUsername
        );

        return $this->success(['id' => $id]);
    }

    /**
     * 管理员查询使用记录.
     */
    #[GetMapping('list')]
    #[Permission('app:clientUsage:list')]
    public function list(): ResponseInterface
    {
        return $this->success(
            $this->service->paginate($this->request->all())
        );
    }
}
