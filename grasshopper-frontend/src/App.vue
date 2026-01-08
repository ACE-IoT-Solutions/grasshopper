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
    <RouterView
      v-if="!grasshopperStore.startMenu"
      :store="grasshopperStore"
    />
    <StartMenu
      v-if="grasshopperStore.startMenu"
      :store="grasshopperStore"
    />
  </v-app>

</template>

<script>
import StartMenu from './components/StartMenu.vue'
import { useGrasshopperStore } from "./stores/index.js";
import DOMPurify from 'dompurify'

// const grasshopperStore = useGrasshopperStore();
export default {
  components: {
    StartMenu,
  },
  data() {
    return {
      grasshopperStore: useGrasshopperStore(),
    }
  },
  mounted() {
    this.runFetchCycle();
    this.handleRouteParams();
  },
  watch: {
    '$route': {
      // eslint-disable-next-line no-unused-vars
      handler: function(newRoute) {
        this.handleRouteParams();
      },
      immediate: true
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
    },
  },
  methods: {
    async runFetchCycle() {
      await this.grasshopperStore.fetchQueue();

      this.refreshInterval = setTimeout(() => {
        this.runFetchCycle();
      }, 30000);
    },
    handleRouteParams() {
      
      // Check if route params exist at all
      if (!this.$route.params) {
        return;
      }
      
      // Check specifically for graphName
      if (this.$route.params.graphName) {
        this.grasshopperStore.setStartMenu(false);
        if (this.$route.params.graphName.includes('_vs_')) {
          this.grasshopperStore.goToGraph(true, this.$route.params.graphName);
        } else {
          this.grasshopperStore.goToGraph(false, this.$route.params.graphName);
        }
      } else {
        this.grasshopperStore.setStartMenu(true);
      }
      this.grasshopperStore.setLoading(false);
    }
  }
}
</script>

<style scoped>
#app {
  background: linear-gradient(to bottom right, #212121, #121212) !important;
}
header {
  line-height: 1.5;
  max-height: 100vh;
}

.logo {
  display: block;
  margin: 0 auto 2rem;
}

.main-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 20px;
}

.nav-link {
  margin: 0 1.5vw;
  padding: 0;
}
.nav-link:hover {
  color: #a6a9b2;
}

.header-btn {
  margin: 0 1.5vw;
  border-radius: 25px;
  color: #FFFD94;
}

.error {
  position: absolute;
  top: 2%;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;
  max-width: 600px;
}

@media (min-width: 1024px) {
  nav {
    text-align: left;
    margin-left: -1rem;
    font-size: 1rem;

    padding: 1rem 0;
    margin-top: 1rem;
  }
}
</style>
