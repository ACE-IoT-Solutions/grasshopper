<template>
  <v-app id="app">
    <v-alert
      v-if="grasshopperStore.globalError"
      class="error"
      density="compact"
      :title="grasshopperStore.alertTitle"
      :type="grasshopperStore.alertType"
      closable
      @click:close="grasshopperStore.setGlobalError(null, null, null, null)"
      >
      <div v-html="sanitizedAlertMessage"></div>
    </v-alert>
    <RouterView :store="grasshopperStore" />
  </v-app>
</template>

<script>
import { useGrasshopperStore } from './stores/index.js'
import DOMPurify from 'dompurify'

export default {
  data() {
    return {
      grasshopperStore: useGrasshopperStore(),
    }
  },
  computed: {
    sanitizedAlertMessage() {
      return DOMPurify.sanitize(
        this.grasshopperStore.errorMessage,
        {
          ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'br'],
          ALLOWED_ATTR: ['href', 'target']
        }
      )
    }
  },
  mounted() {
    this.grasshopperStore.runFetchCycle()
  },
}
</script>

<style scoped>
#app {
  background: linear-gradient(to bottom right, #212121, #121212) !important;
}

.error {
  position: absolute;
  top: 2%;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;
  max-width: 600px;
}
</style>
