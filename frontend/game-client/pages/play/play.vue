<template>
	<view class="shell">
	<view class="stage" :class="orientClass" :style="frameStyle">
		<video
			v-if="bg && bgKind === 'video'"
			:key="'bg-' + bg"
			class="bg"
			:src="bg"
			autoplay
			loop
			muted
			playsinline
			:controls="false"
			:show-center-play-btn="false"
			:enable-progress-gesture="false"
			object-fit="cover"
		></video>
		<image v-else-if="bg" class="bg" :src="bg" mode="aspectFill"></image>
		<view v-else class="bg fallback"></view>
		<view class="top" :style="topStyle">
			<view class="chapter" :style="chapterStyle">
				<image class="chapter-back" :style="backStyle" src="/static/play/back.svg" mode="scaleToFill" @click.stop="backHome"></image>
				<text class="chapter-title" :style="titleStyle">{{ gameTitle }}</text>
			</view>
			<view class="hud-actions">
				<image class="hud-btn" :style="btnStyle" src="/static/play/save.svg" mode="scaleToFill" @click.stop="saveNow"></image>
				<image class="hud-btn" :style="btnGapStyle" src="/static/play/orientation.svg" mode="scaleToFill" @click.stop="switchOrient"></image>
				<view class="hud-btn" :style="btnGapStyle" @click.stop="toggleMute">
					<image class="hud-btn-icon" :src="soundIcon" mode="scaleToFill"></image>
				</view>
			</view>
		</view>
		<view v-if="!ended && !insertOpen" class="cast">
			<template v-for="(fig, index) in figures" :key="index + '-' + fig.url">
				<video
					v-if="fig.kind === 'video'"
					class="cast-figure"
					:style="slotStyle(fig.position)"
					:src="fig.url"
					autoplay
					loop
					muted
					playsinline
					:controls="false"
					:show-center-play-btn="false"
					:enable-progress-gesture="false"
					object-fit="contain"
				></video>
				<image v-else class="cast-figure" :style="slotStyle(fig.position)" :src="fig.url" mode="aspectFit"></image>
			</template>
		</view>
		<view v-if="current && !ended && !insertOpen" class="dock" :class="{ 'dock-land': land, 'dock-choices': showChoices }" :style="dockStyle">
			<view class="panel" :style="panelBoxStyle" @click="advance">
				<image class="panel-bg" :class="{ flip: panelFlip }" :src="panelSrc" mode="scaleToFill"></image>
				<text v-if="speakerLabel" class="panel-name" :style="nameStyle">{{ speakerLabel }}</text>
				<text class="panel-line" :style="lineStyle">{{ shown }}</text>
				<view v-if="showChoices && !land" class="panel-prompt" :style="promptStyle">
					<view class="prompt-line"></view>
					<view class="prompt-row">
						<image class="prompt-arrow" :style="arrowStyle" src="/static/play/choice-arrow.svg?v=2" mode="scaleToFill"></image>
						<text class="prompt-label" :style="promptLabelStyle">{{ t('make_choice') }}</text>
					</view>
				</view>
				<view v-else class="voice-slot" :style="voiceSlotStyle" @click.stop="replayVoice">
					<image class="voice-icon" :style="voiceIconStyle" :src="reading ? '/static/play/voice-pause.svg' : '/static/play/continue.svg?v=2'" mode="aspectFit"></image>
				</view>
			</view>
			<view v-if="showChoices" class="choice-list" :style="choiceListStyle">
				<view v-for="item in current.choices" :key="item.id" class="choice" :style="choiceStyle" @click.stop="pick(item)">
					<image class="choice-bg" src="/static/play/choice.svg?v=2" mode="scaleToFill"></image>
					<text class="choice-text" :style="choiceTextStyle">{{ item.text }}</text>
				</view>
			</view>
		</view>
		<image v-if="current && !ended && !insertOpen" class="forward" :style="forwardStyle" src="/static/play/fast-forward.svg?v=2" mode="scaleToFill" @click.stop="advance"></image>
		<view v-if="insertOpen" class="insert">
			<video
				v-if="insertKind === 'video'"
				class="insert-media"
				:src="insertUrl"
				autoplay
				playsinline
				:muted="false"
				:controls="false"
				:show-center-play-btn="false"
				:enable-progress-gesture="false"
				object-fit="contain"
				@ended="skipInsert"
			></video>
			<image v-else class="insert-media" :src="insertUrl" mode="aspectFit"></image>
			<view class="insert-hit" @click="skipInsert"></view>
			<text class="insert-skip">{{ t('skip') }}</text>
		</view>
		<view v-if="ended" class="ending" :style="endingStyle">
			<view class="ending-card" :style="endingCardStyle">
				<text class="ending-title" :style="endingTitleStyle">{{ endingTitle }}</text>
				<text class="ending-text" :style="endingTextStyle">{{ current ? current.content : '' }}</text>
				<view class="end-btn" :style="endBtnStyle" @click="restart">{{ t('start_over') }}</view>
				<view class="end-btn ghost" :style="endBtnStyle" @click="backHome">{{ t('back_title') }}</view>
			</view>
		</view>
		<view v-if="segmentLoading" class="mask" :style="maskStyle">
			<text class="mask-title" :style="maskTitleStyle">{{ t('new_segment') }}</text>
			<text v-if="segmentError" class="mask-label" :style="maskLabelStyle">{{ t('assets_incomplete') }}</text>
			<view v-if="segmentError" class="end-btn" @click="retrySegment">{{ t('retry') }}</view>
		</view>
	</view>
	</view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onLoad, onUnload } from '@dcloudio/uni-app'
import { activeGameId } from '@/config/game.js'
import { createSave, reportProgress } from '@/api/otome.js'
import { downloadAll, resolveLocal } from '@/utils/assetCache.js'
import { isAppRuntime, readOrient, stageFrame, writeOrient } from '@/utils/orientation.js'
import { currentLang, t } from '@/utils/i18n.js'

const pad = ref(20)
const orient = ref('portrait')
const frame = ref({ width: 375, height: 667, left: 0, top: 0 })
const gameTitle = ref('')
const current = ref(null)
const shown = ref('')
const ended = ref(false)
const endingTitle = ref(t('ending'))
const muted = ref(false)
const segmentLoading = ref(false)
const segmentError = ref(false)
const nodeMap = {}
let script = null
let timer = null
let bgm = null
let bgmSrc = ''
const bgmList = []
let voice = null
let voiceToken = 0
const reading = ref(false)
let effect = null
let busy = false
let pendingId = 0
let loadedChapterId = 0

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
const hudSize = computed(() => {
	const short = Math.min(frame.value.width || 375, frame.value.height || 667)
	return Math.round(short * (land.value ? 0.078 : 0.086))
})
const topStyle = computed(() => {
	const size = hudSize.value
	return {
		paddingTop: Math.max(pad.value, Math.round(size * 0.22)) + 'px',
		paddingLeft: '0px',
		paddingRight: Math.round(size * 0.28) + 'px'
	}
})
const backHeight = computed(() => Math.round(hudSize.value * 42 / 36))
const chapterStyle = computed(() => {
	return { height: backHeight.value + 'px' }
})
const backStyle = computed(() => {
	const height = backHeight.value
	return {
		width: Math.round(height * 41 / 42) + 'px',
		height: height + 'px'
	}
})
const titleStyle = computed(() => {
	const height = backHeight.value
	const width = frame.value.width || 375
	return {
		fontSize: Math.round(height * 0.5) + 'px',
		maxWidth: Math.round(width * (land.value ? 0.42 : 0.48)) + 'px',
		marginLeft: Math.round(height * (land.value ? 0.46 : 0.38)) + 'px'
	}
})
const btnStyle = computed(() => {
	const size = hudSize.value
	return { width: size + 'px', height: size + 'px' }
})
const btnGapStyle = computed(() => {
	const size = hudSize.value
	const gap = land.value ? 0.28 : 0.18
	return {
		width: size + 'px',
		height: size + 'px',
		marginLeft: Math.round(size * gap) + 'px'
	}
})
const soundIcon = computed(() => (muted.value ? '/static/play/mute.svg' : '/static/play/sound.svg'))
const bgMedia = computed(() => pickMedia('background_land_url', 'background_url', 'background_land_kind', 'background_kind'))
const figures = computed(() => {
	const node = current.value
	if (!node) return []
	const raw = node.figures && node.figures.length ? node.figures : [{
		position: 'e',
		url: node.portrait_url,
		kind: node.portrait_kind,
		land_url: node.portrait_land_url,
		land_kind: node.portrait_land_kind,
	}]
	return raw.map((fig) => {
		const land = orient.value === 'landscape'
		const url = land ? (fig.land_url || fig.url) : (fig.url || fig.land_url)
		const kind = land ? (fig.land_url ? fig.land_kind : fig.kind) : (fig.url ? fig.kind : fig.land_kind)
		return { position: fig.position || 'c', url: url || '', kind: kind || 'image' }
	}).filter((fig) => fig.url)
})
const slots = {
	nw: [1, 1], n: [2, 1], ne: [3, 1],
	w: [1, 2], c: [2, 2], e: [3, 2],
	sw: [1, 3], s: [2, 3], se: [3, 3],
}

function slotStyle(position) {
	const pair = slots[position] || slots.c
	return { gridColumn: String(pair[0]), gridRow: String(pair[1]) }
}
const bg = computed(() => bgMedia.value.url)
const bgKind = computed(() => bgMedia.value.kind)
const insertOpen = ref(false)
let insertDone = false
let insertBusy = false
const insertUrl = computed(() => localOf((current.value && current.value.insert_url) || ''))
const insertKind = computed(() => (current.value && current.value.insert_kind) || '')
const showChoices = computed(() => {
	if (insertOpen.value || !current.value || ended.value || segmentLoading.value) {
		return false
	}
	if (current.value.insert_url && !insertDone) {
		return false
	}
	const choices = current.value.choices || []
	return choices.length > 0 && shown.value.length >= (current.value.content || '').length
})
const NARRATORS = new Set([
	'旁白', 'Narrator', 'ナレーション', '내레이션', 'Narrador', 'Narrateur', 'Erzähler',
	'Рассказчик', 'الراوي', 'ผู้บรรยาย', 'Người dẫn', 'Narator', 'Narratore', 'Anlatıcı',
	'Verteller', 'कथावाचक', 'Pencerita', 'Tagapagsalaysay', 'Berättare'
])
const PLAYERS = new Set(['你', '我', 'You', 'YOU', 'User', 'USER', 'USER NAME'])
const PANEL = {
	// ratio 跟 SVG viewBox 一致；pad* 按原型收紧，避免底空过大。
	left: { src: '/static/play/dialog-npc.svg?v=2', ratio: 131 / 323, padTop: 0.34, padBottom: 0.12, padLeft: 0.14, padRight: 0.16, name: { left: 0.19, top: 0.02, width: 0.46, height: 0.2, align: 'left' } },
	tall: { src: '/static/play/dialog-npc-tall.svg?v=2', ratio: 156 / 323, padTop: 0.28, padBottom: 0.12, padLeft: 0.14, padRight: 0.15, name: { left: 0.19, top: 0.015, width: 0.46, height: 0.17, align: 'left' } },
	right: { src: '/static/play/dialog-player.svg?v=2', ratio: 136 / 323, padTop: 0.32, padBottom: 0.12, padLeft: 0.12, padRight: 0.16, name: { left: 0.5, top: 0.02, width: 0.38, height: 0.18, align: 'right' } },
	narr: { src: '/static/play/dialog-narrator.svg?v=2', ratio: 100 / 320, padTop: 0.16, padBottom: 0.14, padLeft: 0.1, padRight: 0.14, name: null },
	choice: { src: '/static/play/dialog-choice.svg?v=2', ratio: 140 / 334, padTop: 0.26, padBottom: 0.28, padLeft: 0.13, padRight: 0.12, name: { left: 0.18, top: 0.02, width: 0.46, height: 0.18, align: 'left' } },
	'choice-right': { src: '/static/play/dialog-choice.svg?v=2', ratio: 140 / 334, padTop: 0.26, padBottom: 0.28, padLeft: 0.12, padRight: 0.14, name: { left: 0.42, top: 0.02, width: 0.42, height: 0.18, align: 'right' }, flip: true },
	'choice-narr': { src: '/static/play/dialog-narrator.svg?v=2', ratio: 100 / 320, padTop: 0.08, padBottom: 0.24, padLeft: 0.1, padRight: 0.14, name: null }
}
const speakerLabel = computed(() => {
	const name = ((current.value && current.value.speaker_name) || '').trim()
	if (!name || NARRATORS.has(name)) return ''
	return name
})
const isPlayerLine = computed(() => {
	const name = speakerLabel.value
	if (!name) return false
	if (PLAYERS.has(name)) return true
	const color = String((current.value && current.value.name_color) || '').toLowerCase()
	return color === '#f3d2dc'
})
const panelKind = computed(() => {
	// 横屏有选项时仍用普通对话框；竖屏才用带「做出你的选择」的 choice 框。
	if (showChoices.value && !land.value) {
		if (!speakerLabel.value) return 'choice-narr'
		return isPlayerLine.value ? 'choice-right' : 'choice'
	}
	if (!speakerLabel.value) return 'narr'
	if (isPlayerLine.value) return 'right'
	const text = (current.value && current.value.content) || ''
	return text.length > 36 ? 'tall' : 'left'
})
const panelMeta = computed(() => PANEL[panelKind.value] || PANEL.left)
const panelSrc = computed(() => panelMeta.value.src)
const panelFlip = computed(() => !!panelMeta.value.flip)
const panelWidth = computed(() => {
	const w = frame.value.width || 375
	if (land.value) {
		return Math.round(w * (showChoices.value ? 0.38 : 0.42))
	}
	return Math.round(w * 0.88)
})
const panelHeight = computed(() => Math.round(panelWidth.value * panelMeta.value.ratio))
const barHeight = computed(() => Math.round((frame.value.width || 375) * 80 / 375))
const dockStyle = computed(() => {
	const w = frame.value.width || 375
	const h = frame.value.height || 667
	if (land.value) {
		// 原型：内容区 = 下半屏 50% × 左侧 88%
		let justify = 'center'
		if (showChoices.value) justify = 'flex-start'
		else if (isPlayerLine.value) justify = 'flex-end'
		return {
			top: Math.round(h * 0.5) + 'px',
			bottom: '0px',
			left: '0px',
			width: Math.round(w * 0.88) + 'px',
			flexDirection: showChoices.value ? 'row' : 'column',
			alignItems: 'center',
			justifyContent: justify,
			paddingLeft: Math.round(w * 0.028) + 'px',
			paddingRight: Math.round(w * 0.016) + 'px',
			paddingBottom: Math.round(h * 0.025) + 'px',
			boxSizing: 'border-box',
			overflow: 'hidden'
		}
	}
	return {
		top: '50%',
		bottom: barHeight.value + 'px',
		left: '0px',
		right: '0px',
		width: '100%',
		flexDirection: 'column',
		alignItems: 'center',
		justifyContent: showChoices.value ? 'flex-end' : 'center',
		paddingBottom: showChoices.value ? Math.round(panelWidth.value * 0.01) + 'px' : '0px',
		boxSizing: 'border-box'
	}
})
const panelBoxStyle = computed(() => {
	const meta = panelMeta.value
	const height = panelHeight.value
	const frameH = frame.value.height || 667
	let padTop = Math.round(height * meta.padTop)
	let padBottom = Math.round(height * meta.padBottom)
	if (land.value) {
		// 横屏收紧上下内边距，避免底空过大顶出屏幕
		padTop = Math.round(height * (meta.name ? 0.22 : 0.12))
		padBottom = Math.round(height * 0.08)
	} else if (showChoices.value) {
		// 给「做出你的选择」提示留足底部空间，避免贴底被裁切
		padBottom = Math.max(padBottom, Math.round(panelWidth.value * 0.12))
	}
	const voiceRoom = showChoices.value ? 0 : 0.08
	const fontSize = Math.round(panelWidth.value * (land.value ? 0.034 : 0.042))
	const innerW = panelWidth.value * (1 - meta.padLeft - meta.padRight - voiceRoom)
	const text = (current.value && current.value.content) || ''
	let units = 0
	for (const ch of text) {
		units += ch.charCodeAt(0) > 255 ? 1 : 0.55
	}
	const lines = Math.max(1, Math.ceil(units / Math.max(1, innerW / fontSize)))
	const need = padTop + padBottom + Math.ceil(lines * fontSize * (land.value ? 1.45 : 1.55)) + Math.round(fontSize * 0.6)
	const minHeight = Math.max(land.value ? Math.round(height * 0.88) : height, need)
	const style = {
		width: panelWidth.value + 'px',
		minHeight: minHeight + 'px',
		height: minHeight + 'px',
		paddingTop: padTop + 'px',
		paddingBottom: padBottom + 'px',
		paddingLeft: Math.round(panelWidth.value * meta.padLeft) + 'px',
		paddingRight: Math.round(panelWidth.value * (meta.padRight + voiceRoom)) + 'px',
		boxSizing: 'border-box'
	}
	if (land.value) {
		// 限制在下半屏内容区内，长文案在框内滚动
		style.maxHeight = Math.round(frameH * 0.42) + 'px'
		style.overflow = 'hidden'
	}
	return style
})
const lineStyle = computed(() => {
	const scale = land.value ? 0.034 : 0.042
	const style = {
		fontSize: Math.round(panelWidth.value * scale) + 'px',
		lineHeight: land.value ? '1.45' : '1.55'
	}
	if (land.value) {
		const frameH = frame.value.height || 667
		const meta = panelMeta.value
		const height = panelHeight.value
		const padTop = Math.round(height * (meta.name ? 0.22 : 0.12))
		const padBottom = Math.round(height * 0.08)
		const maxPanel = Math.round(frameH * 0.42)
		style.maxHeight = Math.max(48, maxPanel - padTop - padBottom) + 'px'
		style.overflow = 'hidden'
	}
	return style
})
const nameStyle = computed(() => {
	const meta = panelMeta.value.name
	const height = panelHeight.value
	const width = panelWidth.value
	if (!meta) return {}
	return {
		left: Math.round(width * meta.left) + 'px',
		top: Math.round(height * meta.top) + 'px',
		width: Math.round(width * meta.width) + 'px',
		height: Math.round(height * meta.height) + 'px',
		lineHeight: Math.round(height * meta.height) + 'px',
		fontSize: Math.round(width * (land.value ? 0.032 : 0.036)) + 'px',
		textAlign: meta.align
	}
})
const promptStyle = computed(() => {
	const width = panelWidth.value
	// dialog-choice.svg 主体底边约在 131/140，底部有透明边；用百分比把提示抬进色块内
	const choiceFrame = panelKind.value === 'choice' || panelKind.value === 'choice-right'
	return {
		bottom: choiceFrame ? '7%' : Math.round(width * 0.018) + 'px',
		paddingBottom: Math.round(width * 0.01) + 'px',
		paddingTop: Math.round(width * 0.012) + 'px'
	}
})
const promptLabelStyle = computed(() => {
	return {
		fontSize: Math.round(panelWidth.value * 0.03) + 'px',
		lineHeight: Math.round(panelWidth.value * 0.042) + 'px'
	}
})
const arrowStyle = computed(() => {
	const size = Math.max(7, Math.round(panelWidth.value * 0.022))
	return { width: size + 'px', height: Math.round(size * 6 / 7) + 'px' }
})
const voiceSlotStyle = computed(() => {
	const width = panelWidth.value
	const height = panelHeight.value
	const meta = panelMeta.value
	const size = Math.round(width * (land.value ? 0.055 : 0.062))
	return {
		width: size + 'px',
		height: size + 'px',
		right: Math.round(width * 0.045) + 'px',
		bottom: Math.round(height * meta.padBottom * 0.35) + 'px'
	}
})
const voiceIconStyle = computed(() => {
	const size = Math.round(panelWidth.value * (land.value ? 0.045 : 0.05))
	return { width: size + 'px', height: size + 'px' }
})
const choiceListStyle = computed(() => {
	const w = frame.value.width || 375
	if (land.value) {
		return {
			width: Math.round(w * 0.38) + 'px',
			marginTop: '0px',
			marginLeft: Math.round(w * 0.02) + 'px'
		}
	}
	return {
		width: Math.round(panelWidth.value * 0.94) + 'px',
		marginTop: Math.round(panelWidth.value * 0.035) + 'px'
	}
})
const choiceStyle = computed(() => {
	const w = frame.value.width || 375
	const width = land.value ? Math.round(w * 0.38) : Math.round(panelWidth.value * 0.94)
	const minHeight = Math.round(width * 65 / 311)
	// 上下留白按按钮宽度算，两行文案仍落在原按钮高度里；更长的句子把按钮撑高。
	const padY = Math.round(width * 0.048)
	return {
		width: width + 'px',
		minHeight: minHeight + 'px',
		height: 'auto',
		paddingTop: padY + 'px',
		paddingBottom: padY + 'px',
		boxSizing: 'border-box',
		marginBottom: Math.round((land.value ? w : panelWidth.value) * (land.value ? 0.012 : 0.01)) + 'px'
	}
})
const choiceTextStyle = computed(() => {
	const w = land.value ? (frame.value.width || 375) * 0.38 : panelWidth.value
	return { fontSize: Math.round(w * (land.value ? 0.034 : 0.04)) + 'px' }
})
const forwardStyle = computed(() => {
	const width = frame.value.width || 375
	const height = frame.value.height || 667
	if (land.value) {
		const size = Math.round(Math.min(width, height) * 0.14)
		return {
			width: size + 'px',
			height: size + 'px',
			right: Math.round(width * 0.02) + 'px',
			bottom: Math.round(height * 0.06) + 'px'
		}
	}
	const bar = barHeight.value
	const size = Math.round(width * 0.17)
	return {
		width: size + 'px',
		height: size + 'px',
		right: Math.round(width * 0.012) + 'px',
		bottom: Math.round((bar - size) / 2) + 'px'
	}
})
const maskStyle = computed(() => {
	const short = Math.min(frame.value.width || 375, frame.value.height || 667)
	return {
		paddingLeft: Math.round(short * 0.08) + 'px',
		paddingRight: Math.round(short * 0.08) + 'px'
	}
})
const maskTitleStyle = computed(() => {
	const short = Math.min(frame.value.width || 375, frame.value.height || 667)
	return {
		fontSize: Math.round(short * (land.value ? 0.045 : 0.048)) + 'px',
		lineHeight: '1.35'
	}
})
const maskLabelStyle = computed(() => {
	const short = Math.min(frame.value.width || 375, frame.value.height || 667)
	return {
		fontSize: Math.round(short * (land.value ? 0.032 : 0.034)) + 'px',
		lineHeight: '1.4'
	}
})
const endingStyle = computed(() => {
	const short = Math.min(frame.value.width || 375, frame.value.height || 667)
	return {
		padding: Math.round(short * (land.value ? 0.06 : 0.08)) + 'px'
	}
})
const endingCardStyle = computed(() => {
	const w = frame.value.width || 375
	const h = frame.value.height || 667
	const short = Math.min(w, h)
	return {
		width: Math.round(w * (land.value ? 0.56 : 0.88)) + 'px',
		maxHeight: Math.round(h * (land.value ? 0.82 : 0.78)) + 'px',
		padding: Math.round(short * 0.05) + 'px ' + Math.round(short * 0.045) + 'px'
	}
})
const endingTitleStyle = computed(() => {
	const short = Math.min(frame.value.width || 375, frame.value.height || 667)
	return {
		fontSize: Math.round(short * (land.value ? 0.05 : 0.056)) + 'px',
		marginBottom: Math.round(short * 0.028) + 'px'
	}
})
const endingTextStyle = computed(() => {
	const short = Math.min(frame.value.width || 375, frame.value.height || 667)
	return {
		fontSize: Math.round(short * (land.value ? 0.032 : 0.036)) + 'px',
		lineHeight: '1.7',
		marginBottom: Math.round(short * 0.04) + 'px'
	}
})
const endBtnStyle = computed(() => {
	const short = Math.min(frame.value.width || 375, frame.value.height || 667)
	const height = Math.round(short * (land.value ? 0.1 : 0.11))
	return {
		height: height + 'px',
		lineHeight: height + 'px',
		fontSize: Math.round(short * (land.value ? 0.034 : 0.038)) + 'px',
		marginBottom: Math.round(short * 0.028) + 'px'
	}
})
onLoad(() => {
	const info = uni.getSystemInfoSync()
	pad.value = info.statusBarHeight || 20
	orient.value = readOrient()
	applyFrame()
	uni.onWindowResize(onResize)
	script = uni.getStorageSync('otome_script_' + activeGameId())
	if (!script || !script.nodes) {
		uni.reLaunch({ url: '/pages/loading/loading?menu=1' })
		return
	}
	gameTitle.value = script.game ? script.game.title : ''
	script.nodes.forEach((item) => {
		nodeMap[item.id] = item
	})
	const resume = Number(uni.getStorageSync('otome_resume_' + activeGameId()) || 0)
	uni.removeStorageSync('otome_resume_' + activeGameId())
	const startId = resume && nodeMap[resume] ? resume : script.entry_node_id
	enterNode(startId)
})

onUnload(() => {
	clearInterval(timer)
	destroyAudio()
	uni.offWindowResize(onResize)
})

function applyFrame() {
	frame.value = stageFrame(orient.value)
	// 锁定竖/横后补一次，避免部分机型首帧拿到未旋转尺寸
	if (isAppRuntime()) {
		setTimeout(() => {
			frame.value = stageFrame(orient.value)
		}, 120)
	}
}

function onResize() {
	applyFrame()
}

function switchOrient() {
	const next = orient.value === 'portrait' ? 'landscape' : 'portrait'
	orient.value = writeOrient(next)
	applyFrame()
}

function pickMedia(landUrl, portUrl, landKind, portKind) {
	const node = current.value
	if (!node) {
		return { url: '', kind: 'image' }
	}
	const land = node[landUrl]
	const port = node[portUrl]
	if (orient.value === 'landscape') {
		if (land) {
			return { url: localOf(land), kind: node[landKind] || 'image' }
		}
		return { url: localOf(port), kind: node[portKind] || 'image' }
	}
	if (port) {
		return { url: localOf(port), kind: node[portKind] || 'image' }
	}
	return { url: localOf(land), kind: node[landKind] || 'image' }
}

function localOf(url) {
	if (!url) {
		return ''
	}
	return resolveLocal(url) || url
}

function textDone() {
	const full = current.value && current.value.content ? current.value.content : ''
	return shown.value.length >= full.length
}

function startType() {
	clearInterval(timer)
	const full = current.value.content || ''
	let index = 0
	shown.value = ''
	timer = setInterval(() => {
		index += 1
		shown.value = full.slice(0, index)
		if (index >= full.length) {
			clearInterval(timer)
		}
	}, 28)
}

function openInsert() {
	const node = current.value
	if (!node || insertDone || insertOpen.value || !node.insert_url) {
		return
	}
	insertOpen.value = true
	if (node.insert_kind === 'video') {
		stopBgm()
	}
}

function chapterOf(id) {
	const keys = (script.nodes || []).filter((item) => item.is_key)
	for (let index = 0; index < keys.length; index += 1) {
		if (keys[index].id === id || reaches(keys[index].id, id)) {
			return keys[index]
		}
	}
	return nodeMap[id] || null
}

function reaches(origin, target) {
	const seen = {}
	const queue = [origin]
	while (queue.length) {
		const currentId = queue.shift()
		if (seen[currentId]) {
			continue
		}
		seen[currentId] = true
		if (currentId === target) {
			return true
		}
		const node = nodeMap[currentId]
		if (!node || (currentId !== origin && node.is_key)) {
			continue
		}
		if (node.next_id) {
			queue.push(node.next_id)
		}
		;(node.choices || []).forEach((choice) => {
			if (choice.next_id) {
				queue.push(choice.next_id)
			}
		})
	}
	return false
}

async function enterNode(id) {
	if (busy) {
		return
	}
	const node = nodeMap[id]
	if (!node) {
		ended.value = true
		endingTitle.value = t('to_be_continued')
		return
	}
	pendingId = id
	const chapter = chapterOf(id)
	const chapterUrls = (chapter && chapter.preload_urls) || []
	if (chapter && chapter.id !== loadedChapterId && chapterUrls.length) {
		segmentLoading.value = true
		segmentError.value = false
		busy = true
		try {
			await downloadAll(chapterUrls)
			loadedChapterId = chapter.id
		} catch (err) {
			segmentError.value = true
			busy = false
			return
		}
		segmentLoading.value = false
		busy = false
	} else if (chapter) {
		loadedChapterId = chapter.id
	}
	ended.value = false
	insertDone = false
	insertOpen.value = false
	current.value = node
	applyAudio(node)
	startType()
	remember(node)
}

function remember(node) {
	reportProgress(node.id).then((res) => {
		const fresh = res && res.results && res.results.newly_unlocked ? res.results.newly_unlocked : []
		if (fresh.length) {
			uni.showToast({ title: t('unlocked_new'), icon: 'none' })
		}
	}).catch(() => {})
}

function saveNow() {
	if (!current.value || segmentLoading.value) {
		return
	}
	createSave(current.value.id).then(() => {
		uni.showToast({ title: t('saved_history'), icon: 'none' })
	}).catch(() => {})
}

function advance() {
	if (!current.value || ended.value || segmentLoading.value || insertOpen.value) {
		return
	}
	ensureBgm()
	if (!textDone()) {
		playEffect(localOf(current.value.interact_url))
		clearInterval(timer)
		shown.value = current.value.content || ''
		return
	}
	if (current.value.insert_url && !insertDone) {
		openInsert()
		return
	}
	if ((current.value.choices || []).length) {
		return
	}
	playEffect(localOf(current.value.interact_url))
	leaveNode()
}

function skipInsert() {
	if (!insertOpen.value || insertBusy) {
		return
	}
	insertBusy = true
	insertOpen.value = false
	insertDone = true
	const node = current.value
	if (node) {
		rememberInsert(node)
		if (node.insert_kind === 'video') {
			applyAudio(node)
		}
	}
	insertBusy = false
	if (!node || (node.choices || []).length) {
		return
	}
	leaveNode()
}

function leaveNode() {
	const node = current.value
	if (!node) {
		return
	}
	if (node.is_ending || !node.next_id) {
		ended.value = true
		endingTitle.value = node.ending_title || t('ending')
		return
	}
	enterNode(node.next_id, false)
}

function rememberInsert(node) {
	reportProgress(node.id, true).then((res) => {
		const fresh = res && res.results && res.results.newly_unlocked ? res.results.newly_unlocked : []
		if (fresh.length) {
			uni.showToast({ title: t('added_gallery'), icon: 'none' })
		}
	}).catch(() => {})
}

function pick(choice) {
	playEffect(localOf(choice.interact_url))
	enterNode(choice.next_id, false)
}

function retrySegment() {
	segmentLoading.value = false
	busy = false
	enterNode(pendingId, false)
}

function restart() {
	backHome()
}

function backHome() {
	destroyAudio()
	uni.reLaunch({ url: '/pages/loading/loading?menu=1' })
}

function toggleMute() {
	muted.value = !muted.value
	if (muted.value) {
		stopBgm()
		return
	}
	if (current.value && current.value.bgm_url) {
		playBgm(localOf(current.value.bgm_url))
	}
}

function applyAudio(node) {
	if (muted.value) {
		stopBgm()
	} else if (node.bgm_url) {
		playBgm(localOf(node.bgm_url))
	} else {
		stopBgm()
	}
	if (node.voice_url) {
		playVoice(localOf(node.voice_url))
		return
	}
	stopVoice()
}

function ensureBgm() {
	if (muted.value || !bgm || !bgmSrc) {
		return
	}
	resumeBgm(bgm)
}

function resumeBgm(audio) {
	if (!audio) {
		return
	}
	try {
		audio.muted = false
		audio.volume = 0.45
	} catch (err) {}
	try {
		const play = audio.play()
		if (play && typeof play.catch === 'function') {
			play.catch(() => {})
		}
	} catch (err) {}
}

function playBgm(src) {
	if (!src || muted.value) {
		stopBgm()
		return
	}
	if (bgm && bgmSrc === src) {
		resumeBgm(bgm)
		return
	}
	stopBgm()
	let audio = null
	if (typeof Audio !== 'undefined') {
		audio = new Audio()
		audio.preload = 'auto'
		audio.loop = true
		audio.volume = 0.45
		audio.src = src
	} else {
		audio = uni.createInnerAudioContext()
		audio.loop = true
		audio.volume = 0.45
		audio.src = src
	}
	bgm = audio
	bgmSrc = src
	bgmList.push(audio)
	resumeBgm(audio)
}

function playEffect(src) {
	stopEffect()
	if (!src) {
		return
	}
	const ctx = uni.createInnerAudioContext()
	ctx.src = src
	ctx.loop = false
	try {
		ctx.play()
	} catch (err) {
		return
	}
	effect = ctx
}

function stopEffect() {
	if (!effect) {
		return
	}
	try {
		effect.stop()
		effect.destroy()
	} catch (err) {
		return
	}
	effect = null
}

function finishVoice(token) {
	if (token !== voiceToken) {
		return
	}
	reading.value = false
}

function playVoice(src) {
	stopVoice()
	if (!src) {
		return
	}
	const token = voiceToken
	const ctx = uni.createInnerAudioContext()
	ctx.src = src
	ctx.loop = false
	const done = () => finishVoice(token)
	if (typeof ctx.onEnded === 'function') {
		ctx.onEnded(done)
	}
	if (typeof ctx.onStop === 'function') {
		ctx.onStop(done)
	}
	if (typeof ctx.onError === 'function') {
		ctx.onError(done)
	}
	try {
		ctx.play()
	} catch (err) {
		reading.value = false
		return
	}
	voice = ctx
	reading.value = true
}

function speakLine() {
	const text = ((current.value && (current.value.content || shown.value)) || '').trim()
	const synth = typeof window !== 'undefined' ? window.speechSynthesis : null
	if (!text || !synth || typeof SpeechSynthesisUtterance === 'undefined') {
		reading.value = false
		return
	}
	const token = voiceToken
	const code = currentLang()
	const voiceLang = {
		'zh-Hans': 'zh-CN',
		'zh-Hant': 'zh-TW',
		en: 'en-US',
		ja: 'ja-JP',
		ko: 'ko-KR',
		es: 'es-ES',
		fr: 'fr-FR',
		de: 'de-DE',
		pt: 'pt-BR',
		ru: 'ru-RU',
		ar: 'ar-SA',
		th: 'th-TH',
		vi: 'vi-VN',
		id: 'id-ID',
		it: 'it-IT',
		tr: 'tr-TR',
		pl: 'pl-PL',
		nl: 'nl-NL',
		hi: 'hi-IN',
		ms: 'ms-MY',
		fil: 'fil-PH',
		sv: 'sv-SE'
	}
	const utterance = new SpeechSynthesisUtterance(text)
	utterance.lang = voiceLang[code] || code || 'zh-CN'
	try {
		const voices = synth.getVoices ? synth.getVoices() : []
		const prefix = utterance.lang.slice(0, 2).toLowerCase()
		const match = (voices || []).find((item) => String(item.lang || '').toLowerCase().indexOf(prefix) === 0)
		if (match) {
			utterance.voice = match
		}
	} catch (err) {}
	utterance.onend = () => finishVoice(token)
	utterance.onerror = () => finishVoice(token)
	reading.value = true
	try {
		if (synth.paused && typeof synth.resume === 'function') {
			synth.resume()
		}
		synth.speak(utterance)
	} catch (err) {
		reading.value = false
	}
}

function stopSpeak() {
	const synth = typeof window !== 'undefined' ? window.speechSynthesis : null
	if (!synth) {
		return
	}
	try {
		synth.cancel()
	} catch (err) {}
}

let voiceToggleAt = 0

function replayVoice() {
	const now = Date.now()
	if (now - voiceToggleAt < 450) {
		return
	}
	voiceToggleAt = now
	if (reading.value) {
		stopVoice()
		return
	}
	voiceToken += 1
	reading.value = true
	const url = current.value && current.value.voice_url
	if (url) {
		playVoice(localOf(url))
		return
	}
	if (voice) {
		try {
			voice.stop()
			voice.destroy()
		} catch (err) {}
		voice = null
	}
	speakLine()
}

function killAudio(audio) {
	if (!audio) {
		return
	}
	try {
		audio.loop = false
	} catch (err) {}
	try {
		audio.muted = true
	} catch (err) {}
	try {
		audio.volume = 0
	} catch (err) {}
	try {
		if (typeof audio.pause === 'function') {
			audio.pause()
		}
	} catch (err) {}
	try {
		if (typeof audio.stop === 'function') {
			audio.stop()
		}
	} catch (err) {}
	try {
		audio.currentTime = 0
	} catch (err) {}
	try {
		audio.removeAttribute('src')
	} catch (err) {
		try {
			audio.src = ''
		} catch (e2) {}
	}
	try {
		if (typeof audio.load === 'function') {
			audio.load()
		}
	} catch (err) {}
	try {
		const raw = audio._audio
		if (raw) {
			raw.loop = false
			raw.muted = true
			raw.volume = 0
			raw.pause()
			raw.removeAttribute('src')
			raw.load()
		}
	} catch (err) {}
	try {
		if (typeof audio.destroy === 'function') {
			audio.destroy()
		}
	} catch (err) {}
}

function stopBgm() {
	const list = bgmList.splice(0, bgmList.length)
	if (bgm && list.indexOf(bgm) < 0) {
		list.push(bgm)
	}
	bgm = null
	bgmSrc = ''
	if (typeof window !== 'undefined' && window.__otomeAllAudio) {
		window.__otomeAllAudio.forEach((audio) => {
			if (audio && audio.loop && list.indexOf(audio) < 0) {
				list.push(audio)
			}
		})
	}
	list.forEach(killAudio)
}

function stopVoice() {
	voiceToken += 1
	reading.value = false
	stopSpeak()
	if (!voice) {
		return
	}
	try {
		voice.stop()
		voice.destroy()
	} catch (err) {
		return
	}
	voice = null
}

function destroyAudio() {
	stopBgm()
	stopVoice()
	stopEffect()
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
.fallback {
	background: #161226;
}
.top {
	position: absolute;
	left: 0;
	right: 0;
	top: 0;
	z-index: 3;
	display: flex;
	flex-direction: row;
	align-items: center;
	justify-content: space-between;
}
.chapter {
	display: flex;
	flex-direction: row;
	align-items: center;
	flex-shrink: 1;
	min-width: 0;
}
.chapter-back {
	flex-shrink: 0;
	display: block;
}
.chapter-title {
	color: #e8c99b;
	font-family: "PingFang SC", "Helvetica Neue", "Noto Sans SC", sans-serif;
	font-weight: 700;
	line-height: 1;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}
.hud-actions {
	display: flex;
	flex-direction: row;
	align-items: center;
	flex-shrink: 0;
	margin-left: 12px;
}
.hud-btn {
	flex-shrink: 0;
	position: relative;
}
.hud-btn-icon {
	width: 100%;
	height: 100%;
	display: block;
	pointer-events: none;
}
.cast {
	position: absolute;
	left: 0;
	right: 0;
	top: 10%;
	bottom: 50%;
	z-index: 1;
	display: grid;
	grid-template-columns: repeat(3, 1fr);
	grid-template-rows: repeat(3, 1fr);
	pointer-events: none;
}
.cast-figure {
	width: 86%;
	height: 92%;
	margin: auto;
	object-fit: contain;
	transform: scale(1.48);
	transform-origin: center center;
}
.is-landscape .cast {
	/* 人物在上半屏，不进内容控件区 */
	top: 4%;
	bottom: 50%;
}
.dock {
	position: absolute;
	left: 0;
	right: 0;
	z-index: 4;
	display: flex;
	flex-direction: column;
	align-items: center;
	box-sizing: border-box;
	overflow: visible;
}
.is-landscape .dock-land {
	right: auto;
}
.is-landscape .dock-choices {
	align-items: center;
}
.is-landscape .choice-list {
	display: flex;
	flex-direction: column;
	justify-content: center;
}
.panel {
	position: relative;
	box-sizing: border-box;
	display: flex;
	flex-direction: column;
	justify-content: flex-start;
	flex-shrink: 0;
	overflow: visible;
}
.panel-bg {
	position: absolute;
	left: 0;
	top: 0;
	width: 100%;
	height: 100%;
	z-index: 0;
	pointer-events: none;
}
.panel-bg :deep(div),
.panel-bg :deep(img) {
	width: 100% !important;
	height: 100% !important;
	object-fit: fill !important;
}
.panel-bg.flip {
	transform: scaleX(-1);
}
.panel-name {
	position: absolute;
	z-index: 1;
	color: #ffffff;
	font-family: "PingFang SC", "Helvetica Neue", "Noto Sans SC", sans-serif;
	font-weight: 700;
	letter-spacing: 0.12em;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}
.panel-line {
	position: relative;
	z-index: 1;
	color: #3a322c;
	font-family: "PingFang SC", "Helvetica Neue", "Noto Sans SC", sans-serif;
	font-weight: 500;
	line-height: 1.55;
	word-break: break-word;
}
.panel-prompt {
	position: absolute;
	left: 0;
	right: 0;
	bottom: 0;
	z-index: 2;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	pointer-events: none;
}
.prompt-line {
	width: 78%;
	height: 1px;
	margin-bottom: 6px;
	background: linear-gradient(90deg, rgba(232, 201, 155, 0), rgba(139, 123, 104, 0.95), rgba(232, 201, 155, 0));
}
.prompt-row {
	display: flex;
	flex-direction: row;
	align-items: center;
}
.prompt-arrow {
	margin-right: 6px;
	flex-shrink: 0;
}
.prompt-label {
	color: #b7a07a;
	font-family: "PingFang SC", "Helvetica Neue", "Noto Sans SC", sans-serif;
	font-weight: 600;
	line-height: 1.4;
	letter-spacing: 0.18em;
}
.voice-slot {
	position: absolute;
	z-index: 5;
	display: flex;
	align-items: center;
	justify-content: center;
	background: transparent;
}
.voice-icon {
	width: 100%;
	height: 100%;
	pointer-events: none;
}
.choice-list {
	position: relative;
	z-index: 1;
	flex-shrink: 0;
}
.choice {
	position: relative;
	display: flex;
	align-items: center;
	justify-content: center;
	flex-shrink: 0;
}
.choice-bg {
	position: absolute;
	left: 0;
	top: 0;
	width: 100%;
	height: 100%;
	pointer-events: none;
}
.choice-text {
	position: relative;
	z-index: 1;
	color: #3f362f;
	font-family: "PingFang SC", "Helvetica Neue", "Noto Sans SC", sans-serif;
	font-weight: 500;
	line-height: 1.3;
	text-align: center;
	padding: 0 18%;
}
.forward {
	position: absolute;
	z-index: 5;
}
.insert {
	position: absolute;
	left: 0;
	top: 0;
	width: 100%;
	height: 100%;
	z-index: 8;
	background: #07060c;
	display: flex;
	align-items: center;
	justify-content: center;
}
.insert-media {
	width: 100%;
	height: 100%;
}
.insert-hit {
	position: absolute;
	left: 0;
	top: 0;
	width: 100%;
	height: 100%;
	z-index: 9;
}
.insert-skip {
	position: absolute;
	right: 28rpx;
	bottom: 36rpx;
	z-index: 10;
	pointer-events: none;
	padding: 12rpx 22rpx;
	color: #f6efe4;
	font-size: 26rpx;
	background: rgba(12, 10, 18, 0.72);
	border: 1px solid rgba(231, 194, 122, 0.45);
}
.ending {
	position: absolute;
	left: 0;
	top: 0;
	right: 0;
	bottom: 0;
	z-index: 7;
	display: flex;
	align-items: center;
	justify-content: center;
	background: rgba(8, 6, 14, 0.72);
	box-sizing: border-box;
}
.ending-card {
	box-sizing: border-box;
	overflow-y: auto;
	background: rgba(12, 10, 18, 0.94);
	border: 1px solid rgba(231, 194, 122, 0.4);
}
.ending-title {
	display: block;
	color: #e7c27a;
}
.ending-text {
	display: block;
	color: #f6efe4;
	word-break: break-word;
}
.end-btn {
	background: #e7c27a;
	color: #2a2112;
	text-align: center;
	border-radius: 999rpx;
}
.end-btn:last-child {
	margin-bottom: 0 !important;
}
.ghost {
	background: transparent;
	color: #e7c27a;
	border: 1px solid rgba(231, 194, 122, 0.5);
}
.mask {
	position: absolute;
	left: 0;
	top: 0;
	right: 0;
	bottom: 0;
	z-index: 6;
	background: rgba(10, 8, 16, 0.86);
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	box-sizing: border-box;
}
.mask-title {
	display: block;
	color: #f6efe4;
	text-align: center;
	margin-bottom: 16rpx;
}
.mask-label {
	display: block;
	color: #b7adc4;
	text-align: center;
	margin-bottom: 18rpx;
}
.bar {
	height: 8rpx;
	background: rgba(255, 255, 255, 0.12);
	border-radius: 8rpx;
	overflow: hidden;
	margin-bottom: 24rpx;
}
.bar-in {
	height: 8rpx;
	background: #e7c27a;
}
</style>
