<template>
  <div class="menu" :class="{ wide: store.graphFormsTab === 'compare' }">
    <div class="menu-header">
      <h4 class="menu-title">{{ store.menuTitle }}</h4>
      <v-btn
        variant="plain"
        :ripple="false"
        icon=""
        id="no-background-hover"
        size="small"
        density="compact"
        @click="closeMenu()"
        ><v-icon>mdi-close</v-icon></v-btn
      >
    </div>
    <GraphForms :store="store" />
  </div>
</template>

<script>
import { gsap } from 'gsap'
import GraphForms from './GraphForms.vue'
export default {
  props: ['store'],
  components: {
    GraphForms,
  },
  mounted() {
    this.store.refreshItems()
    gsap.from('.menu', {
      duration: 0.25,
      opacity: 0,
      y: 50,
      ease: 'power2.out',
    })
  },
  methods: {
    closeMenu() {
      gsap.to('.menu', {
        duration: 0.25,
        opacity: 0,
        y: 50,
        ease: 'power2.in',
        onComplete: () => {
          this.store.setControlMenu(false, null, null)
        },
      })
    },
  },
}
</script>

<style lang="scss" scoped>
.menu {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: min(640px, calc(100vw - 32px));
  transition: width 0.3s ease;
  max-height: calc(100vh - 32px);
  overflow-y: auto;
  padding: 20px 24px 24px;
  border-radius: 16px;
  background: linear-gradient(to bottom right, #212121, #242424);
  box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.5);
  position: absolute;
  top: 12vh;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;
}
.menu.wide {
  width: min(1080px, calc(100vw - 32px));
}
.menu-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.menu-title {
  color: #cdcdcd;
  letter-spacing: 0.1em;
  font-weight: 500;
}
</style>
