import { t } from '../i18n'

export const LANGS = [
  { code: 'zh-Hans', name: '简体中文' },
  { code: 'zh-Hant', name: '繁体中文' },
  { code: 'en', name: '英语' },
  { code: 'ja', name: '日语' },
  { code: 'ko', name: '韩语' },
  { code: 'es', name: '西班牙语' },
  { code: 'fr', name: '法语' },
  { code: 'de', name: '德语' },
  { code: 'pt', name: '葡萄牙语' },
  { code: 'ru', name: '俄语' },
  { code: 'ar', name: '阿拉伯语' },
  { code: 'th', name: '泰语' },
  { code: 'vi', name: '越南语' },
  { code: 'id', name: '印尼语' },
  { code: 'it', name: '意大利语' },
  { code: 'tr', name: '土耳其语' },
  { code: 'pl', name: '波兰语' },
  { code: 'nl', name: '荷兰语' },
  { code: 'hi', name: '印地语' },
  { code: 'ms', name: '马来语' },
  { code: 'fil', name: '菲律宾语' },
  { code: 'sv', name: '瑞典语' },
]

export function langName(code?: string) {
  const key = LANGS.find((item) => item.code === code)?.name
  if (!key) return code || t('简体中文')
  return t(key)
}
