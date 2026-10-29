import { ElMessage, ElMessageBox } from 'element-plus'
import { t } from '../i18n'

export function notify(message: string, type: 'success' | 'warning' | 'error' | 'info' = 'success') {
  ElMessage({ message: t(message), type, duration: 2000 })
}

export async function confirmDelete(message: string, title = '确认删除') {
  try {
    await ElMessageBox.confirm(t(message), t(title), {
      type: 'warning',
      confirmButtonText: t('删除'),
      cancelButtonText: t('取消'),
    })
    return true
  } catch {
    return false
  }
}
