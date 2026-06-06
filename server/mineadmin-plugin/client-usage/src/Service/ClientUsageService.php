<?php

declare(strict_types=1);

namespace Plugin\Gohey\ClientUsage\Service;

use Mine\Exception\MineException;
use Plugin\Gohey\ClientUsage\Model\AppClientUsageLog;

class ClientUsageService
{
    public function report(array $data, array $server, string $authUsername): int
    {
        $username = strtolower(trim((string) ($data['username'] ?? '')));
        $authName = strtolower(trim($authUsername));

        if ($username === '' || $authName === '' || $username !== $authName) {
            throw new MineException('用户名与登录身份不一致', 403);
        }

        $log = AppClientUsageLog::query()->create([
            'username' => $username,
            'client_id' => (string) $data['client_id'],
            'client_platform' => (string) $data['client_platform'],
            'client_version' => (string) ($data['client_version'] ?? ''),
            'event_type' => (string) $data['event_type'],
            'event_detail' => (string) ($data['event_detail'] ?? ''),
            'ip_address' => $server['remote_addr'] ?? null,
            'user_agent' => isset($server['HTTP_USER_AGENT'])
                ? substr((string) $server['HTTP_USER_AGENT'], 0, 255)
                : null,
            'created_at' => ! empty($data['created_at'])
                ? date('Y-m-d H:i:s', strtotime((string) $data['created_at']))
                : date('Y-m-d H:i:s'),
        ]);

        return (int) $log->id;
    }

    public function paginate(array $params): array
    {
        $page = max(1, (int) ($params['page'] ?? 1));
        $pageSize = min(200, max(1, (int) ($params['pageSize'] ?? 50)));

        $query = AppClientUsageLog::query()->orderByDesc('id');

        if (! empty($params['username'])) {
            $query->where('username', strtolower(trim((string) $params['username'])));
        }
        if (! empty($params['client_id'])) {
            $query->where('client_id', (string) $params['client_id']);
        }
        if (! empty($params['client_platform'])) {
            $query->where('client_platform', (string) $params['client_platform']);
        }
        if (! empty($params['event_type'])) {
            $query->where('event_type', (string) $params['event_type']);
        }
        if (! empty($params['start_at'])) {
            $query->where('created_at', '>=', date('Y-m-d H:i:s', strtotime((string) $params['start_at'])));
        }
        if (! empty($params['end_at'])) {
            $query->where('created_at', '<=', date('Y-m-d H:i:s', strtotime((string) $params['end_at'])));
        }

        $paginator = $query->paginate($pageSize, ['*'], 'page', $page);

        return [
            'list' => array_map(static function ($item) {
                return [
                    'id' => $item->id,
                    'username' => $item->username,
                    'client_id' => $item->client_id,
                    'client_platform' => $item->client_platform,
                    'client_version' => $item->client_version,
                    'event_type' => $item->event_type,
                    'event_detail' => $item->event_detail,
                    'ip_address' => $item->ip_address,
                    'created_at' => $item->created_at,
                ];
            }, $paginator->items()),
            'total' => $paginator->total(),
            'page' => $page,
            'pageSize' => $pageSize,
        ];
    }
}
