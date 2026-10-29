<template>
	<view class="page" :style="{ paddingTop: pad + 'px' }">
		<text class="back" @click="back">{{ t('back') }}</text>
		<text class="title">{{ t('gallery') }}</text>
		<view class="tabs">
			<text class="tab" :class="tab === 'video' ? 'on' : ''" @click="tab = 'video'">{{ t('videos') }}</text>
			<text class="tab" :class="tab === 'portrait' ? 'on' : ''" @click="tab = 'portrait'">{{ t('portraits') }}</text>
		</view>
		<view class="grid">
			<view v-for="item in shown" :key="item.id" class="card" :class="item.kind" @click="openItem(item)">
				<view class="media-wrap">
					<image v-if="item.kind === 'portrait' && item.media_url" class="media" :class="item.unlocked ? '' : 'locked'" :src="item.media_url" mode="aspectFill"></image>
					<video v-else-if="item.kind === 'video' && item.media_url" class="media" :class="item.unlocked ? '' : 'locked'" :src="item.media_url" :controls="item.unlocked" :show-center-play-btn="item.unlocked" object-fit="cover"></video>
					<view v-else class="media empty" :class="item.unlocked ? '' : 'locked'"></view>
					<view v-if="!item.unlocked" class="glass">
						<text class="lock">{{ t('locked') }}</text>
					</view>
				</view>
				<text class="name">{{ item.title }}</text>
			</view>
		</view>
		<text v-if="!shown.length" class="hint">{{ t('empty_gallery') }}</text>
		<view v-if="preview" class="preview" @click="preview = null">
			<image v-if="preview.kind === 'portrait'" class="preview-media" :src="preview.media_url" mode="aspectFit"></image>
			<video v-else class="preview-media" :src="preview.media_url" controls autoplay object-fit="contain"></video>
		</view>
	</view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { fetchGallery } from '@/api/otome.js'
import { t } from '@/utils/i18n.js'

const pad = ref(20)
const tab = ref('video')
const items = ref([])
const preview = ref(null)

const shown = computed(() => items.value.filter((item) => item.kind === tab.value))

onShow(() => {
	const info = uni.getSystemInfoSync()
	pad.value = info.statusBarHeight || 20
	load()
})

async function load() {
	try {
		const res = await fetchGallery()
		items.value = (res.results && res.results.items) || []
	} catch (err) {
		uni.showToast({ title: (err && err.message) || t('gallery_failed'), icon: 'none' })
	}
}

function openItem(item) {
	if (!item.unlocked) {
		uni.showToast({ title: t('not_unlocked'), icon: 'none' })
		return
	}
	if (!item.media_url) {
		return
	}
	if (item.kind === 'video') {
		return
	}
	preview.value = item
}

function back() {
	uni.navigateBack()
}
</script>

<style scoped>
.page {
	min-height: 100%;
	padding-left: 32rpx;
	padding-right: 32rpx;
	padding-bottom: 48rpx;
	background: #100c18;
	box-sizing: border-box;
}
.back, .hint {
	display: block;
	color: #b7adc4;
	font-size: 26rpx;
}
.title {
	display: block;
	margin-top: 12rpx;
	color: #f6efe4;
	font-size: 48rpx;
}
.tabs {
	display: flex;
	margin-top: 28rpx;
}
.tab {
	margin-right: 28rpx;
	color: #b7adc4;
	font-size: 30rpx;
	padding-bottom: 8rpx;
}
.on {
	color: #e7c27a;
	border-bottom: 2px solid #e7c27a;
}
.grid {
	display: flex;
	flex-wrap: wrap;
	justify-content: space-between;
}
.card {
	position: relative;
	width: 48%;
	margin-top: 24rpx;
	overflow: hidden;
	border-radius: 18rpx;
	background: #1a1524;
}
.media-wrap {
	position: relative;
	width: 100%;
	overflow: hidden;
}
.card.video .media-wrap {
	height: 420rpx;
}
.card.portrait .media-wrap {
	aspect-ratio: 3 / 4;
}
.media {
	width: 100%;
	height: 100%;
	display: block;
}
.empty {
	background: #241c30;
}
.locked {
	filter: blur(16px);
	transform: scale(1.12);
}
.glass {
	position: absolute;
	left: 0;
	right: 0;
	top: 0;
	bottom: 0;
	display: flex;
	align-items: center;
	justify-content: center;
	background: rgba(255, 255, 255, 0.08);
	backdrop-filter: blur(8px);
}
.lock {
	color: #f6efe4;
	font-size: 28rpx;
	letter-spacing: 4rpx;
}
.name {
	display: block;
	padding: 16rpx 12rpx 18rpx;
	color: #f6efe4;
	font-size: 26rpx;
}
.preview {
	position: fixed;
	left: 0;
	top: 0;
	right: 0;
	bottom: 0;
	z-index: 9;
	background: rgba(8, 6, 12, 0.92);
	display: flex;
	align-items: center;
	justify-content: center;
}
.preview-media {
	width: 100%;
	height: 80%;
}
</style>
