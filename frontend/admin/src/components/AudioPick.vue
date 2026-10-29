<template>
  <div class="audio-pick">
    <div class="audio-pick__row">
      <ElSelect
        v-model="selected"
        clearable
        filterable
        remote
        reserve-keyword
        :remote-method="onSearch"
        :loading="loading"
        :placeholder="t('选择音频')"
        :value-on-clear="null"
        @visible-change="onVisible"
        @end-reached="onEndReached"
      >
        <ElOption v-for="item in assets" :key="item.id" :label="item.name" :value="item.id" />
        <template v-if="hasMore || loadingMore" #footer>
          <button type="button" class="audio-pick__more" :disabled="loadingMore" @click="emit('load-more')">
            {{ loadingMore ? t('加载中…') : t('加载更多') }}
          </button>
        </template>
      </ElSelect>
      <ElButton @click="openListen">{{ t('试听') }}</ElButton>
    </div>
    <p v-if="current" class="admin-muted audio-pick__meta">
      {{ current.name }} · {{ durationText }} · {{ sizeText }}
    </p>

    <ElDialog
      v-model="listenOpen"
      :title="t('试听')"
      width="520px"
      append-to-body
      :close-on-click-modal="!uploading"
      @closed="pausePlayer"
    >
      <div v-if="previewSrc" class="audio-pick__now">
        <p class="audio-pick__name">{{ previewName }}</p>
        <p class="admin-muted">{{ previewDuration }} · {{ previewSize }}</p>
        <audio ref="player" :key="previewSrc" :src="previewSrc" controls autoplay class="audio-pick__player" />
      </div>
      <p v-else class="admin-muted">{{ t('还没有选择音频。选好文件后可以先试听，上传后会直接选中。') }}</p>

      <ElForm class="audio-pick__upload" label-position="top" @submit.prevent="uploadAudio">
        <ElFormItem :label="t('上传新音频')">
          <ElInput v-model="uploadName" :placeholder="t('不填则使用文件名')" />
        </ElFormItem>
        <ElFormItem :label="t('文件')">
          <div class="audio-pick__field">
            <ElUpload
              :key="uploadKey"
              drag
              :auto-upload="false"
              :show-file-list="false"
              :limit="1"
              accept=".mp3,.wav,.m4a,.aac,.ogg,audio/*"
              :on-change="onFile"
              :on-exceed="onExceed"
            >
              <span class="audio-pick__drop">{{ t('把音频拖到这里，或点击选择') }}</span>
            </ElUpload>
            <div v-if="uploadFile" class="audio-pick__file">
              <span>{{ uploadFile.name }} · {{ formatSize(uploadFile.size) }}</span>
              <ElButton link type="danger" :disabled="uploading" @click="clearFile">{{ t('删除') }}</ElButton>
            </div>
          </div>
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton :disabled="uploading" @click="listenOpen = false">{{ t('取消') }}</ElButton>
        <ElButton v-if="uploadFile" type="primary" :loading="uploading" @click="uploadAudio">{{ t('上传并使用') }}</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<script lang="ts" setup>
import { t } from '../i18n'
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import type { UploadFile } from 'element-plus'
import { Asset, AssetInfo, request } from '../services/otome/api'
import { notify } from '../utils/feedback'

const props = withDefaults(
  defineProps<{
    modelValue: number | null
    assets: Asset[]
    gameId: string
    lang: string
    loading?: boolean
    loadingMore?: boolean
    hasMore?: boolean
    /** From node detail bgm_info / voice_info / interact_info for 试听 before list loads. */
    preview?: AssetInfo | null
  }>(),
  { loading: false, loadingMore: false, hasMore: false, preview: null },
)

const emit = defineEmits<{
  'update:modelValue': [value: number | null]
  uploaded: [asset: Asset]
  'visible-change': [open: boolean]
  'load-more': []
  search: [query: string]
}>()

function onVisible(open: boolean) {
  emit('visible-change', open)
}

function onSearch(query: string) {
  emit('search', query)
}

function onEndReached(direction: string) {
  if (direction === 'bottom' && props.hasMore && !props.loadingMore) emit('load-more')
}

const selected = computed({
  get: () => props.modelValue,
  set: (value: number | null) => emit('update:modelValue', value),
})

const listenOpen = ref(false)
const uploading = ref(false)
const uploadName = ref('')
const uploadFile = ref<File | null>(null)
const uploadKey = ref(0)
const localUrl = ref('')
const localDuration = ref<number | null>(null)
const player = ref<HTMLAudioElement | null>(null)
const duration = ref<number | null>(null)
const size = ref<number | null>(null)
const knownSize = new Map<number, number>()
const knownDuration = new Map<number, number>()

const current = computed(() => {
  const fromList = props.assets.find((item) => item.id === props.modelValue)
  if (fromList) return fromList
  if (props.preview && props.preview.id === props.modelValue) {
    return {
      id: props.preview.id,
      name: props.preview.name,
      asset_type: 'audio' as const,
      url: '',
      file_url: props.preview.file_url || '',
      duration: props.preview.duration ?? null,
      file_size: props.preview.file_size ?? null,
      remark: '',
      lang: '',
    }
  }
  return null
})
const durationText = computed(() => formatDuration(duration.value))
const sizeText = computed(() => formatSize(size.value))
const previewSrc = computed(() => localUrl.value || current.value?.file_url || '')
const previewName = computed(() => {
  if (localUrl.value) return uploadName.value.trim() || uploadFile.value?.name || t('新音频')
  return current.value?.name || ''
})
const previewDuration = computed(() => (localUrl.value ? formatDuration(localDuration.value) : durationText.value))
const previewSize = computed(() => (localUrl.value ? formatSize(uploadFile.value?.size ?? null) : sizeText.value))

function formatDuration(seconds: number | null) {
  if (seconds == null || !Number.isFinite(seconds)) return t('时长未知')
  const total = Math.max(0, Math.round(seconds))
  const minutes = Math.floor(total / 60)
  const remain = total % 60
  return `${minutes}:${String(remain).padStart(2, '0')}`
}

function formatSize(bytes: number | null) {
  if (bytes == null || !Number.isFinite(bytes) || bytes < 0) return t('大小未知')
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function readDuration(url: string) {
  return new Promise<number | null>((resolve) => {
    const audio = document.createElement('audio')
    audio.preload = 'metadata'
    const finish = (value: number | null) => {
      audio.onloadedmetadata = null
      audio.onerror = null
      audio.src = ''
      resolve(value)
    }
    audio.onloadedmetadata = () => finish(Number.isFinite(audio.duration) ? audio.duration : null)
    audio.onerror = () => finish(null)
    audio.src = url
  })
}

async function readSize(url: string) {
  try {
    const head = await fetch(url, { method: 'HEAD' })
    const length = Number(head.headers.get('content-length'))
    if (Number.isFinite(length) && length > 0) return length
    const range = head.headers.get('content-range') || ''
    const total = Number(range.split('/')[1])
    if (Number.isFinite(total) && total > 0) return total
  } catch {
    return null
  }
  return null
}

async function loadMeta(asset: Asset) {
  const cachedDuration = asset.duration ?? knownDuration.get(asset.id)
  const cachedSize = asset.file_size ?? knownSize.get(asset.id)
  duration.value = cachedDuration ?? null
  size.value = cachedSize ?? null
  if (!asset.file_url || (cachedDuration != null && cachedSize != null)) return
  const [nextDuration, nextSize] = await Promise.all([
    cachedDuration == null ? readDuration(asset.file_url) : Promise.resolve(cachedDuration),
    cachedSize == null ? readSize(asset.file_url) : Promise.resolve(cachedSize),
  ])
  if (current.value?.id !== asset.id) return
  duration.value = nextDuration
  size.value = nextSize
  if (nextDuration != null) knownDuration.set(asset.id, nextDuration)
  if (nextSize != null) knownSize.set(asset.id, nextSize)
}

function fileLabel(name: string) {
  return name.replace(/\.[^.]+$/, '') || name
}

function openListen() {
  if (!uploadFile.value) uploadName.value = current.value?.name || ''
  listenOpen.value = true
}

function pausePlayer() {
  player.value?.pause()
  uploadName.value = ''
  if (uploadFile.value) clearFile()
}

function revokeLocal() {
  if (!localUrl.value) return
  URL.revokeObjectURL(localUrl.value)
  localUrl.value = ''
  localDuration.value = null
}

async function stageFile(file: File | null) {
  revokeLocal()
  uploadFile.value = file
  if (!file) {
    uploadName.value = current.value?.name || ''
    return
  }
  uploadName.value = fileLabel(file.name)
  const url = URL.createObjectURL(file)
  localUrl.value = url
  localDuration.value = await readDuration(url)
}

function onFile(file: UploadFile) {
  stageFile(file.raw || null)
}

function onExceed(files: File[]) {
  const file = files[0]
  if (!file) return
  uploadKey.value += 1
  stageFile(file)
}

function clearFile() {
  revokeLocal()
  uploadFile.value = null
  uploadKey.value += 1
  uploadName.value = current.value?.name || ''
}

function isAudioFile(file: File) {
  return file.type.startsWith('audio/') || /\.(mp3|wav|m4a|aac|ogg)$/i.test(file.name)
}

async function uploadAudio() {
  const file = uploadFile.value
  if (!file) {
    notify(t('请选择文件'), 'warning')
    return
  }
  if (!isAudioFile(file)) {
    notify(t('音频只支持 mp3、wav、m4a、aac、ogg'), 'warning')
    return
  }
  if (file.size > 20 * 1024 * 1024) {
    notify(t('文件不能超过 20MB'), 'warning')
    return
  }
  uploading.value = true
  try {
    const body = new FormData()
    body.set('file', file)
    body.set('asset_type', 'audio')
    body.set('lang', props.lang || 'zh-Hans')
    body.set('game', props.gameId)
    const name = uploadName.value.trim() || fileLabel(file.name)
    body.set('name', name)
    const data = await request('/assets/upload/', { method: 'POST', body })
    const asset = data.results as Asset
    if (!asset?.id) throw new Error(t('上传失败'))
    knownSize.set(asset.id, file.size)
    if (localDuration.value != null) knownDuration.set(asset.id, localDuration.value)
    emit('uploaded', asset)
    emit('update:modelValue', asset.id)
    clearFile()
    listenOpen.value = false
    notify(t('音频已上传并选中'))
  } catch (err) {
    notify(err instanceof Error ? err.message : t('上传失败'), 'error')
  } finally {
    uploading.value = false
  }
}

onBeforeUnmount(revokeLocal)

watch(current, (asset) => {
  if (!asset) {
    duration.value = null
    size.value = null
    return
  }
  loadMeta(asset)
}, { immediate: true })
</script>

<style lang="scss" scoped>
.audio-pick {
  width: 100%;
}

.audio-pick__row {
  display: flex;
  gap: 8px;
  align-items: center;
  width: 100%;
}

.audio-pick__row :deep(.el-select) {
  flex: 1;
  min-width: 0;
}

.audio-pick__meta {
  margin: 4px 0 0;
  line-height: 1.4;
}

.audio-pick__more {
  display: block;
  width: 100%;
  padding: 8px 12px;
  border: 0;
  background: transparent;
  color: #409eff;
  cursor: pointer;
  text-align: center;
}

.audio-pick__more:disabled {
  color: #a8abb2;
  cursor: default;
}

.audio-pick__name {
  margin: 0 0 4px;
  font-weight: 600;
}

.audio-pick__player {
  width: 100%;
  margin-top: 12px;
}

.audio-pick__upload {
  margin-top: 16px;
}

.audio-pick__field {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  width: 100%;
}

.audio-pick__drop {
  color: #606266;
  font-size: 13px;
  line-height: 1.5;
}

.audio-pick__file {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  margin-top: 8px;
}

.audio-pick__file span {
  min-width: 0;
  word-break: break-all;
}

.audio-pick__upload :deep(.el-form-item__content) {
  display: flex;
  flex-direction: column;
  align-items: stretch;
}

.audio-pick__upload :deep(.el-upload) {
  display: block;
  width: 100%;
}

.audio-pick__upload :deep(.el-upload-dragger) {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: auto;
  min-height: 96px;
  padding: 16px;
  box-sizing: border-box;
}
</style>
