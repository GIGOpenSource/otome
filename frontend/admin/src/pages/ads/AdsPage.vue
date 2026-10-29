<template>
  <ElAlert v-if="error" class="admin-card" :title="error" type="error" show-icon closable @close="error = ''" />

  <ElCard class="admin-card" shadow="never">
    <p class="admin-muted">
      {{ t('用户来源和内置广告都可以按游戏、创建时间筛选。不选时间时统计全部；选了之后，访问、新增、登录、展示和点击只计这段时间。') }}
    </p>
    <ElForm :inline="true" @submit.prevent="load">
      <ElFormItem :label="t('游戏')">
        <ElSelect v-model="gameId" clearable :placeholder="t('全部')" style="width: 220px" @visible-change="onGamesOpen" @change="load">
          <ElOption v-for="item in games" :key="item.id" :label="item.title" :value="item.id" />
        </ElSelect>
      </ElFormItem>
      <LangSelect v-model="lang" filter />
      <ElFormItem :label="t('时间')">
        <ElDatePicker
          v-model="dateRange"
          type="daterange"
          value-format="YYYY-MM-DD"
          :range-separator="t('至')"
          :start-placeholder="t('开始')"
          :end-placeholder="t('结束')"
          :disabled-date="disableFuture"
          :shortcuts="rangeShortcuts"
          unlink-panels
          style="width: 320px"
          @change="onDateRange"
        />
      </ElFormItem>
      <ElFormItem>
        <ElButton type="primary" native-type="submit">{{ t('筛选') }}</ElButton>
      </ElFormItem>
    </ElForm>
  </ElCard>

  <ElTabs v-model="tab" class="admin-card ads-tabs">
    <ElTabPane :label="t('用户来源')" name="channels">
      <div class="pane-actions">
        <p class="admin-muted">{{ t('把落地页链接投到对应渠道。样式共用，统计按链接分开。') }}</p>
        <ElButton type="primary" @click="openCreate">{{ t('创建来源') }}</ElButton>
      </div>

      <ElTable v-loading="loading" :data="channels" row-key="id" border stripe class="ads-table">
        <ElTableColumn :label="t('来源')" min-width="160">
          <template #default="{ row }">
            <div class="admin-speaker">{{ row.name }}</div>
            <div class="admin-sub">{{ row.remark }}</div>
          </template>
        </ElTableColumn>
        <ElTableColumn :label="t('落地页')" min-width="280">
          <template #default="{ row }">
            <a class="admin-link landing-link" :href="row.landing_url" target="_blank" rel="noopener noreferrer">{{
              row.landing_url
            }}</a>
            <div>
              <ElButton link type="primary" @click="copyText(row.landing_url)">{{ t('复制链接') }}</ElButton>
            </div>
          </template>
        </ElTableColumn>
        <ElTableColumn :label="t('渠道 ID')" min-width="140">
          <template #default="{ row }">
            <ElButton link type="primary" @click="copyText(row.channel_id)">{{ row.channel_id }}</ElButton>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="game_title" :label="t('游戏')" min-width="120" />
        <ElTableColumn :label="t('语言')" width="120">
          <template #default="{ row }">
            <ElTag size="small">{{ row.lang_label || langName(row.lang) }}</ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="visit_count" :label="t('访问')" width="80" />
        <ElTableColumn prop="user_count" :label="t('新增用户')" width="100" />
        <ElTableColumn prop="login_count" :label="t('登录')" width="80" />
        <ElTableColumn :label="t('状态')" width="90">
          <template #default="{ row }">
            <ElTag :type="row.status === 1 ? 'success' : 'info'">{{ row.status === 1 ? t('启用') : t('停用') }}</ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn :label="t('操作')" width="210" align="right">
          <template #default="{ row }">
            <ElButton link type="primary" @click="openStats(row)">{{ t('统计') }}</ElButton>
            <ElButton link type="primary" @click="openChannel(row)">{{ t('编辑') }}</ElButton>
            <ElButton link type="danger" @click="removeChannel(row)">{{ t('删除') }}</ElButton>
          </template>
        </ElTableColumn>
      </ElTable>
    </ElTabPane>

    <ElTabPane :label="t('内置广告')" name="builtins">
      <div class="pane-actions">
        <p class="admin-muted">{{ t('广告只出现在所选游戏里。展示人数和点击人数按设备去重，同一人反复打开只计一次。') }}</p>
        <ElButton type="primary" @click="openCreateBuiltin">{{ t('创建广告') }}</ElButton>
      </div>

      <ElTable v-loading="loading" :data="builtins" row-key="id" border stripe class="ads-table">
        <ElTableColumn :label="t('预览')" width="96">
          <template #default="{ row }">
            <img v-if="row.file_url && row.media_kind !== 'video'" :src="row.file_url" alt="" class="admin-thumb" />
          </template>
        </ElTableColumn>
        <ElTableColumn :label="t('广告')" min-width="180">
          <template #default="{ row }">
            <div class="admin-speaker">{{ row.title }}</div>
            <div class="admin-sub">{{ row.slot_label }} · {{ t('排序') }} {{ row.sort_order }}</div>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="game_title" :label="t('游戏')" min-width="120" />
        <ElTableColumn :label="t('语言')" width="120">
          <template #default="{ row }">
            <ElTag size="small">{{ row.lang_label || langName(row.lang) }}</ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="show_people" :label="t('展示人数')" width="100" />
        <ElTableColumn prop="click_people" :label="t('点击人数')" width="100" />
        <ElTableColumn :label="t('状态')" width="90">
          <template #default="{ row }">
            <ElTag :type="row.status === 1 ? 'success' : 'info'">{{ row.status === 1 ? t('启用') : t('停用') }}</ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn :label="t('操作')" width="140" align="right">
          <template #default="{ row }">
            <ElButton link type="primary" @click="openBuiltin(row)">{{ t('编辑') }}</ElButton>
            <ElButton link type="danger" @click="removeBuiltin(row)">{{ t('删除') }}</ElButton>
          </template>
        </ElTableColumn>
      </ElTable>
    </ElTabPane>
  </ElTabs>

  <ElDialog v-model="createOpen" :title="createdChannel ? t('来源已创建') : t('创建用户来源')" width="520px" @closed="createdChannel = null">
    <template v-if="createdChannel">
      <p class="admin-muted">
        {{ t('「{name}」的落地页已生成。样式和这部游戏的下载页一样，这条链接只属于该渠道。', { name: createdChannel.name }) }}
      </p>
      <ElForm label-position="top">
        <ElFormItem :label="t('落地页链接')">
          <ElInput :model-value="createdChannel.landing_url" readonly>
            <template #append>
              <ElButton @click="copyText(createdChannel.landing_url)">{{ t('复制') }}</ElButton>
            </template>
          </ElInput>
        </ElFormItem>
      </ElForm>
    </template>
    <ElForm v-else label-position="top" @submit.prevent="createChannel">
      <ElAlert v-if="formError" :title="formError" type="error" show-icon :closable="false" class="dialog-alert" />
      <p class="admin-muted">{{ t('创建后会生成这条渠道自己的落地页链接，页面样式与游戏下载页相同。') }}</p>
      <LangSelect v-model="channelDraft.lang" />
      <ContentLang v-model="channelCopy" :primary="channelDraft.lang" />
      <ElFormItem :label="t('名称')">
        <ElInput
          :model-value="textValue(channelDraft.name, channelDraft.texts, channelCopy, 'name', channelDraft.lang)"
          :placeholder="emptyHint(channelDraft.name, channelCopy, channelDraft.lang, t('例如 抖音投放'))"
          @update:model-value="writeText(channelDraft, channelCopy, 'name', $event, channelDraft.lang)"
        />
      </ElFormItem>
      <ElFormItem :label="t('游戏')">
        <ElSelect v-model="channelDraft.game" :placeholder="t('选择游戏')" style="width: 100%" @visible-change="onGamesOpen">
          <ElOption v-for="item in games" :key="item.id" :label="item.title" :value="item.id" />
        </ElSelect>
      </ElFormItem>
      <ElFormItem :label="t('备注')">
        <ElInput
          :model-value="textValue(channelDraft.remark, channelDraft.texts, channelCopy, 'remark', channelDraft.lang)"
          :placeholder="emptyHint(channelDraft.remark, channelCopy, channelDraft.lang)"
          @update:model-value="writeText(channelDraft, channelCopy, 'remark', $event, channelDraft.lang)"
        />
      </ElFormItem>
    </ElForm>
    <template #footer>
      <template v-if="createdChannel">
        <ElButton type="primary" @click="createOpen = false">{{ t('完成') }}</ElButton>
      </template>
      <template v-else>
        <ElButton :disabled="saving" @click="createOpen = false">{{ t('取消') }}</ElButton>
        <ElButton type="primary" :loading="saving" @click="createChannel">{{ t('创建') }}</ElButton>
      </template>
    </template>
  </ElDialog>

  <ElDialog v-model="channelOpen" :title="t('编辑用户来源')" width="520px">
    <ElForm v-if="editingChannel" label-position="top">
      <ElFormItem :label="t('落地页链接')">
        <ElInput :model-value="editingChannel.landing_url" readonly>
          <template #append>
            <ElButton @click="copyText(editingChannel.landing_url)">{{ t('复制') }}</ElButton>
          </template>
        </ElInput>
      </ElFormItem>
      <ElFormItem :label="t('渠道 ID')">
        <ElInput :model-value="editingChannel.channel_id" disabled />
      </ElFormItem>
      <LangSelect v-model="editingChannel.lang" />
      <ContentLang v-model="channelCopy" :primary="editingChannel.lang" />
      <ElFormItem :label="t('名称')">
        <ElInput
          :model-value="textValue(editingChannel.name, editingChannel.texts, channelCopy, 'name', editingChannel.lang)"
          :placeholder="emptyHint(editingChannel.name, channelCopy, editingChannel.lang)"
          @update:model-value="writeText(editingChannel, channelCopy, 'name', $event, editingChannel.lang)"
        />
      </ElFormItem>
      <ElFormItem :label="t('游戏')">
        <ElSelect v-model="editingChannel.game_id" style="width: 100%" @visible-change="onGamesOpen">
          <ElOption v-for="item in games" :key="item.id" :label="item.title" :value="item.id" />
        </ElSelect>
      </ElFormItem>
      <ElFormItem :label="t('备注')">
        <ElInput
          :model-value="textValue(editingChannel.remark, editingChannel.texts, channelCopy, 'remark', editingChannel.lang)"
          :placeholder="emptyHint(editingChannel.remark, channelCopy, editingChannel.lang)"
          @update:model-value="writeText(editingChannel, channelCopy, 'remark', $event, editingChannel.lang)"
        />
      </ElFormItem>
      <ElFormItem :label="t('状态')">
        <ElSwitch v-model="editingChannel.status" :active-value="1" :inactive-value="0" />
      </ElFormItem>
    </ElForm>
    <template #footer>
      <ElButton @click="channelOpen = false">{{ t('取消') }}</ElButton>
      <ElButton type="primary" :loading="saving" @click="saveChannel">{{ t('保存') }}</ElButton>
    </template>
  </ElDialog>

  <ElDialog v-model="statsOpen" :title="t('来源统计')" width="640px">
    <template v-if="stats">
      <p class="admin-muted">
        {{
          t('{name} · {game} · 渠道 {channel}。访问 {visits}，新增用户 {users}，登录 {logins}。', {
            name: stats.name,
            game: stats.game_title,
            channel: stats.channel_id,
            visits: stats.visit_count,
            users: stats.user_count,
            logins: stats.login_count,
          })
        }}
      </p>
      <p v-if="stats.landing_url" class="admin-muted">
        {{ t('落地页') }}
        <a class="admin-link" :href="stats.landing_url" target="_blank" rel="noopener noreferrer">{{ stats.landing_url }}</a>
      </p>
      <ElTable :data="stats.players" row-key="id" border stripe :empty-text="t('还没有归因用户')">
        <ElTableColumn prop="uid" label="UID" min-width="140" />
        <ElTableColumn prop="name" :label="t('昵称')" min-width="120" />
        <ElTableColumn prop="login_label" :label="t('登录')" width="120" />
        <ElTableColumn prop="created_at" :label="t('注册时间')" min-width="170" />
      </ElTable>
    </template>
  </ElDialog>

  <ElDialog v-model="adCreateOpen" :title="t('创建内置广告')" width="520px">
    <ElForm label-position="top" @submit.prevent="createBuiltin">
      <ElAlert v-if="adFormError" :title="adFormError" type="error" show-icon :closable="false" class="dialog-alert" />
      <LangSelect v-model="adDraft.lang" />
      <ContentLang v-model="adCopy" :primary="adDraft.lang" />
      <ElFormItem :label="t('标题')">
        <ElInput
          :model-value="textValue(adDraft.title, adDraft.texts, adCopy, 'title', adDraft.lang)"
          :placeholder="emptyHint(adDraft.title, adCopy, adDraft.lang)"
          @update:model-value="writeText(adDraft, adCopy, 'title', $event, adDraft.lang)"
        />
      </ElFormItem>
      <ElFormItem :label="t('游戏')">
        <ElSelect v-model="adDraft.game" :placeholder="t('选择游戏')" style="width: 100%" @visible-change="onGamesOpen">
          <ElOption v-for="item in games" :key="item.id" :label="item.title" :value="item.id" />
        </ElSelect>
      </ElFormItem>
      <ElFormItem :label="t('位置')">
        <ElSelect v-model="adDraft.slot" style="width: 100%">
          <ElOption v-for="item in slots" :key="item.value" :label="item.label" :value="item.value" />
        </ElSelect>
      </ElFormItem>
      <ElFormItem :label="t('素材库图片')">
        <ElSelect v-model="adDraft.image_id" clearable filterable :placeholder="t('可以不选，改填外链')" style="width: 100%" @visible-change="onImagesOpen">
          <ElOption v-for="item in images" :key="item.id" :label="item.name" :value="item.id" />
        </ElSelect>
      </ElFormItem>
      <ElFormItem :label="t('外链素材')">
        <ElInput v-model="adDraft.media_url" placeholder="https://" />
      </ElFormItem>
      <ElFormItem :label="t('点击地址')">
        <ElInput v-model="adDraft.link_url" placeholder="https://" />
      </ElFormItem>
      <ElFormItem :label="t('排序')">
        <ElInputNumber v-model="adDraft.sort_order" :min="0" />
      </ElFormItem>
      <ElFormItem :label="t('状态')">
        <ElSwitch v-model="adDraft.status" :active-value="1" :inactive-value="0" />
      </ElFormItem>
    </ElForm>
    <template #footer>
      <ElButton :disabled="saving" @click="adCreateOpen = false">{{ t('取消') }}</ElButton>
      <ElButton type="primary" :loading="saving" @click="createBuiltin">{{ t('创建') }}</ElButton>
    </template>
  </ElDialog>

  <ElDialog v-model="adOpen" :title="t('编辑内置广告')" width="520px">
    <ElForm v-if="editingAd" label-position="top">
      <LangSelect v-model="editingAd.lang" />
      <ContentLang v-model="adCopy" :primary="editingAd.lang" />
      <ElFormItem :label="t('标题')">
        <ElInput
          :model-value="textValue(editingAd.title, editingAd.texts, adCopy, 'title', editingAd.lang)"
          :placeholder="emptyHint(editingAd.title, adCopy, editingAd.lang)"
          @update:model-value="writeText(editingAd, adCopy, 'title', $event, editingAd.lang)"
        />
      </ElFormItem>
      <ElFormItem :label="t('游戏')">
        <ElSelect v-model="editingAd.game_id" style="width: 100%" @visible-change="onGamesOpen">
          <ElOption v-for="item in games" :key="item.id" :label="item.title" :value="item.id" />
        </ElSelect>
      </ElFormItem>
      <ElFormItem :label="t('位置')">
        <ElSelect v-model="editingAd.slot" style="width: 100%">
          <ElOption v-for="item in slots" :key="item.value" :label="item.label" :value="item.value" />
        </ElSelect>
      </ElFormItem>
      <ElFormItem :label="t('素材库图片')">
        <ElSelect v-model="editingAd.image_id" clearable filterable :placeholder="t('可以不选，改填外链')" style="width: 100%" @visible-change="onImagesOpen">
          <ElOption v-for="item in images" :key="item.id" :label="item.name" :value="item.id" />
        </ElSelect>
      </ElFormItem>
      <ElFormItem :label="t('外链素材')"><ElInput v-model="editingAd.media_url" placeholder="https://" /></ElFormItem>
      <ElFormItem :label="t('点击地址')"><ElInput v-model="editingAd.link_url" placeholder="https://" /></ElFormItem>
      <ElFormItem :label="t('排序')"><ElInputNumber v-model="editingAd.sort_order" :min="0" /></ElFormItem>
      <ElFormItem :label="t('状态')">
        <ElSwitch v-model="editingAd.status" :active-value="1" :inactive-value="0" />
      </ElFormItem>
    </ElForm>
    <template #footer>
      <ElButton @click="adOpen = false">{{ t('取消') }}</ElButton>
      <ElButton type="primary" :loading="saving" @click="saveBuiltin">{{ t('保存') }}</ElButton>
    </template>
  </ElDialog>
</template>

<script lang="ts" setup>
import { t } from '../../i18n'
import { computed, onMounted, reactive, ref } from 'vue'
import LangSelect from '../../components/LangSelect.vue'
import { Asset, Game, isAuthError, listAll, request } from '../../services/otome/api'
import { confirmDelete, notify } from '../../utils/feedback'
import ContentLang from '../../components/ContentLang.vue'
import { cloneTexts, emptyHint, textValue, writeText, type Texts } from '../../utils/contentLang'
import { langName } from '../../utils/langs'

type Channel = {
  id: number
  channel_id: string
  name: string
  game_id: number
  game_title: string
  lang: string
  lang_label?: string
  remark: string
  texts?: Texts
  status: number
  visit_count: number
  user_count: number
  login_count: number
  query: string
  landing_url: string
}
type ChannelStats = Channel & {
  players: { id: number; uid: string; name: string; login_label: string; created_at: string }[]
}
type Builtin = {
  id: number
  game_id: number
  game_title: string
  lang: string
  lang_label?: string
  title: string
  texts?: Texts
  slot: string
  slot_label: string
  image_id: number | null
  media_url: string
  file_url: string
  media_kind: string
  link_url: string
  sort_order: number
  status: number
  show_people: number
  click_people: number
}

const slots = computed(() => [
  { value: 'loading', label: t('开场') },
  { value: 'banner', label: t('横幅') },
  { value: 'popup', label: t('弹窗') },
])
const tab = ref('channels')
const games = ref<Game[]>([])
const images = ref<Asset[]>([])
const channels = ref<Channel[]>([])
const builtins = ref<Builtin[]>([])
const gameId = ref<number | null>(null)
const lang = ref('')
const dateRange = ref<[string, string] | null>(null)
const rangeShortcuts = computed(() => [
  { text: t('近7天'), value: () => [shiftDays(-6), new Date()] },
  { text: t('近14天'), value: () => [shiftDays(-13), new Date()] },
  { text: t('近30天'), value: () => [shiftDays(-29), new Date()] },
])

function shiftDays(days: number) {
  const next = new Date()
  next.setDate(next.getDate() + days)
  return next
}

function formatDay(value: Date) {
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${value.getFullYear()}-${month}-${day}`
}

function disableFuture(value: Date) {
  const end = new Date()
  end.setHours(23, 59, 59, 999)
  return value.getTime() > end.getTime()
}

function clampRange(value: [string, string] | null): [string, string] | null {
  if (!value || !value[0] || !value[1]) return null
  let [start, end] = value[0] <= value[1] ? [value[0], value[1]] : [value[1], value[0]]
  const today = formatDay(new Date())
  if (end > today) end = today
  if (start > end) start = end
  return [start, end]
}

function onDateRange(value: [string, string] | null) {
  dateRange.value = clampRange(value)
  load()
}

function filterQuery() {
  const query = new URLSearchParams()
  if (gameId.value) query.set('game', String(gameId.value))
  if (lang.value) query.set('lang', lang.value)
  if (dateRange.value?.[0]) query.set('date_from', dateRange.value[0])
  if (dateRange.value?.[1]) query.set('date_to', dateRange.value[1])
  const text = query.toString()
  return text ? `?${text}` : ''
}
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const channelOpen = ref(false)
const createOpen = ref(false)
const adOpen = ref(false)
const adCreateOpen = ref(false)
const statsOpen = ref(false)
const editingChannel = ref<Channel | null>(null)
const createdChannel = ref<Channel | null>(null)
const editingAd = ref<Builtin | null>(null)
const stats = ref<ChannelStats | null>(null)
const formError = ref('')
const adFormError = ref('')
const channelCopy = ref('zh-Hans')
const adCopy = ref('zh-Hans')
const channelDraft = reactive({ name: '', lang: 'zh-Hans', texts: {} as Texts, game: null as number | null, remark: '' })
const adDraft = reactive({
  title: '',
  lang: 'zh-Hans',
  texts: {} as Texts,
  game: null as number | null,
  slot: 'loading',
  image_id: null as number | null,
  media_url: '',
  link_url: '',
  sort_order: 0,
  status: 1,
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const query = filterQuery()
    const [channelRes, adRes] = await Promise.all([
      request(`/admin/ads/channels/${query}`),
      request(`/admin/ads/builtins/${query}`),
    ])
    channels.value = channelRes.results || []
    builtins.value = adRes.results || []
  } catch (err) {
    if (!isAuthError(err)) {
      error.value = err instanceof Error ? err.message : t('加载失败')
    }
  } finally {
    loading.value = false
  }
}

function openCreate() {
  channelDraft.name = ''
  channelDraft.texts = {}
  channelDraft.lang = lang.value || 'zh-Hans'
  channelCopy.value = channelDraft.lang
  channelDraft.remark = ''
  channelDraft.game = gameId.value
  createdChannel.value = null
  formError.value = ''
  createOpen.value = true
}

async function createChannel() {
  if (!channelDraft.name.trim() || !channelDraft.game) {
    formError.value = t('请填写来源名称并选择游戏')
    return
  }
  saving.value = true
  formError.value = ''
  try {
    const data = await request('/admin/ads/channels/', {
      method: 'POST',
      body: JSON.stringify({
        name: channelDraft.name.trim(),
        lang: channelDraft.lang || 'zh-Hans',
        texts: channelDraft.texts,
        game: channelDraft.game,
        remark: channelDraft.remark.trim(),
      }),
    })
    createdChannel.value = data.results || null
    notify(t('来源已创建'))
    await load()
  } catch (err) {
    formError.value = err instanceof Error ? err.message : t('创建失败')
  } finally {
    saving.value = false
  }
}

function openChannel(row: Channel) {
  editingChannel.value = { ...row, texts: cloneTexts(row.texts) }
  channelCopy.value = row.lang || 'zh-Hans'
  channelOpen.value = true
}

async function saveChannel() {
  const row = editingChannel.value
  if (!row) return
  saving.value = true
  error.value = ''
  try {
    await request(`/admin/ads/channels/${row.id}/`, {
      method: 'PATCH',
      body: JSON.stringify({
        name: row.name,
        lang: row.lang || 'zh-Hans',
        texts: row.texts || {},
        game: row.game_id,
        remark: row.remark,
        status: row.status,
      }),
    })
    channelOpen.value = false
    notify(t('来源已保存'))
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : t('保存失败')
  } finally {
    saving.value = false
  }
}

async function removeChannel(row: Channel) {
  if (!(await confirmDelete(t('删除来源「{name}」？已归因的玩家仍保留记录。', { name: row.name })))) return
  try {
    await request(`/admin/ads/channels/${row.id}/`, { method: 'DELETE' })
    notify(t('来源已删除'))
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : t('删除失败')
  }
}

async function openStats(row: Channel) {
  stats.value = null
  statsOpen.value = true
  try {
    const data = await request(`/admin/ads/channels/${row.id}/${filterQuery()}`)
    stats.value = data.results
  } catch (err) {
    error.value = err instanceof Error ? err.message : t('统计加载失败')
    statsOpen.value = false
  }
}

function openCreateBuiltin() {
  adDraft.title = ''
  adDraft.texts = {}
  adDraft.lang = lang.value || 'zh-Hans'
  adCopy.value = adDraft.lang
  adDraft.game = gameId.value
  adDraft.slot = 'loading'
  adDraft.image_id = null
  adDraft.media_url = ''
  adDraft.link_url = ''
  adDraft.sort_order = 0
  adDraft.status = 1
  adFormError.value = ''
  adCreateOpen.value = true
}

async function createBuiltin() {
  if (!adDraft.title.trim() || !adDraft.game) {
    adFormError.value = t('请填写广告标题并选择游戏')
    return
  }
  saving.value = true
  adFormError.value = ''
  try {
    await request('/admin/ads/builtins/', {
      method: 'POST',
      body: JSON.stringify({
        title: adDraft.title.trim(),
        lang: adDraft.lang || 'zh-Hans',
        texts: adDraft.texts,
        game: adDraft.game,
        slot: adDraft.slot,
        image: adDraft.image_id,
        media_url: adDraft.media_url.trim(),
        link_url: adDraft.link_url.trim(),
        sort_order: adDraft.sort_order,
        status: adDraft.status,
      }),
    })
    adCreateOpen.value = false
    notify(t('广告已创建'))
    await load()
  } catch (err) {
    adFormError.value = err instanceof Error ? err.message : t('创建失败')
  } finally {
    saving.value = false
  }
}

function openBuiltin(row: Builtin) {
  editingAd.value = { ...row, texts: cloneTexts(row.texts), image_id: row.image_id }
  adCopy.value = row.lang || 'zh-Hans'
  adOpen.value = true
}

async function saveBuiltin() {
  const row = editingAd.value
  if (!row) return
  saving.value = true
  error.value = ''
  try {
    await request(`/admin/ads/builtins/${row.id}/`, {
      method: 'PATCH',
      body: JSON.stringify({
        title: row.title,
        lang: row.lang || 'zh-Hans',
        texts: row.texts || {},
        game: row.game_id,
        slot: row.slot,
        image: row.image_id,
        media_url: row.media_url,
        link_url: row.link_url,
        sort_order: row.sort_order,
        status: row.status,
      }),
    })
    adOpen.value = false
    notify(t('广告已保存'))
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : t('保存失败')
  } finally {
    saving.value = false
  }
}

async function removeBuiltin(row: Builtin) {
  if (!(await confirmDelete(t('删除广告「{title}」？', { title: row.title })))) return
  try {
    await request(`/admin/ads/builtins/${row.id}/`, { method: 'DELETE' })
    notify(t('广告已删除'))
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : t('删除失败')
  }
}

async function copyText(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    notify(t('已复制 {text}', { text }))
  } catch {
    notify(t('复制失败，请手动选择渠道 ID'), 'warning')
  }
}

const gamesReady = ref(false)
const imagesReady = ref(false)
let gamesTask: Promise<void> | null = null
let imagesTask: Promise<void> | null = null

function ensureGames() {
  if (gamesReady.value) return Promise.resolve()
  if (!gamesTask) {
    gamesTask = listAll<Game>('/games/', { brief: 1 })
      .then((items) => {
        games.value = items
        gamesReady.value = true
      })
      .catch((err) => {
        gamesTask = null
        throw err
      })
  }
  return gamesTask
}

function ensureImages() {
  if (imagesReady.value) return Promise.resolve()
  if (!imagesTask) {
    imagesTask = listAll<Asset>('/assets/', { asset_type: 'image', brief: 1 })
      .then((items) => {
        images.value = items
        imagesReady.value = true
      })
      .catch((err) => {
        imagesTask = null
        throw err
      })
  }
  return imagesTask
}

function onPickerOpen(open: boolean, loadPicker: () => Promise<void>) {
  if (!open) return
  loadPicker().catch((err) => {
    error.value = err instanceof Error ? err.message : t('加载失败')
  })
}

function onGamesOpen(open: boolean) {
  onPickerOpen(open, ensureGames)
}

function onImagesOpen(open: boolean) {
  onPickerOpen(open, ensureImages)
}

onMounted(() => {
  load()
})
</script>

<style scoped>
.ads-tabs {
  background: transparent;
}

.ads-table {
  margin-top: 0;
}

.pane-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.pane-actions .admin-muted {
  margin: 0;
}

.landing-link {
  display: inline-block;
  max-width: 100%;
  overflow-wrap: anywhere;
  font-weight: 600;
}

.dialog-alert {
  margin-bottom: 12px;
}
</style>
