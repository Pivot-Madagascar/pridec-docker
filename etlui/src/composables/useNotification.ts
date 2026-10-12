import toast from 'vue3-hot-toast'

export function useNotification() {
  const showNotification = (msg: string, type: 'success' | 'error') => toast[type](msg, { duration: 5000 })
  return { showNotification }
}
