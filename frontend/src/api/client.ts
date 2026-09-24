/** 统一请求封装：拼后端地址、限制等待时间，并保留调用方重试能力。 */
const API_BASE = import.meta.env.VITE_API_BASE ?? ''
const DEFAULT_TIMEOUT_MS = 10_000

type ErrorBody = {
  detail?: unknown
  message?: unknown
}

export function request(path: string, init: RequestInit = {}, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<Response> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs)
  const headers = new Headers(init.headers)
  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  return fetch(path.startsWith('http') ? path : `${API_BASE}${path}`, {
    ...init,
    headers,
    signal: init.signal ?? controller.signal,
  })
    .catch((error: unknown) => {
      if (error instanceof DOMException && error.name === 'AbortError') {
        throw new Error('接口响应超时，请检查网络后重试')
      }
      const detail = error instanceof Error ? error.message : '请求未送达'
      throw new Error(`接口请求失败：${detail}`)
    })
    .finally(() => window.clearTimeout(timeout))
}

export async function readErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const body = (await response.json()) as ErrorBody
    if (typeof body.detail === 'string' && body.detail) return body.detail
    if (typeof body.message === 'string' && body.message) return body.message
  } catch {
    // 非 JSON 错误响应使用调用方的兜底说明。
  }
  return fallback
}

export async function fetchJson<T>(path: string): Promise<T> {
  const response = await request(path)
  if (!response.ok) {
    throw new Error(await readErrorMessage(response, `接口返回 ${response.status}，数据未更新`))
  }
  return (await response.json()) as T
}
