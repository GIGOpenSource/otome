import { locale, t } from '../../i18n'

const TOKEN_KEY = 'otome_admin_token'
const NAME_KEY = 'otome_admin_name'

export class ApiError extends Error {
  status: number

  constructor(message: string, status = 400) {
    super(message)
    this.status = status
  }
}

export function getAdminToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function getAdminName() {
  return localStorage.getItem(NAME_KEY) || '管理员'
}

export function setAdminSession(token: string, username: string) {
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(NAME_KEY, username)
}

export function clearAdminSession() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(NAME_KEY)
}

function loginUrl() {
  const base = import.meta.env.BASE_URL || '/'
  const prefix = base.endsWith('/') ? base.slice(0, -1) : base
  return `${prefix}/auth/login`
}

function onLoginPage() {
  return window.location.pathname.includes('/auth')
}

function errorText(payload: Record<string, unknown> | null, fallback: string) {
  const message = payload?.message || payload?.detail
  if (!message) return fallback
  if (typeof message === 'string') return message
  if (Array.isArray(message)) return message.map(String).join('；')
  if (typeof message === 'object') {
    return Object.entries(message as Record<string, unknown>)
      .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(',') : value}`)
      .join('；')
  }
  return String(message)
}

export function isAuthError(err: unknown) {
  return err instanceof ApiError && (err.status === 401 || err.status === 403)
}

function authStatus(response: Response, data: Record<string, unknown>) {
  const code = Number(data.code)
  if (response.status === 401 || code === 401) return 401
  if (response.status === 403 || code === 403) return 403
  return 0
}

function rejectAuth(data: Record<string, unknown> | null, status: number, redirect: boolean): never {
  clearAdminSession()
  if (redirect && !onLoginPage()) window.location.assign(loginUrl())
  throw new ApiError(errorText(data, t('请重新登录')), status)
}

export async function request(path: string, options: RequestInit = {}, redirectOnAuth = true) {
  const headers = new Headers(options.headers)
  const token = getAdminToken()
  if (token) headers.set('token', token)
  headers.set('X-Otome-Lang', locale.value)
  headers.set('Accept-Language', locale.value)
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const base = import.meta.env.VITE_API_BASE_URL || '/api'
  let response: Response
  try {
    response = await fetch(`${base}/otome${path}`, { ...options, headers })
  } catch {
    throw new ApiError(t('连不上后台'))
  }

  const text = await response.text()
  let data: Record<string, any> = {}
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      if (response.status === 401 || response.status === 403) rejectAuth(null, response.status, redirectOnAuth)
      throw new ApiError(t('后台返回了无法识别的内容'), response.status)
    }
  }

  const status = authStatus(response, data)
  if (status) rejectAuth(data, status, redirectOnAuth)

  if (!response.ok || (typeof data.code === 'number' && data.code >= 400)) {
    throw new ApiError(errorText(data, t('请求失败')), data.code || response.status)
  }
  return data
}

export type Page<T> = {
  items: T[]
  total: number
  totalPages: number
}

export async function loginAdmin(username: string, password: string) {
  const base = import.meta.env.VITE_API_BASE_URL || '/api'
  let response: Response
  try {
    response = await fetch(`${base}/admin/login/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Otome-Lang': locale.value, 'Accept-Language': locale.value },
      body: JSON.stringify({ username, password }),
    })
  } catch {
    throw new ApiError(t('连不上后台'))
  }
  const data = await response.json().catch(() => ({}))
  if (!response.ok || (typeof data.code === 'number' && data.code >= 400)) {
    throw new ApiError(errorText(data, t('登录失败')), data.code || response.status)
  }
  const session = data.results || {}
  if (!session.token) throw new ApiError(t('登录失败'))
  setAdminSession(session.token, session.username || username)
  return session
}

export async function downloadFile(path: string, filename: string) {
  const headers = new Headers()
  const token = getAdminToken()
  if (token) headers.set('token', token)
  headers.set('X-Otome-Lang', locale.value)
  headers.set('Accept-Language', locale.value)
  const base = import.meta.env.VITE_API_BASE_URL || '/api'
  let response: Response
  try {
    response = await fetch(`${base}/otome${path}`, { headers })
  } catch {
    throw new ApiError(t('连不上后台'))
  }
  if (response.status === 401 || response.status === 403) {
    rejectAuth(null, response.status, true)
  }
  if (!response.ok) {
    const data = await response.json().catch(() => null)
    throw new ApiError(errorText(data, t('导出失败')), response.status)
  }
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

export async function listAll<T>(
  path: string,
  params: Record<string, string | number | undefined> = {},
): Promise<T[]> {
  const pageSize = 50
  const first = await list<T>(path, { ...params, currentPage: 1, pageSize })
  const items = first.items.slice()
  for (let page = 2; page <= first.totalPages; page += 1) {
    const next = await list<T>(path, { ...params, currentPage: page, pageSize })
    items.push(...next.items)
  }
  return items
}

export async function list<T>(
  path: string,
  params: Record<string, string | number | undefined> = {},
  redirectOnAuth = true,
): Promise<Page<T>> {
  const query = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '') query.set(key, String(value))
  })
  const data = await request(`${path}?${query.toString()}`, {}, redirectOnAuth)
  const items = Array.isArray(data.results) ? (data.results as T[]) : []
  return {
    items,
    total: data.pagination?.total ?? items.length,
    totalPages: data.pagination?.total_pages ?? 1,
  }
}

export function asId(value: unknown): number | null {
  if (value == null || value === '') return null
  if (typeof value === 'object' && value && 'id' in value) {
    const id = Number((value as { id: unknown }).id)
    return Number.isFinite(id) ? id : null
  }
  const id = Number(value)
  return Number.isFinite(id) ? id : null
}

export type Asset = {
  id: number
  name: string
  asset_type: 'image' | 'audio' | 'video'
  url: string
  file_url: string
  duration?: number | null
  file_size?: number | null
  remark: string
  texts?: Record<string, Record<string, string>>
  lang: string
}

/** Brief audio/image payload returned on node detail as bgm_info / voice_info / interact_info. */
export type AssetInfo = {
  id: number
  name: string
  asset_type?: string
  file_url: string
  duration?: number | null
  file_size?: number | null
}

export type Game = {
  id: number
  code: string | null
  title: string
  subtitle: string
  summary: string
  play_package: string
  ios_app_id: string
  frontend_url: string
  play_url: string
  landing_url: string
  landing_page_url: string
  cover: number | null
  cover_url: string
  status: number
  node_count: number
  lang: string
  texts?: Record<string, Record<string, string>>
  sort_order: number
}

export type CharacterImage = {
  id: number
  label: string
  texts?: Record<string, Record<string, string>>
  image: number
  image_land: number | null
  image_url: string
  image_land_url: string
  sort_order: number
}

export type Character = {
  id: number
  game: number
  name: string
  title: string
  portrait: number | null
  portrait_url: string
  portrait_land: number | null
  images: CharacterImage[]
  name_color: string
  intro: string
  texts?: Record<string, Record<string, string>>
  lang: string
  sort_order: number
}

export type NodeFigure = {
  id: number
  character: number | null
  image: number | null
  position: string
  sort_order: number
}

export type Choice = {
  id: number
  text: string
  texts?: Record<string, Record<string, string>>
  next_node: number
  sort_order: number
  interact: number | null
  interact_info?: AssetInfo | null
}

export type StoryNode = {
  id: number
  game: number
  node_key: string
  sort_order: number
  character: number | null
  speaker_name: string
  content: string
  background: number | null
  portrait: number | null
  bgm: number | null
  voice: number | null
  interact: number | null
  bgm_info?: AssetInfo | null
  voice_info?: AssetInfo | null
  interact_info?: AssetInfo | null
  insert_media: number | null
  insert_title: string
  next_node: number | null
  is_start: boolean
  is_key: boolean
  is_ending: boolean
  ending_title: string
  texts?: Record<string, Record<string, string>>
  lang: string
  cast_mode: 'single' | 'multi'
  figures: NodeFigure[]
  choices: Choice[]
}

export type ChoiceDraft = {
  id?: number
  text: string
  texts?: Record<string, Record<string, string>>
  next_node: number | null
  interact: number | null
}

export async function syncChoices(nodeId: number, drafts: ChoiceDraft[], previous: Choice[]) {
  drafts.forEach((draft) => {
    if (draft.text.trim() && !draft.next_node) throw new ApiError(t('选项必须选择跳转剧情'))
  })
  const kept: number[] = []
  for (let index = 0; index < drafts.length; index += 1) {
    const draft = drafts[index]
    const text = draft.text.trim()
    if (!text) continue
    if (!draft.next_node) throw new ApiError(t('选项必须选择跳转剧情'))
    const body = {
      node: nodeId,
      text,
      texts: draft.texts || {},
      next_node: draft.next_node,
      sort_order: index,
      interact: draft.interact || null,
    }
    if (draft.id) {
      await request(`/choices/${draft.id}/`, { method: 'PATCH', body: JSON.stringify(body) })
      kept.push(draft.id)
    } else {
      const created = await request('/choices/', { method: 'POST', body: JSON.stringify(body) })
      kept.push(created.results.id)
    }
  }
  for (const item of previous) {
    if (!kept.includes(item.id)) {
      await request(`/choices/${item.id}/`, { method: 'DELETE' })
    }
  }
}
