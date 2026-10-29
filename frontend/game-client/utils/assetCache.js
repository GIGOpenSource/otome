import { activeGameId } from '@/config/game.js'
import { t } from '@/utils/i18n.js'

const memory = {}

function storageKey() {
	return 'otome_files_' + activeGameId()
}

function readStore() {
	const saved = uni.getStorageSync(storageKey())
	if (saved && typeof saved === 'object') {
		return saved
	}
	return {}
}

function writeStore(map) {
	uni.setStorageSync(storageKey(), map)
}

function trustWithoutCheck(path) {
	if (!path) {
		return false
	}
	return path.indexOf('blob:') === 0 || path.indexOf('http') === 0
}

function fileExists(path) {
	return new Promise((resolve) => {
		if (!path) {
			resolve(false)
			return
		}
		uni.getFileInfo({
			filePath: path,
			success: () => resolve(true),
			fail: () => resolve(false)
		})
	})
}

function persistFile(tempPath) {
	return new Promise((resolve) => {
		uni.saveFile({
			tempFilePath: tempPath,
			success: (res) => resolve(res.savedFilePath || tempPath),
			fail: () => resolve(tempPath)
		})
	})
}

function downloadOnce(url) {
	return new Promise((resolve, reject) => {
		uni.downloadFile({
			url,
			timeout: 40000,
			success: (res) => {
				if (res.statusCode === 200 && res.tempFilePath) {
					resolve(res.tempFilePath)
					return
				}
				reject(new Error(t('download_failed')))
			},
			fail: (err) => reject(err)
		})
	})
}

export function resolveLocal(url) {
	if (!url) {
		return ''
	}
	return memory[url] || ''
}

async function ensureOne(url) {
	if (memory[url]) {
		if (trustWithoutCheck(memory[url])) {
			return memory[url]
		}
		const alive = await fileExists(memory[url])
		if (alive) {
			return memory[url]
		}
		delete memory[url]
	}
	const store = readStore()
	if (store[url]) {
		const alive = await fileExists(store[url])
		if (alive) {
			memory[url] = store[url]
			return store[url]
		}
	}
	let lastError = null
	for (let attempt = 0; attempt < 3; attempt += 1) {
		try {
			const tempPath = await downloadOnce(url)
			const saved = await persistFile(tempPath)
			memory[url] = saved
			if (saved.indexOf('blob:') !== 0) {
				const next = readStore()
				next[url] = saved
				writeStore(next)
			}
			return saved
		} catch (err) {
			lastError = err
		}
	}
	throw lastError || new Error(t('download_failed'))
}

export async function downloadAll(urls, onProgress) {
	const list = []
	const seen = {}
	;(urls || []).forEach((url) => {
		if (url && !seen[url]) {
			seen[url] = true
			list.push(url)
		}
	})
	const total = list.length
	let done = 0
	if (onProgress) {
		onProgress(done, total)
	}
	if (!total) {
		return 0
	}
	const queue = list.slice()
	async function worker() {
		while (queue.length) {
			const url = queue.shift()
			try {
				await ensureOne(url)
			} catch (err) {
				// 个别旧文件不在磁盘上时，不拦住整章。播放时仍用原来的地址。
			}
			done += 1
			if (onProgress) {
				onProgress(done, total)
			}
		}
	}
	const workers = []
	const count = Math.min(2, queue.length)
	for (let index = 0; index < count; index += 1) {
		workers.push(worker())
	}
	await Promise.all(workers)
	return total
}
