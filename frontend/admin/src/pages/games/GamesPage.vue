<template>
  <ElAlert v-if="error" class="admin-card" :title="error" type="error" show-icon closable @close="error = ''" />

  <ElDialog v-model="createOpen" :title="t('新建故事')" width="520px" :close-on-click-modal="!creating">
    <ElForm label-position="top" @submit.prevent="createGame">
      <LangSelect v-model="draft.lang" />
      <ContentLang v-model="copyLang" :primary="draft.lang" />
      <ElFormItem :label="t('标题')">
        <ElInput
          :model-value="textValue(draft.title, draft.texts, copyLang, 'title', draft.lang)"
          :placeholder="emptyHint(draft.title, copyLang, draft.lang, t('新故事的名字'))"
          clearable
          @update:model-value="writeText(draft, copyLang, 'title', $event, draft.lang)"
          @clear="writeText(draft, copyLang, 'title', '', draft.lang)"
        />
      </ElFormItem>
      <ElFormItem :label="t('副标题')">
        <ElInput
          :model-value="textValue(draft.subtitle, draft.texts, copyLang, 'subtitle', draft.lang)"
          :placeholder="emptyHint(draft.subtitle, copyLang, draft.lang)"
          clearable
          @update:model-value="writeText(draft, copyLang, 'subtitle', $event, draft.lang)"
          @clear="writeText(draft, copyLang, 'subtitle', '', draft.lang)"
        />
      </ElFormItem>
      <ElAlert v-if="formError" :title="formError" type="error" show-icon :closable="false" />
    </ElForm>
    <template #footer>
      <ElButton :disabled="creating" @click="createOpen = false">{{ t('取消') }}</ElButton>
      <ElButton type="primary" :loading="creating" @click="createGame">{{ t('创建') }}</ElButton>
    </template>
  </ElDialog>

  <ElCard class="admin-card" shadow="never">
    <ElForm :inline="true" @submit.prevent="reload">
      <LangSelect v-model="lang" filter />
      <ElFormItem>
        <ElButton type="primary" native-type="submit">{{ t('筛选') }}</ElButton>
        <ElButton @click="openCreate">{{ t('新建故事') }}</ElButton>
      </ElFormItem>
    </ElForm>
  </ElCard>

  <ElCard class="admin-card" shadow="never">
      <ElTable v-loading="loading" :data="games" row-key="id" border stripe flexible style="width: 100%">
      <ElTableColumn :label="t('故事')" min-width="220">
        <template #default="{ row }">
          <RouterLink class="admin-link" :to="{ name: 'game', params: { gameId: row.id } }">{{ row.title }}</RouterLink>
          <div class="admin-sub">{{ row.subtitle }}</div>
        </template>
      </ElTableColumn>
      <ElTableColumn :label="t('语言')" width="120">
        <template #default="{ row }">
          <ElTag size="small">{{ langName(row.lang) }}</ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn :label="t('状态')" width="110">
        <template #default="{ row }">
          <ElTag :type="row.status === 1 ? 'success' : 'warning'">{{ row.status === 1 ? t('已发布') : t('草稿') }}</ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn :label="t('进入游戏')" min-width="220">
        <template #default="{ row }">
          <template v-if="row.play_url">
            <a class="admin-link admin-ellipsis" :href="row.play_url" target="_blank" rel="noopener noreferrer">{{ row.play_url }}</a>
            <div>
              <ElButton link type="primary" @click="copyLink(row.play_url)">{{ t('复制') }}</ElButton>
            </div>
          </template>
          <span v-else class="admin-sub">{{ t('未设置') }}</span>
        </template>
      </ElTableColumn>
      <ElTableColumn :label="t('落地页')" min-width="220">
        <template #default="{ row }">
          <template v-if="row.landing_page_url">
            <a class="admin-link admin-ellipsis" :href="row.landing_page_url" target="_blank" rel="noopener noreferrer">{{
              row.landing_page_url
            }}</a>
            <div>
              <ElButton link type="primary" @click="copyLink(row.landing_page_url)">{{ t('复制') }}</ElButton>
            </div>
          </template>
          <span v-else class="admin-sub">{{ t('未设置') }}</span>
        </template>
      </ElTableColumn>
      <ElTableColumn :label="t('剧情')" width="90">
        <template #default="{ row }">{{ row.node_count || 0 }}</template>
      </ElTableColumn>
      <ElTableColumn prop="sort_order" :label="t('排序')" width="90" />
      <ElTableColumn :label="t('操作')" width="140" align="right">
        <template #default="{ row }">
          <ElButton link type="primary" @click="router.push({ name: 'game', params: { gameId: row.id } })">{{ t('编辑') }}</ElButton>
          <ElButton link type="danger" @click="removeGame(row)">{{ t('删除') }}</ElButton>
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
import { onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import ContentLang from '../../components/ContentLang.vue'
import LangSelect from '../../components/LangSelect.vue'
import { emptyHint, textValue, writeText, type Texts } from '../../utils/contentLang'
import { Game, isAuthError, list, request } from '../../services/otome/api'
import { confirmDelete, notify } from '../../utils/feedback'
import { langName } from '../../utils/langs'

const router = useRouter()
const games = ref<Game[]>([])
const loading = ref(false)
const creating = ref(false)
const createOpen = ref(false)
const error = ref('')
const formError = ref('')
const page = ref(1)
const pageSize = 20
const total = ref(0)
const lang = ref('')
const copyLang = ref('zh-Hans')
const draft = reactive({ title: '', subtitle: '', lang: 'zh-Hans', texts: {} as Texts })

async function load() {
  loading.value = true
  error.value = ''
  try {
    const gamePage = await list<Game>('/games/', { currentPage: page.value, pageSize, lang: lang.value || undefined })
    games.value = gamePage.items
    total.value = gamePage.total
  } catch (err) {
    if (!isAuthError(err)) {
      error.value = err instanceof Error ? err.message : t('加载失败')
    }
  } finally {
    loading.value = false
  }
}

function openCreate() {
  draft.title = ''
  draft.subtitle = ''
  draft.texts = {}
  draft.lang = lang.value || 'zh-Hans'
  copyLang.value = draft.lang
  formError.value = ''
  createOpen.value = true
}

async function createGame() {
  const title = draft.title.trim()
  if (!title) {
    formError.value = t('请填写故事标题')
    return
  }
  creating.value = true
  formError.value = ''
  try {
    const data = await request('/games/', {
      method: 'POST',
      body: JSON.stringify({
        title,
        subtitle: draft.subtitle.trim(),
        lang: draft.lang || 'zh-Hans',
        texts: draft.texts,
        status: 0,
      }),
    })
    notify(t('故事已创建'))
    createOpen.value = false
    router.push({ name: 'game', params: { gameId: data.results.id } })
  } catch (err) {
    formError.value = err instanceof Error ? err.message : t('创建失败')
  } finally {
    creating.value = false
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

async function removeGame(game: Game) {
  const agreed = await confirmDelete(t('确定删除「{title}」？', { title: game.title }), t('删除故事'))
  if (!agreed) return
  try {
    await request(`/games/${game.id}/`, { method: 'DELETE' })
    notify(t('已删除'))
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : t('删除失败')
  }
}

function reload() {
  if (page.value !== 1) page.value = 1
  else load()
}

watch(page, load)
onMounted(load)
</script>
