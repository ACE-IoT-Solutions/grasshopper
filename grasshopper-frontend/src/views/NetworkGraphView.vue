<template>
  <div>
    <NetworkHeader :store="store" />
    <NetworkDiagram :store="store" :key="store.diagramKey" />
    <ControlMenus v-if="store.controlMenu" :store="store" />
    <div v-if="store.controlMenu" class="overlay"></div>
    <LegendMenu v-if="store.legendEnabled" :store="store" />
  </div>
</template>

<script>
import { defineAsyncComponent } from 'vue'

export default {
  props: ['store'],
  components: {
    NetworkHeader: defineAsyncComponent(
      () => import('@/components/NetworkHeader.vue'),
    ),
    NetworkDiagram: defineAsyncComponent(
      () => import('@/components/NetworkDiagram.vue'),
    ),
    ControlMenus: defineAsyncComponent(
      () => import('../components/ControlMenus.vue'),
    ),
    LegendMenu: defineAsyncComponent(
      () => import('../components/LegendMenu.vue'),
    ),
  },
  watch: {
    '$route.fullPath'() {
      this.loadFromRoute()
    },
  },
  async mounted() {
    await this.loadFromRoute()
    this.store.setLoading(false)
  },
  methods: {
    async loadFromRoute() {
      const { name, params, meta } = this.$route
      if (name !== 'graph' && name !== 'compare') return

      const { graph } = params
      const compare = meta.compare

      // already loaded, e.g. navigated here from goToGraph
      if (this.store.fileName === graph && this.store.compareMode === compare) {
        return
      }

      const loaded = await this.store.goToGraph(compare, graph, false)
      if (!loaded) this.$router.replace({ name: 'start' })
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
