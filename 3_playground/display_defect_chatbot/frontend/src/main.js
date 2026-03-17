import { createApp } from 'vue'
import App from './App.vue'
import ChatbotApp from './ChatbotApp.vue'

const mode = new URLSearchParams(location.search).get('mode')
const Root = mode === 'chat' ? ChatbotApp : App

createApp(Root).mount('#app')
