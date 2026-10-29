<template>
  <div class="login-wrap">
    <section class="login-banner">
      <div class="login-mark">乙</div>
      <p class="login-kicker">OTOME</p>
      <h1>{{ t('乙游后台') }}</h1>
      <p>{{ t('在这里编写故事、角色、剧情和素材。发布后，客户端凭游戏 ID 播放。') }}</p>
    </section>
    <section class="login-panel">
      <ElSelect :model-value="locale" class="login-lang" @change="onLang">
        <ElOption v-for="item in LANGS" :key="item.code" :label="item.name" :value="item.code" />
      </ElSelect>
      <RouterView />
    </section>
  </div>
</template>

<script lang="ts" setup>
import { LANGS, locale, setLocale, t } from '../i18n'

function onLang(code: string) {
  setLocale(String(code))
}
</script>

<style lang="scss" scoped>
.login-wrap {
  display: flex;
  min-height: 100vh;
  background: #f0f2f5;
}

.login-banner {
  display: flex;
  flex: 1;
  flex-direction: column;
  justify-content: center;
  padding: 72px;
  color: #fff;
  background:
    radial-gradient(circle at 18% 20%, rgba(255, 255, 255, 0.18), transparent 32%),
    radial-gradient(circle at 80% 72%, rgba(255, 255, 255, 0.12), transparent 28%),
    linear-gradient(160deg, #0958d9 0%, #1677ff 46%, #001529 100%);
}

.login-mark {
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.16);
  font-size: 24px;
  font-weight: 700;
}

.login-kicker {
  margin: 20px 0 0;
  letter-spacing: 0.24em;
  font-size: 13px;
  opacity: 0.8;
}

.login-banner h1 {
  margin: 8px 0 12px;
  font-size: 40px;
  font-weight: 600;
}

.login-banner p:last-child {
  max-width: 420px;
  margin: 0;
  font-size: 16px;
  line-height: 1.8;
  opacity: 0.92;
}

.login-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: min(480px, 100%);
  padding: 32px 24px;
  background: #fff;
}

.login-lang {
  width: 160px;
  margin-bottom: 24px;
}

@media (max-width: 900px) {
  .login-wrap {
    flex-direction: column;
  }

  .login-banner {
    padding: 40px 24px;
  }

  .login-banner h1 {
    font-size: 28px;
  }

  .login-panel {
    flex: 1;
    width: 100%;
  }
}
</style>
