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

    <form class="filter-bar" @submit.prevent="search">
      <label v-for="field in filterFields" :key="field" class="filter-item">
        <span>{{ field }}</span>
        <input v-model.trim="filters[field]" :placeholder="`按${field}检索`" />
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="listState === 'loading'">
          <td :colspan="columnCount" class="state-panel">
            <p>正在读取冷链订单列表，请稍候…</p>
          </td>
        </tr>
        <tr v-else-if="listState === 'error'">
          <td :colspan="columnCount" class="state-panel error-state">
            <p>{{ listError }}</p>
            <button class="btn" type="button" @click="loadList()">重试读取</button>
          </td>
        </tr>
        <tr v-else-if="listState === 'empty'">
          <td :colspan="columnCount" class="empty-state">
            <p>{{ emptyMessage }}</p>
          </td>
        </tr>
        <template v-else>
          <tr v-for="row in rows" :key="String(row.id)">
            <td>
              <RouterLink class="link" :to="`/order/${row.id}`">{{ row[columns[0]] ?? '—' }}</RouterLink>
            </td>
            <td v-for="column in columns.slice(1)" :key="column">{{ row[column] ?? '—' }}</td>
            <td class="row-actions">
              <button
                v-for="action in actions"
                :key="action"
                class="link"
                type="button"
                :disabled="pendingAction === `${row.id}:${action}`"
                @click="runAction(action, row)"
              >
                {{ pendingAction === `${row.id}:${action}` ? '执行中…' : action }}
              </button>
            </td>
          </tr>
        </template>
      </tbody>
    </table>

    <div v-if="listState === 'ready' || listState === 'empty'" class="pagination">
      <button class="btn" type="button" :disabled="page === 1" @click="goPage(page - 1)">上一页</button>
      <span>第 {{ page }} / {{ totalPages }} 页</span>
      <button class="btn" type="button" :disabled="page >= totalPages" @click="goPage(page + 1)">下一页</button>
    </div>

    <footer class="page-foot">
      <span>{{ footerSummary }}</span>
      <span v-if="actionMessage" :class="actionOk ? 'success-text' : 'error-text'">{{ actionMessage }}</span>
    </footer>

    <div v-if="createVisible" class="modal-mask" @click.self="closeCreate">
      <form class="modal-card" @submit.prevent="submitCreate">
        <header class="modal-head">
          <h3>登记冷链订单</h3>
          <button class="link" type="button" @click="closeCreate">关闭</button>
        </header>
        <label v-for="field in requiredFields" :key="field" class="form-item">
          <span>{{ field }}<em>*</em></span>
          <input v-model.trim="createForm[field]" :placeholder="`请输入${field}`" />
        </label>
        <p v-if="createError" class="error-text">{{ createError }}</p>
        <footer class="modal-actions">
          <button class="btn" type="button" @click="closeCreate">取消</button>
          <button class="btn primary" type="submit" :disabled="creating">
            {{ creating ? '提交中…' : '确认登记' }}
          </button>
        </footer>
      </form>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import { requestJson, RequestError } from '@/api/client'

type Row = {
  id: number
  status?: string
  [key: string]: string | number | boolean | null | undefined
}
type PageResult = { items: Row[]; total: number; page: number; size: number }
type ActionResult = { ok: boolean; message: string; entry: Row | null }
type ListState = 'loading' | 'ready' | 'empty' | 'error'
type FilterField = '订单编号' | '客户名称' | '货物名称'

const ENDPOINT = '/api/order'
const PAGE_SIZE = 20
const columns = ['订单编号', '客户名称', '货物名称', '货物类别', '起始冷库', '目的冷库', '要求温度区间', '下单时间']
const actions = ['受理订单', '调度派车', '取消订单']
const stats = [{ label: '今日新增订单', value: 0 }, { label: '待受理订单', value: 0 }, { label: '超期未调度', value: 0 }]
const filterFieldList: FilterField[] = ['订单编号', '客户名称', '货物名称']
const requiredFieldList: FilterField[] = ['订单编号', '客户名称', '货物名称']

const rows = ref<Row[]>([])
const total = ref(0)
const page = ref(1)
const listState = ref<ListState>('loading')
const listError = ref('')
const actionMessage = ref('')
const actionOk = ref(false)
const pendingAction = ref('')
const filters = ref<Record<FilterField, string>>(createEmptyFilters())
const createVisible = ref(false)
const creating = ref(false)
const createError = ref('')
const createForm = reactive<Record<FilterField, string>>(createEmptyFilters())
let listRequestSeq = 0

const filterFields = filterFieldList
const requiredFields = requiredFieldList
const columnCount = columns.length + 1
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))
const hasActiveFilters = computed(() => Object.values(filters.value).some((value) => value.trim().length > 0))
const isPageOutOfRange = computed(() => listState.value === 'empty' && page.value > 1 && total.value === 0)
const emptyMessage = computed(() => {
  if (isPageOutOfRange.value) {
    return `第 ${page.value} 页没有冷链订单记录，请返回上一页或重置筛选条件。`
  }
  return hasActiveFilters.value
    ? '没有符合当前订单编号、客户名称或货物名称条件的冷链订单，请调整筛选条件后重试。'
    : '暂无冷链订单数据，可先登记冷链订单。'
})
const footerSummary = computed(() => {
  if (listState.value === 'loading') {
    return '正在读取冷链订单记录…'
  }
  if (listState.value === 'error') {
    return '列表读取失败，当前未展示旧数据；请处理失败原因后重试。'
  }
  if (listState.value === 'empty') {
    if (isPageOutOfRange.value) return `第 ${page.value} 页超出范围，查询结果为 0 条。`
    return hasActiveFilters.value ? '查询结果为 0 条，表格已清空且未保留上一次结果。' : '共 0 条冷链订单记录。'
  }
  return `共 ${total.value} 条冷链订单记录，当前展示 ${rows.value.length} 条。`
})

function createEmptyFilters(): Record<FilterField, string> {
  return { 订单编号: '', 客户名称: '', 货物名称: '' }
}

function buildQuery(): string {
  const params = new URLSearchParams({ page: String(page.value), size: String(PAGE_SIZE) })
  if (filters.value['订单编号']) params.set('keyword', filters.value['订单编号'])
  if (filters.value['客户名称']) params.set('customer', filters.value['客户名称'])
  if (filters.value['货物名称']) params.set('goods', filters.value['货物名称'])
  return params.toString()
}

async function loadList(clearActionMessage = true) {
  const requestSeq = ++listRequestSeq
  listState.value = 'loading'
  listError.value = ''
  if (clearActionMessage) actionMessage.value = ''
  rows.value = []
  total.value = 0

  try {
    const payload = await requestJson<PageResult>(`${ENDPOINT}?${buildQuery()}`, undefined, '冷链订单列表读取失败，请重试')
    if (requestSeq !== listRequestSeq) return
    if (!Array.isArray(payload.items) || typeof payload.total !== 'number') {
      throw new RequestError('冷链订单列表返回格式不正确，总数与明细无法核对，请重试')
    }
    if (payload.items.length > payload.total) {
      throw new RequestError('冷链订单列表明细数量多于总数，结果不一致，请重试')
    }
    rows.value = payload.items
    total.value = payload.total
    listState.value = payload.total === 0 ? 'empty' : 'ready'
  } catch (error) {
    if (requestSeq !== listRequestSeq) return
    listState.value = 'error'
    listError.value = error instanceof Error ? error.message : '冷链订单列表读取失败，请重试'
  }
}

function search() {
  page.value = 1
  void loadList()
}

function goPage(targetPage: number) {
  page.value = Math.min(Math.max(1, targetPage), totalPages.value)
  void loadList()
}

function resetFilters() {
  filters.value = createEmptyFilters()
  page.value = 1
  void loadList()
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

function openCreate() {
  Object.assign(createForm, createEmptyFilters())
  createError.value = ''
  createVisible.value = true
}

function closeCreate() {
  if (creating.value) return
  createVisible.value = false
}

async function submitCreate() {
  createError.value = ''
  const missing = requiredFields.filter((field) => !createForm[field].trim())
  if (missing.length) {
    createError.value = `缺少必填字段：${missing.join('、')}`
    return
  }

  creating.value = true
  try {
    const result = await requestJson<ActionResult>(
      ENDPOINT,
      {
        method: 'POST',
        body: JSON.stringify({
          values: {
            订单编号: createForm['订单编号'],
            客户名称: createForm['客户名称'],
            货物名称: createForm['货物名称'],
          },
        }),
      },
      '冷链订单登记失败，请核对后重试',
    )
    if (!result.ok) {
      throw new RequestError(result.message || '冷链订单登记失败，请核对后重试')
    }
    createVisible.value = false
    filters.value = createEmptyFilters()
    page.value = 1
    actionOk.value = true
    actionMessage.value = result.message
    await loadList(false)
  } catch (error) {
    createError.value = error instanceof Error ? error.message : '冷链订单登记失败，请核对后重试'
  } finally {
    creating.value = false
  }
}

async function runAction(action: string, row: Row) {
  const actionKey = `${row.id}:${action}`
  if (pendingAction.value) return
  pendingAction.value = actionKey
  actionMessage.value = ''
  actionOk.value = false
  try {
    const result = await requestJson<ActionResult>(
      `${ENDPOINT}/${row.id}/actions`,
      { method: 'POST', body: JSON.stringify({ action }) },
      '冷链订单动作未生效，请稍后重试',
    )
    if (!result.ok) {
      throw new RequestError(result.message || '冷链订单动作未生效，请稍后重试')
    }
    actionOk.value = true
    actionMessage.value = result.message
    await loadList(false)
  } catch (error) {
    actionOk.value = false
    actionMessage.value = error instanceof Error ? error.message : '冷链订单操作失败，请稍后重试'
  } finally {
    pendingAction.value = ''
  }
}

onMounted(loadList)
</script>
