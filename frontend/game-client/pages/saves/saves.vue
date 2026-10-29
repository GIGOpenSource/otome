<template>
	<view class="page" :style="{ paddingTop: pad + 'px' }">
		<text class="back" @click="back">{{ t('back') }}</text>
		<text class="title">{{ t('saves') }}</text>
		<text class="hint">{{ t('save_hint') }}</text>
		<view v-if="errorText" class="hint">{{ errorText }}</view>
		<view v-for="item in saves" :key="item.id" class="card">
			<text class="badge">{{ item.is_auto ? t('auto_save') : t('manual_save') }}</text>
			<text class="name">{{ item.title || item.node_key || t('untitled') }}</text>
			<text class="excerpt">{{ item.excerpt }}</text>
			<view class="row">
				<text class="action" @click="loadSave(item)">{{ t('load') }}</text>
				<text class="action muted" @click="removeSave(item)">{{ t('delete') }}</text>
			</view>
		</view>
		<text v-if="!saves.length && !errorText" class="hint">{{ t('no_saves') }}</text>
	</view>
</template>

<script setup>
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { activeGameId } from '@/config/game.js'
import { deleteSave, fetchSaves } from '@/api/otome.js'
import { t } from '@/utils/i18n.js'

const pad = ref(20)
const saves = ref([])
const errorText = ref('')

onShow(() => {
	const info = uni.getSystemInfoSync()
	pad.value = info.statusBarHeight || 20
	load()
})

async function load() {
	errorText.value = ''
	try {
		const res = await fetchSaves()
		saves.value = (res.results && res.results.saves) || []
	} catch (err) {
		errorText.value = (err && err.message) || t('saves_failed')
	}
}

function loadSave(item) {
	if (!item.node_id) {
		uni.showToast({ title: t('save_missing'), icon: 'none' })
		return
	}
	uni.setStorageSync('otome_resume_' + activeGameId(), item.node_id)
	uni.reLaunch({ url: '/pages/loading/loading?resume=1' })
}

async function removeSave(item) {
	try {
		await deleteSave(item.id)
		saves.value = saves.value.filter((row) => row.id !== item.id)
	} catch (err) {
		uni.showToast({ title: t('delete_failed'), icon: 'none' })
	}
}

function back() {
	uni.navigateBack()
}
</script>

<style scoped>
.page {
	min-height: 100%;
	padding-left: 40rpx;
	padding-right: 40rpx;
	padding-bottom: 48rpx;
	background: #100c18;
	box-sizing: border-box;
}
.back, .hint {
	display: block;
	color: #b7adc4;
	font-size: 26rpx;
	line-height: 1.6;
}
.title {
	display: block;
	margin-top: 12rpx;
	color: #f6efe4;
	font-size: 48rpx;
}
.card {
	margin-top: 28rpx;
	padding: 28rpx;
	border: 1px solid rgba(231, 194, 122, 0.35);
	background: rgba(20, 16, 32, 0.9);
}
.badge {
	display: block;
	color: #e7c27a;
	font-size: 22rpx;
}
.name {
	display: block;
	margin-top: 8rpx;
	color: #f6efe4;
	font-size: 32rpx;
}
.excerpt {
	display: block;
	margin-top: 10rpx;
	color: #b7adc4;
	font-size: 26rpx;
	line-height: 1.6;
}
.row {
	display: flex;
	margin-top: 18rpx;
}
.action {
	margin-right: 28rpx;
	color: #e7c27a;
	font-size: 28rpx;
}
.muted {
	color: #b7adc4;
}
</style>
