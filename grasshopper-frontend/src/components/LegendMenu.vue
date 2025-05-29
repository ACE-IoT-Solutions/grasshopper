<template>
  <div class="legend-menu">
    <div class="header">
      <v-icon size="small" color="#FDFD94" style="padding-left: 20px;">mdi-map-legend</v-icon>
      <!-- <p class="title">LEGEND</p> -->
      <v-btn
        variant="plain"
        :ripple="false"
        icon
        id="no-background-hover"
        size="small"
        @click="store.setLegend(false)"
      >
        <v-icon>mdi-close</v-icon>
      </v-btn>
    </div>
    <div class="content">
      <div class="legend">
        <div class="legend-item" v-for="(item, index) in items" :key="index">
          <div class="title">{{ item.title }}</div>
          <div class="icon">
            <img :src="item.image" alt="" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { gsap } from 'gsap'
import { Draggable } from 'gsap/Draggable'
export default {
  props: ['store'],
  mounted() {
    if (this.store.compareMode) {
      this.items.push({ title: 'Removed', image: '/assets/removed.svg' }, { title: 'Added', image: '/assets/added.svg' })
    }
    gsap.registerPlugin(Draggable)

    gsap.from('.legend-menu', {
      duration: 0.25,
      opacity: 0,
      y: 50,
      x: 50,
      ease: 'power2.out',
    })

    Draggable.create('.legend-menu', {
      type: 'x,y',
      edgeResistance: 0.5,
      bounds: 'body',
    })
  },
  data() {
    return {
      items: [
        { title: 'Grasshopper', image: '/assets/grasshopper icon.svg' },
        { title: 'Device', image: '/assets/device.svg' },
        { title: 'Network', image: '/assets/network.svg' },
        { title: 'Subnet', image: '/assets/lan.svg' },
        { title: 'Router', image: '/assets/router.svg' },
        { title: 'BBMD (ON)', image: '/assets/bbmd-on.svg' },
        { title: 'BBMD (OFF)', image: '/assets/bbmd-off.svg' },
      ],
    }
  },
}
</script>

<style lang="scss" scoped>
.legend-menu {
  background-color: rgba(33, 33, 33, 0.7);
  border-radius: 15px;
  position: absolute;
  bottom: 3%;
  right: 2%;
  box-shadow: 1px 0px 16px -5px rgba(0,0,0,0.75);
  cursor: move;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: 5px;
}
.content {
  padding: 0 20px 20px 20px;
}
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  justify-content: center;
}
.legend-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.legend-item .title {
  font-weight: bold;
  font-size: 14px;
  margin-bottom: 10px;
  color: #cdcdcd;
}
.legend-item .icon img {
  width: 40px;
  height: 40px;
  object-fit: contain;
}
.title {
  color: #CDCDCD;
  font-size: 12px;
  font-weight: bold;
}
</style>
