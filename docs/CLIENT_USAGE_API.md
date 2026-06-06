# 客户端使用统计 API 设计

> 面向 MineAdmin 服务端开发，与桌面客户端 `video-fingerprint-tool` 对接。  
> 客户端已实现上报与查询逻辑，服务端按本文档实现后即可在管理员面板查看**全量用户使用记录**。

---

## 1. 目标

| 能力 | 说明 |
|------|------|
| 上报 | 客户端登录 / 退出 / 生成视频时自动上报 |
| 查询 | 管理员通过 JWT Token 查询全部用户的使用记录 |
| 维度 | 用户名、客户端 ID、平台（windows/macos）、版本、事件类型、详情、时间 |

---

## 2. 数据库设计

```sql
CREATE TABLE app_client_usage_logs (
    id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(64)  NOT NULL COMMENT '登录用户名（小写）',
    client_id     VARCHAR(64)  NOT NULL COMMENT '客户端标识，如 video-fingerprint-tool',
    client_platform VARCHAR(16) NOT NULL COMMENT 'windows / macos / linux',
    client_version  VARCHAR(32) NOT NULL DEFAULT '' COMMENT '客户端版本号',
    event_type    VARCHAR(32)  NOT NULL COMMENT 'login / logout / generate_video',
    event_detail  VARCHAR(512) NOT NULL DEFAULT '' COMMENT '附加信息',
    ip_address    VARCHAR(45)  NULL COMMENT '上报来源 IP（服务端填充）',
    user_agent    VARCHAR(255) NULL COMMENT 'User-Agent（服务端填充）',
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_username (username),
    INDEX idx_client_id (client_id),
    INDEX idx_event_type (event_type),
    INDEX idx_created_at (created_at DESC),
    INDEX idx_client_platform (client_platform)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='桌面客户端使用记录';
```

### 事件类型

| event_type | 触发时机 | event_detail 示例 |
|------------|----------|-------------------|
| `login` | 用户登录成功 | 空 |
| `logout` | 用户退出登录 | 空 |
| `generate_video` | 开始批量生成 | `count=5; source=demo.mp4` |

---

## 3. API 接口

### 3.1 上报使用记录

```
POST /admin/app/clientUsage/report
Authorization: Bearer {access_token}
Content-Type: application/json
```

**权限**：任意已登录用户（JWT 有效即可）。

**请求体**

```json
{
  "username": "alice",
  "client_id": "video-fingerprint-tool",
  "client_platform": "windows",
  "client_version": "1.0.0",
  "event_type": "generate_video",
  "event_detail": "count=5; source=demo.mp4",
  "created_at": "2026-05-28T10:00:00+00:00"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 是 | 登录用户名 |
| client_id | string | 是 | 客户端标识 |
| client_platform | string | 是 | `windows` / `macos` |
| client_version | string | 否 | 版本号，默认空 |
| event_type | string | 是 | 见上表 |
| event_detail | string | 否 | 附加信息 |
| created_at | string | 否 | ISO8601；不传则用服务端当前时间 |

**校验规则**

- `username` 必须与 JWT 对应用户一致（防伪造）
- `client_id` 白名单：`video-fingerprint-tool`（可扩展）
- `event_type` 枚举：`login` / `logout` / `generate_video`

**成功响应**

```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "id": 1001
  }
}
```

**失败响应**

| code | 场景 |
|------|------|
| 401 | Token 无效或过期 |
| 403 | username 与 Token 用户不一致 |
| 422 | 参数校验失败 |

---

### 3.2 查询使用记录（管理员）

```
GET /admin/app/clientUsage/list?page=1&pageSize=200
Authorization: Bearer {access_token}
```

**权限**：仅管理员（角色含 `admin` 或用户名在管理员列表）。

**Query 参数**

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| page | int | 1 | 页码 |
| pageSize | int | 50 | 每页条数，最大 200 |
| username | string | - | 按用户名筛选 |
| client_id | string | - | 按客户端筛选 |
| client_platform | string | - | 按平台筛选 |
| event_type | string | - | 按事件类型筛选 |
| start_at | string | - | 起始时间 ISO8601 |
| end_at | string | - | 结束时间 ISO8601 |

**成功响应**

```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "list": [
      {
        "id": 1001,
        "username": "alice",
        "client_id": "video-fingerprint-tool",
        "client_platform": "windows",
        "client_version": "1.0.0",
        "event_type": "generate_video",
        "event_detail": "count=5; source=demo.mp4",
        "ip_address": "203.0.113.10",
        "created_at": "2026-05-28T10:00:00+00:00"
      }
    ],
    "total": 128,
    "page": 1,
    "pageSize": 200
  }
}
```

**失败响应**

| code | 场景 |
|------|------|
| 401 | Token 无效 |
| 403 | 非管理员 |

---

## 4. Hyperf / MineAdmin 参考实现

### 4.1 Request DTO

```php
<?php
declare(strict_types=1);

namespace App\Admin\Request;

use Mine\MineFormRequest;

class ClientUsageReportRequest extends MineFormRequest
{
    public function rules(): array
    {
        return [
            'username' => 'required|string|max:64',
            'client_id' => 'required|string|in:video-fingerprint-tool',
            'client_platform' => 'required|string|in:windows,macos,linux',
            'client_version' => 'nullable|string|max:32',
            'event_type' => 'required|string|in:login,logout,generate_video',
            'event_detail' => 'nullable|string|max:512',
            'created_at' => 'nullable|date',
        ];
    }
}
```

### 4.2 Controller

```php
<?php
declare(strict_types=1);

namespace App\Admin\Controller;

use App\Admin\Request\ClientUsageReportRequest;
use App\Admin\Service\ClientUsageService;
use Mine\Annotation\Auth;
use Mine\Annotation\Permission;
use Mine\MineController;
use Psr\Http\Message\ResponseInterface;

#[Auth]
class ClientUsageController extends MineController
{
    public function __construct(protected ClientUsageService $service) {}

    #[Permission('app:clientUsage:report')]
    public function report(ClientUsageReportRequest $request): ResponseInterface
    {
        $user = user(); // 当前 JWT 用户
        $data = $request->validated();

        if (strtolower($data['username']) !== strtolower($user->username)) {
            return $this->error('用户名与登录身份不一致', 403);
        }

        $id = $this->service->report($data, $request->getServerParams());

        return $this->success(['id' => $id]);
    }

    #[Permission('app:clientUsage:list')]
    public function list(): ResponseInterface
    {
        // 仅管理员可访问，Permission 中间件 + 角色校验
        $params = $this->request->all();
        $result = $this->service->paginate($params);

        return $this->success($result);
    }
}
```

### 4.3 Service

```php
<?php
declare(strict_types=1);

namespace App\Admin\Service;

use App\Admin\Model\AppClientUsageLog;
use Hyperf\DbConnection\Db;

class ClientUsageService
{
    public function report(array $data, array $server): int
    {
        $log = AppClientUsageLog::create([
            'username' => strtolower($data['username']),
            'client_id' => $data['client_id'],
            'client_platform' => $data['client_platform'],
            'client_version' => $data['client_version'] ?? '',
            'event_type' => $data['event_type'],
            'event_detail' => $data['event_detail'] ?? '',
            'ip_address' => $server['remote_addr'] ?? null,
            'user_agent' => $server['HTTP_USER_AGENT'] ?? null,
            'created_at' => $data['created_at'] ?? date('Y-m-d H:i:s'),
        ]);

        return (int) $log->id;
    }

    public function paginate(array $params): array
    {
        $page = max(1, (int) ($params['page'] ?? 1));
        $pageSize = min(200, max(1, (int) ($params['pageSize'] ?? 50)));

        $query = AppClientUsageLog::query()->orderByDesc('id');

        if (!empty($params['username'])) {
            $query->where('username', strtolower($params['username']));
        }
        if (!empty($params['client_id'])) {
            $query->where('client_id', $params['client_id']);
        }
        if (!empty($params['client_platform'])) {
            $query->where('client_platform', $params['client_platform']);
        }
        if (!empty($params['event_type'])) {
            $query->where('event_type', $params['event_type']);
        }
        if (!empty($params['start_at'])) {
            $query->where('created_at', '>=', $params['start_at']);
        }
        if (!empty($params['end_at'])) {
            $query->where('created_at', '<=', $params['end_at']);
        }

        $paginator = $query->paginate($pageSize, ['*'], 'page', $page);

        return [
            'list' => $paginator->items(),
            'total' => $paginator->total(),
            'page' => $page,
            'pageSize' => $pageSize,
        ];
    }
}
```

### 4.4 路由注册

```php
// config/routes.php 或 Admin 路由文件
Router::addGroup('/admin/app/clientUsage', function () {
    Router::post('/report', 'App\Admin\Controller\ClientUsageController@report');
    Router::get('/list', 'App\Admin\Controller\ClientUsageController@list');
});
```

### 4.5 菜单与权限（MineAdmin 后台）

在「系统管理 > 菜单管理」新增：

| 菜单名 | 路由 | 权限标识 |
|--------|------|----------|
| 客户端使用统计 | `/app/clientUsage` | `app:clientUsage:list` |

权限分配：

| 权限标识 | 说明 | 分配给 |
|----------|------|--------|
| `app:clientUsage:report` | 上报记录 | 所有登录用户角色 |
| `app:clientUsage:list` | 查看统计 | 仅管理员角色 |

---

## 5. 管理后台页面建议（MineAdmin Vue）

表格列与桌面端「使用统计」窗口保持一致：

| 列 | 字段 |
|----|------|
| 时间 | `created_at` |
| 用户名 | `username` |
| 客户端 | `client_id` |
| 平台 | `client_platform` |
| 版本 | `client_version` |
| 事件 | `event_type`（映射为中文：登录/退出/生成视频） |
| 详情 | `event_detail` |
| IP | `ip_address` |

筛选器：用户名、平台、事件类型、时间范围。

---

## 6. 客户端对接说明

桌面客户端已实现：

| 模块 | 文件 | 行为 |
|------|------|------|
| 上报 | `src/usage.py` → `MineAdminAuthClient.report_usage()` | 登录/退出/生成视频时 POST |
| 查询 | `src/admin_panel.py` | 管理员点击「使用统计」GET |
| 本机兜底 | `src/usage.py` → `UsageStore` | API 不可用时显示本机 SQLite 记录 |

客户端 `client_id` 固定为 `video-fingerprint-tool`，无需额外配置。

---

## 7. 联调步骤

1. 在 MineAdmin 服务端执行建表 SQL
2. 部署 Controller / Service / 路由
3. 为管理员角色分配 `app:clientUsage:list` 权限
4. 为普通用户角色分配 `app:clientUsage:report` 权限
5. 桌面客户端登录 → 生成视频 → 管理员打开「使用统计」或 MineAdmin 后台页面验证

**curl 自测**

```bash
# 1. 登录拿 Token
TOKEN=$(curl -s -X POST https://ad-api.paiwan.com/admin/passport/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"YOUR_PASSWORD"}' \
  | jq -r '.data.access_token')

# 2. 上报
curl -X POST https://ad-api.paiwan.com/admin/app/clientUsage/report \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "username":"admin",
    "client_id":"video-fingerprint-tool",
    "client_platform":"macos",
    "client_version":"1.0.0",
    "event_type":"login",
    "event_detail":""
  }'

# 3. 查询（管理员）
curl "https://ad-api.paiwan.com/admin/app/clientUsage/list?page=1&pageSize=20" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 8. 安全建议

1. **username 校验**：上报时强制 `username` 与 JWT 用户一致
2. **list 权限**：仅管理员角色可查询全量记录
3. **频率限制**：单用户 report 建议 ≤ 60 次/分钟（防刷）
4. **数据保留**：建议定期归档 90 天以前的数据
5. **HTTPS**：生产环境强制 HTTPS
