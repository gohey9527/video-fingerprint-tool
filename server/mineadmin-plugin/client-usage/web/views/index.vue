<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { getClientUsageList, type ClientUsageRecord } from '../api/clientUsage'

const loading = ref(false)
const records = ref<ClientUsageRecord[]>([])
const total = ref(0)

const filters = reactive({
  page: 1,
  pageSize: 20,
  username: '',
  client_platform: '',
  event_type: '',
})

const eventLabels: Record<string, string> = {
  login: '登录',
  logout: '退出',
  generate_video: '生成视频',
}

async function loadData() {
  loading.value = true
  try {
    const res = await getClientUsageList({ ...filters })
    records.value = res.data.list ?? []
    total.value = res.data.total ?? 0
  } finally {
    loading.value = false
  }
}

function onSearch() {
  filters.page = 1
  loadData()
}

function onPageChange(page: number) {
  filters.page = page
  loadData()
}

onMounted(loadData)
</script>

<template>
  <div class="client-usage-page">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <span>客户端使用统计</span>
          <span class="subtitle">查看各用户通过 Windows / macOS 客户端使用短视频指纹工具的记录</span>
        </div>
      </template>

      <el-form :inline="true" @submit.prevent="onSearch">
        <el-form-item label="用户名">
          <el-input v-model="filters.username" clearable placeholder="用户名" />
        </el-form-item>
        <el-form-item label="平台">
          <el-select v-model="filters.client_platform" clearable placeholder="全部">
            <el-option label="Windows" value="windows" />
            <el-option label="macOS" value="macos" />
          </el-select>
        </el-form-item>
        <el-form-item label="事件">
          <el-select v-model="filters.event_type" clearable placeholder="全部">
            <el-option label="登录" value="login" />
            <el-option label="退出" value="logout" />
            <el-option label="生成视频" value="generate_video" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="onSearch">查询</el-button>
        </el-form-item>
      </el-form>

      <el-table v-loading="loading" :data="records" stripe>
        <el-table-column prop="created_at" label="时间" width="180" />
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="client_id" label="客户端" width="180" />
        <el-table-column prop="client_platform" label="平台" width="100" />
        <el-table-column prop="client_version" label="版本" width="90" />
        <el-table-column label="事件" width="110">
          <template #default="{ row }">
            {{ eventLabels[row.event_type] ?? row.event_type }}
          </template>
        </el-table-column>
        <el-table-column prop="event_detail" label="详情" min-width="200" show-overflow-tooltip />
        <el-table-column prop="ip_address" label="IP" width="140" />
      </el-table>

      <div class="pager">
        <el-pagination
          background
          layout="total, prev, pager, next"
          :total="total"
          :page-size="filters.pageSize"
          :current-page="filters.page"
          @current-change="onPageChange"
        />
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.client-usage-page {
  padding: 16px;
}

.header-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.subtitle {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  font-weight: normal;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
