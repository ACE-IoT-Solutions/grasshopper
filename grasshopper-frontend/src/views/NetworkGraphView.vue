<template>
  <div>
    <v-alert
      v-if="loadError"
      class="error"
      density="compact"
      title="Error"
      type="warning"
      color="#db5a5e"
      closable
      @click:close="loadError = false"
      >Graph <strong>{{ $route.params.graphName }}</strong> does not exist.
    </v-alert>
    <NetworkHeader :store="store" />
    <NetworkDiagram :store="store" :key="store.diagramKey" />
    <ControlMenus v-if="store.controlMenu" :store="store"/>
    <CompareLoad v-if="store.compareLoad && store.currentTask != null" :store="store" />
    <div v-if="store.controlMenu" class="overlay"></div>
    <LegendMenu v-if="store.legendEnabled" :store="store" />
    <!-- <LegendMenu /> -->
  </div>
</template>

<script>
import NetworkHeader from '@/components/NetworkHeader.vue';
import NetworkDiagram from '@/components/NetworkDiagram.vue';
import ControlMenus from '../components/ControlMenus.vue';
import axios from 'axios';
import CompareLoad from '../components/CompareLoad.vue';
import LegendMenu from '../components/LegendMenu.vue';
export default {
  props: ["store"],
  components: {
    NetworkDiagram,
    NetworkHeader,
    ControlMenus,
    CompareLoad,
    LegendMenu,
  },
  watch: {
    // eslint-disable-next-line no-unused-vars
    'store.reloadKey'(newVal, oldVal) {
      this.fetchAll();
      this.fetchConfig();
    },
  },
  computed: {
    graphName() {
      return this.$route.params.graphName;
    },
  },
  setup() {
    return {}
  },
  created() {
    this.runFetchCycle();
  },
  mounted() {
    if (this.$route.params.graphName) {
      if (this.$route.params.graphName.includes('_vs_')) {
        this.loadCompare(this.$route.params.graphName);
      }
      else {
        this.goToGraph(this.$route.params.graphName);
      }
    }
  },
  beforeUnmount() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
    }
  },
  data() {
    return {
      host: window.location.protocol + '//' + window.location.host,
      refreshInterval: null,
      defaultInterval: 300000,
      genInterval: 300000,
      loadError: false,
    };
  },
  methods: {
    async goToGraph(graph) {
      this.setupLoad = true

      await axios
        .get(`${this.host}/api/operations/ttl_network/${graph}`, {
          responseType: 'json',
        })
        .then(response => {
          this.store.setCompareMode(false)
          this.store.setCurrentGraph(response.data, graph)
        })
        .catch(error => {
          console.log(error)
          this.loadError = true
        })
    },
    async loadCompare(graph) {
      this.compareLoad = true

      await axios
        .get(`${this.host}/api/operations/ttl_compare/${graph}`, {
          responseType: 'json',
        })
        .then(response => {
          this.store.setCompareMode(true)
          this.store.setCurrentGraph(response.data, graph)
        })
        .catch(error => {
          console.log(error)
          this.loadError = true
        })
    },
    async runFetchCycle() {
      await this.fetchAll();
      
      const interval = (this.store.currentTask != "None") ? this.genInterval : this.defaultInterval;
      
      this.refreshInterval = setTimeout(() => {
        this.runFetchCycle();
      }, interval);
    },
    async fetchQueue() {
      await axios
        .get(
          `${this.host}/api/operations/ttl_compare_queue`,
          {
            responseType: "json"
          }
        )
        .then((response) => {

          this.store.setQueue(response.data.processing_task, response.data.queue);

          response.data.processing_task != "None" ? this.store.setCompareLoad(true) : this.store.setCompareLoad(false);;
        })
        .catch((error) => {
          console.log(error);
        });
    },
    async fetchAll() {
      await Promise.all([
        this.fetchQueue()
      ]);
    },
  },
}
</script>

<style lang="scss" scoped>
.overlay {
  background-color: black;
  opacity: 30%;
  position: absolute;
  top: 0;
  left: 0;
  z-index: 999;
  height: 100vh;
  width: 100vw;
}
.error {
  position: absolute;
  top: 2%;
  left: 50%;
  transform: translateX(-50%);
  z-index: 999;
  max-width: 600px;
}
</style>
