<template>
  <div>
    <NetworkHeader :store="store" />
    <NetworkDiagram :store="store" :key="store.diagramKey" />
    <ControlMenus v-if="store.controlMenu" :store="store"/>
    <CompareLoad v-if="store.compareLoad" :store="store" />
    <div v-if="store.controlMenu" class="overlay"></div>
    <LegendMenu v-if="store.legendEnabled" :store="store" />
  </div>
</template>

<script>
import NetworkHeader from '@/components/NetworkHeader.vue';
import NetworkDiagram from '@/components/NetworkDiagram.vue';
import ControlMenus from '../components/ControlMenus.vue';
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
  },
  mounted() {
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
