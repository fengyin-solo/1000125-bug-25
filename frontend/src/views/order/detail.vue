<template>
  <section class="page" data-module="order-detail">
    <header class="page-head">
      <div>
        <h2>冷链订单详情</h2>
        <p class="page-desc">查看订单编号、客户、货物与当前状态；读取失败时保留重试入口并说明失败原因。</p>
      </div>
      <div class="page-actions">
        <RouterLink class="btn" to="/order">返回订单列表</RouterLink>
      </div>
    </header>

    <article v-if="detailState === 'loading'" class="state-card">
      <h3>正在读取订单详情…</h3>
      <p class="muted-text">正在加载订单编号 {{ orderId }} 的明细，请稍候。</p>
    </article>

    <article v-else-if="detailState === 'error'" class="state-card error-state">
      <h3>订单详情读取失败</h3>
      <p>{{ errorMessage }}</p>
      <button class="btn primary" type="button" @click="loadDetail">重新读取</button>
    </article>

    <article v-else-if="detailState === 'not-found'" class="state-card">
      <h3>未找到对应冷链订单</h3>
      <p>{{ errorMessage }}</p>
      <RouterLink class="btn" to="/order">返回列表重新查询</RouterLink>
    </article>

    <article v-else-if="detail" class="detail-card">
      <header class="detail-head">
        <div>
          <span class="detail-label">订单编号</span>
          <h3>{{ detail['订单编号'] }}</h3>
        </div>
        <span class="status-badge">{{ detail.status || '状态未知' }}</span>
      </header>

      <dl class="detail-grid">
        <div v-for="field in detailFields" :key="field" class="detail-item">
          <dt>{{ field }}</dt>
          <dd>{{ detail[field] || '—' }}</dd>
        </div>
        <div class="detail-item">
          <dt>记录 ID</dt>
          <dd>{{ detail.id }}</dd>
        </div>
      </dl>
    </article>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { requestJson, RequestError } from '@/api/client'

type Detail = {
  id: number
  status?: string
  [key: string]: string | number | boolean | null | undefined
}
type DetailState = 'loading' | 'ready' | 'not-found' | 'error'

const route = useRoute()
const detailFields = ['客户名称', '货物名称', '货物类别', '起始冷库', '目的冷库', '要求温度区间', '下单时间']

const detail = ref<Detail | null>(null)
const detailState = ref<DetailState>('loading')
const errorMessage = ref('')

const orderId = computed(() => String(route.params.id ?? ''))

async function loadDetail() {
  detailState.value = 'loading'
  errorMessage.value = ''
  detail.value = null

  try {
    const result = await requestJson<Detail | null>(
      `/api/order/${encodeURIComponent(orderId.value)}`,
      undefined,
      '冷链订单详情读取失败，请稍后重试',
    )
    if (!result) {
      throw new RequestError('冷链订单详情为空，请返回列表后重试')
    }
    detail.value = result
    detailState.value = 'ready'
  } catch (error) {
    detail.value = null
    if (error instanceof RequestError && error.status === 404) {
      detailState.value = 'not-found'
    } else {
      detailState.value = 'error'
    }
    errorMessage.value = error instanceof Error
      ? error.message
      : '冷链订单详情读取失败，请稍后重试'
  }
}

watch(orderId, loadDetail, { immediate: true })
</script>
