<template>
	<view class="shell">
	<view class="stage" :class="[orientClass, { bare: !coverReady }]" :style="frameStyle">
		<video
			v-if="cover && coverKind === 'video'"
			:key="'cover-' + cover"
			class="bg"
			:src="cover"
			autoplay
			loop
			muted
			playsinline
			:controls="false"
			:show-center-play-btn="false"
			:enable-progress-gesture="false"
			object-fit="cover"
			@loadeddata="onCoverReady"
		></video>
		<image v-else-if="cover" class="bg" :src="cover" mode="aspectFill" @load="onCoverReady"></image>
		<view v-if="coverReady" class="shade"></view>
		<view v-else class="veil"></view>
		<image class="mode-btn" :src="modeIcon" mode="aspectFit" :style="modeStyle" @click="switchOrient"></image>
		<view class="body">
		<view class="hero" :style="heroStyle">
		<picker class="brand-pick" mode="selector" :range="langNames" :value="langIndex" @change="onLang">
			<view class="brand-wrap">
				<text class="brand" :style="typeStyle.brand">{{ t('app_name') }}</text>
			</view>
		</picker>
		<text v-if="coverReady" class="title" :style="typeStyle.title">{{ title }}</text>
		<view v-if="showConnect" class="connect" :class="{ lead: !coverReady }">
			<text class="connect-label" :style="connectLabelStyle">{{ t('connecting') }}</text>
			<view class="track">
				<view class="track-in" :style="{ width: bootPercent + '%' }">
					<view class="track-arrow"></view>
				</view>
			</view>
		</view>
		<text v-if="coverReady && entered" class="uid-line" :style="typeStyle.uid">UID {{ uid || 'XXXXXXXX' }}</text>
		<view class="copy" :style="copyStyle">
		<text v-if="blurb" class="invite" :style="typeStyle.invite">{{ blurb }}</text>
		<view v-if="downloading" class="panel">
			<text class="label">{{ progressLabel }}</text>
			<view class="bar">
				<view class="bar-in" :style="{ width: percent + '%' }"></view>
			</view>
			<text class="hint">{{ t('saving_assets') }}</text>
		</view>
		<view v-else-if="errorText" class="panel">
			<text class="hint">{{ errorText }}</text>
		</view>
		<view v-if="ad && !downloading" class="ad" @click="openAd">
			<video
				v-if="ad.media_url && ad.media_kind === 'video'"
				class="ad-media"
				:src="ad.media_url"
				autoplay
				muted
				loop
				playsinline
				:controls="false"
				:show-center-play-btn="false"
				object-fit="cover"
			></video>
			<image v-else-if="ad.media_url" class="ad-media" :src="ad.media_url" mode="aspectFill"></image>
			<view class="ad-copy">
				<text class="ad-title">{{ ad.title }}</text>
				<text v-if="ad.link_url" class="ad-go">{{ t('view') }}</text>
			</view>
			<text class="ad-close" @click.stop="ad = null">{{ t('close') }}</text>
		</view>
		</view>
		</view>
		<view v-if="!downloading && errorText" class="btn solid" :style="slot('primary')" @click="retry">{{ t('retry') }}</view>
		<view v-else-if="!downloading && !entered" class="dock" :class="{ dim: !coverReady }">
			<view class="btn solid" :style="slot('primary')" @click="useDevice">{{ loggingIn ? t('signing_in') : t('device_login') }}</view>
			<view class="btn line" :style="slot('google')" @click="useGoogle">
				<view class="g-logo" :style="logoStyle"></view>
				<text :style="btnText">{{ t('google_login') }}</text>
			</view>
		</view>
		<view v-else-if="!downloading && entered" class="dock" :class="{ locked: !menuReady }">
			<view class="btn solid" :style="slot('continue')" @click="start(false)">{{ hasSave ? t('menu_continue') : t('start_game') }}</view>
			<view class="btn fill" :style="slot('archives')" @click="openSaves">{{ t('menu_archives') }}</view>
			<view class="btn fill" :style="slot('stories')" @click="openGallery">{{ t('menu_stories') }}</view>
			<view v-if="land" class="btn fill" :style="slot('quit')" @click="logout">{{ t('menu_quit') }}</view>
			<text class="restart" :style="restartStyle" @click="start(true)">{{ t('menu_restart') }}</text>
			<view v-if="!land" class="btn line" :style="slot('quit')" @click="logout">{{ t('menu_quit') }}</view>
		</view>
		</view>
	</view>
	</view>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { onLoad, onShow, onUnload } from '@dcloudio/uni-app'
import { activeGameId } from '@/config/game.js'
import {
	deviceLogin,
	ensureGame,
	rememberClick,
	fetchAds,
	trackAd,
	fetchMe,
	fetchSaves,
	fetchScript,
	googleClientId,
	googleLogin,
	rememberChannel,
	saveSession
} from '@/api/otome.js'
import { LANGS, lang, setLang, t } from '@/utils/i18n.js'
import { resolveLocal } from '@/utils/assetCache.js'
import { isAppRuntime, readOrient, stageFrame, writeOrient } from '@/utils/orientation.js'

const pad = ref(20)
const orient = ref('portrait')
const frame = ref({ width: 375, height: 667, left: 0, top: 0 })
const entered = ref(!!uni.getStorageSync('token'))
const ready = ref(false)
const menuReady = ref(false)
const loggingIn = ref(false)
const uid = ref(uni.getStorageSync('otome_uid') || '')
const loginLabel = ref(t('device_login'))
const hasSave = ref(false)
const title = ref(t('connecting'))
const subtitle = ref('')
const summary = ref('')
const downloading = ref(false)
const mediaReady = ref(false)
const bootPercent = ref(6)
let bootTimer = null
const errorText = ref('')
const done = ref(0)
const total = ref(0)
const script = ref(null)
const ad = ref(null)
let resumeRequested = false
let autoNodeId = 0
let googleReady = ''

const frameStyle = computed(() => {
	if (isAppRuntime()) {
		return { left: '0px', top: '0px', width: '100%', height: '100%' }
	}
	return {
		width: frame.value.width + 'px',
		height: frame.value.height + 'px',
		left: frame.value.left + 'px',
		top: frame.value.top + 'px'
	}
})
const orientClass = computed(() => (orient.value === 'landscape' ? 'is-landscape' : 'is-portrait'))
const land = computed(() => orient.value === 'landscape')
const modeIcon = computed(() => (land.value ? '/static/login/landscape.svg' : '/static/login/portrait.svg'))
const modeStyle = computed(() => {
	const w = frame.value.width || 375
	const h = frame.value.height || 667
	const size = Math.round(Math.min(w, h) * 0.1)
	const inset = Math.round(Math.min(w, h) * 0.036)
	return {
		width: size + 'px',
		height: size + 'px',
		top: Math.round(Math.min(w, h) * 0.1) + 'px',
		right: inset + 'px'
	}
})
const heroStyle = computed(() => {
	if (land.value) {
		return { left: '5%', top: '26%', width: '42%' }
	}
	return { left: '12%', top: '16.5%', width: '76%' }
})
const copyStyle = computed(() => {
	const w = frame.value.width || 375
	const h = frame.value.height || 667
	const scale = Math.min(w, h) / 375
	const heroTop = h * (land.value ? 0.26 : 0.165)
	// 横屏按钮在右侧，文字可以铺到舞台底部。竖屏停在第一颗按钮上方。
	const limitBottom = land.value ? h * 0.92 : h * (entered.value ? 0.5 : 0.57)
	const font = 32 * scale
	const heroW = w * (land.value ? 0.42 : 0.76)
	const lines = textLines(title.value, heroW, font * 0.62)
	const uidGap = entered.value ? 28 : 0
	const lead = (16 + 6 + uidGap + 12 + 8) * scale + lines * font * 1.05
	const height = Math.max(Math.round(h * 0.08), Math.round(limitBottom - heroTop - lead))
	return { height: height + 'px' }
})
const typeStyle = computed(() => {
	const w = frame.value.width || 375
	const h = frame.value.height || 667
	// 原型字号 15 / 32 / 11 / 11，按短边相对 375 缩放，横竖屏同一比例。
	const scale = Math.min(w, h) / 375
	const px = (n) => Math.round(n * scale) + 'px'
	return {
		brand: { fontSize: px(16), lineHeight: '1', letterSpacing: '0.16em' },
		title: { fontSize: px(32), lineHeight: '1.1', marginTop: px(6) },
		uid: { fontSize: px(12), lineHeight: '1', marginTop: px(28), color: 'rgba(204, 184, 145, 1)' },
		invite: {
			fontSize: px(12),
			lineHeight: '1.7',
			marginTop: px(entered.value ? 8 : 12),
			color: 'rgba(255, 255, 255, 0.69)'
		}
	}
})
const connectLabelStyle = computed(() => {
	const w = frame.value.width || 375
	const h = frame.value.height || 667
	const scale = Math.min(w, h) / 375
	const size = coverReady.value ? 15 : 22
	return {
		fontSize: Math.round(size * scale) + 'px',
		marginTop: Math.round((coverReady.value ? 18 : 22) * scale) + 'px'
	}
})
const btnText = computed(() => {
	const h = frame.value.height || 667
	const size = Math.round(h * (land.value ? 0.038 : 0.022))
	return { fontSize: size + 'px', letterSpacing: '0.08em' }
})
const logoStyle = computed(() => {
	const h = frame.value.height || 667
	const size = Math.round(h * (land.value ? 0.046 : 0.026))
	return { width: size + 'px', height: size + 'px', marginRight: Math.round(size * 0.4) + 'px' }
})
const restartStyle = computed(() => {
	const w = frame.value.width || 375
	const h = frame.value.height || 667
	const size = Math.round(h * (land.value ? 0.034 : 0.02))
	if (land.value) {
		return {
			left: Math.round(w * 0.5) + 'px',
			width: Math.round(w * 0.41) + 'px',
			top: Math.round(h * (0.632 + 0.155 + 0.036)) + 'px',
			fontSize: size + 'px',
			lineHeight: '1',
			textAlign: 'center'
		}
	}
	return {
		left: '9.3%',
		width: '79.7%',
		top: Math.round(h * 0.838) + 'px',
		fontSize: size + 'px',
		textAlign: 'center'
	}
})

function textLines(text, width, charWidth) {
	const value = String(text || '')
	if (!width || !charWidth) return 1
	let used = 0
	let lines = 1
	for (const ch of value) {
		const wide = /[\u2e80-\u9fff]/.test(ch)
		used += wide ? charWidth / 0.62 : charWidth
		if (used > width) {
			lines += 1
			used = wide ? charWidth / 0.62 : charWidth
		}
	}
	return lines
}

function slot(name) {
	const w = frame.value.width || 375
	const h = frame.value.height || 667
	const wide = land.value
	const map = wide
		? { primary: 0.385, google: 0.557, continue: 0.181, archives: 0.33, stories: 0.48, quit: 0.632 }
		: { primary: 0.59, google: 0.672, continue: 0.52, archives: 0.594, stories: 0.669, quit: 0.874 }
	const height = wide ? 0.125 : 0.061
	return {
		left: Math.round(w * (wide ? 0.5 : 0.093)) + 'px',
		width: Math.round(w * (wide ? 0.41 : 0.797)) + 'px',
		top: Math.round(h * map[name]) + 'px',
		height: Math.round(h * height) + 'px',
		fontSize: Math.round(h * (wide ? 0.038 : 0.022)) + 'px'
	}
}
const langNames = LANGS.map((item) => item.name)
const langIndex = computed(() => {
	const index = LANGS.findIndex((item) => item.code === lang.value)
	return index < 0 ? 0 : index
})
const coverMedia = computed(() => {
	const game = script.value && script.value.game
	if (!game) {
		return { url: '', kind: 'image' }
	}
	const land = game.cover_land_url || ''
	const port = game.cover_url || ''
	if (orient.value === 'landscape') {
		if (land) {
			return { url: resolveLocal(land) || land, kind: game.cover_land_kind || 'image' }
		}
		return { url: port ? (resolveLocal(port) || port) : '', kind: game.cover_kind || 'image' }
	}
	if (port) {
		return { url: resolveLocal(port) || port, kind: game.cover_kind || 'image' }
	}
	return { url: land ? (resolveLocal(land) || land) : '', kind: game.cover_land_kind || 'image' }
})
const cover = computed(() => coverMedia.value.url)
const coverKind = computed(() => coverMedia.value.kind)
const coverReady = computed(() => !!cover.value && mediaReady.value)
const bootDone = computed(() => bootPercent.value >= 100 && ready.value && (coverReady.value || !cover.value))
const showConnect = computed(() => !entered.value && !errorText.value && !bootDone.value)
const blurb = computed(() => summary.value || subtitle.value)
const percent = computed(() => {
	if (!total.value) {
		return 8
	}
	return Math.round(done.value / total.value * 100)
})
const progressLabel = computed(() => {
	if (!total.value) {
		return t('checking')
	}
	return t('assets_progress', { done: done.value, total: total.value })
})

function readLaunchClick() {
	try {
		const runtime = typeof plus !== 'undefined' && plus.runtime ? plus.runtime : null
		const args = runtime ? String(runtime.arguments || '') : ''
		const found = args.match(/(?:^|[?&])click_id=([^&]+)/)
		if (found) {
			rememberClick(decodeURIComponent(found[1]))
		}
		const channel = args.match(/(?:^|[?&])ch=([^&]+)/)
		if (channel) {
			rememberChannel(decodeURIComponent(channel[1]))
		}
	} catch (err) {
		// 浏览器里没有安装来源参数
	}
}

watch(cover, () => {
	mediaReady.value = false
})

function onCoverReady() {
	mediaReady.value = true
}

function markBootDone() {
	bootPercent.value = 100
	if (bootTimer) {
		clearInterval(bootTimer)
		bootTimer = null
	}
}

function startBootProgress() {
	if (bootTimer) {
		return
	}
	bootTimer = setInterval(() => {
		if (ready.value && (coverReady.value || !cover.value)) {
			markBootDone()
			return
		}
		if (bootPercent.value < 86) {
			bootPercent.value = Math.min(86, bootPercent.value + 2 + Math.round(Math.random() * 4))
		}
	}, 220)
}

onLoad((query) => {
	const info = uni.getSystemInfoSync()
	pad.value = info.statusBarHeight || 20
	orient.value = readOrient()
	applyFrame()
	uni.onWindowResize(onResize)
	resumeRequested = query.resume === '1'
	rememberChannel(query && (query.ch || query.channel))
	rememberClick(query && query.click)
	readLaunchClick()
	startBootProgress()
	boot()
})

onShow(() => {
	if (entered.value && uni.getStorageSync('token')) {
		refreshSaves()
	}
})

onUnload(() => {
	uni.offWindowResize(onResize)
	if (bootTimer) {
		clearInterval(bootTimer)
		bootTimer = null
	}
})

function applyFrame() {
	frame.value = stageFrame(orient.value)
}

function onResize() {
	applyFrame()
}

function onLang(event) {
	const index = Number(event.detail.value)
	const item = LANGS[index]
	if (item) setLang(item.code)
}

function switchOrient() {
	const next = orient.value === 'portrait' ? 'landscape' : 'portrait'
	orient.value = writeOrient(next)
	applyFrame()
}

async function boot() {
	errorText.value = ''
	ready.value = false
	bootPercent.value = 6
	startBootProgress()
	try {
		await ensureGame()
	} catch (err) {
		errorText.value = (err && err.message) || t('network_error')
		return
	}
	if (!activeGameId()) {
		errorText.value = t('missing_game_id')
		return
	}
	try {
		const res = await fetchScript()
		script.value = res.results || {}
		title.value = script.value.game && script.value.game.title ? script.value.game.title : t('app_name')
		subtitle.value = script.value.game ? script.value.game.subtitle : ''
		summary.value = script.value.game ? script.value.game.summary : ''
		uni.setStorageSync('otome_script_' + activeGameId(), script.value)
		loadAd()
	} catch (err) {
		const message = err && err.message ? err.message : ''
		errorText.value = message || t('network_error')
		return
	}
	ready.value = true
	if (uni.getStorageSync('token')) {
		try {
			const res = await fetchMe()
			await enter(res.results || {}, { resume: resumeRequested })
			return
		} catch (err) {
			if (!sessionRejected(err)) {
				entered.value = true
				menuReady.value = true
				refreshSaves()
				return
			}
			uni.removeStorageSync('token')
			uni.removeStorageSync('otome_uid')
			uni.removeStorageSync('otome_player')
			uid.value = ''
		}
	}
	entered.value = false
	menuReady.value = false
}

function sessionRejected(err) {
	const code = Number((err && (err.code || err.statusCode || (err.data && err.data.code))) || 0)
	return code === 401 || code === 403
}

async function loadAd() {
	try {
		const res = await fetchAds()
		const rows = (res.results && res.results.ads) || []
		ad.value = rows.find((item) => item.slot === 'popup')
			|| rows.find((item) => item.slot === 'loading')
			|| rows[0]
			|| null
		if (ad.value) {
			trackAd(ad.value.id, 'show')
		}
	} catch (err) {
		ad.value = null
	}
}

function openAd() {
	if (ad.value) {
		trackAd(ad.value.id, 'click')
	}
	const url = ad.value && ad.value.link_url
	if (!url) {
		return
	}
	if (typeof plus !== 'undefined' && plus.runtime && plus.runtime.openURL) {
		plus.runtime.openURL(url)
		return
	}
	if (typeof window !== 'undefined') {
		window.open(url, '_blank')
	}
}

async function enter(player, options = {}) {
	applyPlayer(player)
	await refreshSaves()
	entered.value = true
	if (options.resume) {
		resumeRequested = false
		if (!uni.getStorageSync('otome_resume_' + activeGameId()) && autoNodeId) {
			uni.setStorageSync('otome_resume_' + activeGameId(), autoNodeId)
		}
		uni.redirectTo({ url: '/pages/play/play' })
		return
	}
	// 登录按钮和「开始游戏」位置重叠，松开手指时会点到新按钮。先挡住菜单点击。
	menuReady.value = false
	setTimeout(() => {
		menuReady.value = true
	}, 450)
}

async function useDevice() {
	if (loggingIn.value || !ready.value) {
		return
	}
	loggingIn.value = true
	errorText.value = ''
	try {
		const res = await deviceLogin()
		await enter(res.results || {})
	} catch (err) {
		const message = err && err.message ? err.message : t('login_failed')
		uni.showToast({ title: message, icon: 'none' })
	} finally {
		loggingIn.value = false
	}
}

function applyPlayer(player) {
	const saved = saveSession(player)
	uid.value = saved.uid || ''
	loginLabel.value = saved.login_label || t('device_login')
}

async function refreshSaves() {
	try {
		const res = await fetchSaves()
		const rows = (res.results && res.results.saves) || []
		const auto = rows.find((item) => item.is_auto && item.node_id)
		autoNodeId = auto ? auto.node_id : 0
		hasSave.value = !!autoNodeId
	} catch (err) {
		hasSave.value = false
	}
}

function retry() {
	boot()
}

async function start(fresh) {
	if (!menuReady.value) {
		return
	}
	if (!script.value) {
		await boot()
		return
	}
	if (fresh) {
		uni.removeStorageSync('otome_resume_' + activeGameId())
	} else if (!uni.getStorageSync('otome_resume_' + activeGameId()) && autoNodeId) {
		uni.setStorageSync('otome_resume_' + activeGameId(), autoNodeId)
	}
	uni.redirectTo({ url: '/pages/play/play' })
}

function openSaves() {
	uni.navigateTo({ url: '/pages/saves/saves' })
}

function openGallery() {
	uni.navigateTo({ url: '/pages/gallery/gallery' })
}

function logout() {
	if (!menuReady.value) {
		return
	}
	uni.removeStorageSync('token')
	uni.removeStorageSync('otome_uid')
	uni.removeStorageSync('otome_player')
	uni.removeStorageSync('otome_resume_' + activeGameId())
	uid.value = ''
	loginLabel.value = t('device_login')
	hasSave.value = false
	autoNodeId = 0
	entered.value = false
	menuReady.value = false
	// #ifdef H5
	if (window.google && window.google.accounts && window.google.accounts.id) {
		window.google.accounts.id.disableAutoSelect()
	}
	// #endif
}

async function useGoogle() {
	if (!ready.value) {
		return
	}
	googleReady = googleReady || await googleClientId()
	if (!googleReady) {
		uni.showToast({ title: t('google_missing'), icon: 'none' })
		return
	}
	// #ifdef H5
	loadGoogle(googleReady)
	// #endif
	// #ifndef H5
	uni.showToast({ title: t('google_browser'), icon: 'none' })
	// #endif
}

function loadGoogle(clientId) {
	const promptGoogle = () => {
		window.google.accounts.id.initialize({
			client_id: clientId,
			callback: async (resp) => {
				try {
					const res = await googleLogin(resp.credential)
					await enter(res.results || {})
					uni.showToast({ title: t('google_ok'), icon: 'none' })
				} catch (err) {
					const message = err && err.message ? err.message : t('google_failed')
					uni.showToast({ title: message, icon: 'none' })
				}
			}
		})
		window.google.accounts.id.prompt()
	}
	if (window.google && window.google.accounts) {
		promptGoogle()
		return
	}
	const scriptTag = document.createElement('script')
	scriptTag.src = 'https://accounts.google.com/gsi/client'
	scriptTag.onload = promptGoogle
	scriptTag.onerror = () => {
		uni.showToast({ title: t('google_script'), icon: 'none' })
	}
	document.head.appendChild(scriptTag)
}

</script>

<style scoped>
.shell {
	position: fixed;
	left: 0;
	top: 0;
	right: 0;
	bottom: 0;
	width: 100%;
	height: 100%;
	background: #07060c;
}
.stage {
	position: absolute;
	left: 0;
	top: 0;
	right: 0;
	bottom: 0;
	width: 100%;
	height: 100%;
	background: #100c18;
	overflow: hidden;
}
.stage.bare {
	background: #3c1748;
}
.veil {
	position: absolute;
	left: 0;
	top: 0;
	right: 0;
	bottom: 0;
	background: linear-gradient(180deg, rgba(18, 6, 28, 0.28) 0%, rgba(42, 12, 58, 0.18) 42%, rgba(12, 4, 20, 0.55) 100%);
	pointer-events: none;
}
.bg {
	position: absolute;
	left: 0;
	top: 0;
	right: 0;
	bottom: 0;
	width: 100%;
	height: 100%;
	object-fit: cover;
	object-position: center;
	pointer-events: none;
}
.shade {
	position: absolute;
	left: 0;
	top: 0;
	right: 0;
	bottom: 0;
	background: linear-gradient(180deg, rgba(8, 6, 14, 0.12) 0%, rgba(8, 6, 14, 0.02) 36%, rgba(10, 6, 18, 0.2) 62%, rgba(16, 8, 28, 0.72) 100%);
}
.is-landscape .shade {
	background: linear-gradient(90deg, rgba(6, 8, 18, 0.28) 0%, rgba(6, 8, 18, 0.02) 38%, rgba(8, 6, 20, 0.42) 100%);
}
.mode-btn {
	position: absolute;
	z-index: 3;
}
.body {
	position: absolute;
	left: 0;
	top: 0;
	width: 100%;
	height: 100%;
	z-index: 1;
}
.hero {
	position: absolute;
}
.brand-pick,
.brand-wrap {
	display: block;
	line-height: 1;
}
.brand-wrap {
	padding: 0;
	margin: 0;
}
.copy {
	width: 100%;
	overflow-x: hidden;
	overflow-y: auto;
	-webkit-overflow-scrolling: touch;
}
.brand {
	display: block;
	color: #e4c48a;
	letter-spacing: 0.22em;
	text-transform: uppercase;
}
.title {
	display: block;
	color: #f7f4ef;
	line-height: 1.1;
	font-weight: 500;
	font-family: "Iowan Old Style", Palatino, "Palatino Linotype", "Times New Roman", "Songti SC", serif;
	text-shadow: 0 2px 16px rgba(0, 0, 0, 0.35);
}
.uid-line,
.invite {
	display: block;
	font-style: italic;
	font-weight: 400;
	font-family: "Iowan Old Style", Palatino, "Times New Roman", "Songti SC", serif;
}
.uid-line {
	color: #b7aa9c;
	letter-spacing: 0.04em;
}
.connect {
	width: 100%;
}
.connect-label {
	display: block;
	color: #f7f4ef;
	font-weight: 500;
	line-height: 1.2;
}
.connect.lead .connect-label {
	font-weight: 600;
}
.track {
	position: relative;
	margin-top: 14px;
	height: 3px;
	background: rgba(255, 255, 255, 0.22);
	border-radius: 3px;
}
.track-in {
	position: relative;
	height: 3px;
	border-radius: 3px;
	background: linear-gradient(90deg, rgba(255, 236, 196, 0.15) 0%, #f0d7a2 62%, #fff 100%);
}
.track-arrow {
	position: absolute;
	right: -1px;
	top: 50%;
	width: 0;
	height: 0;
	border-top: 5px solid transparent;
	border-bottom: 5px solid transparent;
	border-left: 8px solid #fff;
	transform: translate(40%, -50%);
	filter: drop-shadow(0 0 4px rgba(255, 244, 220, 0.85));
}
.dock.dim .solid {
	background: linear-gradient(90deg, rgba(122, 86, 150, 0.55) 0%, rgba(92, 58, 128, 0.5) 100%);
	color: rgba(255, 255, 255, 0.62);
}
.dock.dim .line {
	background: rgba(8, 6, 14, 0.45);
	border-color: rgba(255, 255, 255, 0.28);
}
.dock.dim .btn text {
	color: rgba(255, 255, 255, 0.62);
}
.invite {
	color: rgba(214, 206, 198, 0.92);
}
.ad {
	position: relative;
	margin-top: 28rpx;
	overflow: hidden;
	border-radius: 24rpx;
	background: rgba(20, 16, 28, 0.72);
	border: 1px solid rgba(231, 194, 122, 0.35);
}
.ad-media {
	display: block;
	width: 100%;
	height: 280rpx;
	background: #1a1522;
}
.ad-copy {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 18rpx 24rpx 22rpx;
}
.ad-title {
	color: #f6efe4;
	font-size: 28rpx;
}
.ad-go,
.ad-close {
	color: #e7c27a;
	font-size: 24rpx;
}
.ad-close {
	position: absolute;
	right: 16rpx;
	top: 12rpx;
	padding: 8rpx 12rpx;
}
.panel {
	margin-top: 16px;
}
.locked {
	pointer-events: none;
}
.label {
	display: block;
	color: #f6efe4;
	font-size: 28rpx;
	margin-bottom: 18rpx;
}
.bar {
	height: 8rpx;
	background: rgba(255, 255, 255, 0.12);
	border-radius: 8rpx;
	overflow: hidden;
}
.bar-in {
	height: 8rpx;
	background: #e7c27a;
}
.hint {
	display: block;
	margin-top: 22rpx;
	color: #b7adc4;
	font-size: 26rpx;
	line-height: 1.6;
}
.btn {
	position: absolute;
	margin: 0;
	border-radius: 999rpx;
	display: flex;
	align-items: center;
	justify-content: center;
	color: #fff;
	font-weight: 600;
	letter-spacing: 0.08em;
	box-sizing: border-box;
}
.solid {
	background: linear-gradient(90deg, #e7a6ff 0%, #c56bff 46%, #9a45f0 100%);
}
.fill {
	background: linear-gradient(90deg, rgba(88, 58, 112, 0.82) 0%, rgba(46, 28, 72, 0.88) 100%);
}
.line {
	background: rgba(10, 8, 16, 0.28);
	border: 1px solid rgba(255, 255, 255, 0.62);
}
.btn text {
	color: #fff;
	font-weight: 600;
	letter-spacing: 0.08em;
}
.g-logo {
	width: 34rpx;
	height: 34rpx;
	margin-right: 14rpx;
	flex-shrink: 0;
	background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'%3E%3Cpath fill='%23FFC107' d='M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.3 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 8 3.1l5.7-5.7C34.2 6.1 29.4 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.2-.1-2.3-.4-3.5z'/%3E%3Cpath fill='%23FF3D00' d='M6.3 14.7l6.6 4.8C14.7 16 19 12 24 12c3.1 0 5.8 1.2 8 3.1l5.7-5.7C34.2 6.1 29.4 4 24 4 16.3 4 9.6 8.3 6.3 14.7z'/%3E%3Cpath fill='%234CAF50' d='M24 44c5.2 0 10-2 13.6-5.2l-6.3-5.3C29.2 35.1 26.7 36 24 36c-5.3 0-9.7-3.3-11.3-8l-6.5 5C9.5 39.6 16.2 44 24 44z'/%3E%3Cpath fill='%231976D2' d='M43.6 20.5H42V20H24v8h11.3c-1.1 3.2-3.5 5.7-6.6 7.1l6.3 5.3C37.4 38.4 44 33 44 24c0-1.2-.1-2.3-.4-3.5z'/%3E%3C/svg%3E") center / contain no-repeat;
}
.restart {
	position: absolute;
	color: #f4f1ec;
	letter-spacing: 0.12em;
	font-weight: 600;
}
</style>
