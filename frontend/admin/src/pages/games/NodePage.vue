<template>
  <div v-loading="loading" class="node-editor">
    <ElDialog v-model="mediaPreviewOpen" :title="mediaPreviewTitle" width="480px" append-to-body align-center @closed="closeMediaPreview">
      <video v-if="mediaPreviewIsVideo" :src="mediaPreviewUrl" class="media-preview-player" controls autoplay playsinline />
      <img v-else-if="mediaPreviewUrl" :src="mediaPreviewUrl" alt="" class="media-preview-player" />
    </ElDialog>
    <div class="admin-toolbar">
      <h1 class="admin-toolbar__title">{{ isNew ? t('新剧情') : form.node_key || t('编辑剧情') }}</h1>
      <div class="admin-actions">
        <ElButton v-if="!isNew" @click="copyCurrent">{{ t('基于此新建') }}</ElButton>
        <ElButton @click="router.push({ name: 'game', params: { gameId }, query: { tab: 'plot' } })">{{ t('返回故事') }}</ElButton>
      </div>
    </div>
    <ElAlert v-if="error" class="admin-card" :title="error" type="error" show-icon closable @close="error = ''" />
    <ElAlert
      v-if="copySourceKey"
      class="admin-card"
      :title="t('这是从「{key}」复制的场景，改完后保存才会写入。', { key: copySourceKey })"
      type="info"
      show-icon
      :closable="false"
    />

    <ElCard class="admin-card" shadow="never">
      <template #header><div class="admin-card-head">{{ t('对白') }}</div></template>
      <ElForm label-position="top" @submit.prevent>
        <div class="admin-form-grid">
          <LangSelect v-model="form.lang" />
          <ElFormItem class="is-full"><ContentLang v-model="copyLang" :primary="form.lang" /></ElFormItem>
          <ElFormItem :label="t('剧情编号')"><ElInput v-model="form.node_key" :placeholder="t('同一故事内不能重复')" /></ElFormItem>
          <ElFormItem :label="t('排序')"><ElInputNumber v-model="form.sort_order" :min="0" controls-position="right" /></ElFormItem>
          <ElFormItem :label="t('说话角色')">
            <ElSelect
              v-model="form.character"
              clearable
              filterable
              :loading="charactersLoading"
              :placeholder="t('旁白')"
              :value-on-clear="null"
              @visible-change="onCharactersOpen"
            >
              <ElOption v-for="item in characterOptions" :key="item.id" :label="item.label" :value="item.id" />
            </ElSelect>
          </ElFormItem>
          <ElFormItem :label="t('显示名')">
            <ElInput
              :model-value="textValue(form.speaker_name, form.texts, copyLang, 'speaker_name', form.lang)"
              :placeholder="emptyHint(form.speaker_name, copyLang, form.lang, t('留空则使用角色名'))"
              @update:model-value="writeText(form, copyLang, 'speaker_name', $event, form.lang)"
            />
          </ElFormItem>
          <ElFormItem class="is-full" :label="t('对白')">
            <ElInput
              :model-value="textValue(form.content, form.texts, copyLang, 'content', form.lang)"
              :placeholder="emptyHint(form.content, copyLang, form.lang)"
              type="textarea"
              :rows="4"
              @update:model-value="writeText(form, copyLang, 'content', $event, form.lang)"
            />
          </ElFormItem>
          <ElFormItem :label="t('背景（图片或视频）')">
            <div class="media-pick">
              <ElSelect
                v-model="form.background"
                clearable
                filterable
                remote
                reserve-keyword
                :remote-method="searchVisuals"
                :loading="visualsLoading"
                :placeholder="t('选择素材')"
                :value-on-clear="null"
                @visible-change="onVisualsOpen"
                @end-reached="onVisualsEndReached"
              >
                <ElOption v-for="item in visualOptions" :key="item.id" :label="item.label" :value="item.id" />
                <template v-if="visualsHasMore || visualsLoadingMore" #footer>
                  <button type="button" class="picker-more" :disabled="visualsLoadingMore" @click="loadMoreVisuals">
                    {{ visualsLoadingMore ? t('加载中…') : t('加载更多') }}
                  </button>
                </template>
              </ElSelect>
              <ElButton :disabled="!form.background" :loading="previewing === 'background'" @click="previewVisual('background')">
                {{ t('预览') }}
              </ElButton>
            </div>
          </ElFormItem>
          <ElFormItem class="is-full cast-mode" :label="t('画面人数')">
            <ElRadioGroup v-model="castMode">
              <ElRadioButton value="single">{{ t('单角色') }}</ElRadioButton>
              <ElRadioButton value="multi">{{ t('多角色') }}</ElRadioButton>
            </ElRadioGroup>
            <p class="admin-muted">{{ t('说话角色只决定对话框里的名字。画面上站谁、用哪张图、站在哪一格，在下面单独选。') }}</p>
          </ElFormItem>
          <ElFormItem :label="t('背景音乐')">
            <AudioPick
              v-model="form.bgm"
              :assets="audios"
              :preview="audioPreview(form.bgm)"
              :loading="audiosLoading"
              :loading-more="audiosLoadingMore"
              :has-more="audiosHasMore"
              :game-id="gameId"
              :lang="form.lang"
              @uploaded="addAudio"
              @visible-change="onAudiosOpen"
              @load-more="loadMoreAudios"
              @search="searchAudios"
            />
          </ElFormItem>
          <ElFormItem :label="t('语音')">
            <AudioPick
              v-model="form.voice"
              :assets="audios"
              :preview="audioPreview(form.voice)"
              :loading="audiosLoading"
              :loading-more="audiosLoadingMore"
              :has-more="audiosHasMore"
              :game-id="gameId"
              :lang="form.lang"
              @uploaded="addAudio"
              @visible-change="onAudiosOpen"
              @load-more="loadMoreAudios"
              @search="searchAudios"
            />
          </ElFormItem>
          <ElFormItem :label="t('交互音频')">
            <AudioPick
              v-model="form.interact"
              :assets="audios"
              :preview="audioPreview(form.interact)"
              :loading="audiosLoading"
              :loading-more="audiosLoadingMore"
              :has-more="audiosHasMore"
              :game-id="gameId"
              :lang="form.lang"
              @uploaded="addAudio"
              @visible-change="onAudiosOpen"
              @load-more="loadMoreAudios"
              @search="searchAudios"
            />
          </ElFormItem>
          <ElFormItem :label="t('结束后插入（视频或图片）')">
            <div class="media-pick">
              <ElSelect
                v-model="form.insert_media"
                clearable
                filterable
                remote
                reserve-keyword
                :remote-method="searchVisuals"
                :loading="visualsLoading"
                :placeholder="t('选择素材')"
                :value-on-clear="null"
                @visible-change="onVisualsOpen"
                @end-reached="onVisualsEndReached"
              >
                <ElOption v-for="item in visualOptions" :key="item.id" :label="item.label" :value="item.id" />
                <template v-if="visualsHasMore || visualsLoadingMore" #footer>
                  <button type="button" class="picker-more" :disabled="visualsLoadingMore" @click="loadMoreVisuals">
                    {{ visualsLoadingMore ? t('加载中…') : t('加载更多') }}
                  </button>
                </template>
              </ElSelect>
              <ElButton :disabled="!form.insert_media" :loading="previewing === 'insert'" @click="previewVisual('insert')">
                {{ t('预览') }}
              </ElButton>
            </div>
          </ElFormItem>
          <ElFormItem :label="t('解锁标题')">
            <ElInput
              :model-value="textValue(form.insert_title, form.texts, copyLang, 'insert_title', form.lang)"
              :placeholder="emptyHint(form.insert_title, copyLang, form.lang, t('留空则使用素材名，看过或跳过后出现在故事解锁'))"
              @update:model-value="writeText(form, copyLang, 'insert_title', $event, form.lang)"
            />
          </ElFormItem>
          <ElFormItem :label="t('下一句')">
            <ElSelect
              v-model="form.next_node"
              clearable
              filterable
              :loading="nodesLoading"
              :placeholder="t('选择剧情')"
              :value-on-clear="null"
              @visible-change="onNodesOpen"
            >
              <ElOption v-for="item in nextOptions" :key="item.id" :label="item.label" :value="item.id" />
            </ElSelect>
          </ElFormItem>
          <ElFormItem :label="t('结局标题')">
            <ElInput
              :model-value="textValue(form.ending_title, form.texts, copyLang, 'ending_title', form.lang)"
              :placeholder="emptyHint(form.ending_title, copyLang, form.lang)"
              @update:model-value="writeText(form, copyLang, 'ending_title', $event, form.lang)"
            />
          </ElFormItem>
        </div>
        <div class="admin-actions">
          <ElCheckbox v-model="form.is_start">{{ t('开场') }}</ElCheckbox>
          <ElCheckbox v-model="form.is_key">{{ t('关键节点，进入前下载本段资源') }}</ElCheckbox>
          <ElCheckbox v-model="form.is_ending">{{ t('结局') }}</ElCheckbox>
        </div>
      </ElForm>
    </ElCard>

    <ElCard class="admin-card" shadow="never">
      <template #header><div class="admin-card-head">{{ t('画面角色') }}</div></template>
      <p v-if="!figures.length" class="admin-muted">{{ t('这一句可以不放人。') }}</p>
      <div v-for="(figure, index) in figures" :key="index" class="figure-row">
        <ElSelect
          v-model="figure.character"
          clearable
          filterable
          :loading="charactersLoading"
          :placeholder="t('角色')"
          :value-on-clear="null"
          @change="onFigureCharacter(figure)"
          @visible-change="onCharactersOpen"
        >
          <ElOption v-for="item in characterOptions" :key="item.id" :label="item.label" :value="item.id" />
        </ElSelect>
        <ElSelect
          v-model="figure.image"
          clearable
          filterable
          :loading="charactersLoading"
          :placeholder="t('这张立绘')"
          :value-on-clear="null"
          @visible-change="onCharactersOpen"
        >
          <ElOption v-for="item in imagesOf(figure.character)" :key="item.id" :label="item.label" :value="item.id" />
        </ElSelect>
        <div class="pos-grid" role="group" :aria-label="t('位置')">
          <button
            v-for="spot in positions"
            :key="spot.id"
            type="button"
            class="pos-cell"
            :class="{ on: figure.position === spot.id }"
            @click="figure.position = spot.id"
          >
            {{ spot.label }}
          </button>
        </div>
        <ElButton v-if="castMode === 'multi'" type="danger" plain @click="figures.splice(index, 1)">{{ t('移除') }}</ElButton>
      </div>
      <ElButton v-if="castMode === 'multi' || !figures.length" @click="addFigure">{{ t('添加角色') }}</ElButton>
    </ElCard>

    <ElCard class="admin-card" shadow="never">
      <template #header><div class="admin-card-head">{{ t('选项') }}</div></template>
      <p v-if="isNew" class="admin-muted">{{ t('可以先写好选项，保存剧情时会一起写入。') }}</p>
      <p class="admin-muted">{{ t('交互音频在玩家点击时播放一次。对白上的音频用于点击对话框，选项上的音频用于点这个选项。') }}</p>
      <div v-for="(choice, index) in choices" :key="index" class="choice-row">
        <ElInput
          :model-value="textValue(choice.text, choice.texts, copyLang, 'text', form.lang)"
          :placeholder="emptyHint(choice.text, copyLang, form.lang, t('选项 {n}', { n: index + 1 }))"
          @update:model-value="writeText(choice, copyLang, 'text', $event, form.lang)"
        />
        <ElSelect v-model="choice.next_node" filterable :loading="nodesLoading" :placeholder="t('跳转到')" @visible-change="onNodesOpen">
          <ElOption v-for="item in choiceOptions" :key="item.id" :label="item.label" :value="item.id" />
        </ElSelect>
        <AudioPick
          v-model="choice.interact"
          :assets="audios"
          :preview="audioPreview(choice.interact)"
          :loading="audiosLoading"
          :loading-more="audiosLoadingMore"
          :has-more="audiosHasMore"
          :game-id="gameId"
          :lang="form.lang"
          @uploaded="addAudio"
          @visible-change="onAudiosOpen"
          @load-more="loadMoreAudios"
          @search="searchAudios"
        />
        <ElButton type="danger" plain @click="choices.splice(index, 1)">{{ t('移除') }}</ElButton>
      </div>
      <ElButton @click="choices.push({ text: '', texts: {}, next_node: null, interact: null })">{{ t('添加选项') }}</ElButton>
    </ElCard>

    <div class="admin-actions">
      <ElButton type="primary" :loading="saving" @click="save()">{{ t('保存剧情') }}</ElButton>
      <ElTooltip :disabled="!continueReason" :content="continueReason" placement="top">
        <span class="continue-wrap">
          <ElButton :disabled="!!continueReason" :loading="saving" @click="save({ continueNext: true })">
            {{ t('保存并接着写下一句') }}
          </ElButton>
        </span>
      </ElTooltip>
      <ElButton v-if="!isNew" type="danger" plain @click="removeNode">{{ t('删除剧情') }}</ElButton>
    </div>
    <p v-if="continueReason" class="admin-muted continue-hint">{{ continueReason }}</p>
  </div>
</template>

<script lang="ts" setup>
import { t } from '../../i18n'
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AudioPick from '../../components/AudioPick.vue'
import ContentLang from '../../components/ContentLang.vue'
import LangSelect from '../../components/LangSelect.vue'
import {
  Asset,
  AssetInfo,
  Character,
  ChoiceDraft,
  StoryNode,
  asId,
  isAuthError,
  list,
  listAll,
  request,
  syncChoices,
} from '../../services/otome/api'
import { cloneTexts, emptyHint, textValue, writeText, type Texts } from '../../utils/contentLang'
import { confirmDelete, notify } from '../../utils/feedback'

const route = useRoute()
const router = useRouter()
const gameId = computed(() => String(route.params.gameId))
const nodeId = computed(() => String(route.params.nodeId))
const isNew = computed(() => nodeId.value === 'new')
const contentTabs = ['line', 'visual', 'audio', 'insert', 'choice']
const contentTab = ref(contentTabs.includes(String(route.query.tab)) ? String(route.query.tab) : 'line')
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const characters = ref<Character[]>([])
const visuals = ref<Asset[]>([])
const audios = ref<Asset[]>([])
const nodes = ref<StoryNode[]>([])
const previousChoices = ref<StoryNode['choices']>([])
const choices = ref<ChoiceDraft[]>([])
const continueFrom = ref<number | null>(null)
const copySourceKey = ref('')
const CONTINUE_KEY = 'otome-node-continue'
const COPY_KEY = 'otome-node-copy'
const copyLang = ref('zh-Hans')
const castMode = ref<'single' | 'multi'>('single')
const figures = ref<FigureDraft[]>([])
const positions = computed(() => [
  { id: 'nw', label: t('左上') },
  { id: 'n', label: t('上') },
  { id: 'ne', label: t('右上') },
  { id: 'w', label: t('左') },
  { id: 'c', label: t('中') },
  { id: 'e', label: t('右') },
  { id: 'sw', label: t('左下') },
  { id: 's', label: t('下') },
  { id: 'se', label: t('右下') },
])
type FigureDraft = {
  character: number | null
  image: number | null
  position: string
}
const form = reactive({
  lang: 'zh-Hans',
  texts: {} as Texts,
  node_key: '',
  sort_order: 0,
  character: null as number | null,
  speaker_name: '',
  content: '',
  background: null as number | null,
  portrait: null as number | null,
  bgm: null as number | null,
  voice: null as number | null,
  interact: null as number | null,
  insert_media: null as number | null,
  insert_title: '',
  next_node: null as number | null,
  is_start: false,
  is_key: false,
  is_ending: false,
  ending_title: '',
})

const characterOptions = computed(() => characters.value.map((item) => ({ id: item.id, label: item.name })))
const visualOptions = computed(() =>
  visuals.value.map((item) => ({
    id: item.id,
    label: `${item.asset_type === 'video' ? t('视频') : t('图片')} · ${item.name}`,
  })),
)
const mediaPreviewOpen = ref(false)
const mediaPreviewTitle = ref('')
const mediaPreviewUrl = ref('')
const mediaPreviewIsVideo = ref(false)
const previewing = ref<'background' | 'insert' | ''>('')

function closeMediaPreview() {
  mediaPreviewUrl.value = ''
  mediaPreviewIsVideo.value = false
}

function openMediaPreview(title: string, asset: Asset) {
  if (!asset.file_url) {
    notify(t('没有可预览的地址'), 'warning')
    return
  }
  mediaPreviewTitle.value = title
  mediaPreviewUrl.value = asset.file_url
  mediaPreviewIsVideo.value = asset.asset_type === 'video'
  mediaPreviewOpen.value = true
}

async function resolveVisual(id: number) {
  const found = visuals.value.find((item) => item.id === id)
  if (found) return found
  const data = await request(`/assets/${id}/`)
  const asset = data.results as Asset
  if (asset?.id) mergeAssets(visuals, [asset])
  return asset?.id ? asset : null
}

async function previewVisual(kind: 'background' | 'insert') {
  const id = kind === 'background' ? form.background : form.insert_media
  if (!id) return
  previewing.value = kind
  try {
    const asset = await resolveVisual(id)
    if (!asset) {
      notify(t('没有可预览的地址'), 'warning')
      return
    }
    openMediaPreview(kind === 'background' ? t('背景（图片或视频）') : t('结束后插入（视频或图片）'), asset)
  } catch (err) {
    report(err)
  } finally {
    previewing.value = ''
  }
}
function nodeLabel(item: StoryNode) {
  const line = (item.content || '').replace(/\s+/g, ' ').trim()
  const excerpt = line.length > 24 ? `${line.slice(0, 24)}…` : line
  return excerpt ? `${item.node_key} · ${excerpt}` : item.node_key
}

const nextOptions = computed(() =>
  nodes.value
    .filter((item) => String(item.id) !== nodeId.value)
    .map((item) => ({ id: item.id, label: nodeLabel(item) })),
)
const choiceOptions = computed(() => nodes.value.map((item) => ({ id: item.id, label: nodeLabel(item) })))

const continueReason = computed(() => {
  const reasons: string[] = []
  if (form.is_ending) reasons.push(t('当前句是结局，不能接着写下一句'))
  if (choices.value.some(choiceFilled)) reasons.push(t('当前句包含选项，请用现有方式配置分支'))
  if (form.next_node) reasons.push(t('当前句已有下一句，不能覆盖已有剧情'))
  return reasons.join('；')
})

function choiceFilled(choice: ChoiceDraft) {
  if (choice.id || choice.next_node) return true
  if (choice.text.trim()) return true
  return Object.values(choice.texts || {}).some((pack) => (pack.text || '').trim())
}

function imagesOf(characterId: number | null) {
  const found = characters.value.find((item) => item.id === characterId)
  return (found?.images || []).map((item) => ({ id: item.id, label: item.label || t('立绘 {id}', { id: item.id }) }))
}

function blankFigure(): FigureDraft {
  const taken = new Set(figures.value.map((item) => item.position))
  const spot = positions.value.find((item) => !taken.has(item.id))
  return { character: form.character, image: null, position: spot?.id || 'c' }
}

function addFigure() {
  if (castMode.value === 'single' && figures.value.length) return
  figures.value.push(blankFigure())
}

function onFigureCharacter(figure: FigureDraft) {
  const allowed = new Set(imagesOf(figure.character).map((item) => item.id))
  if (figure.image && !allowed.has(figure.image)) figure.image = null
}

watch(castMode, (mode) => {
  if (mode === 'single' && figures.value.length > 1) figures.value.splice(1)
})

type ContinueDraft = {
  gameId: string
  fromId: number
  lang: string
  node_key: string
  sort_order: number
  background: number | null
  portrait: number | null
  cast_mode: 'single' | 'multi'
  figures: FigureDraft[]
  bgm: number | null
}

function nextNodeKey(current: string) {
  const taken = new Set(nodes.value.map((item) => item.node_key))
  const base = current.trim()
  if (base) taken.add(base)
  const match = base.match(/^(.*?)(\d+)$/)
  if (match) {
    const prefix = match[1]
    const width = /^0\d+$/.test(match[2]) ? match[2].length : 0
    let n = Number(match[2]) + 1
    let candidate = ''
    do {
      candidate = prefix + (width ? String(n).padStart(width, '0') : String(n))
      n += 1
    } while (taken.has(candidate))
    return candidate
  }
  if (!base) {
    let n = 1
    while (taken.has(String(n))) n += 1
    return String(n)
  }
  let n = 2
  let candidate = `${base}-${n}`
  while (taken.has(candidate)) {
    n += 1
    candidate = `${base}-${n}`
  }
  return candidate
}

function readContinueDraft(): ContinueDraft | null {
  if (route.query.continue !== '1') return null
  const raw = sessionStorage.getItem(CONTINUE_KEY)
  if (!raw) return null
  try {
    const draft = JSON.parse(raw) as ContinueDraft
    if (String(draft.gameId) !== gameId.value || !draft.fromId) return null
    return draft
  } catch {
    return null
  }
}

function blankNode() {
  form.lang = 'zh-Hans'
  form.texts = {}
  copyLang.value = 'zh-Hans'
  form.node_key = ''
  form.sort_order = nodes.value.reduce((max, item) => Math.max(max, item.sort_order), 0) + 1
  form.character = null
  form.speaker_name = ''
  form.content = ''
  form.background = null
  form.portrait = null
  castMode.value = 'single'
  figures.value = []
  form.bgm = null
  form.voice = null
  form.interact = null
  form.insert_media = null
  form.insert_title = ''
  form.next_node = null
  form.is_start = false
  form.is_key = false
  form.is_ending = false
  form.ending_title = ''
  previousChoices.value = []
  choices.value = []
  continueFrom.value = null
  copySourceKey.value = ''
}

const audioInfos = ref<Record<number, AssetInfo>>({})

function audioPreview(id: number | null | undefined) {
  if (id == null) return null
  return audioInfos.value[id] || null
}

function rememberAudioInfo(info?: AssetInfo | null) {
  if (!info?.id) return
  audioInfos.value = { ...audioInfos.value, [info.id]: info }
  if (audios.value.some((item) => item.id === info.id)) {
    audios.value = audios.value.map((item) =>
      item.id === info.id
        ? {
            ...item,
            name: info.name || item.name,
            file_url: info.file_url || item.file_url,
            duration: info.duration ?? item.duration,
            file_size: info.file_size ?? item.file_size,
          }
        : item,
    )
    return
  }
  audios.value = [
    ...audios.value,
    {
      id: info.id,
      name: info.name || '',
      asset_type: 'audio',
      url: '',
      file_url: info.file_url || '',
      duration: info.duration ?? null,
      file_size: info.file_size ?? null,
      remark: '',
      lang: '',
    },
  ]
}

function addAudio(asset: Asset) {
  rememberAudioInfo({
    id: asset.id,
    name: asset.name,
    asset_type: asset.asset_type,
    file_url: asset.file_url,
    duration: asset.duration,
    file_size: asset.file_size,
  })
}

function copyCurrent() {
  sessionStorage.setItem(
    COPY_KEY,
    JSON.stringify({
      gameId: gameId.value,
      sourceId: nodeId.value,
      node_key: form.node_key,
      sort_order: form.sort_order,
      lang: form.lang,
      texts: form.texts,
      character: form.character,
      speaker_name: form.speaker_name,
      content: form.content,
      background: form.background,
      portrait: form.portrait,
      cast_mode: castMode.value,
      figures: figures.value,
      bgm: form.bgm,
      voice: form.voice,
      interact: form.interact,
      bgm_info: audioPreview(form.bgm),
      voice_info: audioPreview(form.voice),
      interact_info: audioPreview(form.interact),
      insert_media: form.insert_media,
      insert_title: form.insert_title,
      next_node: form.next_node,
      is_key: form.is_key,
      is_ending: form.is_ending,
      ending_title: form.ending_title,
      choices: choices.value.map((item) => ({
        text: item.text,
        texts: item.texts,
        next_node: item.next_node,
        interact: item.interact,
        interact_info: audioPreview(item.interact),
      })),
    }),
  )
  router.push({ name: 'node', params: { gameId: gameId.value, nodeId: 'new' }, query: { copy: nodeId.value } })
}

function readEditorCopy(copyId: string) {
  const raw = sessionStorage.getItem(COPY_KEY)
  if (!raw) return null
  try {
    const draft = JSON.parse(raw) as StoryNode & { gameId?: string; sourceId?: string }
    if (String(draft.gameId) !== gameId.value || String(draft.sourceId) !== String(copyId)) return null
    sessionStorage.removeItem(COPY_KEY)
    return draft
  } catch {
    return null
  }
}

function applyCopy(source: StoryNode) {
  blankNode()
  form.lang = source.lang || 'zh-Hans'
  form.texts = cloneTexts(source.texts)
  copyLang.value = form.lang
  form.node_key = nextNodeKey(source.node_key)
  form.sort_order = (Number(source.sort_order) || 0) + 1
  form.character = source.character
  form.speaker_name = source.speaker_name || ''
  form.content = source.content || ''
  form.background = source.background
  form.portrait = source.portrait
  castMode.value = source.cast_mode === 'multi' ? 'multi' : 'single'
  figures.value = (source.figures || []).map((item) => ({
    character: item.character,
    image: item.image,
    position: item.position || 'c',
  }))
  form.bgm = source.bgm
  form.voice = source.voice
  form.interact = source.interact
  rememberAudioInfo(source.bgm_info)
  rememberAudioInfo(source.voice_info)
  rememberAudioInfo(source.interact_info)
  form.insert_media = source.insert_media
  form.insert_title = source.insert_title || ''
  form.next_node = source.next_node
  form.is_key = source.is_key
  form.is_ending = source.is_ending
  form.ending_title = source.ending_title || ''
  choices.value = (source.choices || []).map((item) => {
    rememberAudioInfo(item.interact_info)
    return {
      text: item.text,
      texts: cloneTexts(item.texts),
      next_node: item.next_node,
      interact: item.interact,
    }
  })
  copySourceKey.value = source.node_key
}

function applyContinueDraft(draft: ContinueDraft) {
  blankNode()
  form.lang = draft.lang || 'zh-Hans'
  copyLang.value = form.lang
  form.node_key = draft.node_key
  form.sort_order = draft.sort_order
  form.background = draft.background
  form.portrait = draft.portrait
  castMode.value = draft.cast_mode === 'multi' ? 'multi' : 'single'
  figures.value = (draft.figures || []).map((item) => ({
    character: item.character,
    image: item.image,
    position: item.position || 'c',
  }))
  form.bgm = draft.bgm
  continueFrom.value = draft.fromId
}

function fill(node: StoryNode) {
  continueFrom.value = null
  copySourceKey.value = ''
  form.lang = node.lang || 'zh-Hans'
  form.texts = cloneTexts(node.texts)
  copyLang.value = form.lang
  form.node_key = node.node_key
  form.sort_order = node.sort_order || 0
  form.character = node.character
  form.speaker_name = node.speaker_name || ''
  form.content = node.content || ''
  form.background = node.background
  form.portrait = node.portrait
  castMode.value = node.cast_mode === 'multi' ? 'multi' : 'single'
  figures.value = (node.figures || []).map((item) => ({
    character: item.character,
    image: item.image,
    position: item.position || 'c',
  }))
  form.bgm = node.bgm
  form.voice = node.voice
  form.interact = node.interact
  rememberAudioInfo(node.bgm_info)
  rememberAudioInfo(node.voice_info)
  rememberAudioInfo(node.interact_info)
  form.insert_media = node.insert_media
  form.insert_title = node.insert_title || ''
  form.next_node = node.next_node
  form.is_start = node.is_start
  form.is_key = node.is_key
  form.is_ending = node.is_ending
  form.ending_title = node.ending_title || ''
  previousChoices.value = node.choices || []
  choices.value = (node.choices || []).map((item) => {
    rememberAudioInfo(item.interact_info)
    return {
      id: item.id,
      text: item.text,
      texts: cloneTexts(item.texts),
      next_node: item.next_node,
      interact: item.interact,
    }
  })
}

type PickerKey = 'characters' | 'nodes'
const PICKER_PAGE_SIZE = 20
const pickerReady: Record<PickerKey, boolean> = {
  characters: false,
  nodes: false,
}
const pickerTask: Record<PickerKey, Promise<void> | null> = {
  characters: null,
  nodes: null,
}
const charactersLoading = ref(false)
const visualsLoading = ref(false)
const visualsLoadingMore = ref(false)
const audiosLoading = ref(false)
const audiosLoadingMore = ref(false)
const nodesLoading = ref(false)
const visualsPage = ref(0)
const visualsTotalPages = ref(1)
const audiosPage = ref(0)
const audiosTotalPages = ref(1)
const visualsKeyword = ref('')
const audiosKeyword = ref('')
const visualsHasMore = computed(() => visualsPage.value < visualsTotalPages.value)
const audiosHasMore = computed(() => audiosPage.value < audiosTotalPages.value)
let visualsRequest: Promise<void> | null = null
let audiosRequest: Promise<void> | null = null
let visualsSeq = 0
let audiosSeq = 0
let visualsSearchTimer = 0
let audiosSearchTimer = 0
let loadedGame = ''

function resetPickers() {
  characters.value = []
  visuals.value = []
  audios.value = []
  nodes.value = []
  audioInfos.value = {}
  pickerReady.characters = false
  pickerReady.nodes = false
  pickerTask.characters = null
  pickerTask.nodes = null
  charactersLoading.value = false
  visualsLoading.value = false
  visualsLoadingMore.value = false
  audiosLoading.value = false
  audiosLoadingMore.value = false
  nodesLoading.value = false
  visualsPage.value = 0
  visualsTotalPages.value = 1
  audiosPage.value = 0
  audiosTotalPages.value = 1
  visualsKeyword.value = ''
  audiosKeyword.value = ''
  visualsRequest = null
  audiosRequest = null
  window.clearTimeout(visualsSearchTimer)
  window.clearTimeout(audiosSearchTimer)
}

function report(err: unknown) {
  if (!isAuthError(err)) {
    error.value = err instanceof Error ? err.message : t('加载失败')
  }
}

function mergeAssets(target: { value: Asset[] }, items: Asset[]) {
  if (!items.length) return
  const seen = new Set(target.value.map((item) => item.id))
  const next = items.filter((item) => !seen.has(item.id))
  if (next.length) target.value = [...target.value, ...next]
}

function keepAssets(target: Asset[], ids: Array<number | null | undefined>) {
  const wanted = new Set(ids.filter((id): id is number => id != null))
  if (!wanted.size) return [] as Asset[]
  return target.filter((item) => wanted.has(item.id))
}

function selectedAudioIds() {
  return [form.bgm, form.voice, form.interact, ...choices.value.map((item) => item.interact)]
}

function ensurePicker(key: PickerKey, loading: { value: boolean }, loadItems: () => Promise<void>) {
  if (pickerReady[key]) return Promise.resolve()
  const pending = pickerTask[key]
  if (pending) return pending
  loading.value = true
  const task = loadItems()
    .then(() => {
      pickerReady[key] = true
    })
    .catch((err) => {
      pickerTask[key] = null
      throw err
    })
    .finally(() => {
      loading.value = false
    })
  pickerTask[key] = task
  return task
}

function ensureCharacters() {
  return ensurePicker('characters', charactersLoading, async () => {
    characters.value = await listAll<Character>('/characters/', { game: gameId.value })
  })
}

function ensureNodes() {
  return ensurePicker('nodes', nodesLoading, async () => {
    nodes.value = await listAll<StoryNode>('/nodes/', { game: gameId.value })
  })
}

async function fetchVisualPage(page: number, seq: number) {
  const keyword = visualsKeyword.value
  const data = await list<Asset>('/assets/', {
    brief: 1,
    currentPage: page,
    pageSize: PICKER_PAGE_SIZE,
    name: keyword || undefined,
  })
  if (seq !== visualsSeq || keyword !== visualsKeyword.value) return
  const items = data.items.filter((item) => item.asset_type === 'image' || item.asset_type === 'video')
  if (page === 1) {
    const kept = keepAssets(visuals.value, [form.background, form.insert_media])
    const ids = new Set(items.map((item) => item.id))
    visuals.value = [...kept.filter((item) => !ids.has(item.id)), ...items]
  } else {
    mergeAssets(visuals, items)
  }
  visualsPage.value = page
  visualsTotalPages.value = Math.max(data.totalPages, 1)
}

async function loadVisuals(reset = false) {
  if (!reset && visualsRequest) return visualsRequest
  if (!reset && visualsPage.value >= visualsTotalPages.value) return
  const nextPage = reset ? 1 : visualsPage.value + 1
  if (!reset && nextPage > visualsTotalPages.value) return
  const seq = reset ? ++visualsSeq : visualsSeq
  if (reset || visualsPage.value === 0) visualsLoading.value = true
  else visualsLoadingMore.value = true
  const task = fetchVisualPage(nextPage, seq)
    .catch((err) => {
      if (seq === visualsSeq) report(err)
      throw err
    })
    .finally(() => {
      if (seq !== visualsSeq) return
      visualsLoading.value = false
      visualsLoadingMore.value = false
      visualsRequest = null
    })
  visualsRequest = task
  return task
}

function loadMoreVisuals() {
  if (visualsLoading.value || visualsLoadingMore.value) return
  if (visualsPage.value >= visualsTotalPages.value) return
  loadVisuals().catch(() => {})
}

function searchVisuals(query: string) {
  window.clearTimeout(visualsSearchTimer)
  visualsSearchTimer = window.setTimeout(() => {
    const next = query.trim()
    if (next === visualsKeyword.value && visualsPage.value > 0) return
    visualsKeyword.value = next
    visualsPage.value = 0
    visualsTotalPages.value = 1
    loadVisuals(true).catch(() => {})
  }, 300)
}

async function fetchAudioPage(page: number, seq: number) {
  const keyword = audiosKeyword.value
  const data = await list<Asset>('/assets/', {
    brief: 1,
    asset_type: 'audio',
    currentPage: page,
    pageSize: PICKER_PAGE_SIZE,
    name: keyword || undefined,
  })
  if (seq !== audiosSeq || keyword !== audiosKeyword.value) return
  if (page === 1) {
    const kept = keepAssets(audios.value, selectedAudioIds())
    const ids = new Set(data.items.map((item) => item.id))
    audios.value = [...kept.filter((item) => !ids.has(item.id)), ...data.items]
  } else {
    mergeAssets(audios, data.items)
  }
  audiosPage.value = page
  audiosTotalPages.value = Math.max(data.totalPages, 1)
}

async function loadAudios(reset = false) {
  if (!reset && audiosRequest) return audiosRequest
  if (!reset && audiosPage.value >= audiosTotalPages.value) return
  const nextPage = reset ? 1 : audiosPage.value + 1
  if (!reset && nextPage > audiosTotalPages.value) return
  const seq = reset ? ++audiosSeq : audiosSeq
  if (reset || audiosPage.value === 0) audiosLoading.value = true
  else audiosLoadingMore.value = true
  const task = fetchAudioPage(nextPage, seq)
    .catch((err) => {
      if (seq === audiosSeq) report(err)
      throw err
    })
    .finally(() => {
      if (seq !== audiosSeq) return
      audiosLoading.value = false
      audiosLoadingMore.value = false
      audiosRequest = null
    })
  audiosRequest = task
  return task
}

function loadMoreAudios() {
  if (audiosLoading.value || audiosLoadingMore.value) return
  if (audiosPage.value >= audiosTotalPages.value) return
  loadAudios().catch(() => {})
}

function searchAudios(query: string) {
  window.clearTimeout(audiosSearchTimer)
  audiosSearchTimer = window.setTimeout(() => {
    const next = query.trim()
    if (next === audiosKeyword.value && audiosPage.value > 0) return
    audiosKeyword.value = next
    audiosPage.value = 0
    audiosTotalPages.value = 1
    loadAudios(true).catch(() => {})
  }, 300)
}

function onCharactersOpen(open: boolean) {
  if (open) ensureCharacters().catch(report)
}

function onVisualsOpen(open: boolean) {
  if (open && visualsPage.value === 0) loadVisuals(true).catch(() => {})
}

function onVisualsEndReached(direction: string) {
  if (direction === 'bottom') loadMoreVisuals()
}

function onAudiosOpen(open: boolean) {
  if (open && audiosPage.value === 0) loadAudios(true).catch(() => {})
}

function onNodesOpen(open: boolean) {
  if (open) ensureNodes().catch(report)
}

function resetForm() {
  form.lang = 'zh-Hans'
  form.texts = {}
  copyLang.value = 'zh-Hans'
  form.node_key = ''
  form.sort_order = 0
  form.character = null
  form.speaker_name = ''
  form.content = ''
  form.background = null
  form.portrait = null
  castMode.value = 'single'
  figures.value = []
  form.bgm = null
  form.voice = null
  form.interact = null
  form.insert_media = null
  form.insert_title = ''
  form.next_node = null
  form.is_start = false
  form.is_key = false
  form.is_ending = false
  form.ending_title = ''
  previousChoices.value = []
  choices.value = []
}

async function load() {
  loading.value = true
  error.value = ''
  if (loadedGame !== gameId.value) {
    resetPickers()
    loadedGame = gameId.value
  }
  try {
    if (isNew.value) {
      const draft = readContinueDraft()
      const copyId = Array.isArray(route.query.copy) ? route.query.copy[0] : route.query.copy
      if (draft) {
        applyContinueDraft(draft)
        return
      }
      if (copyId) {
        const editorCopy = readEditorCopy(String(copyId))
        await ensureNodes()
        const source = editorCopy || nodes.value.find((item) => String(item.id) === String(copyId))
        if (source) applyCopy(source)
        else {
          resetForm()
          continueFrom.value = null
          copySourceKey.value = ''
          error.value = t('要复制的场景不存在')
        }
        return
      }
      resetForm()
      continueFrom.value = null
      copySourceKey.value = ''
      return
    }
    const data = await request(`/nodes/${nodeId.value}/`)
    const current = data.results as StoryNode
    if (!current?.id) {
      error.value = t('剧情不存在')
      return
    }
    fill(current)
  } catch (err) {
    report(err)
  } finally {
    loading.value = false
  }
}

function payload() {
  return {
    game: Number(gameId.value),
    lang: form.lang || 'zh-Hans',
    texts: form.texts,
    node_key: form.node_key.trim(),
    sort_order: Number(form.sort_order) || 0,
    character: asId(form.character),
    speaker_name: form.speaker_name.trim(),
    content: form.content.trim(),
    background: asId(form.background),
    portrait: asId(form.portrait),
    cast_mode: castMode.value,
    figures: (castMode.value === 'single' ? figures.value.slice(0, 1) : figures.value).map((item) => ({
      character: item.character,
      image: item.image,
      position: item.position,
    })),
    bgm: asId(form.bgm),
    voice: asId(form.voice),
    interact: asId(form.interact),
    insert_media: asId(form.insert_media),
    insert_title: form.insert_title.trim(),
    next_node: asId(form.next_node),
    is_start: form.is_start,
    is_key: form.is_key,
    is_ending: form.is_ending,
    ending_title: form.ending_title.trim(),
  }
}

function continueDraft(fromId: number): ContinueDraft {
  return {
    gameId: gameId.value,
    fromId,
    lang: form.lang || 'zh-Hans',
    node_key: nextNodeKey(form.node_key),
    sort_order: (Number(form.sort_order) || 0) + 1,
    background: form.background,
    portrait: form.portrait,
    cast_mode: castMode.value,
    figures: figures.value.map((item) => ({ ...item })),
    bgm: form.bgm,
  }
}

async function linkPrevious(fromId: number, savedId: number) {
  const data = await request(`/nodes/${fromId}/`)
  const previous = data.results as StoryNode
  if (previous.is_ending || previous.next_node || (previous.choices || []).length) return 'blocked' as const
  await request(`/nodes/${fromId}/`, { method: 'PATCH', body: JSON.stringify({ next_node: savedId }) })
  return 'linked' as const
}

async function save(options?: { continueNext?: boolean }) {
  if (options?.continueNext && continueReason.value) {
    notify(continueReason.value, 'warning')
    return
  }
  if (!form.node_key.trim() || !form.content.trim()) {
    notify(t('请填写剧情编号和对白'), 'warning')
    return
  }
  const nextId = asId(form.next_node)
  if (!isNew.value && nextId && String(nextId) === nodeId.value) {
    notify(t('下一句不能指向自己'), 'warning')
    return
  }
  const created = isNew.value
  const linkFrom = created ? continueFrom.value : null
  saving.value = true
  error.value = ''
  try {
    const body = payload()
    const data = created
      ? await request('/nodes/', { method: 'POST', body: JSON.stringify(body) })
      : await request(`/nodes/${nodeId.value}/`, { method: 'PUT', body: JSON.stringify(body) })
    const savedId = data.results.id as number
    await syncChoices(savedId, choices.value, previousChoices.value)
    let linkState: 'none' | 'linked' | 'blocked' | 'failed' = 'none'
    if (linkFrom) {
      try {
        linkState = await linkPrevious(linkFrom, savedId)
      } catch {
        linkState = 'failed'
      }
    }
    if (linkState === 'linked') notify(t('剧情已保存，并接上了上一句'))
    else if (linkState === 'blocked') notify(t('剧情已保存。上一句已有后续，这次没有改连接'), 'warning')
    else if (linkState === 'failed') notify(t('剧情已保存，但没有接上上一句'), 'warning')
    else notify(t('剧情已保存'))
    if (options?.continueNext) {
      sessionStorage.setItem(CONTINUE_KEY, JSON.stringify(continueDraft(savedId)))
      const before = nodeId.value
      await router.push({ name: 'node', params: { gameId: gameId.value, nodeId: 'new' }, query: { continue: '1' } })
      if (before === 'new') await load()
      return
    }
    if (linkFrom) sessionStorage.removeItem(CONTINUE_KEY)
    if (created) {
      await router.replace({ name: 'node', params: { gameId: gameId.value, nodeId: savedId } })
    } else {
      await load()
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : t('保存失败')
  } finally {
    saving.value = false
  }
}

async function removeNode() {
  const agreed = await confirmDelete(t('指向这段剧情的选项和下一句会被清掉。'), t('删除剧情'))
  if (!agreed) return
  await request(`/nodes/${nodeId.value}/`, { method: 'DELETE' })
  router.push({ name: 'game', params: { gameId: gameId.value }, query: { tab: 'plot' } })
}

watch(nodeId, load, { immediate: true })

watch(
  () => [form.background, form.insert_media] as const,
  ([background, insert]) => {
    if (background) resolveVisual(background).catch(report)
    if (insert) resolveVisual(insert).catch(report)
  },
)

</script>

<style lang="scss" scoped>
.node-editor {
  min-height: 240px;
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

.picker-more {
  display: block;
  width: 100%;
  padding: 8px 12px;
  border: 0;
  background: transparent;
  color: #409eff;
  cursor: pointer;
  text-align: center;
}

.picker-more:disabled {
  color: #a8abb2;
  cursor: default;
}

.media-preview-player {
  display: block;
  width: 100%;
  max-height: 70vh;
  object-fit: contain;
  background: #f5f7fa;
}

.continue-wrap {
  display: inline-block;
}

.continue-hint {
  margin: 8px 0 0;
}

.cast-mode :deep(.el-form-item__content) {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.cast-mode .admin-muted {
  width: 100%;
  margin: 8px 0 0;
}

.choice-row {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr) minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  margin-bottom: 12px;
}

.choice-row :deep(.el-select) {
  width: 100%;
}

.figure-row {
  display: grid;
  grid-template-columns: minmax(140px, 1fr) minmax(160px, 1fr) auto auto;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
}

.pos-grid {
  display: grid;
  grid-template-columns: repeat(3, 52px);
  gap: 4px;
}

.pos-cell {
  height: 32px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  background: #fff;
  color: #606266;
  cursor: pointer;
}

.pos-cell.on {
  border-color: #7c5cbf;
  background: #f3eefe;
  color: #5b3f96;
}

@media (max-width: 768px) {
  .figure-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .choice-row {
    grid-template-columns: 1fr;
  }
}
</style>
