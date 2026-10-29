import { GAME_ID, GOOGLE_CLIENT_ID, activeGameId, setActiveGameId, storySlug } from '@/config/game.js'
import { deleteRequest, getRequest, postRequest } from '@/utils/http.js'

export function ensureGame() {
	const slug = storySlug()
	if (!slug) {
		setActiveGameId(GAME_ID)
		return Promise.resolve(activeGameId())
	}
	return getRequest('/otome/play/games/resolve/', { slug }, {
		showLoading: false,
		errorOutput: false,
		timeout: 60000
	}).then((body) => {
		const id = body && body.results ? body.results.id : 0
		setActiveGameId(id)
		if (!activeGameId()) {
			return Promise.reject(body || { message: '' })
		}
		return activeGameId()
	})
}

export function fetchScript() {
	return getRequest('/otome/play/games/' + activeGameId() + '/script/', {}, {
		showLoading: false,
		errorOutput: false,
		timeout: 60000
	})
}

export function fetchPlayConfig() {
	return getRequest('/otome/play/config/', {}, {
		showLoading: false,
		errorOutput: false
	})
}

export function deviceId() {
	let id = uni.getStorageSync('otome_device_id')
	if (id) {
		return id
	}
	try {
		const info = uni.getSystemInfoSync()
		id = info.deviceId || ''
	} catch (err) {
		id = ''
	}
	if (!id || id === 'unknown') {
		id = 'web-' + Date.now().toString(36) + Math.random().toString(36).slice(2, 10)
	}
	uni.setStorageSync('otome_device_id', id)
	return id
}

export function saveSession(data) {
	const player = data || {}
	uni.setStorageSync('token', player.token || '')
	uni.setStorageSync('otome_uid', player.uid || '')
	uni.setStorageSync('otome_player', player)
	return player
}

export function currentPlayer() {
	return uni.getStorageSync('otome_player') || {}
}

export function fetchMe() {
	return getRequest('/otome/play/me/', {}, {
		showLoading: false,
		errorOutput: false
	})
}

export function channelCode() {
	return uni.getStorageSync('otome_channel_' + activeGameId()) || ''
}

export function rememberChannel(code) {
	const text = String(code || '').trim()
	if (!text) {
		return
	}
	uni.setStorageSync('otome_channel_' + activeGameId(), text.slice(0, 16))
}

export function clickToken() {
	return uni.getStorageSync('otome_click_id') || ''
}

export function rememberClick(id) {
	const text = String(id || '').trim()
	if (!text) {
		return
	}
	uni.setStorageSync('otome_click_id', text.slice(0, 32))
}

export function fetchAds() {
	const channel = channelCode()
	const query = channel ? ('?channel=' + encodeURIComponent(channel)) : ''
	return getRequest('/otome/play/games/' + activeGameId() + '/ads/' + query, {}, {
		showLoading: false,
		errorOutput: false
	})
}

export function trackAd(adId, action) {
	const id = Number(adId)
	if (!id) {
		return Promise.resolve()
	}
	return postRequest('/otome/play/games/' + activeGameId() + '/ads/' + id + '/track/', {
		action,
		device_id: deviceId()
	}, {
		showLoading: false,
		errorOutput: false
	}).catch(() => {})
}

export function deviceLogin() {
	return postRequest('/otome/play/auth/device/', {
		device_id: deviceId(),
		game_id: activeGameId(),
		channel_id: channelCode(),
		click_id: clickToken()
	}, {
		showLoading: false,
		errorOutput: false,
		timeout: 60000
	})
}

export function googleLogin(credential) {
	return postRequest('/otome/play/auth/google/', {
		credential,
		device_id: deviceId(),
		game_id: activeGameId(),
		channel_id: channelCode(),
		click_id: clickToken()
	}, {
		showLoading: false,
		errorOutput: false
	})
}

export function fetchSaves() {
	return getRequest('/otome/play/games/' + activeGameId() + '/saves/', {}, {
		showLoading: false,
		errorOutput: false
	})
}

export function createSave(nodeId) {
	return postRequest('/otome/play/games/' + activeGameId() + '/saves/', {
		node_id: nodeId
	}, {
		showLoading: false,
		errorOutput: false
	})
}

export function deleteSave(saveId) {
	return deleteRequest('/otome/play/games/' + activeGameId() + '/saves/' + saveId + '/', {}, {
		showLoading: false,
		errorOutput: false
	})
}

export function fetchGallery() {
	return getRequest('/otome/play/games/' + activeGameId() + '/gallery/', {}, {
		showLoading: false,
		errorOutput: false
	})
}

export function reportProgress(nodeId, insertSeen) {
	return postRequest('/otome/play/games/' + activeGameId() + '/progress/', {
		node_id: nodeId,
		insert_seen: !!insertSeen
	}, {
		showLoading: false,
		errorOutput: false
	})
}

export async function googleClientId() {
	if (GOOGLE_CLIENT_ID) {
		return GOOGLE_CLIENT_ID
	}
	try {
		const res = await fetchPlayConfig()
		return (res.results && res.results.google_client_id) || ''
	} catch (err) {
		return ''
	}
}
