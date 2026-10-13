import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface Dhis2User {
    id: string | null
    email: string | null
    username: string | null
    displayName: string | null
    is_admin?: boolean // DHIS2 authority ALL; missing in sessions stored before 2026-10-13
}

// The session itself is an HttpOnly cookie set by etlhub: JavaScript never sees it.
// `user` is only a hint for the router; etlhub answers 401 when the session is gone.
export const useAuthStore = defineStore('auth', () => {
    const user = ref<Dhis2User | null>(null)

    const isAuthenticated = computed(() => !!user.value)

    function setUser(newUser: Dhis2User | null) {
        user.value = newUser
        if (newUser) {
            localStorage.setItem('user', JSON.stringify(newUser))
        } else {
            localStorage.removeItem('user')
        }
    }

    function clear() {
        user.value = null
        localStorage.removeItem('user')
        localStorage.removeItem('token') // left by the old token login
    }

    const storedUser = localStorage.getItem('user')
    if (storedUser) {
        user.value = JSON.parse(storedUser)
    }

    return {
        user,
        isAuthenticated,
        setUser,
        clear,
    }
})
