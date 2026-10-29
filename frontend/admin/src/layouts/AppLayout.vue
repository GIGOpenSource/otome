<template>
  <div class="admin-shell" :class="{ 'is-collapse': collapsed, 'is-mobile': isMobile }">
    <aside class="admin-side">
      <div class="admin-logo">
        <span class="admin-logo__mark">乙</span>
        <span v-show="!collapsed || isMobile" class="admin-logo__text">{{ t('乙游后台') }}</span>
      </div>
      <ElScrollbar class="admin-menu">
        <ElMenu
          :key="activeMenu"
          :default-active="activeMenu"
          :collapse="collapsed && !isMobile"
          :collapse-transition="false"
          background-color="#001529"
          text-color="rgba(255,255,255,0.75)"
          active-text-color="#ffffff"
          router
        >
          <ElMenuItem index="/games">
            <ElIcon><Notebook /></ElIcon>
            <template #title>{{ t('游戏列表') }}</template>
          </ElMenuItem>
          <ElMenuItem index="/data">
            <ElIcon><DataLine /></ElIcon>
            <template #title>{{ t('数据列表') }}</template>
          </ElMenuItem>
          <ElMenuItem index="/frontend-users">
            <ElIcon><User /></ElIcon>
            <template #title>{{ t('用户列表') }}</template>
          </ElMenuItem>
          <ElMenuItem index="/backend-users">
            <ElIcon><Avatar /></ElIcon>
            <template #title>{{ t('后台用户') }}</template>
          </ElMenuItem>
          <ElMenuItem index="/assets">
            <ElIcon><Picture /></ElIcon>
            <template #title>{{ t('素材库') }}</template>
          </ElMenuItem>
          <ElMenuItem index="/ads">
            <ElIcon><Promotion /></ElIcon>
            <template #title>{{ t('广告') }}</template>
          </ElMenuItem>
        </ElMenu>
      </ElScrollbar>
    </aside>

    <div v-if="isMobile && !collapsed" class="admin-mask" @click="collapsed = true" />

    <div class="admin-body">
      <header class="admin-header">
        <ElIcon class="admin-fold" @click="collapsed = !collapsed">
          <Fold v-if="!collapsed" />
          <Expand v-else />
        </ElIcon>
        <ElBreadcrumb separator="/">
          <ElBreadcrumbItem v-for="(item, index) in crumbs" :key="`${item.title}-${index}`" :to="item.to">
            {{ item.title }}
          </ElBreadcrumbItem>
        </ElBreadcrumb>
        <div class="admin-header__right">
          <ElSelect :model-value="locale" class="admin-lang" @change="onLang">
            <ElOption v-for="item in LANGS" :key="item.code" :label="langName(item.code)" :value="item.code" />
          </ElSelect>
          <ElDropdown trigger="click">
            <span class="admin-user">
              <ElAvatar :size="28">管</ElAvatar>
              <span>{{ adminName }}</span>
              <ElIcon><ArrowDown /></ElIcon>
            </span>
            <template #dropdown>
              <ElDropdownMenu>
                <ElDropdownItem @click="logout">{{ t('退出登录') }}</ElDropdownItem>
              </ElDropdownMenu>
            </template>
          </ElDropdown>
        </div>
      </header>

      <div class="admin-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.path"
          type="button"
          class="admin-tab"
          :class="{ active: tab.path === route.path }"
          @click="router.push(tab.path)"
        >
          <span>{{ tab.title }}</span>
          <ElIcon v-if="tab.closable" class="admin-tab__close" @click.stop="closeTab(tab.path)"><Close /></ElIcon>
        </button>
      </div>

      <main class="admin-content">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowDown, Avatar, Close, DataLine, Expand, Fold, Notebook, Picture, Promotion, User } from '@element-plus/icons-vue'
import { clearAdminSession, getAdminName } from '../services/otome/api'
import { LANGS, locale, setLocale, t } from '../i18n'
import { langName } from '../utils/langs'

type TabItem = { path: string; title: string; closable: boolean }
type Crumb = { title: string; to?: string | { path: string } }

const TAB_KEY = 'otome-admin-tabs'
const COLLAPSE_KEY = 'otome-admin-collapse'

const storedName = getAdminName()
const adminName = computed(() => (storedName === '管理员' ? t('管理员') : storedName))
const route = useRoute()
const router = useRouter()
const isMobile = ref(window.innerWidth < 992)
const collapsed = ref(isMobile.value || localStorage.getItem(COLLAPSE_KEY) === '1')
const tabs = ref<TabItem[]>(readTabs())

const activeMenu = computed(() => {
  if (route.name === 'data') return '/data'
  if (route.name === 'frontend-users') return '/frontend-users'
  if (route.name === 'backend-users') return '/backend-users'
  if (route.name === 'assets') return '/assets'
  if (route.name === 'ads') return '/ads'
  return '/games'
})

const crumbs = computed<Crumb[]>(() => {
  if (route.name === 'data') return [{ title: t('数据列表') }]
  if (route.name === 'frontend-users') return [{ title: t('用户列表') }]
  if (route.name === 'backend-users') return [{ title: t('后台用户') }]
  if (route.name === 'assets') return [{ title: t('素材库') }]
  if (route.name === 'ads') return [{ title: t('广告') }]
  if (route.name === 'game') {
    return [{ title: t('游戏列表'), to: '/games' }, { title: t('编辑故事') }]
  }
  if (route.name === 'node') {
    return [
      { title: t('游戏列表'), to: '/games' },
      { title: t('编辑故事'), to: { path: `/games/${route.params.gameId}` } },
      { title: route.params.nodeId === 'new' ? t('新剧情') : t('编辑剧情') },
    ]
  }
  return [{ title: t('游戏列表') }]
})

function titleFor(path: string) {
  const matched = router.resolve(path)
  if (matched.name === 'game') return `${t('编辑故事')} ${matched.params.gameId}`
  if (matched.name === 'node') return matched.params.nodeId === 'new' ? t('新剧情') : `${t('编辑剧情')} ${matched.params.nodeId}`
  return t((matched.meta.title as string) || '页面')
}

function readTabs() {
  try {
    const parsed = JSON.parse(sessionStorage.getItem(TAB_KEY) || '[]')
    if (!Array.isArray(parsed)) return []
    const seen = new Set<string>()
    const items: TabItem[] = []
    parsed.forEach((item) => {
      if (!item || typeof item.path !== 'string' || typeof item.title !== 'string') return
      const raw = item.path.split('?')[0]
      const path = raw === '/otome-users' ? '/frontend-users' : raw
      if (seen.has(path)) return
      seen.add(path)
      items.push({ path, title: titleFor(path), closable: path !== '/games' })
    })
    return items
  } catch {
    return []
  }
}

function syncTab() {
  const path = route.path
  const title = titleFor(path)
  const found = tabs.value.find((item) => item.path === path)
  if (found) {
    found.title = title
    return
  }
  tabs.value.push({ path, title, closable: route.name !== 'games' })
}

function closeTab(path: string) {
  const index = tabs.value.findIndex((item) => item.path === path)
  if (index < 0 || !tabs.value[index].closable) return
  const closingActive = route.path === path
  tabs.value.splice(index, 1)
  if (!closingActive) return
  const next = tabs.value[index] || tabs.value[index - 1]
  router.push(next?.path || '/games')
}

function refreshTabTitles() {
  tabs.value.forEach((tab) => {
    tab.title = titleFor(tab.path)
  })
  document.title = `${titleFor(route.path)} · ${t('乙游后台')}`
}

function onLang(code: string) {
  setLocale(String(code))
  refreshTabTitles()
}

function logout() {
  clearAdminSession()
  tabs.value = []
  sessionStorage.removeItem(TAB_KEY)
  router.push({ name: 'login' })
}

function onResize() {
  const mobile = window.innerWidth < 992
  if (mobile === isMobile.value) return
  isMobile.value = mobile
  collapsed.value = mobile || localStorage.getItem(COLLAPSE_KEY) === '1'
}

watch(
  tabs,
  (value) => sessionStorage.setItem(TAB_KEY, JSON.stringify(value)),
  { deep: true },
)

watch(locale, refreshTabTitles)

watch(collapsed, (value) => {
  if (!isMobile.value) localStorage.setItem(COLLAPSE_KEY, value ? '1' : '0')
})

watch(
  () => route.path,
  () => {
    syncTab()
    if (isMobile.value) collapsed.value = true
  },
  { immediate: true },
)

onMounted(() => window.addEventListener('resize', onResize))
onBeforeUnmount(() => window.removeEventListener('resize', onResize))
</script>

<style lang="scss" scoped>
.admin-shell {
  display: flex;
  width: 100%;
  max-width: 100%;
  height: 100vh;
  height: 100dvh;
  overflow: hidden;
  background: #f0f2f5;
}

.admin-side {
  display: flex;
  flex-direction: column;
  width: 210px;
  height: 100vh;
  flex-shrink: 0;
  background: #001529;
  transition: width 0.2s;
}

.admin-shell.is-collapse:not(.is-mobile) .admin-side {
  width: 64px;
}

.admin-shell.is-collapse:not(.is-mobile) .admin-logo {
  justify-content: center;
  padding: 0;
}

.admin-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 48px;
  padding: 0 16px;
  overflow: hidden;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  white-space: nowrap;
}

.admin-logo__mark {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  flex-shrink: 0;
  border-radius: 6px;
  background: #1677ff;
  font-size: 16px;
}

.admin-menu {
  flex: 1;
  min-height: 0;
}

.admin-menu :deep(.el-menu) {
  border-right: none;
}

.admin-menu :deep(.el-menu-item) {
  height: 44px;
  line-height: 44px;
}

.admin-menu :deep(.el-menu-item.is-active) {
  background: #1677ff !important;
}

.admin-menu :deep(.el-menu-item:hover) {
  background: rgba(255, 255, 255, 0.08) !important;
}

.admin-menu :deep(.el-menu-item.is-active:hover) {
  background: #1677ff !important;
}

.admin-mask {
  position: fixed;
  inset: 0;
  z-index: 19;
  background: rgba(0, 0, 0, 0.45);
}

.admin-body {
  display: flex;
  flex: 1 1 0;
  flex-direction: column;
  width: 0;
  min-width: 0;
  max-width: 100%;
}

.admin-header {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  height: 48px;
  padding: 0 16px;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  z-index: 10;
}

.admin-header :deep(.el-breadcrumb) {
  min-width: 0;
  overflow: hidden;
}

.admin-fold {
  font-size: 18px;
  cursor: pointer;
}

.admin-header__right {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: auto;
}

.admin-lang {
  width: 148px;
}

.admin-user {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #303133;
  cursor: pointer;
  outline: none;
}

.admin-tabs {
  display: flex;
  align-items: flex-end;
  gap: 6px;
  height: 40px;
  padding: 0 12px;
  overflow-x: auto;
  background: #fff;
  border-top: 1px solid #f0f0f0;
}

.admin-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 32px;
  padding: 0 12px;
  border: 1px solid #e4e7ed;
  border-bottom: none;
  border-radius: 4px 4px 0 0;
  background: #fafafa;
  color: #606266;
  font-size: 13px;
  white-space: nowrap;
  cursor: pointer;
}

.admin-tab.active {
  position: relative;
  top: 1px;
  background: #fff;
  color: #1677ff;
}

.admin-tab__close {
  font-size: 12px;
}

.admin-tab__close:hover {
  color: #f56c6c;
}

.admin-content {
  flex: 1 1 0;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  min-height: 0;
  padding: 16px;
  overflow: auto;
  box-sizing: border-box;
}

@media (max-width: 991px) {
  .admin-header {
    height: auto;
    min-height: 48px;
    padding: 8px 12px;
    flex-wrap: wrap;
  }

  .admin-lang {
    width: 120px;
  }

  .admin-content {
    padding: 12px;
  }

  .admin-side {
    position: fixed;
    z-index: 20;
    top: 0;
    left: 0;
    box-shadow: 2px 0 8px rgba(0, 0, 0, 0.2);
  }

  .admin-shell.is-mobile.is-collapse .admin-side {
    width: 0;
    overflow: hidden;
  }
}
</style>
