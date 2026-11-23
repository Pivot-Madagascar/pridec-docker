import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
// services/auth imports this store too (login): harmless, each uses the other only inside its functions.
import { logout as endSession } from '@/services/auth'

export interface Dhis2User {
    id: string | null
    email: string | null
    username: string | null
    displayName: string | null
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

    // Log out (side menu): ends the session, then forgets the user and goes to the login page, even if the request
    // fails (the session then expires on its own).
    async function logout() {
        try {
            await endSession()
        } catch (e) {
            console.warn('Logout request failed; the session expires on its own:', (e as Error)?.message)
        }
        clear()
        window.location.href = '/login'
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
        logout,
    }
})
