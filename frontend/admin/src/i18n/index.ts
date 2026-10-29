import { computed, ref } from 'vue'
import { EN } from './catalog'
import { JA } from './ja'
import { KO } from './ko'
import { ES } from './es'
import { FR } from './fr'
import { PT } from './pt'
import { IT } from './it'
import { DE } from './de'
import { NL } from './nl'
import { SV } from './sv'
import { PL } from './pl'
import { RU } from './ru'
import { TR } from './tr'
import { AR } from './ar'
import { HI } from './hi'
import { TH } from './th'
import { VI } from './vi'
import { ID } from './id'
import { MS } from './ms'
import { FIL } from './fil'
import { toTraditional } from './s2t'
import type { Language } from 'element-plus/es/locale'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import zhTw from 'element-plus/es/locale/lang/zh-tw'
import enLocale from 'element-plus/es/locale/lang/en'
import jaLocale from 'element-plus/es/locale/lang/ja'
import koLocale from 'element-plus/es/locale/lang/ko'
import esLocale from 'element-plus/es/locale/lang/es'
import frLocale from 'element-plus/es/locale/lang/fr'
import deLocale from 'element-plus/es/locale/lang/de'
import ptLocale from 'element-plus/es/locale/lang/pt'
import ruLocale from 'element-plus/es/locale/lang/ru'
import arLocale from 'element-plus/es/locale/lang/ar'
import thLocale from 'element-plus/es/locale/lang/th'
import viLocale from 'element-plus/es/locale/lang/vi'
import idLocale from 'element-plus/es/locale/lang/id'
import itLocale from 'element-plus/es/locale/lang/it'
import trLocale from 'element-plus/es/locale/lang/tr'
import plLocale from 'element-plus/es/locale/lang/pl'
import nlLocale from 'element-plus/es/locale/lang/nl'
import hiLocale from 'element-plus/es/locale/lang/hi'
import msLocale from 'element-plus/es/locale/lang/ms'
import svLocale from 'element-plus/es/locale/lang/sv'

/** Same codes as story-info LangSelect (`utils/langs`). */
export const LANGS = [
  { code: 'zh-Hans', name: '简体中文', dir: 'ltr' },
  { code: 'zh-Hant', name: '繁體中文', dir: 'ltr' },
  { code: 'en', name: 'English', dir: 'ltr' },
  { code: 'ja', name: '日本語', dir: 'ltr' },
  { code: 'ko', name: '한국어', dir: 'ltr' },
  { code: 'es', name: 'Español', dir: 'ltr' },
  { code: 'fr', name: 'Français', dir: 'ltr' },
  { code: 'de', name: 'Deutsch', dir: 'ltr' },
  { code: 'pt', name: 'Português', dir: 'ltr' },
  { code: 'ru', name: 'Русский', dir: 'ltr' },
  { code: 'ar', name: 'العربية', dir: 'rtl' },
  { code: 'th', name: 'ไทย', dir: 'ltr' },
  { code: 'vi', name: 'Tiếng Việt', dir: 'ltr' },
  { code: 'id', name: 'Bahasa Indonesia', dir: 'ltr' },
  { code: 'it', name: 'Italiano', dir: 'ltr' },
  { code: 'tr', name: 'Türkçe', dir: 'ltr' },
  { code: 'pl', name: 'Polski', dir: 'ltr' },
  { code: 'nl', name: 'Nederlands', dir: 'ltr' },
  { code: 'hi', name: 'हिन्दी', dir: 'ltr' },
  { code: 'ms', name: 'Bahasa Melayu', dir: 'ltr' },
  { code: 'fil', name: 'Filipino', dir: 'ltr' },
  { code: 'sv', name: 'Svenska', dir: 'ltr' },
] as const

export type LangCode = (typeof LANGS)[number]['code']

const STORAGE = 'otome_admin_lang'
const UI_CODES = new Set<string>(LANGS.map((item) => item.code))

const packs: Record<string, Record<string, string>> = {
  'zh-Hans': {},
  'zh-Hant': {
    乙游后台: '乙女後台',
    游戏列表: '遊戲列表',
    数据列表: '數據列表',
    用户列表: '用戶列表',
    后台用户: '後台用戶',
    素材库: '素材庫',
    广告: '廣告',
    编辑故事: '編輯故事',
    编辑剧情: '編輯劇情',
    新剧情: '新劇情',
    退出登录: '登出',
    语言: '語言',
    登录: '登入',
    用户名: '用戶名',
    密码: '密碼',
    请填写用户名: '請填寫用戶名',
    请填写密码: '請填寫密碼',
    登录失败: '登入失敗',
    管理员: '管理員',
    页面: '頁面',
  },
  en: EN,
  ja: JA,
  ko: KO,
  es: ES,
  fr: FR,
  pt: PT,
  it: IT,
  de: DE,
  nl: NL,
  sv: SV,
  pl: PL,
  ru: RU,
  tr: TR,
  ar: AR,
  hi: HI,
  th: TH,
  vi: VI,
  id: ID,
  ms: MS,
  fil: FIL,
}

const elementPacks: Record<string, Language> = {
  'zh-Hans': zhCn,
  'zh-Hant': zhTw,
  en: enLocale,
  ja: jaLocale,
  ko: koLocale,
  es: esLocale,
  fr: frLocale,
  de: deLocale,
  pt: ptLocale,
  ru: ruLocale,
  ar: arLocale,
  th: thLocale,
  vi: viLocale,
  id: idLocale,
  it: itLocale,
  tr: trLocale,
  pl: plLocale,
  nl: nlLocale,
  hi: hiLocale,
  ms: msLocale,
  sv: svLocale,
}

function normalize(raw: string) {
  const lowered = raw.trim().replace('_', '-').toLowerCase()
  if (!lowered) return ''
  if (lowered.includes('hant') || lowered === 'zh-tw' || lowered === 'zh-hk' || lowered === 'zh-mo') return 'zh-Hant'
  if (lowered.startsWith('zh')) return 'zh-Hans'
  const primary = lowered.split('-')[0]
  const code = primary === 'tl' ? 'fil' : primary
  return UI_CODES.has(code) ? code : ''
}

function readLocale() {
  const saved = normalize(localStorage.getItem(STORAGE) || '')
  if (saved) return saved as LangCode
  return (normalize(navigator.language) || 'zh-Hans') as LangCode
}

export const locale = ref<LangCode>(readLocale())

export function setLocale(code: string) {
  const next = (normalize(code) || 'zh-Hans') as LangCode
  locale.value = next
  localStorage.setItem(STORAGE, next)
  const meta = LANGS.find((item) => item.code === next)
  document.documentElement.lang = next
  document.documentElement.dir = meta?.dir || 'ltr'
}

export function t(key: string, vars?: Record<string, string | number>) {
  let text = key
  if (locale.value === 'zh-Hans') text = key
  else if (locale.value === 'zh-Hant') {
    const custom = packs['zh-Hant'][key]
    text = custom || toTraditional(key)
  } else text = packs[locale.value]?.[key] || EN[key] || key
  if (vars) {
    Object.entries(vars).forEach(([name, value]) => {
      text = text.split(`{${name}}`).join(String(value))
    })
  }
  return text
}

export const elementLocale = computed(() => elementPacks[locale.value] || enLocale)

setLocale(locale.value)
