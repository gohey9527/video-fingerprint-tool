# MineAdmin 插件：客户端使用统计

与桌面端 `video-fingerprint-tool` 对接，提供：

- `POST /admin/app/clientUsage/report` — 客户端上报
- `GET /admin/app/clientUsage/list` — 管理员查询
- MineAdmin 后台页面「客户端使用统计」

## 安装步骤

### 1. 复制插件到 MineAdmin 项目

```bash
# 在 MineAdmin 项目根目录执行
cp -r /path/to/video-fingerprint-tool/server/mineadmin-plugin/client-usage \
  plugin/gohey/client-usage
```

目录结构应为：

```
plugin/gohey/client-usage/
├── mine.json
├── src/
├── Database/
└── web/
```

### 2. 安装插件

在 MineAdmin 项目根目录：

```bash
# 方式 A：后台「插件管理 → 本地上传安装」上传 zip 包

# 方式 B：命令行（若已配置 mine 插件命令）
php bin/hyperf.php mine:plugin:install gohey/client-usage
```

或手动触发安装脚本后重启 Hyperf：

```bash
php bin/hyperf.php
# 在插件管理中点击安装，安装时会自动执行 Database/Migrations
```

### 3. 配置权限

在 MineAdmin 后台 **系统管理 → 角色管理**，为相应角色分配：

| 权限标识 | 说明 | 建议分配 |
|----------|------|----------|
| `app:clientUsage:report` | 上报使用记录 | 所有需要登录的用户角色 |
| `app:clientUsage:list` | 查看使用统计 | 仅管理员角色 |

若权限列表中尚未出现上述标识，可先在 **菜单管理** 新增菜单：

| 字段 | 值 |
|------|-----|
| 菜单名称 | 客户端使用统计 |
| 路由 | `/app/clientUsage` |
| 权限标识 | `app:clientUsage:list` |
| 组件路径 | `/plugin/gohey/client-usage/views/index.vue` |

### 4. 重启服务

```bash
php bin/hyperf.php start
# 或 docker compose restart
```

## 手动建表（可选）

若无法执行迁移，可直接执行 SQL：

```sql
CREATE TABLE app_client_usage_logs (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(64) NOT NULL,
    client_id VARCHAR(64) NOT NULL,
    client_platform VARCHAR(16) NOT NULL,
    client_version VARCHAR(32) NOT NULL DEFAULT '',
    event_type VARCHAR(32) NOT NULL,
    event_detail VARCHAR(512) NOT NULL DEFAULT '',
    ip_address VARCHAR(45) NULL,
    user_agent VARCHAR(255) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_username (username),
    INDEX idx_client_id (client_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='桌面客户端使用记录';
```

## 联调验证

```bash
TOKEN=$(curl -s -X POST https://ad-api.paiwan.com/admin/passport/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"YOUR_PASSWORD"}' \
  | jq -r '.data.access_token')

curl -X POST https://ad-api.paiwan.com/admin/app/clientUsage/report \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "username":"admin",
    "client_id":"video-fingerprint-tool",
    "client_platform":"macos",
    "client_version":"1.0.0",
    "event_type":"login"
  }'

curl "https://ad-api.paiwan.com/admin/app/clientUsage/list?page=1&pageSize=20" \
  -H "Authorization: Bearer $TOKEN"
```

## 打包为 zip（便于后台上传）

```bash
cd server/mineadmin-plugin
zip -r client-usage.zip client-usage
```

## 兼容说明

- 基于 MineAdmin 2.x / 3.x Hyperf 插件规范编写
- 若 `Mine\MineController` / `Mine\MineFormRequest` 命名空间不同，请按项目实际基类调整 Controller 与 Request 的 `use` 语句
- 若 `user()` 辅助函数不可用，可在 Controller 中改为注入 `CurrentUser` 服务获取用户名

## 相关文档

- API 详细设计：`docs/CLIENT_USAGE_API.md`（项目根目录）
- 桌面客户端：`src/usage.py`、`src/admin_panel.py`
