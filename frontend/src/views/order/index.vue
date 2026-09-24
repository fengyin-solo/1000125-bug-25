<template>
  <section class="page" data-module="order">
    <header class="page-head">
      <div>
        <h2>冷链订单管理</h2>
        <p class="page-desc">维护冷链订单，围绕订单编号、客户名称、货物名称、货物类别做登记、筛选与状态流转。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记冷链订单</button>
        <button class="btn" type="button" @click="exportRows">导出冷链订单清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label class="filter-item">
        <span>订单编号</span>
        <input v-model="filters.keyword" placeholder="按订单编号检索" />
      </label>
      <label class="filter-item">
        <span>订单状态</span>
        <select v-model="filters.status">
          <option value="">全部状态</option>
          <option v-for="status in statuses" :key="status" :value="status">{{ status }}</option>
        </select>
      </label>
      <button class="btn" type="submit" :disabled="loading">查询</button>
      <button class="btn ghost" type="button" :disabled="loading" @click="resetFilters">重置条件</button>
    </form>

    <div v-if="errorMessage && rows.length" class="state-panel error" role="alert">
      <div>
        <strong>列表读取失败：</strong>{{ errorMessage }}
      </div>
      <button class="btn small" type="button" :disabled="loading" @click="reload">重新加载</button>
    </div>
    <div v-if="noticeMessage" class="state-panel success" role="status">{{ noticeMessage }}</div>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <template v-if="!errorMessage || rows.length">
          <tr v-for="row in rows" :key="String(row.id)">
            <td v-for="column in columns" :key="column">
              <RouterLink v-if="column === '订单编号'" class="link" :to="`/order/${row.id}`">
                {{ row[column] ?? '—' }}
              </RouterLink>
              <template v-else>{{ row[column] ?? '—' }}</template>
            </td>
            <td class="row-actions">
              <button
                v-for="action in actions"
                :key="action"
                class="link"
                type="button"
                :disabled="actionPendingKey === `${row.id}-${action}`"
                @click="runAction(action, row)"
              >
                {{ actionPendingKey === `${row.id}-${action}` ? '处理中…' : action }}
              </button>
            </td>
          </tr>
        </template>
        <tr v-if="loading && !rows.length">
          <td :colspan="columnCount" class="empty-state">正在加载冷链订单，请稍候…</td>
        </tr>
        <tr v-else-if="errorMessage && !rows.length">
          <td :colspan="columnCount" class="state-cell">
            <div class="state-panel error" role="alert">
              <div>
                <strong>冷链订单列表读取失败。</strong>
                <p>{{ errorMessage }}</p>
              </div>
              <button class="btn" type="button" @click="reload">重试</button>
            </div>
          </td>
        </tr>
        <tr v-else-if="!loading && !rows.length">
          <td :colspan="columnCount" class="empty-state">{{ emptyMessage }}</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>{{ loading ? '正在读取…' : `共 ${total} 条冷链订单记录` }}</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>

    <div v-if="showCreate" class="modal-mask" @click.self="closeCreate">
      <form class="modal" @submit.prevent="submitCreate">
        <header class="modal-head">
          <h3>登记冷链订单</h3>
          <button class="btn ghost small" type="button" :disabled="creating" @click="closeCreate">关闭</button>
        </header>
        <div class="form-grid">
          <label v-for="field in requiredFields" :key="field" class="form-item">
            <span>{{ field }}</span>
            <input v-model="createForm[field]" :disabled="creating" :placeholder="`请输入${field}`" />
          </label>
        </div>
        <p v-if="createError" class="error-text" role="alert">{{ createError }}</p>
        <footer class="modal-foot">
          <button class="btn" type="button" :disabled="creating" @click="closeCreate">取消</button>
          <button class="btn primary" type="submit" :disabled="creating">{{ creating ? '提交中…' : '确认登记' }}</button>
        </footer>
      </form>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { readErrorMessage, request } from '@/api/client'

type Row = Record<string, string | number | boolean | null>
type PageResult = {
  items: Row[]
  total: number
  page: number
  size: number
}
type ActionResult = {
  ok: boolean
  message: string
  entry?: Row | null
}

const ENDPOINT = '/api/order'
const columns = ['订单编号', '客户名称', '货物名称', '货物类别', '起始冷库', '目的冷库', '要求温度区间', '下单时间']
const actions = ['受理订单', '调度派车', '取消订单']
const statuses = ['待受理', '已受理', '已调度', '已完结', '已取消']
const requiredFields = ['订单编号', '客户名称', '货物名称']
const stats = [{ label: '今日新增订单', value: 0 }, { label: '待受理订单', value: 0 }, { label: '超期未调度', value: 0 }]

const rows = ref<Row[]>([])
const total = ref(0)
const loading = ref(false)
const errorMessage = ref('')
const noticeMessage = ref('')
const actionPendingKey = ref('')
const filters = reactive({ keyword: '', status: '' })

const showCreate = ref(false)
const creating = ref(false)
const createError = ref('')
const createForm = reactive<Record<string, string>>({
  订单编号: '',
  客户名称: '',
  货物名称: '',
})

const columnCount = columns.length + 1
const hasFilter = computed(() => Boolean(filters.keyword.trim() || filters.status))
const emptyMessage = computed(() => {
  if (hasFilter.value) return '没有符合查询条件的冷链订单，请调整订单编号或状态后重试'
  return '暂无冷链订单数据，可先登记冷链订单'
})

function resetFilters() {
  filters.keyword = ''
  filters.status = ''
  void reload()
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

function openCreate() {
  createForm.订单编号 = ''
  createForm.客户名称 = ''
  createForm.货物名称 = ''
  createError.value = ''
  showCreate.value = true
}

function closeCreate() {
  if (creating.value) return
  showCreate.value = false
}

async function submitCreate() {
  createError.value = ''
  creating.value = true
  try {
    const response = await request(ENDPOINT, {
      method: 'POST',
      body: JSON.stringify({ values: { ...createForm } }),
    })
    const result = (await response.json()) as ActionResult
    if (!response.ok || !result.ok) {
      createError.value = result.message || '冷链订单未登记成功，请检查后重试'
      return
    }
    showCreate.value = false
    noticeMessage.value = result.message || '冷链订单已登记'
    window.setTimeout(() => {
      noticeMessage.value = ''
    }, 3000)
    await reload()
  } catch (error) {
    createError.value = error instanceof Error ? error.message : '冷链订单提交失败，请重试'
  } finally {
    creating.value = false
  }
}

async function runAction(action: string, row: Row) {
  errorMessage.value = ''
  actionPendingKey.value = `${row.id}-${action}`
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ values: { action } }),
    })
    const result = (await response.json()) as ActionResult
    if (!response.ok || !result.ok) {
      throw new Error(result.message || '冷链订单动作未生效，请稍后重试')
    }
    noticeMessage.value = result.message
    window.setTimeout(() => {
      noticeMessage.value = ''
    }, 3000)
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '冷链订单操作失败'
  } finally {
    actionPendingKey.value = ''
  }
}

async function reload() {
  loading.value = true
  errorMessage.value = ''
  const params = new URLSearchParams()
  if (filters.keyword.trim()) params.set('keyword', filters.keyword.trim())
  if (filters.status) params.set('status', filters.status)
  const query = params.toString()

  try {
    const response = await request(`${ENDPOINT}${query ? `?${query}` : ''}`)
    if (!response.ok) {
      throw new Error(await readErrorMessage(response, '冷链订单列表读取失败'))
    }
    const payload = (await response.json()) as PageResult
    const start = (payload.page - 1) * payload.size
    const expectedCount = payload.total === 0 || start >= payload.total ? 0 : Math.min(payload.size, payload.total - start)
    if (
      !Array.isArray(payload.items)
      || !Number.isInteger(payload.total)
      || payload.page < 1
      || payload.size < 1
      || payload.items.length !== expectedCount
    ) {
      throw new Error('列表返回结果与总数不一致，请重试')
    }
    rows.value = payload.items
    total.value = payload.total
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '冷链订单列表读取失败'
  } finally {
    loading.value = false
  }
}

onMounted(reload)
</script>
