import App from './App'
import { createSSRApp } from 'vue'
import uviewPlus from 'uview-plus'

if (typeof window !== 'undefined' && !window.__otomeAudioHook) {
	window.__otomeAudioHook = true
	window.__otomeAllAudio = []
	const NativeAudio = window.Audio
	window.Audio = function OtomeAudio(...args) {
		const audio = new NativeAudio(...args)
		window.__otomeAllAudio.push(audio)
		return audio
	}
	window.Audio.prototype = NativeAudio.prototype
}

// Chrome/WebView 默认把部分 touch 监听标成 passive；uni 等库仍会 preventDefault，控制台会刷屏。
// 事件不可取消时跳过，避免警告，不影响可取消事件的正常拦截。
if (typeof window !== 'undefined' && !window.__otomePassiveTouchFix && window.Event) {
	window.__otomePassiveTouchFix = true
	const nativePrevent = Event.prototype.preventDefault
	Event.prototype.preventDefault = function otomePreventDefault() {
		if (!this.cancelable) {
			return
		}
		return nativePrevent.call(this)
	}
}

export function createApp() {
	const app = createSSRApp(App)
	app.use(uviewPlus)
	return {
		app
	}
}
