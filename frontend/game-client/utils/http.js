import { API_HOST } from '@/config/game.js'
import { currentLang, t } from '@/utils/i18n.js'

const MEDIA_ORIGIN = /^https?:\/\/(?:www\.)?example\.com(?=\/media\/)/

function localizeMedia(value) {
	// 仅 H5 开发代理需要把媒体改成本地相对路径；App 真机没有代理，改了会加载失败。
	if (!import.meta.env.DEV || process.env.UNI_PLATFORM !== 'h5') {
		return value
	}
	if (typeof value === 'string') {
		return value.replace(MEDIA_ORIGIN, '')
	}
	if (Array.isArray(value)) {
		return value.map(localizeMedia)
	}
	if (value && typeof value === 'object') {
		const next = {}
		Object.keys(value).forEach((key) => {
			next[key] = localizeMedia(value[key])
		})
		return next
	}
	return value
}

function request(url, params, other = {}) {
	const header = Object.assign({
		'Content-Type': 'application/json',
		'Accept-Language': currentLang(),
		'X-Otome-Lang': currentLang()
	}, other.header || {})
	const token = uni.getStorageSync('token') || ''
	if (token) {
		header.token = token
	}
	return new Promise((resolve, reject) => {
		uni.request({
			url: API_HOST + url,
			data: params,
			method: other.method || 'GET',
			header,
			timeout: other.timeout || 20000,
			success: (res) => {
				const body = localizeMedia(res.data || {})
				if (res.statusCode === 200 || res.statusCode === 201) {
					if (body.code === 200 || body.code === 201) {
						resolve(body)
						return
					}
					if (other.errorOutput !== false) {
						uni.showToast({
							title: body.message || t('request_failed'),
							icon: 'none'
						})
					}
					reject(body)
					return
				}
				if (other.errorOutput !== false) {
					uni.showToast({
						title: t('request_failed'),
						icon: 'none'
					})
				}
				reject(res)
			},
			fail: (err) => {
				if (other.errorOutput !== false) {
					uni.showToast({
						title: t('network_error'),
						icon: 'none'
					})
				}
				reject(err)
			}
		})
	})
}

function getRequest(url, params = {}, other = {}) {
	return request(url, params, Object.assign({}, other, { method: 'GET' }))
}

function postRequest(url, params = {}, other = {}) {
	return request(url, params, Object.assign({}, other, { method: 'POST' }))
}

function putRequest(url, params = {}, other = {}) {
	return request(url, params, Object.assign({}, other, { method: 'PUT' }))
}

function deleteRequest(url, params = {}, other = {}) {
	return request(url, params, Object.assign({}, other, { method: 'DELETE' }))
}

function getImg(url) {
	return `/static/${url}.png`
}

export {
	request,
	getRequest,
	postRequest,
	putRequest,
	deleteRequest,
	getImg
}
