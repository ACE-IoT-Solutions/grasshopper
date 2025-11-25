<template>
  <div class="hidden-menu">
    <div class="card-close">
      <!-- <p>Edge Info</p> -->
      <v-btn
        @click="closeMenu()"
        variant="plain"
        :ripple="false"
        icon=""
        id="no-background-hover"
        size="small"
        density="compact"
      >
        <v-icon>mdi-close</v-icon>
      </v-btn>
    </div>
    <v-card>
      <v-tabs v-model="hiddenTabs" align-tabs="start">
        <v-tab v-if="hiddenSubnetIds.length > 0" value="subnet" size="x-small">Subnets</v-tab>
        <v-tab v-if="hiddenBbmdIds.length > 0" value="bbmd" size="x-small">BBMDs</v-tab>
        <v-tab v-if="hiddenRouterIds.length > 0" value="router" size="x-small">Routers</v-tab>
        <v-tab v-if="hiddenNetworkIds.length > 0" value="network" size="x-small">Networks</v-tab>
        <v-tab v-if="hiddenDeviceIds.length > 0" value="device" size="x-small">Devices</v-tab>
      </v-tabs>
      <v-card-text>
        <v-tabs-window v-model="hiddenTabs">
          <v-tabs-window-item v-if="hiddenSubnetIds.length > 0" value="subnet">
            <div
              v-for="(item, index) in hiddenSubnetIds"
              :key="index"
              class="item-row"
            >
              <p>{{ item }}</p>
              <v-btn
                @click="showSet('subnet', item)"
                variant="plain"
                size="small"
                append-icon="mdi-eye-outline"
              >
                Show
              </v-btn>
            </div>
          </v-tabs-window-item>
          <v-tabs-window-item v-if="hiddenBbmdIds.length > 0" value="bbmd">
            <div
              v-for="(item, index) in hiddenBbmdIds"
              :key="index"
              class="item-row"
            >
              <p>{{ item }}</p>
              <v-btn
                @click="showSet('bbmd', item)"
                variant="plain"
                size="small"
                append-icon="mdi-eye-outline"
              >
                Show
              </v-btn>
            </div>
          </v-tabs-window-item>
          <v-tabs-window-item v-if="hiddenRouterIds.length > 0" value="router">
            <div
              v-for="(item, index) in hiddenRouterIds"
              :key="index"
              class="item-row"
            >
              <p>{{ item }}</p>
              <v-btn
                @click="showSet('router', item)"
                variant="plain"
                size="small"
                append-icon="mdi-eye-outline"
              >
                Show
              </v-btn>
            </div>
          </v-tabs-window-item>
          <v-tabs-window-item v-if="hiddenNetworkIds.length > 0" value="network">
            <div
              v-for="(item, index) in hiddenNetworkIds"
              :key="index"
              class="item-row"
            >
              <p>{{ item }}</p>
              <v-btn
                @click="showSet('network', item)"
                variant="plain"
                size="small"
                append-icon="mdi-eye-outline"
              >
                Show
              </v-btn>
            </div>
          </v-tabs-window-item>
          <v-tabs-window-item v-if="hiddenDeviceIds.length > 0" value="device">
            <div
              v-for="(item, index) in hiddenDeviceIds"
              :key="index"
              class="item-row"
            >
              <p>{{ item }}</p>
              <v-btn
                @click="showSet('device', item)"
                variant="plain"
                size="small"
                append-icon="mdi-eye-outline"
              >
                Show
              </v-btn>
            </div>
          </v-tabs-window-item>
        </v-tabs-window>
      </v-card-text>
    </v-card>
  </div>
</template>

<script>
import { gsap } from 'gsap'
export default {
  props: [
    'hiddenSubnetIds',
    'hiddenDeviceIds',
    'hiddenNetworkIds',
    'hiddenRouterIds',
    'hiddenBbmdIds',
    'store',
  ],
  data() {
    return {
      hiddenTabs: null,
    }
  },
  mounted() {
    gsap.from('.hidden-menu', {
      duration: 0.25,
      opacity: 0,
      y: 50,
      x: 50,
      ease: 'power2.out',
    })
  },
  watch: {
    emptyCard(newVal) {
      if (newVal) {
        this.closeMenu()
      }
    },
  },
  computed: {
    emptyCard() {
      return (
        this.hiddenSubnetIds.length === 0 &&
        this.hiddenDeviceIds.length === 0 &&
        this.hiddenNetworkIds.length === 0 &&
        this.hiddenRouterIds.length === 0 &&
        this.hiddenBbmdIds.length === 0
      )
    },
  },
  methods: {
    showSet(type, item) {
      this.$emit('showSet', type, item)
    },
    closeMenu() {
      gsap.to('.hidden-menu', {
        duration: 0.25,
        opacity: 0,
        y: 50,
        x: 50,
        ease: 'power2.in',
        onComplete: () => {
          this.store.setHiddenMenu(false)
        },
      })
    },
  },
}
</script>

<style lang="scss" scoped>
.hidden-menu {
  position: absolute;
  bottom: 2.5%;
  right: 1%;
  padding: 10px;
  /* width: 350px; */
  background-color: #212121;
  border-radius: 8px;
  z-index: 999;
  box-shadow: 0px 1px 1px rgba(0, 0, 0, 0.1);
}
.card-close {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 6px;
}
.item-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
