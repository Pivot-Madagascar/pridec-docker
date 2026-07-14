import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface Dhis2User {
    id: string | null
    email: string | null
    username: string | null
    displayName: string | null
}

export const useAuthStore = defineStore('auth', () => {
    const token = ref<string | null>(localStorage.getItem('token'))
    const user = ref<Dhis2User | null>(null)

    const isAuthenticated = computed(() => !!token.value)

    function setToken(newToken: string | null) {
        token.value = newToken
        if (newToken) {
            localStorage.setItem('token', newToken)
        } else {
            localStorage.removeItem('token')
        }
    }

    function setUser(newUser: Dhis2User | null) {
        user.value = newUser
        if (newUser) {
            localStorage.setItem('user', JSON.stringify(newUser))
        } else {
            localStorage.removeItem('user')
        }
    }

    function clear() {
        token.value = null
        user.value = null
        localStorage.removeItem('token')
        localStorage.removeItem('user')
    }

    const storedUser = localStorage.getItem('user')
    if (storedUser && token.value) {
        user.value = JSON.parse(storedUser)
    }

    return {
        token,
        user,
        isAuthenticated,
        setToken,
        setUser,
        clear,
    }
})