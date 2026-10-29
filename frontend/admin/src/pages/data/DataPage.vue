<template>
  <ElAlert v-if="error" class="admin-card" :title="error" type="error" show-icon closable @close="error = ''" />

  <ElCard class="admin-card" shadow="never">
    <ElForm :inline="true" @submit.prevent="search">
      <ElFormItem :label="t('游戏')">
        <ElSelect v-model="gameId" clearable :placeholder="t('全部')" style="width: 220px" @visible-change="onGamesOpen">
          <ElOption v-for="item in gameOptions" :key="item.id" :label="item.label" :value="item.id" />
        </ElSelect>
      </ElFormItem>
      <LangSelect v-model="tableLang" filter />
      <ElFormItem>
        <ElButton type="primary" native-type="submit">{{ t('筛选') }}</ElButton>
      </ElFormItem>
    </ElForm>
  </ElCard>

  <ElTabs v-model="tab" class="admin-card data-tabs">
    <ElTabPane :label="t('表格')" name="table">
      <ElCard shadow="never">
        <p class="admin-muted">{{ t('登录、存档、解锁和游玩进度的明细。每条都带游戏标签。') }}</p>
        <ElForm :inline="true" @submit.prevent="searchTable">
          <ElFormItem :label="t('游戏')">
            <ElSelect v-model="gameId" clearable :placeholder="t('全部')" style="width: 180px" @visible-change="onGamesOpen" @change="onGameChange">
              <ElOption v-for="item in gameOptions" :key="item.id" :label="item.label" :value="item.id" />
            </ElSelect>
          </ElFormItem>
          <LangSelect v-model="tableLang" filter />
          <ElFormItem :label="t('时间')">
            <ElDatePicker
              v-model="tableRange"
              type="daterange"
              value-format="YYYY-MM-DD"
              :range-separator="t('至')"
              :start-placeholder="t('开始')"
              :end-placeholder="t('结束')"
              :disabled-date="disableFuture"
              :shortcuts="rangeShortcuts"
              unlink-panels
              style="width: 320px"
              @change="onTableRange"
            />
          </ElFormItem>
          <ElFormItem :label="t('类型')">
            <ElSelect v-model="kind" clearable :placeholder="t('全部')" style="width: 160px">
              <ElOption v-for="item in kinds" :key="item.value" :label="item.label" :value="item.value" />
            </ElSelect>
          </ElFormItem>
          <ElFormItem :label="t('搜索')">
            <ElInput v-model="keyword" :placeholder="t('UID、邮箱或内容')" clearable />
          </ElFormItem>
          <ElFormItem>
            <ElButton type="primary" native-type="submit">{{ t('筛选') }}</ElButton>
            <ElButton native-type="button" :loading="exporting" style="margin-left: 8px" @click="exportCsv">{{ t('导出 CSV') }}</ElButton>
          </ElFormItem>
        </ElForm>
        <ElTable v-loading="loading" :data="rows" row-key="id" border stripe>
          <ElTableColumn prop="created_at" :label="t('时间')" min-width="170" />
          <ElTableColumn :label="t('游戏')" min-width="120">
            <template #default="{ row }">
              <ElTag type="info">{{ row.game_title }}</ElTag>
            </template>
          </ElTableColumn>
          <ElTableColumn :label="t('语言')" width="120">
            <template #default="{ row }">
              <ElTag size="small">{{ row.lang_label || langName(row.lang) }}</ElTag>
            </template>
          </ElTableColumn>
          <ElTableColumn prop="kind_label" :label="t('类型')" width="100" />
          <ElTableColumn prop="uid" label="UID" min-width="140" show-overflow-tooltip />
          <ElTableColumn prop="title" :label="t('内容')" min-width="160" show-overflow-tooltip />
          <ElTableColumn prop="detail" :label="t('说明')" min-width="180" show-overflow-tooltip />
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
    </ElTabPane>

    <ElTabPane :label="t('图表')" name="chart">
      <ElCard v-loading="insightLoading" shadow="never">
        <div class="pane-head">
          <p class="admin-muted">
            {{ t('区间内的新注册作为 100%，后面是这些人目前进度达到该档的比例。选了渠道编号后，只统计从这条用户来源进来的玩家。') }}
          </p>
          <ElForm :inline="true" class="pane-filters chart-filters" @submit.prevent>
            <ElFormItem :label="t('游戏')">
              <ElSelect v-model="chartGameId" style="width: 180px" @change="onChartGame">
                <ElOption :value="0" :label="t('全部')" />
                <ElOption v-for="game in funnels" :key="game.id" :label="game.title" :value="game.id" />
              </ElSelect>
            </ElFormItem>
            <LangSelect v-model="chartLang" filter />
            <ElFormItem :label="t('渠道编号')">
              <ElSelect
                v-model="chartChannel"
                clearable
                filterable
                :placeholder="t('全部')"
                style="width: 220px"
                @change="onChartChannel"
              >
                <ElOption
                  v-for="item in chartChannelOptions"
                  :key="item.channel_id"
                  :label="channelLabel(item)"
                  :value="item.channel_id"
                />
              </ElSelect>
            </ElFormItem>
            <ElFormItem :label="t('日期')">
              <ElDatePicker
                v-model="chartRange"
                type="daterange"
                value-format="YYYY-MM-DD"
                :range-separator="t('至')"
                :start-placeholder="t('开始')"
                :end-placeholder="t('结束')"
                :clearable="false"
                :disabled-date="disableFuture"
                :shortcuts="rangeShortcuts"
                unlink-panels
                style="width: 320px"
                @change="onChartRange"
              />
            </ElFormItem>
          </ElForm>
        </div>
        <p v-if="!funnels.length" class="admin-muted">{{ t('还没有可统计的游戏。') }}</p>
        <section v-else-if="activeFunnel" class="funnel">
          <header class="funnel-head">
            <strong>{{ activeFunnel.title }}</strong>
            <span>{{ chartCaption }}</span>
          </header>
          <p v-if="!activeFunnel.players" class="admin-muted">{{ chartChannel ? t('这条渠道在这个区间没有新注册。') : t('这个区间没有新注册。') }}</p>
          <div v-else class="funnel-cols">
            <div v-for="step in activeFunnel.steps" :key="step.threshold" class="funnel-col">
              <span class="funnel-value">{{ step.rate }}%<br />{{ t('{count} 人', { count: step.count }) }}</span>
              <div class="funnel-track">
                <div
                  class="funnel-bar"
                  :class="{ 'is-done': step.threshold === 100 }"
                  :style="{ height: barHeight(step) }"
                />
              </div>
              <span class="funnel-label">{{ step.label }}</span>
            </div>
          </div>
        </section>
      </ElCard>
    </ElTabPane>

    <ElTabPane :label="t('留存')" name="retention">
      <ElCard v-loading="insightLoading" shadow="never">
        <div class="pane-head is-stack">
          <p class="admin-muted">{{ retentionNote }}</p>
          <ElForm :inline="true" class="pane-filters" @submit.prevent="loadInsights">
            <ElFormItem :label="t('游戏')">
              <ElSelect v-model="gameId" clearable :placeholder="t('全部')" style="width: 180px" @visible-change="onGamesOpen" @change="onGameChange">
                <ElOption v-for="item in gameOptions" :key="item.id" :label="item.label" :value="item.id" />
              </ElSelect>
            </ElFormItem>
            <LangSelect v-model="retentionLang" filter />
            <ElFormItem :label="t('日期')">
              <ElDatePicker
                v-model="retentionRange"
                type="daterange"
                value-format="YYYY-MM-DD"
                :range-separator="t('至')"
                :start-placeholder="t('开始')"
                :end-placeholder="t('结束')"
                :clearable="false"
                :disabled-date="disableFuture"
                :shortcuts="rangeShortcuts"
                unlink-panels
                style="width: 320px"
                @change="onRetentionRange"
              />
            </ElFormItem>
          </ElForm>
        </div>
        <ElTable :data="retention.rows" border stripe>
          <ElTableColumn prop="date" :label="t('日期')" width="120" fixed />
          <ElTableColumn prop="new_users" :label="t('新增')" width="80" fixed />
          <ElTableColumn
            v-for="col in retention.columns"
            :key="col.key"
            :label="col.label"
            min-width="92"
            align="center"
          >
            <template #default="{ row }">
              <div v-if="!cellOf(row, col.key).ready" class="retain-empty">{{ t('未到') }}</div>
              <div v-else-if="!row.new_users" class="retain-empty">—</div>
              <div
                v-else
                class="retain-cell"
                :style="{ background: heat(cellOf(row, col.key).rate), color: heatText(cellOf(row, col.key).rate) }"
              >
                <strong>{{ cellOf(row, col.key).rate }}%</strong>
                <span>{{ t('{count}人', { count: cellOf(row, col.key).count }) }}</span>
              </div>
            </template>
          </ElTableColumn>
        </ElTable>
      </ElCard>
    </ElTabPane>

    <ElTabPane :label="t('概览')" name="overview">
      <ElCard v-loading="insightLoading" shadow="never">
        <div class="pane-head is-stack">
          <p class="admin-muted">{{ overviewNote }}</p>
          <ElForm :inline="true" class="pane-filters" @submit.prevent="loadInsights">
            <ElFormItem :label="t('游戏')">
              <ElSelect v-model="gameId" clearable :placeholder="t('全部')" style="width: 180px" @visible-change="onGamesOpen" @change="onGameChange">
                <ElOption v-for="item in gameOptions" :key="item.id" :label="item.label" :value="item.id" />
              </ElSelect>
            </ElFormItem>
            <LangSelect v-model="overviewLang" filter />
            <ElFormItem :label="t('日期')">
              <ElDatePicker
                v-model="overviewRange"
                type="daterange"
                value-format="YYYY-MM-DD"
                :range-separator="t('至')"
                :start-placeholder="t('开始')"
                :end-placeholder="t('结束')"
                :clearable="false"
                :disabled-date="disableFuture"
                :shortcuts="rangeShortcuts"
                unlink-panels
                style="width: 320px"
                @change="onOverviewRange"
              />
            </ElFormItem>
          </ElForm>
        </div>
        <div class="stat-grid">
          <article class="stat">
            <div class="stat-label">{{ t('新增') }}</div>
            <div class="stat-value">{{ overview.new_users }}</div>
            <div class="stat-sub">{{ t('区间内新注册') }}</div>
          </article>
          <article class="stat">
            <div class="stat-label">{{ t('三日留存') }}</div>
            <div class="stat-value">{{ rateText(overview.retention_3.rate) }}</div>
            <div class="stat-sub">{{ cohortText(overview.retention_3) }}</div>
          </article>
          <article class="stat">
            <div class="stat-label">{{ t('七日留存') }}</div>
            <div class="stat-value">{{ rateText(overview.retention_7.rate) }}</div>
            <div class="stat-sub">{{ cohortText(overview.retention_7) }}</div>
          </article>
          <article class="stat">
            <div class="stat-label">{{ t('活跃') }}</div>
            <div class="stat-value">{{ overview.dau }}</div>
            <div class="stat-sub">{{ t('区间内有行为的玩家') }}</div>
          </article>
          <article class="stat">
            <div class="stat-label">{{ t('广告展示人数') }}</div>
            <div class="stat-value">{{ overview.ad_people }}</div>
            <div class="stat-sub">{{ t('区间内落地页去重访客') }}</div>
          </article>
        </div>

        <h3 class="section-title">{{ t('区间内新增的渠道来源') }}</h3>
        <p v-if="!overview.channels.length" class="admin-muted">{{ t('这个区间没有新增。') }}</p>
        <div v-else class="channel-list">
          <div v-for="item in overview.channels" :key="item.name" class="channel-row">
            <span class="channel-name">{{ item.name }}</span>
            <div class="channel-track">
              <div class="channel-bar" :style="{ width: `${item.share}%` }" />
            </div>
            <span class="channel-value">{{ t('{count} 人', { count: item.count }) }} · {{ item.share }}%</span>
          </div>
        </div>
      </ElCard>
    </ElTabPane>
  </ElTabs>
</template>

<script lang="ts" setup>
import { t } from '../../i18n'
import { computed, onMounted, ref, watch } from 'vue'
import LangSelect from '../../components/LangSelect.vue'
import { Game, downloadFile, isAuthError, list, listAll, request } from '../../services/otome/api'
import { langName } from '../../utils/langs'

type Row = {
  id: number
  created_at: string
  game_title: string
  lang?: string
  lang_label?: string
  kind_label: string
  uid: string
  title: string
  detail: string
}

type FunnelStep = {
  label: string
  threshold: number
  count: number
  rate: number
}

type Funnel = {
  id: number
  title: string
  players: number
  steps: FunnelStep[]
}

type RetainCell = {
  key: string
  count: number | null
  rate: number | null
  ready: boolean
}

type RetainRow = {
  date: string
  new_users: number
  cells: RetainCell[]
}

type Cohort = {
  date: string
  end?: string
  cohort: number
  retained: number
  rate: number | null
}

type ChannelShare = {
  name: string
  count: number
  share: number
}

type SourceChannel = {
  channel_id: string
  name: string
  game_id: number
  game_title: string
}

const kinds = computed(() => [
  { value: 'login', label: t('登录') },
  { value: 'save', label: t('存档') },
  { value: 'unlock', label: t('解锁') },
  { value: 'progress', label: t('进度') },
])
const rows = ref<Row[]>([])
const gameOptions = ref<{ id: number; label: string }[]>([])
const gameId = ref<number | null>(null)
const tableLang = ref('')
const chartLang = ref('')
const retentionLang = ref('')
const overviewLang = ref('')
const kind = ref<string | null>(null)
const keyword = ref('')
const loading = ref(false)
const exporting = ref(false)
const insightLoading = ref(false)
const error = ref('')
const page = ref(1)
const pageSize = 30
const total = ref(0)
const RETENTION_SPAN_DEFAULT = 14
const RETENTION_SPAN_MAX = 90
const tab = ref('table')
const chartGameId = ref(0)
const chartChannel = ref('')
const sourceChannels = ref<SourceChannel[]>([])
const funnels = ref<Funnel[]>([])
const retention = ref<{ columns: { key: string; label: string }[]; rows: RetainRow[] }>({ columns: [], rows: [] })
const chartRange = ref<[string, string]>(defaultRetentionRange())
const tableRange = ref<[string, string] | null>(null)
const overviewRange = ref<[string, string]>(defaultRetentionRange())
const retentionRange = ref<[string, string]>(defaultRetentionRange())
const rangeShortcuts = computed(() => [
  { text: t('近7天'), value: () => [addDays(new Date(), -6), new Date()] },
  { text: t('近14天'), value: () => [addDays(new Date(), -13), new Date()] },
  { text: t('近30天'), value: () => [addDays(new Date(), -29), new Date()] },
])
const overview = ref({
  new_users: 0,
  dau: 0,
  retention_3: emptyCohort(),
  retention_7: emptyCohort(),
  ad_people: 0,
  channels: [] as ChannelShare[],
})

const retentionNote = computed(() => {
  const [start, end] = retentionRange.value
  const scope = gameId.value
    ? t('按进入所选游戏的日期分行。')
    : t('未选游戏时，按玩家第一次进入游戏的日期分行。')
  return t('{start} 至 {end}，最多 {max} 天。{scope}当天有登录、存档、解锁或进度，就算这一天回来过。还没到的天数标成未到。', {
    start,
    end,
    max: RETENTION_SPAN_MAX,
    scope,
  })
})

const overviewNote = computed(() => {
  const [start, end] = overviewRange.value
  return t('{start} 至 {end}。三日、七日留存看的是观察日落在这个区间的人，注册后第 3 天或第 7 天有没有再来。', { start, end })
})

function formatDay(value: Date) {
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${value.getFullYear()}-${month}-${day}`
}

function todayText() {
  return formatDay(new Date())
}

function parseDay(value: string) {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, (month || 1) - 1, day || 1)
}

function addDays(value: Date, days: number) {
  const next = new Date(value)
  next.setDate(next.getDate() + days)
  return next
}

function defaultRetentionRange(): [string, string] {
  return [formatDay(addDays(new Date(), -(RETENTION_SPAN_DEFAULT - 1))), todayText()]
}

function clampRetention(value: [string, string] | null): [string, string] {
  if (!value || value.length < 2 || !value[0] || !value[1]) return defaultRetentionRange()
  let [start, end] = value[0] <= value[1] ? [value[0], value[1]] : [value[1], value[0]]
  const today = todayText()
  if (end > today) end = today
  if (start > end) start = end
  const earliest = formatDay(addDays(parseDay(end), -(RETENTION_SPAN_MAX - 1)))
  if (start < earliest) start = earliest
  return [start, end]
}

function emptyCohort(): Cohort {
  return { date: '', cohort: 0, retained: 0, rate: null }
}

function disableFuture(value: Date) {
  const end = new Date()
  end.setHours(23, 59, 59, 999)
  return value.getTime() > end.getTime()
}

const chartChannelOptions = computed(() => {
  if (!chartGameId.value) return sourceChannels.value
  return sourceChannels.value.filter((item) => item.game_id === chartGameId.value)
})

const chartCaption = computed(() => {
  const [start, end] = chartRange.value
  const people = activeFunnel.value?.players ?? 0
  const channel = chartChannel.value ? t('，渠道 {channel}', { channel: chartChannel.value }) : ''
  return t('{start} 至 {end}{channel} 注册 {people} 人', { start, end, channel, people })
})

const activeFunnel = computed(() => {
  const items = funnels.value
  if (!items.length) return null
  const picked = items.find((item) => item.id === chartGameId.value)
  if (picked) return picked
  return combineFunnels(items)
})

function combineFunnels(items: Funnel[]): Funnel {
  const players = items.reduce((sum, item) => sum + item.players, 0)
  const steps = items[0].steps.map((step, index) => {
    const count = items.reduce((sum, item) => sum + (item.steps[index]?.count || 0), 0)
    return {
      label: step.label,
      threshold: step.threshold,
      count,
      rate: players ? Math.round((count * 100) / players) : 0,
    }
  })
  return { id: 0, title: t('全部游戏'), players, steps }
}

function channelLabel(item: SourceChannel) {
  const name = item.name ? ` ${item.name}` : ''
  if (!chartGameId.value && item.game_title) return `${item.channel_id}${name} · ${item.game_title}`
  return `${item.channel_id}${name}`
}

function barHeight(step: FunnelStep) {
  if (!step.count) return '0%'
  return `${Math.max(step.rate, 4)}%`
}

function cellOf(row: RetainRow, key: string): RetainCell {
  return row.cells.find((item) => item.key === key) || { key, count: null, rate: null, ready: false }
}

function heat(rate: number | null) {
  if (rate == null) return 'transparent'
  return `rgba(22, 119, 255, ${(0.12 + (rate / 100) * 0.72).toFixed(3)})`
}

function heatText(rate: number | null) {
  return (rate || 0) >= 55 ? '#ffffff' : '#1f2329'
}

function rateText(rate: number | null) {
  return rate == null ? '—' : `${rate}%`
}

function cohortText(item: Cohort) {
  if (!item.cohort) return t('对应注册日没有新增')
  const start = (item.date || '').slice(5)
  const end = (item.end || item.date || '').slice(5)
  const when = start && end && start !== end ? t('{start} 至 {end}', { start, end }) : start
  return t('{when} 注册 {cohort} 人，回来 {retained} 人', { when, cohort: item.cohort, retained: item.retained })
}

async function loadInsights() {
  insightLoading.value = true
  try {
    const query = new URLSearchParams()
    if (gameId.value) query.set('game', String(gameId.value))
    const [chartFrom, chartTo] = chartRange.value
    if (chartFrom) query.set('date_from', chartFrom)
    if (chartTo) query.set('date_to', chartTo)
    if (chartChannel.value) query.set('channel', chartChannel.value)
    if (chartLang.value) query.set('chart_lang', chartLang.value)
    if (retentionLang.value) query.set('retention_lang', retentionLang.value)
    if (overviewLang.value) query.set('overview_lang', overviewLang.value)
    const [overviewFrom, overviewTo] = overviewRange.value
    if (overviewFrom) query.set('overview_from', overviewFrom)
    if (overviewTo) query.set('overview_to', overviewTo)
    const [retentionFrom, retentionTo] = retentionRange.value
    if (retentionFrom) query.set('retention_from', retentionFrom)
    if (retentionTo) query.set('retention_to', retentionTo)
    const data = await request(`/admin/data/insights/?${query.toString()}`)
    const body = data.results || {}
    if (body.date_from && body.date_to) chartRange.value = [body.date_from, body.date_to]
    if (body.overview_from && body.overview_to) overviewRange.value = [body.overview_from, body.overview_to]
    if (body.retention_from && body.retention_to) {
      retentionRange.value = [body.retention_from, body.retention_to]
    }
    funnels.value = body.funnels || []
    sourceChannels.value = body.source_channels || []
    retention.value = body.retention || { columns: [], rows: [] }
    const summary = body.overview || {}
    overview.value = {
      new_users: summary.new_users || 0,
      dau: summary.dau || 0,
      retention_3: summary.retention_3 || emptyCohort(),
      retention_7: summary.retention_7 || emptyCohort(),
      ad_people: summary.ad_people || 0,
      channels: summary.channels || [],
    }
  } catch (err) {
    if (!isAuthError(err)) {
      error.value = err instanceof Error ? err.message : t('统计加载失败')
    }
  } finally {
    insightLoading.value = false
  }
}

function onChartGame() {
  if (!chartChannel.value) return
  const allowed = chartChannelOptions.value.some((item) => item.channel_id === chartChannel.value)
  if (!allowed) {
    chartChannel.value = ''
    loadInsights()
  }
}

function onChartChannel() {
  loadInsights()
}

function onChartRange(value: [string, string] | null) {
  chartRange.value = clampRetention(value)
  loadInsights()
}

function onOverviewRange(value: [string, string] | null) {
  overviewRange.value = clampRetention(value)
  loadInsights()
}

function onRetentionRange(value: [string, string] | null) {
  retentionRange.value = clampRetention(value)
  loadInsights()
}

function onGameChange() {
  search()
}

function clampTableRange(value: [string, string] | null): [string, string] | null {
  if (!value || !value[0] || !value[1]) return null
  let [start, end] = value[0] <= value[1] ? [value[0], value[1]] : [value[1], value[0]]
  const today = todayText()
  if (end > today) end = today
  if (start > end) start = end
  return [start, end]
}

function onTableRange(value: [string, string] | null) {
  tableRange.value = clampTableRange(value)
  searchTable()
}

async function load() {
  loading.value = true
  try {
    const pageData = await list<Row>('/admin/data/', {
      game: gameId.value || undefined,
      lang: tableLang.value || undefined,
      kind: kind.value || undefined,
      q: keyword.value.trim() || undefined,
      date_from: tableRange.value?.[0],
      date_to: tableRange.value?.[1],
      currentPage: page.value,
      pageSize,
    })
    rows.value = pageData.items
    total.value = pageData.total
  } catch (err) {
    if (!isAuthError(err)) {
      error.value = err instanceof Error ? err.message : t('加载失败')
    }
  } finally {
    loading.value = false
  }
}

async function exportCsv() {
  exporting.value = true
  error.value = ''
  try {
    const query = new URLSearchParams()
    if (gameId.value) query.set('game', String(gameId.value))
    if (kind.value) query.set('kind', kind.value)
    if (tableLang.value) query.set('lang', tableLang.value)
    if (keyword.value.trim()) query.set('q', keyword.value.trim())
    if (tableRange.value?.[0]) query.set('date_from', tableRange.value[0])
    if (tableRange.value?.[1]) query.set('date_to', tableRange.value[1])
    const span = tableRange.value ? `${tableRange.value[0]}_${tableRange.value[1]}` : todayText()
    await downloadFile(`/admin/data/export/?${query.toString()}`, t('数据列表-{span}.csv', { span }))
  } catch (err) {
    if (!isAuthError(err)) {
      error.value = err instanceof Error ? err.message : t('导出失败')
    }
  } finally {
    exporting.value = false
  }
}

function searchTable() {
  error.value = ''
  if (page.value !== 1) page.value = 1
  else load()
}

function search() {
  error.value = ''
  loadInsights()
  searchTable()
}

const gamesReady = ref(false)
let gamesTask: Promise<void> | null = null

function ensureGames() {
  if (gamesReady.value) return Promise.resolve()
  if (!gamesTask) {
    gamesTask = listAll<Game>('/games/', { brief: 1 })
      .then((games) => {
        gameOptions.value = games.map((item) => ({ id: item.id, label: item.title }))
        gamesReady.value = true
      })
      .catch((err) => {
        gamesTask = null
        throw err
      })
  }
  return gamesTask
}

function onGamesOpen(open: boolean) {
  if (!open) return
  ensureGames().catch((err) => {
    error.value = err instanceof Error ? err.message : t('加载失败')
  })
}

onMounted(async () => {
  await Promise.all([load(), loadInsights()])
})
watch(page, load)
watch(tableLang, () => searchTable())
watch([chartLang, retentionLang, overviewLang], () => loadInsights())
watch(funnels, (items) => {
  if (chartGameId.value && !items.some((item) => item.id === chartGameId.value)) {
    chartGameId.value = 0
  }
})
</script>

<style scoped>
.data-tabs :deep(.el-tabs__header) {
  margin-bottom: 12px;
}

.pane-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.pane-head .admin-muted {
  flex: 1;
  min-width: 220px;
}

.pane-head.is-stack {
  flex-direction: column;
  align-items: flex-start;
}

.pane-head.is-stack .pane-filters {
  margin-left: 0;
}

.pane-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  margin-left: auto;
}

.data-tabs :deep(.pane-filters.el-form--inline) {
  margin-bottom: 0;
}

.pane-filters :deep(.el-form-item) {
  margin-right: 0;
  margin-bottom: 0;
}

.chart-filters {
  flex-wrap: wrap;
}

.funnel-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.funnel-head strong {
  color: #1f2329;
}

.funnel-head span,
.funnel-label,
.funnel-value {
  color: #606266;
  font-size: 13px;
}

.funnel-cols {
  display: flex;
  align-items: stretch;
  gap: 12px;
  margin-top: 16px;
  overflow-x: auto;
}

.funnel-col {
  display: flex;
  flex: 1 0 76px;
  flex-direction: column;
  align-items: center;
  min-width: 76px;
}

.funnel-track {
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  width: 100%;
  max-width: 48px;
  height: 180px;
  background: #f5f7fa;
  border-radius: 4px;
}

.funnel-bar {
  width: 100%;
  border-radius: 4px;
  background: linear-gradient(180deg, #69b1ff, #1677ff);
}

.funnel-bar.is-done {
  background: linear-gradient(180deg, #95de64, #52c41a);
}

.funnel-value,
.funnel-label {
  text-align: center;
  line-height: 1.35;
}

.funnel-value {
  margin-bottom: 8px;
}

.funnel-label {
  margin-top: 8px;
}

.retain-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin: -8px -12px;
  padding: 8px 4px;
  line-height: 1.3;
}

.retain-cell span {
  font-size: 12px;
  opacity: 0.8;
}

.retain-empty {
  color: #909399;
  font-size: 12px;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}

.stat {
  padding: 16px;
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 6px;
}

.stat-label,
.stat-sub,
.section-title {
  color: #909399;
  font-size: 13px;
}

.stat-value {
  margin: 8px 0 4px;
  color: #1f2329;
  font-size: 28px;
  font-weight: 600;
  line-height: 1.1;
}

.section-title {
  margin: 20px 0 12px;
  color: #1f2329;
  font-size: 15px;
  font-weight: 600;
}

.channel-row {
  display: grid;
  grid-template-columns: 120px minmax(0, 1fr) 120px;
  gap: 8px;
  align-items: center;
  margin-top: 10px;
}

.channel-name,
.channel-value {
  color: #606266;
  font-size: 13px;
}

.channel-value {
  text-align: right;
}

.channel-track {
  height: 12px;
  overflow: hidden;
  background: #f0f2f5;
  border-radius: 999px;
}

.channel-bar {
  height: 100%;
  background: #1677ff;
  border-radius: 999px;
}

@media (max-width: 768px) {
  .channel-row {
    grid-template-columns: 88px minmax(0, 1fr);
  }

  .channel-value {
    grid-column: 2;
    text-align: left;
  }
}
</style>
