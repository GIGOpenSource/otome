import { t } from '../i18n'

export const SOURCE_LANG = 'zh-Hans'

export const CONTENT_LANGS = [
  { code: 'zh-Hans', name: '简体中文' },
  { code: 'zh-Hant', name: '繁體中文' },
  { code: 'en', name: 'English' },
  { code: 'ja', name: '日本語' },
  { code: 'ko', name: '한국어' },
  { code: 'es', name: 'Español' },
  { code: 'fr', name: 'Français' },
  { code: 'de', name: 'Deutsch' },
  { code: 'pt', name: 'Português' },
  { code: 'ru', name: 'Русский' },
  { code: 'ar', name: 'العربية' },
  { code: 'th', name: 'ไทย' },
  { code: 'vi', name: 'Tiếng Việt' },
  { code: 'id', name: 'Bahasa Indonesia' },
  { code: 'it', name: 'Italiano' },
  { code: 'tr', name: 'Türkçe' },
  { code: 'pl', name: 'Polski' },
  { code: 'nl', name: 'Nederlands' },
  { code: 'hi', name: 'हिन्दी' },
  { code: 'ms', name: 'Bahasa Melayu' },
  { code: 'fil', name: 'Filipino' },
  { code: 'sv', name: 'Svenska' },
]

export type Texts = Record<string, Record<string, string>>

export function cloneTexts(raw: unknown): Texts {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return {}
  const out: Texts = {}
  Object.entries(raw as Record<string, unknown>).forEach(([code, pack]) => {
    if (!pack || typeof pack !== 'object' || Array.isArray(pack)) return
    const row: Record<string, string> = {}
    Object.entries(pack as Record<string, unknown>).forEach(([field, value]) => {
      row[field] = value == null ? '' : String(value)
    })
    out[code] = row
  })
  return out
}

export function textValue(source: string, texts: Texts | undefined, lang: string, field: string, primary = SOURCE_LANG) {
  if (lang === (primary || SOURCE_LANG)) return source || ''
  return texts?.[lang]?.[field] ?? ''
}

export function writeText(
  target: { texts?: Texts } & Record<string, unknown>,
  lang: string,
  field: string,
  value: string,
  primary = SOURCE_LANG,
) {
  if (lang === (primary || SOURCE_LANG)) {
    target[field] = value
    return
  }
  if (!target.texts) target.texts = {}
  if (!target.texts[lang]) target.texts[lang] = {}
  target.texts[lang][field] = value
}

export function emptyHint(source: string, lang: string, primary = SOURCE_LANG, fallback = '') {
  if (lang === (primary || SOURCE_LANG)) return fallback
  return source || t('留空则使用主语言')
}
