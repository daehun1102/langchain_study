// frontend/src/composables/useUserEmail.js
import { ref, watch } from 'vue'

export function useUserEmail() {
  const userEmail = ref(localStorage.getItem('user_email') || '')
  watch(userEmail, v => {
    try { localStorage.setItem('user_email', v || '') } catch (_) {}
  })
  return { userEmail }
}
