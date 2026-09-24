<template>
  <section class="page" data-module="order-detail">
    <header class="page-head">
      <div>
        <h2>冷链订单详情</h2>
        <p class="page-desc">查看订单基础信息、当前状态和温控要求。读取失败时可在本页直接重试。</p>
      </div>
      <div class="page-actions">
        <RouterLink class="btn" to="/order">返回订单列表</RouterLink>
      </div>
    </header>

    <div v-if="loading" class="state-panel" role="status">正在读取冷链订单详情，请稍候…</div>

    <div v-else-if="errorMessage" class="state-panel error" role="alert">
      <div>
        <strong>{{ notFound ? '未找到冷链订单。' : '冷链订单详情读取失败。' }}</strong>
        <p>{{ errorMessage }}</p>
      </div>
      <button class="btn" type="button" @click="loadDetail">重试</button>
    </div>

    <template v-else-if="entry">
      <div class="detail-head">
        <div>
          <span class="stat-label">订单编号</span>
          <strong>{{ fieldValue('订单编号') }}</strong>
        </div>
        <span class="status-badge">{{ fieldValue('status') }}</span>
      </div>

      <dl class="detail-grid">
        <div v-for="item in detailFields" :key="item.key" class="detail-item">
          <dt>{{ item.label }}</dt>
          <dd>{{ fieldValue(item.key) }}</dd>
        </div>
      </dl>
    </template>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { readErrorMessage, request } from '@/api/client'

type Detail = Record<string, string | number | boolean | null>

const detailFields = [
  { key: '订单编号', label: '订单编号' },
  { key: '客户名称', label: '客户名称' },
  { key: '货物名称', label: '货物名称' },
  { key: '货物类别', label: '货物类别' },
  { key: '起始冷库', label: '起始冷库' },
  { key: '目的冷库', label: '目的冷库' },
  { key: '要求温度区间', label: '要求温度区间' },
  { key: '下单时间', label: '下单时间' },
  { key: 'status', label: '订单状态' },
]
const route = useRoute()
const entry = ref<Detail | null>(null)
const loading = ref(false)
const errorMessage = ref('')
const notFound = ref(false)

function fieldValue(field: string): string {
  const value = entry.value?.[field]
  return value === null || value === undefined || value === '' ? '—' : String(value)
}

async function loadDetail() {
  const id = Number(route.params.id)
  entry.value = null
  errorMessage.value = ''
  notFound.value = false

  if (!Number.isInteger(id) || id <= 0) {
    notFound.value = true
    errorMessage.value = `订单标识「${String(route.params.id)}」无效，请从订单列表重新进入`
    return
  }

  loading.value = true
  try {
    const response = await request(`/api/order/${id}`)
    if (!response.ok) {
      notFound.value = response.status === 404
      throw new Error(
        await readErrorMessage(response, notFound.value ? '该冷链订单不存在或已归档' : '冷链订单详情读取失败'),
      )
    }
    entry.value = (await response.json()) as Detail
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '冷链订单详情读取失败'
  } finally {
    loading.value = false
  }
}

watch(() => route.params.id, loadDetail)
onMounted(loadDetail)
</script>
