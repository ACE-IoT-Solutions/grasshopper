<template>
  <div class="startup-page">
    <div
      class="startup-menu"
      :class="{ wide: store.graphFormsTab === 'compare' }"
    >
      <img src="@/assets/grasshopper-drk-bg.svg" class="logo-image" />
      <GraphForms :store="store" />
    </div>
  </div>
</template>

<script>
import GraphForms from './GraphForms.vue'
export default {
  props: ['store'],
  components: {
    GraphForms,
  },
  mounted() {
    this.store.refreshItems()
  },
}
</script>

<style lang="scss" scoped>
.startup-page {
  display: flex;
  justify-content: center;
  min-height: 100vh;
  /* top-aligned so switching tabs doesn't shift the card */
  padding: 10vh 16px 40px;
}
.startup-menu {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: min(720px, 100%);
  height: fit-content;
  transition: width 0.3s ease;
  padding: 24px;
  border-radius: 16px;
  background: linear-gradient(to bottom right, #212121, #242424);
  box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.5);
}
.startup-menu.wide {
  /* compare tab sits calendar and saved compares side by side */
  width: min(1080px, 100%);
}
.logo-image {
  height: 56px;
  margin: 4px auto 8px;
}
</style>
