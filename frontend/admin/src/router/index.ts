import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'

import AuthLayout from '../layouts/AuthLayout.vue'
import AppLayout from '../layouts/AppLayout.vue'
import { getAdminToken } from '../services/otome/api'
import { t } from '../i18n'

const routes: Array<RouteRecordRaw> = [
  {
    name: 'admin',
    path: '/',
    component: AppLayout,
    redirect: { name: 'games' },
    children: [
      {
        name: 'games',
        path: 'games',
        component: () => import('../pages/games/GamesPage.vue'),
        meta: { title: '游戏列表' },
      },
      {
        name: 'data',
        path: 'data',
        component: () => import('../pages/data/DataPage.vue'),
        meta: { title: '数据列表' },
      },
      {
        name: 'frontend-users',
        path: 'frontend-users',
        component: () => import('../pages/otome-users/UsersPage.vue'),
        meta: { title: '用户列表', side: 'frontend' },
      },
      {
        name: 'backend-users',
        path: 'backend-users',
        component: () => import('../pages/otome-users/UsersPage.vue'),
        meta: { title: '后台用户', side: 'backend' },
      },
      {
        path: 'otome-users',
        redirect: { name: 'frontend-users' },
      },
      {
        name: 'game',
        path: 'games/:gameId',
        component: () => import('../pages/games/GamePage.vue'),
        meta: { title: '编辑故事' },
      },
      {
        name: 'node',
        path: 'games/:gameId/nodes/:nodeId',
        component: () => import('../pages/games/NodePage.vue'),
        meta: { title: '编辑剧情' },
      },
      {
        name: 'assets',
        path: 'assets',
        component: () => import('../pages/assets/AssetsPage.vue'),
        meta: { title: '素材库' },
      },
      {
        name: 'ads',
        path: 'ads',
        component: () => import('../pages/ads/AdsPage.vue'),
        meta: { title: '广告' },
      },
    ],
  },
  {
    path: '/auth',
    component: AuthLayout,
    children: [
      {
        name: 'login',
        path: 'login',
        component: () => import('../pages/auth/Login.vue'),
        meta: { title: '登录' },
      },
      {
        path: '',
        redirect: { name: 'login' },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: { name: 'games' },
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  scrollBehavior(_to, _from, savedPosition) {
    if (savedPosition) return savedPosition
    return { top: 0 }
  },
  routes,
})

router.beforeEach((to) => {
  const loggedIn = Boolean(getAdminToken())
  if (to.name !== 'login' && !loggedIn) return { name: 'login' }
  if (to.name === 'login' && loggedIn) return { name: 'games' }
})

router.afterEach((to) => {
  const title = (to.meta.title as string) || '乙游后台'
  document.title = `${t(title)} · ${t('乙游后台')}`
})

export default router
