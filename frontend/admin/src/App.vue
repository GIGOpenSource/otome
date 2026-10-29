<template>
  <ElConfigProvider :locale="elementLocale">
    <RouterView />
  </ElConfigProvider>
</template>

<script lang="ts" setup>
import { elementLocale } from './i18n'
</script>
