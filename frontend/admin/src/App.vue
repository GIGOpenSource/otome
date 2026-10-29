<template>
  <ElConfigProvider :locale="elementLocale">
    <RouterView :key="locale" />
  </ElConfigProvider>
</template>

<script lang="ts" setup>
import { elementLocale, locale } from './i18n'
</script>
