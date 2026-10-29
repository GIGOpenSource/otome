<template>
  <ElFormItem :label="t('语言')">
    <ElSelect
      v-model="model"
      filterable
      :clearable="filter"
      :placeholder="filter ? t('全部') : t('选择语言')"
      :style="{ width: width || (filter ? '180px' : '100%') }"
    >
      <ElOption v-for="item in LANGS" :key="item.code" :label="langName(item.code)" :value="item.code" />
    </ElSelect>
  </ElFormItem>
</template>

<script lang="ts" setup>
import { t } from '../i18n'
import { LANGS, langName } from '../utils/langs'

withDefaults(
  defineProps<{
    filter?: boolean
    width?: string
  }>(),
  { filter: false, width: '' },
)

const model = defineModel<string>({ default: '' })
</script>
