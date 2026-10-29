<template>
  <div v-loading="loading" class="admin-editor">
    <div class="admin-toolbar">
      <div>
        <h1 class="admin-toolbar__title">{{ game?.title || t('编辑故事') }}</h1>
        <div v-if="game" class="admin-toolbar__meta">
          {{ t('游戏 ID') }} <b>{{ game.id }}</b>
          <ElButton link type="primary" @click="copyId">{{ t('复制') }}</ElButton>
        </div>
        <div v-if="game?.play_url" class="admin-toolbar__meta">
          {{ t('进入游戏') }}
          <a class="admin-link" :href="game.play_url" target="_blank" rel="noopener noreferrer">{{ game.play_url }}</a>
          <ElButton link type="primary" @click="copyLink(game.play_url)">{{ t('复制') }}</ElButton>
        </div>
        <div v-if="game?.landing_page_url" class="admin-toolbar__meta">
          {{ t('落地页') }}
          <a class="admin-link" :href="game.landing_page_url" target="_blank" rel="noopener noreferrer">{{
            game.landing_page_url
          }}</a>
          <ElButton link type="primary" @click="copyLink(game.landing_page_url)">{{ t('复制') }}</ElButton>
        </div>
      </div>
      <ElButton @click="router.push({ name: 'games' })">{{ t('返回列表') }}</ElButton>
    </div>

    <ElDialog v-model="mediaPreviewOpen" :title="mediaPreviewTitle" width="480px" append-to-body align-center @closed="closeMediaPreview">
      <video v-if="isVideoUrl(mediaPreviewUrl)" :src="mediaPreviewUrl" class="media-preview-video" controls autoplay playsinline />
      <img v-else-if="mediaPreviewUrl" :src="mediaPreviewUrl" alt="" class="media-preview-image" />
    </ElDialog>

    <ElAlert v-if="error" class="admin-card" :title="error" type="error" show-icon closable @close="error = ''" />

    <ElCard class="admin-card" shadow="never">
      <ElTabs v-model="section" class="story-tabs">
        <ElTabPane :label="t('故事信息')" name="info">
      <ElForm label-position="top" @submit.prevent>
        <div class="admin-form-grid">
          <LangSelect v-model="form.lang" />
          <ElFormItem class="is-full"><ContentLang v-model="storyCopy" :primary="form.lang" /></ElFormItem>
          <ElFormItem :label="t('标题')">
            <ElInput
              :model-value="textValue(form.title, form.texts, storyCopy, 'title', form.lang)"
              :placeholder="emptyHint(form.title, storyCopy, form.lang)"
              @update:model-value="writeText(form, storyCopy, 'title', $event, form.lang)"
            />
          </ElFormItem>
          <ElFormItem :label="t('副标题')">
            <ElInput
              :model-value="textValue(form.subtitle, form.texts, storyCopy, 'subtitle', form.lang)"
              :placeholder="emptyHint(form.subtitle, storyCopy, form.lang)"
              @update:model-value="writeText(form, storyCopy, 'subtitle', $event, form.lang)"
            />
          </ElFormItem>
          <ElFormItem :label="t('编码')"><ElInput v-model="form.code" :placeholder="t('可留空')" /></ElFormItem>
          <ElFormItem :label="t('排序')"><ElInputNumber v-model="form.sort_order" :min="0" controls-position="right" /></ElFormItem>
          <ElFormItem class="is-full" :label="t('封面（图片或视频）')">
            <div class="media-pick">
              <ElSelect v-model="form.cover" clearable filterable :placeholder="t('选择素材')" :value-on-clear="null" @visible-change="onCoverOpen">
                <ElOption v-for="item in imageOptions" :key="item.id" :label="item.label" :value="item.id" />
              </ElSelect>
              <ElButton :disabled="!form.cover" @click="previewCover">{{ t('预览') }}</ElButton>
            </div>
          </ElFormItem>
          <ElFormItem :label="t('Google 包名')"><ElInput v-model="form.play_package" placeholder="com.example.game" /></ElFormItem>
          <ElFormItem label="App Store ID"><ElInput v-model="form.ios_app_id" :placeholder="t('数字 ID')" /></ElFormItem>
          <ElFormItem class="is-full" :label="t('进入游戏')">
            <ElInput v-model="form.frontend_url" :placeholder="t('玩家打开游戏的地址，留空则用本地客户端')" />
          </ElFormItem>
          <ElFormItem class="is-full" :label="t('落地页')">
            <ElInput v-model="form.landing_url" :placeholder="t('下载落地页地址，留空则用 /land/游戏ID/')" />
          </ElFormItem>
          <ElFormItem class="is-full" :label="t('简介')">
            <ElInput
              :model-value="textValue(form.summary, form.texts, storyCopy, 'summary', form.lang)"
              :placeholder="emptyHint(form.summary, storyCopy, form.lang)"
              type="textarea"
              :rows="3"
              @update:model-value="writeText(form, storyCopy, 'summary', $event, form.lang)"
            />
          </ElFormItem>
        </div>
        <div class="admin-actions">
          <ElCheckbox v-model="published">{{ t('发布。玩家客户端只能打开已发布的故事') }}</ElCheckbox>
          <ElButton type="primary" :loading="saving" @click="saveGame">{{ t('保存') }}</ElButton>
          <ElButton type="danger" plain @click="removeGame">{{ t('删除故事') }}</ElButton>
        </div>
      </ElForm>
        </ElTabPane>

        <ElTabPane :label="t('角色')" name="characters">
      <div class="admin-pane-tools">
        <ElForm :inline="true" @submit.prevent>
          <LangSelect v-model="characterLang" filter />
        </ElForm>
        <span class="admin-muted">{{ t('点编辑打开角色详情。') }}</span>
        <ElButton type="primary" size="small" @click="openCharacter()">{{ t('添加角色') }}</ElButton>
      </div>
      <ElTable :data="characters" row-key="id" border stripe>
        <ElTableColumn :label="t('语言')" width="120">
          <template #default="{ row }">
            <ElTag size="small">{{ langName(row.lang) }}</ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn :label="t('角色')" min-width="160">
          <template #default="{ row }">
            <span :style="{ color: row.name_color || '#e7c27a' }">{{ row.name }}</span>
            <div class="admin-sub">{{ row.title }}</div>
          </template>
        </ElTableColumn>
        <ElTableColumn :label="t('立绘')" width="90">
          <template #default="{ row }">
            <video v-if="isVideoUrl(row.portrait_url)" :src="row.portrait_url" class="admin-thumb" muted />
            <img v-else-if="row.portrait_url" :src="row.portrait_url" alt="" class="admin-thumb" />
          </template>
        </ElTableColumn>
        <ElTableColumn prop="sort_order" :label="t('排序')" width="90" />
        <ElTableColumn :label="t('操作')" width="140" align="right">
          <template #default="{ row }">
            <ElButton link type="primary" @click="editCharacter(row)">{{ t('编辑') }}</ElButton>
            <ElButton link type="danger" @click="removeCharacter(row)">{{ t('删除') }}</ElButton>
          </template>
        </ElTableColumn>
      </ElTable>
      <div class="admin-pager">
        <ElPagination v-model:current-page="characterPage" background layout="total, prev, pager, next" :page-size="pageSize" :total="characterTotal" />
      </div>
        </ElTabPane>

        <ElTabPane :label="t('素材')" name="assets">
      <p class="admin-muted">{{ t('角色和素材都在这部游戏里改。视频会进故事解锁。') }}</p>
      <ElForm :inline="true" @submit.prevent>
        <LangSelect v-model="assetLang" filter />
      </ElForm>
      <ElForm :inline="true" @submit.prevent="uploadAssetFile">
        <LangSelect v-model="assetDraft.lang" width="180px" />
        <ElFormItem :label="t('名称')">
          <ElInput
            :model-value="textValue(assetDraft.name, assetDraft.texts, assetCopy, 'name', assetDraft.lang)"
            :placeholder="emptyHint(assetDraft.name, assetCopy, assetDraft.lang)"
            style="width: 180px"
            @update:model-value="writeText(assetDraft, assetCopy, 'name', $event, assetDraft.lang)"
          />
        </ElFormItem>
        <ContentLang v-model="assetCopy" :primary="assetDraft.lang" />
        <ElFormItem :label="t('类型')">
          <ElSelect v-model="assetDraft.asset_type" style="width: 120px">
            <ElOption v-for="item in assetTypes" :key="item.value" :label="item.label" :value="item.value" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem>
          <ElUpload :key="uploadKey" :auto-upload="false" :limit="1" :on-change="onAssetFile" :on-remove="clearAssetFile">
            <ElButton>{{ t('选择文件') }}</ElButton>
          </ElUpload>
        </ElFormItem>
        <ElFormItem>
          <ElButton type="primary" native-type="submit" :loading="uploading">{{ t('上传到这部游戏') }}</ElButton>
        </ElFormItem>
      </ElForm>
      <ElTable :data="assets" row-key="id" border stripe>
        <ElTableColumn :label="t('语言')" width="120">
          <template #default="{ row }">
            <ElTag size="small">{{ langName(row.lang) }}</ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="name" :label="t('名称')" min-width="160" />
        <ElTableColumn :label="t('类型')" width="90">
          <template #default="{ row }">{{ typeLabel(row.asset_type) }}</template>
        </ElTableColumn>
        <ElTableColumn :label="t('操作')" width="90" align="right">
          <template #default="{ row }">
            <ElButton link type="danger" @click="removeAsset(row)">{{ t('删除') }}</ElButton>
          </template>
        </ElTableColumn>
      </ElTable>
      <div class="admin-pager">
        <ElPagination v-model:current-page="assetPage" background layout="total, prev, pager, next" :page-size="pageSize" :total="assetTotal" />
      </div>
        </ElTabPane>

        <ElTabPane :label="t('故事解锁')" name="gallery">
      <p class="admin-muted">{{ t('玩家在菜单里按视频和立绘切换。没解锁的会盖一层毛玻璃。') }}</p>
      <ElForm label-position="top" @submit.prevent>
        <ElForm :inline="true" @submit.prevent>
          <LangSelect v-model="galleryLang" filter />
        </ElForm>
        <div class="admin-form-grid">
          <LangSelect v-model="galleryDraft.lang" />
          <ElFormItem class="is-full"><ContentLang v-model="galleryCopy" :primary="galleryDraft.lang" /></ElFormItem>
          <ElFormItem :label="t('标题')">
            <ElInput
              :model-value="textValue(galleryDraft.title, galleryDraft.texts, galleryCopy, 'title', galleryDraft.lang)"
              :placeholder="emptyHint(galleryDraft.title, galleryCopy, galleryDraft.lang)"
              @update:model-value="writeText(galleryDraft, galleryCopy, 'title', $event, galleryDraft.lang)"
            />
          </ElFormItem>
          <ElFormItem :label="t('类型')">
            <ElSelect v-model="galleryDraft.kind">
              <ElOption v-for="item in galleryKinds" :key="item.value" :label="item.label" :value="item.value" />
            </ElSelect>
          </ElFormItem>
          <ElFormItem :label="t('素材')">
            <ElSelect v-model="galleryDraft.asset" filterable :placeholder="t('选择素材')">
              <ElOption v-for="item in galleryAssetOptions" :key="item.id" :label="item.label" :value="item.id" />
            </ElSelect>
          </ElFormItem>
          <ElFormItem :label="t('走到这句后解锁')">
            <ElSelect v-model="galleryDraft.unlock_node" clearable filterable :placeholder="t('可选')" :value-on-clear="null">
              <ElOption v-for="item in nodeOptions" :key="item.id" :label="item.label" :value="item.id" />
            </ElSelect>
          </ElFormItem>
          <ElFormItem class="is-full">
            <ElCheckbox v-model="galleryDraft.unlocked_by_default">{{ t('默认解锁') }}</ElCheckbox>
          </ElFormItem>
        </div>
        <ElButton type="primary" :loading="savingGallery" @click="saveGallery">
          {{ galleryDraft.id ? t('保存解锁') : t('添加解锁') }}
        </ElButton>
      </ElForm>
      <ElTable :data="gallery" row-key="id" border stripe style="margin-top: 16px">
        <ElTableColumn :label="t('语言')" width="120">
          <template #default="{ row }">
            <ElTag size="small">{{ langName(row.lang) }}</ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="title" :label="t('标题')" min-width="160" />
        <ElTableColumn :label="t('类型')" width="100">
          <template #default="{ row }">{{ row.kind === 'video' ? t('视频') : t('立绘') }}</template>
        </ElTableColumn>
        <ElTableColumn :label="t('操作')" width="140" align="right">
          <template #default="{ row }">
            <ElButton link type="primary" @click="editGallery(row)">{{ t('编辑') }}</ElButton>
            <ElButton link type="danger" @click="removeGallery(row)">{{ t('删除') }}</ElButton>
          </template>
        </ElTableColumn>
      </ElTable>
      <div class="admin-pager">
        <ElPagination v-model:current-page="galleryPage" background layout="total, prev, pager, next" :page-size="pageSize" :total="galleryTotal" />
      </div>
        </ElTabPane>

        <ElTabPane :label="t('剧情')" name="plot">
      <div class="admin-pane-tools">
        <ElForm :inline="true" @submit.prevent>
          <LangSelect v-model="plotLang" filter />
        </ElForm>
        <ElRadioGroup v-model="plotMode" size="small">
          <ElRadioButton value="list">{{ t('列表') }}</ElRadioButton>
          <ElRadioButton value="flow">{{ t('流程图') }}</ElRadioButton>
        </ElRadioGroup>
        <ElButton type="primary" size="small" @click="router.push({ name: 'node', params: { gameId, nodeId: 'new' } })">
          {{ t('新剧情') }}
        </ElButton>
      </div>
      <PlotFlow v-if="plotMode === 'flow'" :game-id="gameId" :nodes="flowNodes" :loading="flowLoading" :speaker-of="speakerOf" @changed="load" />
      <template v-else>
      <ElTable :data="nodes" row-key="id" border stripe>
        <ElTableColumn :label="t('语言')" width="120">
          <template #default="{ row }">
            <ElTag size="small">{{ langName(row.lang) }}</ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="node_key" :label="t('编号')" width="140" />
        <ElTableColumn :label="t('对白')" min-width="240">
          <template #default="{ row }">
            <div class="admin-speaker">{{ speakerOf(row) }}</div>
            <div class="admin-ellipsis">{{ row.content }}</div>
          </template>
        </ElTableColumn>
        <ElTableColumn :label="t('标记')" width="180">
          <template #default="{ row }">
            <div class="admin-flags">
              <ElTag v-if="row.is_start" size="small">{{ t('开场') }}</ElTag>
              <ElTag v-if="row.is_key" size="small" type="warning">{{ t('关键') }}</ElTag>
              <ElTag v-if="row.is_ending" size="small" type="success">{{ t('结局') }}</ElTag>
            </div>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="sort_order" :label="t('排序')" width="90" />
        <ElTableColumn :label="t('操作')" width="180" align="right">
          <template #default="{ row }">
            <ElButton link type="primary" @click="router.push({ name: 'node', params: { gameId, nodeId: row.id } })">
              {{ t('编辑') }}
            </ElButton>
            <ElButton link type="primary" @click="copyNode(row.id)">{{ t('基于此新建') }}</ElButton>
          </template>
        </ElTableColumn>
      </ElTable>
      <div class="admin-pager">
        <ElPagination v-model:current-page="nodePage" background layout="total, prev, pager, next" :page-size="pageSize" :total="nodeTotal" />
      </div>
      </template>
        </ElTabPane>
      </ElTabs>
    </ElCard>

    <ElDialog v-model="characterOpen" :title="character.id ? t('编辑角色') : t('添加角色')" width="760px">
      <ElForm label-position="top" @submit.prevent>
        <div class="admin-form-grid">
          <LangSelect v-model="character.lang" />
          <ElFormItem class="is-full"><ContentLang v-model="characterCopy" :primary="character.lang" /></ElFormItem>
          <ElFormItem :label="t('姓名')">
            <ElInput
              :model-value="textValue(character.name, character.texts, characterCopy, 'name', character.lang)"
              :placeholder="emptyHint(character.name, characterCopy, character.lang)"
              @update:model-value="writeText(character, characterCopy, 'name', $event, character.lang)"
            />
          </ElFormItem>
          <ElFormItem :label="t('身份')">
            <ElInput
              :model-value="textValue(character.title, character.texts, characterCopy, 'title', character.lang)"
              :placeholder="emptyHint(character.title, characterCopy, character.lang)"
              @update:model-value="writeText(character, characterCopy, 'title', $event, character.lang)"
            />
          </ElFormItem>
          <ElFormItem :label="t('名字颜色')">
            <div class="admin-color">
              <ElColorPicker :model-value="character.name_color" @update:model-value="setColor" />
              <ElInput v-model="character.name_color" />
            </div>
          </ElFormItem>
          <ElFormItem :label="t('排序')">
            <ElInputNumber v-model="character.sort_order" :min="0" controls-position="right" />
          </ElFormItem>
          <ElFormItem class="is-full" :label="t('立绘组')">
            <p class="admin-muted">{{ t('同一角色可以有多套立绘。竖屏、横屏各选一张，剧情里按套选用。') }}</p>
            <div v-for="(row, index) in character.images" :key="index" class="image-row">
              <ElInput
                :model-value="textValue(row.label, row.texts, characterCopy, 'label', character.lang)"
                :placeholder="emptyHint(row.label, characterCopy, character.lang, t('名称，如默认、生气'))"
                @update:model-value="writeText(row, characterCopy, 'label', $event, character.lang)"
              />
              <ElSelect v-model="row.image" clearable filterable :placeholder="t('竖屏')" :value-on-clear="null">
                <ElOption v-for="item in imageOptions" :key="item.id" :label="item.label" :value="item.id" />
              </ElSelect>
              <ElSelect v-model="row.image_land" clearable filterable :placeholder="t('横屏')" :value-on-clear="null">
                <ElOption v-for="item in imageOptions" :key="item.id" :label="item.label" :value="item.id" />
              </ElSelect>
              <ElButton type="danger" plain @click="character.images.splice(index, 1)">{{ t('移除') }}</ElButton>
            </div>
            <div class="image-actions">
              <ElButton @click="character.images.push({ label: '', texts: {}, image: null, image_land: null })">{{ t('添加一套') }}</ElButton>
              <ElUpload
                :key="portraitUploadKey"
                multiple
                :auto-upload="false"
                :show-file-list="false"
                accept=".jpg,.jpeg,.png,.webp,.gif,.svg,image/*"
                :on-change="queuePortraitFiles"
              >
                <ElButton native-type="button" :loading="uploadingPortraits">{{ t('批量上传并添加立绘') }}</ElButton>
              </ElUpload>
            </div>
            <p class="admin-muted">{{ t('一次选择多张图片。每张生成一套立绘，名称默认用文件名，竖屏和横屏先用同一张，可再改。点保存后写入这个角色。') }}</p>
          </ElFormItem>
          <ElFormItem class="is-full" :label="t('介绍')">
            <ElInput
              :model-value="textValue(character.intro, character.texts, characterCopy, 'intro', character.lang)"
              :placeholder="emptyHint(character.intro, characterCopy, character.lang)"
              type="textarea"
              :rows="3"
              @update:model-value="writeText(character, characterCopy, 'intro', $event, character.lang)"
            />
          </ElFormItem>
        </div>
      </ElForm>
      <template #footer>
        <ElButton @click="characterOpen = false">{{ t('取消') }}</ElButton>
        <ElButton type="primary" :loading="savingCharacter" @click="saveCharacter">{{ t('保存') }}</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<script lang="ts" setup>
import { t } from '../../i18n'
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { UploadFile, UploadFiles } from 'element-plus'
import ContentLang from '../../components/ContentLang.vue'
import LangSelect from '../../components/LangSelect.vue'
import { Asset, Character, Game, StoryNode, asId, isAuthError, list, listAll, request } from '../../services/otome/api'
import { confirmDelete, notify } from '../../utils/feedback'
import { cloneTexts, emptyHint, textValue, writeText, type Texts } from '../../utils/contentLang'
import { langName } from '../../utils/langs'
import PlotFlow from './PlotFlow.vue'

const route = useRoute()
const router = useRouter()
const gameId = computed(() => String(route.params.gameId))
const sections = ['info', 'characters', 'assets', 'gallery', 'plot'] as const
type Section = (typeof sections)[number]

function readSection(value: unknown): Section {
  const raw = Array.isArray(value) ? value[0] : value
  return sections.includes(raw as Section) ? (raw as Section) : 'info'
}

const section = ref<Section>(readSection(route.query.tab))
const plotMode = ref(sessionStorage.getItem('otome-plot-mode') === 'flow' ? 'flow' : 'list')
const game = ref<Game | null>(null)
const pageSize = 20
const characters = ref<Character[]>([])
const characterPage = ref(1)
const characterTotal = ref(0)
const nodes = ref<StoryNode[]>([])
const flowNodes = ref<StoryNode[]>([])
const flowLoading = ref(false)
const nodePage = ref(1)
const nodeTotal = ref(0)
const pickerAssets = ref<Asset[]>([])
const pickerNodes = ref<StoryNode[]>([])
const assetsLoaded = ref(false)
const nodesLoaded = ref(false)
const assets = ref<Asset[]>([])
const assetPage = ref(1)
const assetTotal = ref(0)
const gallery = ref<GalleryRow[]>([])
const galleryPage = ref(1)
const galleryTotal = ref(0)
const loading = ref(false)
const saving = ref(false)
const savingCharacter = ref(false)
const characterOpen = ref(false)
const uploading = ref(false)
const uploadingPortraits = ref(false)
const portraitUploadKey = ref(0)
const savingGallery = ref(false)
const uploadKey = ref(0)
const assetFile = ref<File | null>(null)
const error = ref('')
const published = ref(false)
const characterLang = ref('')
const assetLang = ref('')
const galleryLang = ref('')
const plotLang = ref('')
const storyCopy = ref('zh-Hans')
const characterCopy = ref('zh-Hans')
const galleryCopy = ref('zh-Hans')
const assetCopy = ref('zh-Hans')
const form = reactive({
  title: '',
  lang: 'zh-Hans',
  texts: {} as Texts,
  subtitle: '',
  summary: '',
  play_package: '',
  ios_app_id: '',
  frontend_url: '',
  landing_url: '',
  code: '',
  cover: null as number | null,
  sort_order: 0,
})
type ImageDraft = { id?: number; label: string; texts: Texts; image: number | null; image_land: number | null }
const character = reactive({
  id: 0,
  lang: 'zh-Hans',
  texts: {} as Texts,
  name: '',
  title: '',
  name_color: '#e7c27a',
  intro: '',
  portrait: null as number | null,
  sort_order: 0,
  images: [] as ImageDraft[],
})
const assetDraft = reactive({ name: '', lang: 'zh-Hans', texts: {} as Texts, asset_type: 'image' })
const galleryDraft = reactive({
  id: 0,
  lang: 'zh-Hans',
  texts: {} as Texts,
  title: '',
  kind: 'portrait',
  asset: null as number | null,
  unlock_node: null as number | null,
  unlocked_by_default: false,
})
type GalleryRow = {
  id: number
  kind: string
  lang: string
  title: string
  texts?: Texts
  asset: number | null
  unlock_node: number | null
  unlocked_by_default: boolean
}
const assetTypes = computed(() => [
  { value: 'image', label: t('图片') },
  { value: 'audio', label: t('音频') },
  { value: 'video', label: t('视频') },
])
const galleryKinds = computed(() => [
  { value: 'portrait', label: t('立绘') },
  { value: 'video', label: t('视频') },
])

const imageOptions = computed(() =>
  pickerAssets.value
    .filter((item) => item.asset_type === 'image' || item.asset_type === 'video')
    .map((item) => ({ id: item.id, label: `${typeLabel(item.asset_type)} · ${item.name}` })),
)
const galleryAssetOptions = computed(() =>
  pickerAssets.value.map((item) => ({ id: item.id, label: `${typeLabel(item.asset_type)} · ${item.name}` })),
)
const nodeOptions = computed(() =>
  pickerNodes.value.map((item) => {
    const line = (item.content || '').replace(/\s+/g, ' ').trim()
    const excerpt = line.length > 28 ? `${line.slice(0, 28)}…` : line
    const speaker = speakerOf(item)
    return { id: item.id, label: excerpt ? `${speaker}：${excerpt}` : speaker }
  }),
)

function isVideoUrl(url?: string) {
  return !!url && /\.(mp4|webm|mov)(\?|$)/i.test(url)
}

function typeLabel(value: string) {
  if (value === 'video') return t('视频')
  if (value === 'audio') return t('音频')
  return t('图片')
}

function setColor(value: string | null) {
  character.name_color = value || '#e7c27a'
}

function copyNode(id: number) {
  router.push({ name: 'node', params: { gameId: gameId.value, nodeId: 'new' }, query: { copy: String(id) } })
}

function speakerOf(node: StoryNode) {
  if (node.speaker_name) return node.speaker_name
  return characters.value.find((item) => item.id === node.character)?.name || t('旁白')
}

function resetCharacter() {
  character.id = 0
  character.lang = 'zh-Hans'
  character.texts = {}
  character.name = ''
  characterCopy.value = 'zh-Hans'
  character.title = ''
  character.name_color = '#e7c27a'
  character.intro = ''
  character.portrait = null
  character.sort_order = 0
  character.images = []
}

function openCharacter(item?: Character) {
  ensureAssets().catch(() => {})
  if (!item) {
    resetCharacter()
    characterOpen.value = true
    return
  }
  character.id = item.id
  character.lang = item.lang || 'zh-Hans'
  character.texts = cloneTexts(item.texts)
  characterCopy.value = character.lang
  character.name = item.name
  character.title = item.title
  character.name_color = item.name_color || '#e7c27a'
  character.intro = item.intro
  character.portrait = item.portrait
  character.sort_order = item.sort_order
  character.images = (item.images || []).map((image) => ({
    id: image.id,
    label: image.label,
    texts: cloneTexts(image.texts),
    image: image.image,
    image_land: image.image_land,
  }))
  if (!character.images.length && item.portrait) {
    character.images = [{ label: '', texts: {}, image: item.portrait, image_land: item.portrait_land }]
  }
  characterOpen.value = true
}

function editCharacter(item: Character) {
  openCharacter(item)
}

async function loadCharacters() {
  const page = await list<Character>('/characters/', {
    game: gameId.value,
    currentPage: characterPage.value,
    pageSize,
    lang: characterLang.value || undefined,
  })
  characters.value = page.items
  characterTotal.value = page.total
}

async function loadAssets() {
  const page = await list<Asset>('/assets/', {
    game: gameId.value,
    currentPage: assetPage.value,
    pageSize,
    lang: assetLang.value || undefined,
  })
  assets.value = page.items
  assetTotal.value = page.total
}

async function loadGallery() {
  const page = await list<GalleryRow>('/gallery/', {
    game: gameId.value,
    currentPage: galleryPage.value,
    pageSize,
    lang: galleryLang.value || undefined,
  })
  gallery.value = page.items
  galleryTotal.value = page.total
  await Promise.all([ensureAssets(), ensureNodes()])
}

async function loadPlot() {
  if (plotMode.value === 'flow') {
    flowLoading.value = true
    try {
      flowNodes.value = await listAll<StoryNode>('/nodes/', { game: gameId.value, graph: 1 })
      nodeTotal.value = flowNodes.value.length
    } finally {
      flowLoading.value = false
    }
    return
  }
  const page = await list<StoryNode>('/nodes/', {
    game: gameId.value,
    currentPage: nodePage.value,
    pageSize,
    lang: plotLang.value || undefined,
  })
  nodes.value = page.items
  nodeTotal.value = page.total
}

async function ensureAssets() {
  if (assetsLoaded.value) return
  pickerAssets.value = await listAll<Asset>('/assets/', { game: gameId.value, brief: 1 })
  assetsLoaded.value = true
}

async function ensureNodes() {
  if (nodesLoaded.value) return
  pickerNodes.value = await listAll<StoryNode>('/nodes/', { game: gameId.value })
  nodesLoaded.value = true
}

const mediaPreviewOpen = ref(false)
const mediaPreviewTitle = ref('')
const mediaPreviewUrl = ref('')

function openMediaPreview(title: string, url: string) {
  if (!url) return
  mediaPreviewTitle.value = title
  mediaPreviewUrl.value = url
  mediaPreviewOpen.value = true
}

function closeMediaPreview() {
  const video = document.querySelector<HTMLVideoElement>('.media-preview-video')
  video?.pause()
  mediaPreviewUrl.value = ''
}

async function previewCover() {
  if (!form.cover) return
  try {
    await ensureAssets()
  } catch (err) {
    error.value = err instanceof Error ? err.message : t('加载失败')
    return
  }
  const asset = pickerAssets.value.find((item) => item.id === form.cover)
  const url = asset?.file_url || (game.value?.cover === form.cover ? game.value.cover_url : '')
  if (!url) {
    notify(t('没有可预览的地址'), 'warning')
    return
  }
  openMediaPreview(t('封面（图片或视频）'), url)
}

function onCoverOpen(open: boolean) {
  if (!open) return
  ensureAssets().catch((err) => {
    error.value = err instanceof Error ? err.message : t('加载失败')
  })
}

async function loadSection() {
  if (section.value === 'characters') await loadCharacters()
  else if (section.value === 'assets') await loadAssets()
  else if (section.value === 'gallery') await loadGallery()
  else if (section.value === 'plot') await loadPlot()
}

async function load() {
  loading.value = true
  error.value = ''
  pickerAssets.value = []
  pickerNodes.value = []
  assetsLoaded.value = false
  nodesLoaded.value = false
  try {
    const gameRes = await request(`/games/${gameId.value}/`)
    const current = gameRes.results as Game
    game.value = current
    form.title = current.title
    form.lang = current.lang || 'zh-Hans'
    form.texts = cloneTexts(current.texts)
    storyCopy.value = form.lang
    form.subtitle = current.subtitle || ''
    form.summary = current.summary || ''
    form.play_package = current.play_package || ''
    form.ios_app_id = current.ios_app_id || ''
    form.frontend_url = current.frontend_url || ''
    form.landing_url = current.landing_url || ''
    form.code = current.code || ''
    form.cover = current.cover
    form.sort_order = current.sort_order || 0
    published.value = current.status === 1
    await loadSection()
  } catch (err) {
    if (!isAuthError(err)) {
      error.value = err instanceof Error ? err.message : t('加载失败')
    }
  } finally {
    loading.value = false
  }
}

async function saveGame() {
  if (!form.title.trim()) {
    notify(t('标题不能为空'), 'warning')
    return
  }
  const storyNodes = section.value === 'plot' ? nodeTotal.value : game.value?.node_count || 0
  if (published.value && storyNodes === 0) {
    notify(t('先写至少一段剧情，再发布'), 'warning')
    return
  }
  saving.value = true
  try {
    const data = await request(`/games/${gameId.value}/`, {
      method: 'PUT',
      body: JSON.stringify({
        title: form.title.trim(),
        lang: form.lang || 'zh-Hans',
        texts: form.texts,
        subtitle: form.subtitle.trim(),
        summary: form.summary.trim(),
        play_package: form.play_package.trim(),
        ios_app_id: form.ios_app_id.trim(),
        frontend_url: form.frontend_url.trim(),
        landing_url: form.landing_url.trim(),
        code: form.code.trim() || null,
        cover: asId(form.cover),
        sort_order: Number(form.sort_order) || 0,
        status: published.value ? 1 : 0,
      }),
    })
    game.value = data.results
    notify(t('故事已保存'))
  } catch (err) {
    error.value = err instanceof Error ? err.message : t('保存失败')
  } finally {
    saving.value = false
  }
}

async function removeGame() {
  const agreed = await confirmDelete(t('删除后，客户端将无法再读取这部故事。'), t('删除故事'))
  if (!agreed) return
  await request(`/games/${gameId.value}/`, { method: 'DELETE' })
  router.push({ name: 'games' })
}

async function saveCharacter() {
  if (!character.name.trim()) {
    notify(t('角色名不能为空'), 'warning')
    return
  }
  savingCharacter.value = true
  try {
    const body = {
      game: Number(gameId.value),
      lang: character.lang || 'zh-Hans',
      texts: character.texts,
      name: character.name.trim(),
      title: character.title.trim(),
      name_color: (character.name_color || '#e7c27a').trim() || '#e7c27a',
      intro: character.intro.trim(),
      portrait: asId(character.portrait),
      sort_order: Number(character.sort_order) || 0,
      images: character.images
        .filter((row) => row.image)
        .map((row) => ({
          id: row.id,
          label: row.label.trim(),
          texts: row.texts,
          image: row.image,
          image_land: row.image_land,
        })),
    }
    if (character.id) {
      await request(`/characters/${character.id}/`, { method: 'PUT', body: JSON.stringify(body) })
    } else {
      await request('/characters/', { method: 'POST', body: JSON.stringify(body) })
    }
    notify(t('角色已保存'))
    characterOpen.value = false
    resetCharacter()
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : t('保存角色失败')
  } finally {
    savingCharacter.value = false
  }
}

async function removeCharacter(item: Character) {
  const agreed = await confirmDelete(t('确定删除「{name}」？', { name: item.name }), t('删除角色'))
  if (!agreed) return
  await request(`/characters/${item.id}/`, { method: 'DELETE' })
  if (character.id === item.id) resetCharacter()
  await load()
}

function isPortraitFile(file: File) {
  return file.type.startsWith('image/') || /\.(jpe?g|png|gif|webp|svg)$/i.test(file.name)
}

let portraitTimer = 0
function queuePortraitFiles(_file: UploadFile, files: UploadFiles) {
  window.clearTimeout(portraitTimer)
  portraitTimer = window.setTimeout(() => {
    const batch: File[] = []
    files.forEach((item) => {
      if (item.raw) batch.push(item.raw)
    })
    portraitUploadKey.value += 1
    uploadPortraitBatch(batch)
  }, 30)
}

async function uploadPortraitBatch(files: File[]) {
  const imagesOnly = files.filter(isPortraitFile)
  if (!imagesOnly.length) {
    notify(t('请选择图片'), 'warning')
    return
  }
  uploadingPortraits.value = true
  let added = 0
  const failed: string[] = []
  try {
    for (const file of imagesOnly) {
      const label = file.name.replace(/\.[^.]+$/, '') || file.name
      try {
        const body = new FormData()
        body.set('file', file)
        body.set('asset_type', 'image')
        body.set('lang', character.lang || 'zh-Hans')
        body.set('game', gameId.value)
        body.set('name', label)
        const data = await request('/assets/upload/', { method: 'POST', body })
        const asset = data.results as Asset
        if (!asset?.id) throw new Error(t('上传失败'))
        images.value = [...images.value, asset]
        assets.value = [...assets.value, asset]
        character.images.push({ label, texts: {}, image: asset.id, image_land: asset.id })
        added += 1
      } catch {
        failed.push(file.name)
      }
    }
  } finally {
    uploadingPortraits.value = false
  }
  if (added) notify(t('已添加 {n} 套立绘。确认名称后保存角色', { n: added }))
  if (failed.length) error.value = t('这些图片没有上传成功：{names}', { names: failed.join('、') })
}

function onAssetFile(file: UploadFile) {
  assetFile.value = file.raw || null
}

function clearAssetFile() {
  assetFile.value = null
}

async function uploadAssetFile() {
  if (!assetFile.value) {
    notify(t('请选择文件'), 'warning')
    return
  }
  uploading.value = true
  try {
    const body = new FormData()
    body.set('file', assetFile.value)
    body.set('asset_type', assetDraft.asset_type)
    body.set('lang', assetDraft.lang || 'zh-Hans')
    body.set('game', gameId.value)
    if (assetDraft.name.trim()) body.set('name', assetDraft.name.trim())
    body.set('texts', JSON.stringify(assetDraft.texts || {}))
    await request('/assets/upload/', { method: 'POST', body })
    notify(t('素材已上传'))
    assetDraft.name = ''
    assetDraft.texts = {}
    assetFile.value = null
    uploadKey.value += 1
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : t('上传失败')
  } finally {
    uploading.value = false
  }
}

async function removeAsset(item: Asset) {
  const agreed = await confirmDelete(t('确定删除「{name}」？用到它的剧情会失去这件素材。', { name: item.name }), t('删除素材'))
  if (!agreed) return
  await request(`/assets/${item.id}/`, { method: 'DELETE' })
  await load()
}

async function editGallery(item: GalleryRow) {
  try {
    const data = await request(`/gallery/${item.id}/`)
    const row = data.results as GalleryRow
    galleryDraft.id = row.id
    galleryDraft.lang = row.lang || 'zh-Hans'
    galleryDraft.texts = cloneTexts(row.texts)
    galleryCopy.value = galleryDraft.lang
    galleryDraft.title = row.title
    galleryDraft.kind = row.kind
    galleryDraft.asset = row.asset
    galleryDraft.unlock_node = row.unlock_node
    galleryDraft.unlocked_by_default = row.unlocked_by_default
  } catch (err) {
    error.value = err instanceof Error ? err.message : t('加载失败')
  }
}

async function saveGallery() {
  if (!galleryDraft.title.trim() || !galleryDraft.asset) {
    notify(t('请填写标题并选择素材'), 'warning')
    return
  }
  savingGallery.value = true
  try {
    const body = {
      game: Number(gameId.value),
      lang: galleryDraft.lang || 'zh-Hans',
      texts: galleryDraft.texts,
      title: galleryDraft.title.trim(),
      kind: galleryDraft.kind,
      asset: galleryDraft.asset,
      unlock_node: galleryDraft.unlock_node,
      unlocked_by_default: galleryDraft.unlocked_by_default,
      sort_order: 0,
    }
    if (galleryDraft.id) {
      await request(`/gallery/${galleryDraft.id}/`, { method: 'PUT', body: JSON.stringify(body) })
    } else {
      await request('/gallery/', { method: 'POST', body: JSON.stringify(body) })
    }
    galleryDraft.id = 0
    galleryDraft.lang = 'zh-Hans'
    galleryDraft.texts = {}
    galleryDraft.title = ''
    galleryDraft.asset = null
    galleryDraft.unlock_node = null
    galleryDraft.unlocked_by_default = false
    notify(t('解锁内容已保存'))
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : t('保存解锁失败')
  } finally {
    savingGallery.value = false
  }
}

async function removeGallery(item: GalleryRow) {
  await request(`/gallery/${item.id}/`, { method: 'DELETE' })
  if (galleryDraft.id === item.id) galleryDraft.id = 0
  await load()
}

async function copyId() {
  if (!game.value) return
  try {
    await navigator.clipboard.writeText(String(game.value.id))
    notify(t('已复制游戏 ID'))
  } catch {
    notify(t('复制失败'), 'warning')
  }
}

async function copyLink(url: string) {
  try {
    await navigator.clipboard.writeText(url)
    notify(t('链接已复制'))
  } catch {
    notify(t('复制失败'), 'warning')
  }
}

watch(plotMode, (value) => {
  sessionStorage.setItem('otome-plot-mode', value)
  if (section.value === 'plot') loadPlot().catch((err) => {
    error.value = err instanceof Error ? err.message : t('加载失败')
  })
})
watch(section, (value) => {
  loadSection().catch((err) => {
    error.value = err instanceof Error ? err.message : t('加载失败')
  })
  if (readSection(route.query.tab) === value) return
  router.replace({ name: 'game', params: { gameId: gameId.value }, query: { tab: value } })
})
function turnPage(page: { value: number }, next: number, reload: () => Promise<void>) {
  if (page.value !== next) page.value = next
  else reload().catch(() => {})
}
watch(characterLang, () => turnPage(characterPage, 1, loadCharacters))
watch(assetLang, () => turnPage(assetPage, 1, loadAssets))
watch(galleryLang, () => turnPage(galleryPage, 1, loadGallery))
watch(plotLang, () => turnPage(nodePage, 1, loadPlot))
watch(characterPage, () => { if (section.value === 'characters') loadCharacters() })
watch(assetPage, () => { if (section.value === 'assets') loadAssets() })
watch(galleryPage, () => { if (section.value === 'gallery') loadGallery() })
watch(nodePage, () => { if (section.value === 'plot' && plotMode.value === 'list') loadPlot() })
watch(
  () => route.query.tab,
  (value) => {
    const next = readSection(value)
    if (section.value !== next) section.value = next
  },
)
watch(gameId, () => {
  characterPage.value = 1
  assetPage.value = 1
  galleryPage.value = 1
  nodePage.value = 1
  load()
}, { immediate: true })
</script>

<style lang="scss" scoped>
.admin-editor {
  min-height: 240px;
}

.story-tabs :deep(.el-tabs__header) {
  margin-bottom: 16px;
}

.image-row {
  display: grid;
  grid-template-columns: minmax(140px, 0.8fr) minmax(180px, 1fr) minmax(180px, 1fr) auto;
  gap: 12px;
  align-items: center;
  margin-bottom: 12px;
}

.image-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  margin-bottom: 8px;
}

.admin-pane-tools {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.media-pick {
  display: flex;
  gap: 8px;
  align-items: center;
  width: 100%;
}

.media-pick :deep(.el-select) {
  flex: 1;
  min-width: 0;
}

.media-preview-video,
.media-preview-image {
  display: block;
  width: 100%;
  max-height: 70vh;
  object-fit: contain;
}
</style>
