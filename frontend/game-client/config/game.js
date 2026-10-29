// 每一份客户端只改游戏 ID 和接口地址。故事、图片、音频都在后台管理面板配置。
export const GAME_ID = 1
export const APP_NAME = "星河剧场"

let resolvedGameId = 0

// 主站是 / 。每部已发布故事的地址是 /编码/ ，编码在路径第一段。
export function storySlug() {
	if (typeof window === "undefined" || !window.location) {
		return ""
	}
	const slug = decodeURIComponent((window.location.pathname || "/").split("/").filter(Boolean)[0] || "")
	if (!slug || slug === "assets" || slug === "admin") {
		return ""
	}
	return slug
}

export function activeGameId() {
	return resolvedGameId || GAME_ID
}

export function setActiveGameId(id) {
	const number = Number(id)
	if (number > 0) {
		resolvedGameId = number
	}
}
// 只有 H5 开发服务器能代理 /api。App 没有这份代理，相对路径会请求失败。
// 代理只能匹配 /api/otome/ 接口，不能匹配整个 /api，否则源码模块 /api/otome.js 会被转走，页面停在连接超时。
// App 与正式包请求下面的完整地址。可用 VITE_API_HOST 覆盖。
const REMOTE_API = "http://127.0.0.1:8001/api"
const h5DevProxy = import.meta.env.DEV && process.env.UNI_PLATFORM === "h5"
export const API_HOST = import.meta.env.VITE_API_HOST || (h5DevProxy ? "/api" : REMOTE_API)
// 留空时使用后台环境变量 GOOGLE_CLIENT_ID。两边都空则只能用设备号快速登录。
export const GOOGLE_CLIENT_ID = ""
