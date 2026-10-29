import { computed, ref } from 'vue'
import { EN } from './catalog'
import { JA } from './ja'
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

const zh: Record<string, string> = {
  乙游后台: '乙游后台',
  游戏列表: '游戏列表',
  数据列表: '数据列表',
  用户列表: '用户列表',
  后台用户: '后台用户',
  素材库: '素材库',
  广告: '广告',
  编辑故事: '编辑故事',
  编辑剧情: '编辑剧情',
  新剧情: '新剧情',
  退出登录: '退出登录',
  语言: '语言',
  登录: '登录',
  用户名: '用户名',
  密码: '密码',
  请填写用户名: '请填写用户名',
  请填写密码: '请填写密码',
  登录失败: '登录失败',
  '用用户名和密码进入后台。三部游戏都在这一套后台里管理。': '用用户名和密码进入后台。三部游戏都在这一套后台里管理。',
  '在这里编写故事、角色、剧情和素材。发布后，客户端凭游戏 ID 播放。':
    '在这里编写故事、角色、剧情和素材。发布后，客户端凭游戏 ID 播放。',
  页面: '页面',
  管理员: '管理员',
}

const en: Record<string, string> = {
  乙游后台: 'Otome Admin',
  游戏列表: 'Games',
  数据列表: 'Data',
  用户列表: 'Players',
  后台用户: 'Staff',
  素材库: 'Library',
  广告: 'Ads',
  编辑故事: 'Edit story',
  编辑剧情: 'Edit scene',
  新剧情: 'New scene',
  退出登录: 'Sign out',
  语言: 'Language',
  登录: 'Sign in',
  用户名: 'Username',
  密码: 'Password',
  请填写用户名: 'Enter a username',
  请填写密码: 'Enter a password',
  登录失败: 'Sign-in failed',
  '用用户名和密码进入后台。三部游戏都在这一套后台里管理。': 'Sign in with your username and password. All games are managed here.',
  '在这里编写故事、角色、剧情和素材。发布后，客户端凭游戏 ID 播放。':
    'Write stories, characters, scenes, and files here. After publishing, the player app loads them by game ID.',
  页面: 'Page',
  管理员: 'Admin',
}

function fill(partial: Record<string, string>) {
  return { ...en, ...partial }
}

const packs: Record<string, Record<string, string>> = {
  'zh-Hans': zh,
  'zh-Hant': fill({
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
  }),
  en,
  ja: fill({
    乙游后台: '乙女ゲーム管理',
    游戏列表: 'ゲーム',
    数据列表: 'データ',
    用户列表: 'プレイヤー',
    后台用户: 'スタッフ',
    素材库: '素材',
    广告: '広告',
    编辑故事: '物語を編集',
    编辑剧情: 'シーンを編集',
    新剧情: '新しいシーン',
    退出登录: 'ログアウト',
    语言: '言語',
    登录: 'ログイン',
    用户名: 'ユーザー名',
    密码: 'パスワード',
    管理员: '管理者',
  }),
  ko: fill({
    乙游后台: '오토메 관리',
    游戏列表: '게임',
    数据列表: '데이터',
    用户列表: '플레이어',
    后台用户: '스태프',
    素材库: '자료',
    广告: '광고',
    退出登录: '로그아웃',
    语言: '언어',
    登录: '로그인',
    用户名: '사용자 이름',
    密码: '비밀번호',
  }),
  es: fill({ 乙游后台: 'Admin otome', 游戏列表: 'Juegos', 数据列表: 'Datos', 用户列表: 'Jugadores', 后台用户: 'Equipo', 素材库: 'Archivos', 广告: 'Anuncios', 退出登录: 'Salir', 语言: 'Idioma', 登录: 'Entrar' }),
  fr: fill({ 乙游后台: 'Admin otome', 游戏列表: 'Jeux', 数据列表: 'Données', 用户列表: 'Joueurs', 后台用户: 'Équipe', 素材库: 'Fichiers', 广告: 'Annonces', 退出登录: 'Quitter', 语言: 'Langue', 登录: 'Connexion' }),
  de: fill({ 乙游后台: 'Otome-Verwaltung', 游戏列表: 'Spiele', 数据列表: 'Daten', 用户列表: 'Spieler', 后台用户: 'Team', 素材库: 'Medien', 广告: 'Anzeigen', 退出登录: 'Abmelden', 语言: 'Sprache', 登录: 'Anmelden' }),
  pt: fill({ 乙游后台: 'Admin otome', 游戏列表: 'Jogos', 数据列表: 'Dados', 用户列表: 'Jogadores', 后台用户: 'Equipe', 素材库: 'Arquivos', 广告: 'Anúncios', 退出登录: 'Sair', 语言: 'Idioma', 登录: 'Entrar' }),
  ru: fill({ 乙游后台: 'Админка отоме', 游戏列表: 'Игры', 数据列表: 'Данные', 用户列表: 'Игроки', 后台用户: 'Команда', 素材库: 'Файлы', 广告: 'Реклама', 退出登录: 'Выйти', 语言: 'Язык', 登录: 'Войти' }),
  ar: fill({ 乙游后台: 'إدارة الأوتومي', 游戏列表: 'الألعاب', 数据列表: 'البيانات', 用户列表: 'اللاعبون', 后台用户: 'الفريق', 素材库: 'الملفات', 广告: 'الإعلانات', 退出登录: 'خروج', 语言: 'اللغة', 登录: 'دخول' }),
  th: fill({ 乙游后台: 'แอดมินโอโตเมะ', 游戏列表: 'เกม', 数据列表: 'ข้อมูล', 用户列表: 'ผู้เล่น', 后台用户: 'ทีม', 素材库: 'ไฟล์', 广告: 'โฆษณา', 退出登录: 'ออก', 语言: 'ภาษา', 登录: 'เข้าสู่ระบบ' }),
  vi: fill({ 乙游后台: 'Quản trị otome', 游戏列表: 'Game', 数据列表: 'Dữ liệu', 用户列表: 'Người chơi', 后台用户: 'Nhân sự', 素材库: 'Thư viện', 广告: 'Quảng cáo', 退出登录: 'Đăng xuất', 语言: 'Ngôn ngữ', 登录: 'Đăng nhập' }),
  id: fill({ 乙游后台: 'Admin otome', 游戏列表: 'Game', 数据列表: 'Data', 用户列表: 'Pemain', 后台用户: 'Staf', 素材库: 'Berkas', 广告: 'Iklan', 退出登录: 'Keluar', 语言: 'Bahasa', 登录: 'Masuk' }),
  it: fill({ 乙游后台: 'Admin otome', 游戏列表: 'Giochi', 数据列表: 'Dati', 用户列表: 'Giocatori', 后台用户: 'Staff', 素材库: 'File', 广告: 'Annunci', 退出登录: 'Esci', 语言: 'Lingua', 登录: 'Accedi' }),
  tr: fill({ 乙游后台: 'Otome yönetim', 游戏列表: 'Oyunlar', 数据列表: 'Veri', 用户列表: 'Oyuncular', 后台用户: 'Ekip', 素材库: 'Dosyalar', 广告: 'Reklamlar', 退出登录: 'Çıkış', 语言: 'Dil', 登录: 'Giriş' }),
  pl: fill({ 乙游后台: 'Panel otome', 游戏列表: 'Gry', 数据列表: 'Dane', 用户列表: 'Gracze', 后台用户: 'Zespół', 素材库: 'Pliki', 广告: 'Reklamy', 退出登录: 'Wyloguj', 语言: 'Język', 登录: 'Zaloguj' }),
  nl: fill({ 乙游后台: 'Otome-beheer', 游戏列表: 'Spellen', 数据列表: 'Data', 用户列表: 'Spelers', 后台用户: 'Team', 素材库: 'Bestanden', 广告: 'Advertenties', 退出登录: 'Afmelden', 语言: 'Taal', 登录: 'Inloggen' }),
  hi: fill({ 乙游后台: 'ओटोमे एडमिन', 游戏列表: 'गेम', 数据列表: 'डेटा', 用户列表: 'खिलाड़ी', 后台用户: 'स्टाफ', 素材库: 'फ़ाइलें', 广告: 'विज्ञापन', 退出登录: 'साइन आउट', 语言: 'भाषा', 登录: 'साइन इन' }),
  ms: fill({ 乙游后台: 'Admin otome', 游戏列表: 'Permainan', 数据列表: 'Data', 用户列表: 'Pemain', 后台用户: 'Kakitangan', 素材库: 'Fail', 广告: 'Iklan', 退出登录: 'Log keluar', 语言: 'Bahasa', 登录: 'Log masuk' }),
  fil: fill({ 乙游后台: 'Otome admin', 游戏列表: 'Mga laro', 数据列表: 'Data', 用户列表: 'Mga manlalaro', 后台用户: 'Staff', 素材库: 'Files', 广告: 'Ads', 退出登录: 'Sign out', 语言: 'Wika', 登录: 'Sign in' }),
  sv: fill({ 乙游后台: 'Otome-admin', 游戏列表: 'Spel', 数据列表: 'Data', 用户列表: 'Spelare', 后台用户: 'Personal', 素材库: 'Filer', 广告: 'Annonser', 退出登录: 'Logga ut', 语言: 'Språk', 登录: 'Logga in' }),
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
  return LANGS.some((item) => item.code === code) ? code : ''
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
  const pack = packs[locale.value] || {}
  let text = key
  if (locale.value === 'zh-Hans') text = key
  else if (locale.value === 'zh-Hant') {
    const custom = pack[key]
    text = custom && custom !== en[key] ? custom : toTraditional(key)
  } else if (locale.value === 'ja') text = JA[key] || EN[key] || key
  else text = pack[key] || EN[key] || key
  if (vars) {
    Object.entries(vars).forEach(([name, value]) => {
      text = text.split(`{${name}}`).join(String(value))
    })
  }
  return text
}

export const elementLocale = computed(() => elementPacks[locale.value] || enLocale)

setLocale(locale.value)
