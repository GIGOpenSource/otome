<template>
  <ElAlert v-if="error" class="admin-card" :title="error" type="error" show-icon closable @close="error = ''" />

  <ElDialog v-model="uploadOpen" :title="t('上传文件')" width="520px" :close-on-click-modal="!uploading">
    <ElForm label-position="top" @submit.prevent="upload">
      <LangSelect v-model="uploadLang" />
      <ContentLang v-model="uploadCopy" :primary="uploadLang" />
      <ElFormItem :label="t('名称')">
        <ElInput
          :model-value="textValue(uploadForm.name, uploadForm.texts, uploadCopy, 'name', uploadLang)"
          :placeholder="emptyHint(uploadForm.name, uploadCopy, uploadLang, t('不填则使用文件名'))"
          @update:model-value="writeText(uploadForm, uploadCopy, 'name', $event, uploadLang)"
        />
      </ElFormItem>
      <ElFormItem :label="t('类型')">
        <ElSelect v-model="uploadType" style="width: 100%">
          <ElOption v-for="item in typeOptions" :key="item.value" :label="item.text" :value="item.value" />
        </ElSelect>
      </ElFormItem>
      <ElFormItem :label="t('文件')">
        <div ref="uploadBlock" class="asset-upload-block">
          <ElUpload
            :key="uploadKey"
            class="asset-upload"
            drag
            :auto-upload="false"
            :show-file-list="false"
            :limit="1"
            accept=".jpg,.jpeg,.png,.webp,.gif,.svg,.mp3,.wav,.m4a,.aac,.ogg"
            :on-change="onUploadChange"
            :on-exceed="onUploadExceed"
          >
            <img v-if="previewUrl" :src="previewUrl" alt="" class="upload-preview" />
          </ElUpload>
          <button type="button" class="upload-tip" :disabled="uploading" @click="openFilePicker">
            {{ t('把文件拖到这里，或点击选择') }}
          </button>
          <div v-if="uploadFile" class="upload-meta">
            <span>{{ uploadFile.name }}</span>
            <ElButton link type="danger" :disabled="uploading" @click="clearUploadFile">{{ t('删除') }}</ElButton>
          </div>
        </div>
      </ElFormItem>
    </ElForm>
    <template #footer>
      <ElButton native-type="button" :disabled="uploading" @click="uploadOpen = false">{{ t('取消') }}</ElButton>
      <ElButton native-type="button" type="primary" :loading="uploading" :disabled="uploading" @click="upload">{{ t('上传') }}</ElButton>
    </template>
  </ElDialog>

  <ElDialog v-model="linkOpen" :title="t('外链')" width="520px" :close-on-click-modal="!savingLink">
    <ElForm label-position="top" @submit.prevent="saveLink">
      <LangSelect v-model="link.lang" />
      <ContentLang v-model="linkCopy" :primary="link.lang" />
      <ElFormItem :label="t('名称')">
        <ElInput
          :model-value="textValue(link.name, link.texts, linkCopy, 'name', link.lang)"
          :placeholder="emptyHint(link.name, linkCopy, link.lang)"
          @update:model-value="writeText(link, linkCopy, 'name', $event, link.lang)"
        />
      </ElFormItem>
      <ElFormItem :label="t('类型')">
        <ElSelect v-model="link.asset_type" style="width: 100%">
          <ElOption v-for="item in typeOptions" :key="item.value" :label="item.text" :value="item.value" />
        </ElSelect>
      </ElFormItem>
      <ElFormItem :label="t('地址')"><ElInput v-model="link.url" placeholder="https://" /></ElFormItem>
      <ElFormItem :label="t('备注')">
        <ElInput
          :model-value="textValue(link.remark, link.texts, linkCopy, 'remark', link.lang)"
          :placeholder="emptyHint(link.remark, linkCopy, link.lang)"
          @update:model-value="writeText(link, linkCopy, 'remark', $event, link.lang)"
        />
      </ElFormItem>
    </ElForm>
    <template #footer>
      <ElButton :disabled="savingLink" @click="linkOpen = false">{{ t('取消') }}</ElButton>
      <ElButton type="primary" :loading="savingLink" @click="saveLink">{{ t('保存') }}</ElButton>
    </template>
  </ElDialog>

  <ElDialog
    v-model="viewerOpen"
    :title="viewer?.name || t('预览')"
    width="720px"
    align-center
    append-to-body
    destroy-on-close
    @close="pauseViewer"
    @closed="closeViewer"
  >
    <div v-if="viewer" ref="viewerBody" class="viewer-body">
      <img
        v-if="viewer.asset_type === 'image' && !brokenImages.has(viewer.id)"
        :src="viewer.file_url"
        alt=""
        class="viewer-image"
        @error="markImageBroken(viewer.id)"
      />
      <div v-else-if="viewer.asset_type === 'image'" class="viewer-empty" />
      <audio v-else-if="viewer.asset_type === 'audio'" :src="viewer.file_url" controls autoplay class="viewer-audio" />
      <video v-else :src="viewer.file_url" controls autoplay playsinline class="viewer-video" />
    </div>
  </ElDialog>

  <ElCard class="admin-card" shadow="never">
    <ElForm :inline="true" @submit.prevent="reload">
      <ElFormItem :label="t('名称')">
        <ElInput v-model="keyword" :placeholder="t('搜索名称')" clearable style="width: 220px" />
      </ElFormItem>
      <LangSelect v-model="lang" filter />
      <ElFormItem :label="t('类型')">
        <ElSelect v-model="assetType" style="width: 140px">
          <ElOption v-for="item in filterOptions" :key="item.value" :label="item.text" :value="item.value" />
        </ElSelect>
      </ElFormItem>
      <ElFormItem>
        <ElButton type="primary" native-type="submit">{{ t('查询') }}</ElButton>
        <ElButton @click="openUpload">{{ t('上传文件') }}</ElButton>
        <ElButton @click="openLink">{{ t('外链') }}</ElButton>
      </ElFormItem>
    </ElForm>
    <ElTable v-loading="loading" :data="assets" row-key="id" border stripe>
      <ElTableColumn :label="t('语言')" width="120">
        <template #default="{ row }">
          <ElTag size="small">{{ langName(row.lang) }}</ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn prop="name" :label="t('名称')" min-width="140" />
      <ElTableColumn :label="t('类型')" width="90">
        <template #default="{ row }">{{ assetTypeText(row.asset_type) }}</template>
      </ElTableColumn>
      <ElTableColumn :label="t('地址')" min-width="220">
        <template #default="{ row }">
          <a v-if="addresses[row.id]" class="admin-link admin-ellipsis" :href="addresses[row.id]" target="_blank">{{ addresses[row.id] }}</a>
          <ElButton v-else link type="primary" :loading="addressingId === row.id" @click="showAddress(row)">{{ t('查看地址') }}</ElButton>
        </template>
      </ElTableColumn>
      <ElTableColumn :label="t('操作')" width="140" align="right">
        <template #default="{ row }">
          <ElButton link type="primary" :loading="previewingId === row.id" @click="openViewer(row)">{{ t('预览') }}</ElButton>
          <ElButton link type="danger" @click="removeAsset(row)">{{ t('删除') }}</ElButton>
        </template>
      </ElTableColumn>
    </ElTable>
    <div class="admin-pager">
      <ElPagination
        v-model:current-page="page"
        background
        layout="total, prev, pager, next"
        :page-size="pageSize"
        :total="total"
      />
    </div>
  </ElCard>
</template>

<script lang="ts" setup>
import { t } from '../../i18n'
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import type { UploadFile, UploadFiles } from 'element-plus'
import LangSelect from '../../components/LangSelect.vue'
import { Asset, isAuthError, list, request } from '../../services/otome/api'
import { confirmDelete, notify } from '../../utils/feedback'
import ContentLang from '../../components/ContentLang.vue'
import { emptyHint, textValue, writeText, type Texts } from '../../utils/contentLang'
import { langName } from '../../utils/langs'

const typeOptions = computed(() => [
  { text: t('图片'), value: 'image' },
  { text: t('音频'), value: 'audio' },
  { text: t('视频'), value: 'video' },
])
const filterOptions = computed(() => [{ text: t('全部'), value: '' }, ...typeOptions.value])
const assets = ref<Asset[]>([])
const loading = ref(false)
const uploading = ref(false)
const savingLink = ref(false)
const error = ref('')
const page = ref(1)
const pageSize = 20
const total = ref(0)
const keyword = ref('')
const lang = ref('')
const assetType = ref('')
const uploadOpen = ref(false)
const linkOpen = ref(false)
const uploadForm = reactive({ name: '', texts: {} as Texts })
const uploadLang = ref('zh-Hans')
const uploadCopy = ref('zh-Hans')
const linkCopy = ref('zh-Hans')
const uploadType = ref<'image' | 'audio' | 'video'>('image')
const uploadFile = ref<File | null>(null)
const uploadKey = ref(0)
const previewUrl = ref('')
const uploadBlock = ref<HTMLElement | null>(null)
const viewerOpen = ref(false)
const viewer = ref<Asset | null>(null)
const viewerBody = ref<HTMLElement | null>(null)
const brokenImages = ref(new Set<number>())
const addresses = ref<Record<number, string>>({})
const previewingId = ref(0)
const addressingId = ref(0)
const detailCache = new Map<number, Asset>()
const link = reactive({ name: '', lang: 'zh-Hans', texts: {} as Texts, asset_type: 'image' as 'image' | 'audio' | 'video', url: '', remark: '' })

function revokePreview() {
  if (!previewUrl.value) return
  URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = ''
}

function isImageFile(file: File) {
  return file.type.startsWith('image/') || /\.(jpe?g|png|gif|webp|svg)$/i.test(file.name)
}

function fileLabel(name: string) {
  return name.replace(/\.[^.]+$/, '') || name
}

function applyUploadFile(file: File | null) {
  uploadFile.value = file
  revokePreview()
  if (file && isImageFile(file)) previewUrl.value = URL.createObjectURL(file)
  writeText(uploadForm, uploadCopy.value, 'name', file ? fileLabel(file.name) : '', uploadLang.value)
}

function onUploadChange(_file: UploadFile, files: UploadFiles) {
  applyUploadFile(files.at(-1)?.raw ?? null)
}

function onUploadExceed(files: File[]) {
  const file = files[0]
  if (!file) return
  uploadKey.value += 1
  applyUploadFile(file)
}

function clearUploadFile() {
  uploadFile.value = null
  revokePreview()
  uploadKey.value += 1
  writeText(uploadForm, uploadCopy.value, 'name', '', uploadLang.value)
}

function openFilePicker() {
  if (uploading.value) return
  uploadBlock.value?.querySelector<HTMLInputElement>('input[type=file]')?.click()
}

function assetTypeText(type: Asset['asset_type']) {
  if (type === 'audio') return t('音频')
  if (type === 'video') return t('视频')
  return t('图片')
}

function markImageBroken(id: number) {
  if (brokenImages.value.has(id)) return
  const next = new Set(brokenImages.value)
  next.add(id)
  brokenImages.value = next
}

async function assetDetail(asset: Asset) {
  const cached = detailCache.get(asset.id)
  if (cached) return cached
  const data = await request(`/assets/${asset.id}/`)
  const detail = data.results as Asset
  detailCache.set(asset.id, detail)
  if (detail.file_url) addresses.value = { ...addresses.value, [asset.id]: detail.file_url }
  return detail
}

async function openViewer(asset: Asset) {
  if (previewingId.value) return
  previewingId.value = asset.id
  try {
    const detail = await assetDetail(asset)
    if (!detail.file_url) {
      notify(t('没有可预览的地址'), 'warning')
      return
    }
    viewer.value = detail
    viewerOpen.value = true
  } catch (err) {
    error.value = err instanceof Error ? err.message : t('加载失败')
  } finally {
    previewingId.value = 0
  }
}

async function showAddress(asset: Asset) {
  if (addressingId.value) return
  addressingId.value = asset.id
  try {
    const detail = await assetDetail(asset)
    if (!detail.file_url) notify(t('没有可预览的地址'), 'warning')
  } catch (err) {
    error.value = err instanceof Error ? err.message : t('加载失败')
  } finally {
    addressingId.value = 0
  }
}

function pauseViewer() {
  viewerBody.value?.querySelectorAll('audio, video').forEach((node) => {
    if (node instanceof HTMLMediaElement) node.pause()
  })
}

function closeViewer() {
  viewer.value = null
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await list<Asset>('/assets/', {
      currentPage: page.value,
      pageSize,
      name: keyword.value.trim(),
      lang: lang.value || undefined,
      asset_type: assetType.value,
    })
    assets.value = data.items
    total.value = data.total
    brokenImages.value = new Set()
    addresses.value = {}
    detailCache.clear()
  } catch (err) {
    if (!isAuthError(err)) {
      error.value = err instanceof Error ? err.message : t('加载失败')
    }
  } finally {
    loading.value = false
  }
}

function reload() {
  if (page.value !== 1) page.value = 1
  else load()
}

function openUpload() {
  uploadForm.name = ''
  uploadForm.texts = {}
  uploadLang.value = 'zh-Hans'
  uploadCopy.value = uploadLang.value
  uploadType.value = 'image'
  clearUploadFile()
  uploadOpen.value = true
}

async function upload() {
  if (uploading.value) return
  const file = uploadFile.value
  if (!file) {
    notify(t('请选择文件'), 'warning')
    return
  }
  if (file.size > 20 * 1024 * 1024) {
    notify(t('文件不能超过 20MB'), 'warning')
    return
  }
  uploading.value = true
  try {
    const form = new FormData()
    form.append('file', file)
    form.append('asset_type', uploadType.value)
    form.append('lang', uploadLang.value || 'zh-Hans')
    form.append('texts', JSON.stringify(uploadForm.texts))
    if (uploadForm.name.trim()) form.append('name', uploadForm.name.trim())
    await request('/assets/upload/', { method: 'POST', body: form })
    notify(t('上传成功'))
    uploadOpen.value = false
    clearUploadFile()
    uploadForm.name = ''
    uploadForm.texts = {}
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : t('上传失败')
  } finally {
    uploading.value = false
  }
}

function openLink() {
  link.name = ''
  link.lang = 'zh-Hans'
  link.texts = {}
  linkCopy.value = link.lang
  link.asset_type = 'image'
  link.url = ''
  link.remark = ''
  linkOpen.value = true
}

async function saveLink() {
  if (!link.name.trim() || !link.url.trim()) {
    notify(t('名称和地址必填'), 'warning')
    return
  }
  savingLink.value = true
  try {
    await request('/assets/', {
      method: 'POST',
      body: JSON.stringify({
        name: link.name.trim(),
        lang: link.lang || 'zh-Hans',
        texts: link.texts,
        asset_type: link.asset_type,
        url: link.url.trim(),
        remark: link.remark.trim(),
      }),
    })
    notify(t('外链已保存'))
    linkOpen.value = false
    link.name = ''
    link.lang = 'zh-Hans'
    link.texts = {}
    link.url = ''
    link.remark = ''
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : t('保存失败')
  } finally {
    savingLink.value = false
  }
}

async function removeAsset(asset: Asset) {
  const agreed = await confirmDelete(t('确定删除「{name}」？引用它的画面会失去这张图或这段声音。', { name: asset.name }), t('删除素材'))
  if (!agreed) return
  await request(`/assets/${asset.id}/`, { method: 'DELETE' })
  notify(t('已删除'))
  await load()
}

watch(page, load)
watch(uploadOpen, (open) => {
  if (!open) clearUploadFile()
})
onMounted(load)
onBeforeUnmount(revokePreview)
</script>

<style lang="scss" scoped>
.asset-upload-block {
  flex: 1 0 100%;
  width: 100%;
  min-width: 0;
}

.asset-upload {
  display: block;
  width: 100%;

  :deep(.el-upload-dragger) {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    min-height: 180px;
    padding: 12px;
    box-sizing: border-box;
  }
}

.upload-tip {
  display: block;
  width: 100%;
  margin: 8px 0 0;
  padding: 0;
  border: 0;
  background: transparent;
  color: #909399;
  font: inherit;
  font-size: 13px;
  line-height: 1.4;
  text-align: left;
  cursor: pointer;

  &:disabled {
    cursor: not-allowed;
  }
}

.upload-preview {
  display: block;
  max-width: 100%;
  max-height: 220px;
  object-fit: contain;
}

.upload-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
  margin-top: 4px;
  color: #606266;
  font-size: 13px;
  line-height: 1.4;

  span {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.viewer-empty {
  display: block;
  width: min(100%, 360px);
  height: 220px;
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
}

.viewer-body {
  display: flex;
  justify-content: center;
}

.viewer-image,
.viewer-video {
  display: block;
  max-width: 100%;
  max-height: 70vh;
  object-fit: contain;
}

.viewer-audio {
  width: 100%;
}

</style>
