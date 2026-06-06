<?php

declare(strict_types=1);

namespace Plugin\Gohey\ClientUsage\Model;

use Mine\MineModel;

/**
 * @property int $id
 * @property string $username
 * @property string $client_id
 * @property string $client_platform
 * @property string $client_version
 * @property string $event_type
 * @property string $event_detail
 * @property string|null $ip_address
 * @property string|null $user_agent
 * @property string $created_at
 */
class AppClientUsageLog extends MineModel
{
    public bool $timestamps = false;

    protected ?string $table = 'app_client_usage_logs';

    protected array $fillable = [
        'username',
        'client_id',
        'client_platform',
        'client_version',
        'event_type',
        'event_detail',
        'ip_address',
        'user_agent',
        'created_at',
    ];
}
