import { ref, watch } from 'vue'

const userEmail = ref(localStorage.getItem('user_email') || '')
watch(userEmail, v => {
  try { localStorage.setItem('user_email', v || '') } catch (_) {}
})

export function useUserEmail() {
  return { userEmail }
}
