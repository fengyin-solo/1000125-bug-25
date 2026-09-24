/** 统一请求封装：拼后端地址、限制超时，并把失败原因转换成页面可读文案。 */
const API_BASE = import.meta.env.VITE_API_BASE ?? ''
const DEFAULT_TIMEOUT_MS = 10_000

export class RequestError extends Error {
  status?: number

  constructor(message: string, status?: number) {
    super(message)
    this.name = 'RequestError'
    this.status = status
  }
}

export function request(path: string, init: RequestInit = {}, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<Response> {
  const url = path.startsWith('http') ? path : `${API_BASE}${path}`
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs)
  const signal = init.signal

  signal?.addEventListener('abort', () => controller.abort(), { once: true })

  return fetch(url, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init.headers },
    signal: controller.signal,
  })
    .catch((error: unknown) => {
      if (error instanceof DOMException && error.name === 'AbortError') {
        throw new RequestError(`接口请求超时（${Math.round(timeoutMs / 1000)} 秒），数据未更新，请检查网络后重试`)
      }
      const detail = error instanceof Error ? error.message : '请求未送达'
      throw new RequestError(`接口请求失败：${detail}`)
    })
    .finally(() => window.clearTimeout(timeout))
}

export async function readErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const payload = await response.json()
    const detail = payload?.detail ?? payload?.message
    if (typeof detail === 'string' && detail.trim()) {
      return detail
    }
    if (Array.isArray(detail) && detail.length > 0) {
      return detail.map((item) => item?.msg).filter(Boolean).join('；') || fallback
    }
  } catch {
    // 后端返回非 JSON 时使用调用方给出的兜底说明。
  }
  return fallback
}

export async function requestJson<T>(
  path: string,
  init?: RequestInit,
  fallback = '接口读取失败，请稍后重试',
  timeoutMs = DEFAULT_TIMEOUT_MS,
): Promise<T> {
  const response = await request(path, init, timeoutMs)
  if (!response.ok) {
    throw new RequestError(await readErrorMessage(response, fallback), response.status)
  }
  return (await response.json()) as T
}

export async function fetchJson<T>(path: string): Promise<T> {
  return requestJson<T>(path, undefined, `接口数据读取失败，请稍后重试`)
}
