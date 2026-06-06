<?php

declare(strict_types=1);

namespace Plugin\Gohey\ClientUsage\Http\Request;

use Mine\MineFormRequest;

class ClientUsageReportRequest extends MineFormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'username' => 'required|string|max:64',
            'client_id' => 'required|string|max:64|in:video-fingerprint-tool',
            'client_platform' => 'required|string|in:windows,macos,linux',
            'client_version' => 'nullable|string|max:32',
            'event_type' => 'required|string|in:login,logout,generate_video',
            'event_detail' => 'nullable|string|max:512',
            'created_at' => 'nullable|date',
        ];
    }

    public function messages(): array
    {
        return [
            'username.required' => '用户名不能为空',
            'client_id.in' => '不支持的客户端标识',
            'client_platform.in' => '客户端平台无效',
            'event_type.in' => '事件类型无效',
        ];
    }
}
