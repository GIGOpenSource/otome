<template>
  <div class="login-card">
    <h2>{{ t('登录') }}</h2>
    <p class="admin-muted">{{ t('用用户名和密码进入后台。三部游戏都在这一套后台里管理。') }}</p>
    <ElForm ref="formRef" :model="form" :rules="rules" @submit.prevent="submit">
      <ElFormItem prop="username">
        <ElInput
          v-model="form.username"
          size="large"
          :placeholder="t('用户名')"
          autocomplete="username"
          @keyup.enter="submit"
        >
          <template #prefix>
            <ElIcon><User /></ElIcon>
          </template>
        </ElInput>
      </ElFormItem>
      <ElFormItem prop="password">
        <ElInput
          v-model="form.password"
          size="large"
          type="password"
          show-password
          :placeholder="t('密码')"
          autocomplete="current-password"
          @keyup.enter="submit"
        >
          <template #prefix>
            <ElIcon><Lock /></ElIcon>
          </template>
        </ElInput>
      </ElFormItem>
      <ElAlert v-if="error" class="login-alert" :title="error" type="error" show-icon :closable="false" />
      <ElButton class="login-submit" type="primary" size="large" native-type="submit" :loading="loading">
        {{ t('登录') }}
      </ElButton>
    </ElForm>
  </div>
</template>

<script lang="ts" setup>
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import type { FormInstance, FormRules } from 'element-plus'
import { Lock, User } from '@element-plus/icons-vue'
import { clearAdminSession, loginAdmin } from '../../services/otome/api'
import { t } from '../../i18n'

const router = useRouter()
const formRef = ref<FormInstance>()
const form = reactive({ username: '', password: '' })
const error = ref('')
const loading = ref(false)
const rules = computed<FormRules>(() => ({
  username: [{ required: true, message: t('请填写用户名'), trigger: 'blur' }],
  password: [{ required: true, message: t('请填写密码'), trigger: 'blur' }],
}))

async function submit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  error.value = ''
  try {
    await loginAdmin(form.username.trim(), form.password)
    router.push({ name: 'games' })
  } catch (err) {
    clearAdminSession()
    error.value = err instanceof Error ? err.message : t('登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style lang="scss" scoped>
.login-card {
  width: 100%;
  max-width: 360px;
}

.login-card h2 {
  margin: 0 0 8px;
  color: #1f2329;
  font-size: 28px;
  font-weight: 600;
}

.login-alert {
  margin-bottom: 16px;
}

.login-submit {
  width: 100%;
}
</style>
