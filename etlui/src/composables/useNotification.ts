import { ref } from 'vue'
import toast from 'vue3-hot-toast'

export function useNotification() {
  const notification = ref('')
  const notificationType = ref<'success' | 'error'>('success')

  const showNotification = (msg: string, type: 'success' | 'error') => {
    notification.value = msg
    notificationType.value = type
    
    if (type === 'success') {
      toast.success(msg, { duration: 5000 })
    } else {
      toast.error(msg, { duration: 5000 })
    }
  }

  return {
    notification,
    notificationType,
    showNotification,
  }
}