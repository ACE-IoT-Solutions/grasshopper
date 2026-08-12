<template>
  <div class="legend-menu">
    <div class="header">
      <v-icon size="small" color="#FDFD94" class="legend-icon"
        >mdi-compass</v-icon
      >
      <v-btn
        variant="plain"
        :ripple="false"
        icon
        id="no-background-hover"
        size="small"
        @click="closeMenu()"
      >
        <v-icon>mdi-close</v-icon>
      </v-btn>
    </div>
    <div class="content">
      <div class="section-title">Nodes</div>
      <div class="legend">
        <div class="legend-item" v-for="(item, index) in items" :key="index">
          <div class="title">{{ item.title }}</div>
          <div class="icon">
            <img :src="item.image" alt="" />
          </div>
        </div>
      </div>
      <div class="section-title">Edges</div>
      <div class="edge-legend">
        <div class="edge-item" v-for="(edge, index) in edgeTypes" :key="'edge-' + index">
          <div
            class="edge-line"
            :class="{ 'dashed': edge.dash }"
            :style="{ borderColor: edge.color }"
          ></div>
          <div class="edge-label">{{ edge.title }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { gsap } from 'gsap'
import { Draggable } from 'gsap/Draggable'

import routerSvg from '@/assets/router.svg'
import networkSvg from '@/assets/network.svg'
import deviceSvg from '@/assets/device.svg'
import bbmdOnSvg from '@/assets/bbmd-on.svg'
import bbmdOffSvg from '@/assets/bbmd-off.svg'
import subnetSvg from '@/assets/lan.svg'
import grasshopperSvg from '@/assets/grasshopper-logomark.svg'
import removedSvg from '@/assets/removed.svg'
import addedSvg from '@/assets/added.svg'
export default {
  props: ['store'],
  mounted() {
    if (this.store.compareMode) {
      this.items.push(
        { title: 'Removed', image: removedSvg },
        { title: 'Added', image: addedSvg },
      )
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
        { title: 'Grasshopper', image: grasshopperSvg },
        { title: 'Device', image: deviceSvg },
        { title: 'Network', image: networkSvg },
        { title: 'Subnet', image: subnetSvg },
        { title: 'Router', image: routerSvg },
        { title: 'BBMD (ON)', image: bbmdOnSvg },
        { title: 'BBMD (OFF)', image: bbmdOffSvg },
      ],
      edgeTypes: [
        { title: 'BBMD → Subnet', color: 'rgb(200, 100, 200)', dash: false },
        { title: 'Router → Subnet', color: 'rgb(220, 80, 80)', dash: false },
        { title: 'Device → Subnet', color: 'rgb(100, 180, 100)', dash: false },
        { title: 'Grasshopper', color: 'rgb(0, 180, 180)', dash: false },
        { title: 'BDT Entry', color: 'rgb(255, 165, 0)', dash: true },
        { title: 'FDT Entry', color: 'rgb(0, 200, 255)', dash: true },
      ],
    }
  },
  methods: {
    closeMenu() {
      gsap.to('.legend-menu', {
        duration: 0.15,
        opacity: 0,
        ease: 'power2.in',
        onComplete: () => {
          this.store.setLegend(false)
        },
      })
    },
  },
}
</script>

<style lang="scss" scoped>
.legend-menu {
  background-color: rgba(33, 33, 33, 0.9);
  border-radius: 15px;
  position: absolute;
  bottom: 3%;
  right: 2%;
  box-shadow: 1px 0px 16px -5px rgba(0, 0, 0, 0.75);
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
  color: #cdcdcd;
  font-size: 12px;
  font-weight: bold;
}
.legend-icon {
  padding-left: 20px;
}
.section-title {
  color: #888;
  font-size: 11px;
  text-transform: uppercase;
  margin-bottom: 10px;
  margin-top: 5px;
  letter-spacing: 0.5px;
}
.edge-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  justify-content: flex-start;
}
.edge-item {
  display: flex;
  align-items: center;
  gap: 6px;
}
.edge-line {
  width: 28px;
  height: 0;
  border-top: 3px solid;
}
.edge-line.dashed {
  border-top-style: dashed;
}
.edge-label {
  color: #cdcdcd;
  font-size: 11px;
}
</style>
