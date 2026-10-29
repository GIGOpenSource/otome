const KEY = 'otome_orient'

export function readOrient() {
	const saved = uni.getStorageSync(KEY)
	if (saved === 'landscape' || saved === 'portrait') {
		return saved
	}
	return 'portrait'
}

export function writeOrient(mode) {
	const next = mode === 'landscape' ? 'landscape' : 'portrait'
	uni.setStorageSync(KEY, next)
	lockDevice(next)
	return next
}

export function isAppRuntime() {
	return typeof plus !== 'undefined' && !!(plus.screen && plus.screen.lockOrientation)
}

function screenSize() {
	if (!isAppRuntime() && typeof window !== 'undefined' && window.innerWidth && window.innerHeight) {
		return { width: window.innerWidth, height: window.innerHeight }
	}
	const info = uni.getSystemInfoSync()
	return {
		width: info.windowWidth || info.screenWidth || 375,
		height: info.windowHeight || info.screenHeight || 667
	}
}

export function frameOf(mode) {
	const screen = screenSize()
	const screenW = screen.width
	const screenH = screen.height
	let width = screenW
	let height = screenH
	if (mode === 'landscape') {
		height = Math.min(screenH, screenW * 9 / 16)
		width = height * 16 / 9
		if (width > screenW) {
			width = screenW
			height = width * 9 / 16
		}
	} else {
		// 竖屏贴齐窗口上下沿。手机比 9:16 更高时不再上下留黑；窗口更宽时只在左右留边。
		height = screenH
		width = Math.min(screenW, screenH * 9 / 16)
	}
	width = Math.floor(width)
	height = Math.floor(height)
	return {
		width: width,
		height: height,
		left: Math.floor((screenW - width) / 2),
		top: Math.floor((screenH - height) / 2)
	}
}

// App 旋转真机后铺满窗口。H5 竖屏铺满高度；横屏仍用 16:9，避免竖屏窗口里被拉成长条。
export function stageFrame(mode) {
	if (isAppRuntime()) {
		const screen = screenSize()
		return {
			width: Math.floor(screen.width),
			height: Math.floor(screen.height),
			left: 0,
			top: 0
		}
	}
	return frameOf(mode)
}

function lockDevice(mode) {
	try {
		if (typeof plus === 'undefined' || !plus.screen || !plus.screen.lockOrientation) {
			return
		}
		plus.screen.lockOrientation(mode === 'landscape' ? 'landscape-primary' : 'portrait-primary')
	} catch (err) {
		return
	}
}
