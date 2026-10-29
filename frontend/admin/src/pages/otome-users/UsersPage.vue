<template>
  <ElAlert v-if="error" class="admin-card" :title="error" type="error" show-icon closable @close="error = ''" />

  <ElCard class="admin-card" shadow="never">
    <p class="admin-muted">{{ hint }}</p>
    <ElForm :inline="true" @submit.prevent="load">
      <ElFormItem :label="side === 'frontend' ? t('游戏标签') : t('权限范围')">
        <ElSelect v-model="gameId" clearable :placeholder="t('全部')" style="width: 220px">
          <ElOption v-for="item in games" :key="item.id" :label="item.title" :value="item.id" />
        </ElSelect>
      </ElFormItem>
      <LangSelect v-model="lang" filter />
      <ElFormItem :label="t('搜索')">
        <ElInput v-model="keyword" :placeholder="side === 'frontend' ? t('UID、昵称或邮箱') : t('账号或邮箱')" clearable />
      </ElFormItem>
      <ElFormItem>
        <ElButton type="primary" native-type="submit">{{ t('筛选') }}</ElButton>
      </ElFormItem>
    </ElForm>
  </ElCard>

  <ElCard class="admin-card" shadow="never">
    <template #header>
      <div class="admin-card-head">
        <span>{{ title }}</span>
        <ElButton v-if="side === 'backend' && canManage" type="primary" @click="openCreate">{{ t('创建用户') }}</ElButton>
      </div>
    </template>
    <ElTable v-loading="loading" :data="rows" row-key="id" border stripe>
      <ElTableColumn v-if="side === 'frontend'" label="UID" min-width="180">
        <template #default="{ row }">
          <div class="admin-speaker">{{ row.uid }}</div>
          <div class="admin-sub">{{ row.name }} {{ row.email }}</div>
        </template>
      </ElTableColumn>
      <ElTableColumn v-else :label="t('账号')" min-width="180">
        <template #default="{ row }">
          <div class="admin-speaker">{{ row.name }}</div>
          <div class="admin-sub">{{ row.email }}</div>
        </template>
      </ElTableColumn>
      <ElTableColumn v-if="side === 'frontend'" prop="login_label" :label="t('登录')" width="120" />
      <ElTableColumn :label="t('语言')" width="120">
        <template #default="{ row }">
          <ElTag size="small">{{ row.lang_label || langName(row.lang) }}</ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn v-if="side === 'frontend'" prop="created_at" :label="t('注册日期')" width="170" />
      <ElTableColumn v-else :label="t('角色')" width="120">
        <template #default="{ row }">{{ roleLabel(row.role) }}</template>
      </ElTableColumn>
      <ElTableColumn v-if="side === 'frontend'" :label="t('广告渠道')" min-width="160">
        <template #default="{ row }">
          <template v-if="row.channel_id">
            <div class="admin-speaker">{{ row.channel_name }}</div>
            <div class="admin-sub">{{ row.channel_id }}</div>
          </template>
        </template>
      </ElTableColumn>
      <ElTableColumn v-if="side === 'frontend'" :label="t('游戏标签')" min-width="220">
        <template #default="{ row }">
          <div class="admin-tags">
            <ElTag v-for="tag in row.tags" :key="tag.id" size="small">{{ tag.title }}</ElTag>
          </div>
        </template>
      </ElTableColumn>
      <ElTableColumn v-if="side === 'frontend'" :label="t('游戏进度')" min-width="220">
        <template #default="{ row }">
          <div v-for="item in row.progress" :key="item.id" class="user-progress">
            <div class="admin-speaker">{{ item.title }}</div>
            <div v-if="item.percent == null" class="admin-sub">{{ t('未开始') }}</div>
            <template v-else>
              <ElProgress :percentage="item.percent" :stroke-width="8" />
              <div v-if="item.node_key" class="admin-sub">{{ item.node_key }}</div>
            </template>
          </div>
          <span v-if="!row.progress?.length" class="admin-muted">{{ t('未开始') }}</span>
        </template>
      </ElTableColumn>
      <ElTableColumn v-else :label="t('权限范围')" min-width="240">
        <template #default="{ row }">
          <span v-if="row.role === 'super_admin'">{{ t('全部游戏') }}</span>
          <div v-else class="admin-tags">
            <ElTag v-for="tag in row.tags" :key="tag.id" size="small">{{ tag.title }}</ElTag>
            <span v-if="!row.tags.length" class="admin-muted">{{ t('仅自己创建的游戏') }}</span>
          </div>
        </template>
      </ElTableColumn>
      <ElTableColumn v-if="side === 'backend' && canManage" :label="t('操作')" width="90" fixed="right">
        <template #default="{ row }">
          <ElButton v-if="canEdit(row)" link type="primary" @click="openEdit(row)">{{ t('编辑') }}</ElButton>
        </template>
      </ElTableColumn>
    </ElTable>
  </ElCard>

  <ElDialog v-model="editorOpen" :title="form.id ? t('编辑权限') : t('创建用户')" width="520px">
    <ElForm label-width="88px" @submit.prevent="saveStaff">
      <ElFormItem :label="t('用户名')">
        <ElInput v-model="form.username" :disabled="!!form.id" maxlength="20" :placeholder="t('2 到 20 个字符')" />
      </ElFormItem>
      <ElFormItem :label="t('邮箱')">
        <ElInput v-model="form.email" :disabled="!!form.id" :placeholder="t('登录不用邮箱，用于区分账号')" />
      </ElFormItem>
      <ElFormItem v-if="!form.id" :label="t('密码')">
        <ElInput v-model="form.password" type="password" show-password :placeholder="t('至少 6 位')" />
      </ElFormItem>
      <ElFormItem :label="t('角色')">
        <ElSelect v-model="form.role" style="width: 100%">
          <ElOption v-for="item in assignableRoles" :key="item.value" :label="item.label" :value="item.value" />
        </ElSelect>
      </ElFormItem>
      <LangSelect v-model="form.lang" />
      <ElFormItem v-if="form.role !== 'super_admin'" :label="t('权限范围')">
        <ElSelect
          v-model="form.game_ids"
          multiple
          filterable
          :placeholder="t('不选则只能管理自己以后创建的游戏')"
          style="width: 100%"
        >
          <ElOption v-for="item in games" :key="item.id" :label="item.title" :value="item.id" />
        </ElSelect>
      </ElFormItem>
    </ElForm>
    <template #footer>
      <ElButton @click="editorOpen = false">{{ t('取消') }}</ElButton>
      <ElButton type="primary" :loading="saving" @click="saveStaff">{{ t('保存') }}</ElButton>
    </template>
  </ElDialog>
</template>

<script lang="ts" setup>
import { t } from '../../i18n'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import LangSelect from '../../components/LangSelect.vue'
import { isAuthError, request } from '../../services/otome/api'
import { notify } from '../../utils/feedback'
import { langName } from '../../utils/langs'

type Tag = { id: number; title: string }
type Progress = { id: number; title: string; percent: number | null; node_key?: string }
type Person = {
  id: number
  side: 'frontend' | 'backend'
  uid?: string
  name: string
  email: string
  role?: string
  login_label?: string
  lang?: string
  lang_label?: string
  channel_id?: string
  channel_name?: string
  created_at?: string
  game_ids: number[]
  tags: Tag[]
  progress?: Progress[]
}

const route = useRoute()
const side = computed(() => (route.meta.side === 'backend' ? 'backend' : 'frontend'))
const roleOptions = computed(() => [
  { value: 'operator', label: t('运营') },
  { value: 'admin', label: t('管理员') },
  { value: 'super_admin', label: t('超级管理员') },
])
const title = computed(() => (side.value === 'frontend' ? t('用户列表') : t('后台用户')))
const hint = computed(() =>
  side.value === 'frontend'
    ? t('设备号或 Google 登录的玩家。游戏标签在进入游戏后自动加上，这里只展示。')
    : t('超级管理员用来管理管理员，并能管理全部游戏。管理员只能创建运营，并指定对方能管理哪些游戏。'),
)
const rows = ref<Person[]>([])
const games = ref<Tag[]>([])
const gameId = ref<number | null>(null)
const lang = ref('')
const keyword = ref('')
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const canManage = ref(false)
const viewerRole = ref('')
const viewerId = ref<number | null>(null)
const assignableRoles = computed(() => (
  viewerRole.value === 'super_admin'
    ? roleOptions.value
    : roleOptions.value.filter((item) => item.value === 'operator')
))
const editorOpen = ref(false)
const form = reactive({
  id: 0,
  username: '',
  email: '',
  password: '',
  role: 'operator',
  lang: 'zh-Hans',
  game_ids: [] as number[],
})

function roleLabel(role?: string) {
  return roleOptions.value.find((item) => item.value === role)?.label || role || ''
}

function canEdit(row: Person) {
  if (row.id === viewerId.value) return false
  if (viewerRole.value === 'super_admin') return true
  return row.role === 'operator'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const query = new URLSearchParams({ side: side.value })
    if (gameId.value) query.set('game', String(gameId.value))
    if (lang.value) query.set('lang', lang.value)
    if (keyword.value.trim()) query.set('q', keyword.value.trim())
    const data = await request(`/admin/users/?${query.toString()}`)
    const body = data.results || {}
    rows.value = (side.value === 'frontend' ? body.frontend : body.backend) || []
    games.value = body.games || []
    canManage.value = !!body.can_manage
    viewerRole.value = body.viewer_role || ''
    viewerId.value = body.viewer_id ?? null
  } catch (err) {
    if (!isAuthError(err)) {
      error.value = err instanceof Error ? err.message : t('加载失败')
    }
  } finally {
    loading.value = false
  }
}

function openCreate() {
  form.id = 0
  form.username = ''
  form.email = ''
  form.password = ''
  form.role = 'operator'
  form.lang = 'zh-Hans'
  form.game_ids = []
  editorOpen.value = true
}

function openEdit(person: Person) {
  form.id = person.id
  form.username = person.name
  form.email = person.email
  form.password = ''
  form.role = person.role || 'operator'
  form.lang = person.lang || 'zh-Hans'
  form.game_ids = [...person.game_ids]
  editorOpen.value = true
}

async function saveStaff() {
  error.value = ''
  const gameIds = form.role === 'super_admin' ? [] : form.game_ids
  saving.value = true
  try {
    if (!form.id) {
      await request('/admin/users/', {
        method: 'POST',
        body: JSON.stringify({
          username: form.username.trim(),
          email: form.email.trim(),
          password: form.password,
          role: form.role,
          lang: form.lang || 'zh-Hans',
          game_ids: gameIds,
        }),
      })
      notify(t('用户已创建'))
    } else {
      await request('/admin/users/tags/', {
        method: 'POST',
        body: JSON.stringify({
          side: 'backend',
          owner_id: form.id,
          role: form.role,
          lang: form.lang || 'zh-Hans',
          game_ids: gameIds,
        }),
      })
      notify(t('权限已保存'))
    }
    editorOpen.value = false
    await load()
  } catch (err) {
    const message = err instanceof Error ? err.message : t('保存失败')
    error.value = message
    notify(message, 'error')
  } finally {
    saving.value = false
  }
}

watch(side, () => {
  gameId.value = null
  lang.value = ''
  keyword.value = ''
  rows.value = []
  load()
})

onMounted(load)
</script>

<style scoped>
.user-progress + .user-progress {
  margin-top: 10px;
}

.user-progress :deep(.el-progress__text) {
  min-width: 36px;
  font-size: 12px !important;
}
</style>
