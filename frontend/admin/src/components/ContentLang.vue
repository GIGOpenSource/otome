<template>
  <div class="content-lang">
    <span>{{ t('文案语言') }}</span>
    <ElSelect :model-value="modelValue" filterable style="width: 220px" @update:model-value="emit('update:modelValue', $event)">
      <ElOption v-for="item in CONTENT_LANGS" :key="item.code" :label="langName(item.code)" :value="item.code" />
    </ElSelect>
    <span v-if="modelValue !== primary" class="admin-muted">{{ t('留空则使用主语言，没有主语言时再用英文') }}</span>
  </div>
</template>

<script lang="ts" setup>
import { t } from '../i18n'
import { CONTENT_LANGS, SOURCE_LANG } from '../utils/contentLang'
import { langName } from '../utils/langs'

withDefaults(
  defineProps<{ modelValue: string; primary?: string }>(),
  { primary: SOURCE_LANG },
)
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
</script>

<style lang="scss" scoped>
.content-lang {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}
</style>
