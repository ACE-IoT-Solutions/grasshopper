<template>
    <div class="hidden-menu">
        <div class="card-close" style="margin-bottom: 6px;">
          <!-- <p>Edge Info</p> -->
          <v-btn
            @click="close()"
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
          <v-tabs
            v-model="hiddenTabs"
            align-tabs="start"
          >
            <v-tab value="subnet" size="x-small">Subnets</v-tab>
            <v-tab value="bbmd" size="x-small">BBMDs</v-tab>
            <v-tab value="router" size="x-small">Routers</v-tab>
            <v-tab value="network" size="x-small">Networks</v-tab>
            <v-tab value="device" size="x-small">Devices</v-tab>
          </v-tabs>
          <v-card-text>
            <v-tabs-window v-model="hiddenTabs">
              <v-tabs-window-item value="subnet">
                <div
                  v-for="(item, index) in hiddenSubnetIds"
                  :key="index"
                  style="display: flex; justify-content: space-between; align-items: center;"
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
              <v-tabs-window-item value="bbmd">
                <div
                  v-for="(item, index) in hiddenBbmdIds"
                  :key="index"
                  style="display: flex; justify-content: space-between; align-items: center;"
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
              <v-tabs-window-item value="router">
                <div
                  v-for="(item, index) in hiddenRouterIds"
                  :key="index"
                  style="display: flex; justify-content: space-between; align-items: center;"
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
              <v-tabs-window-item value="network">
                <div
                  v-for="(item, index) in hiddenNetworkIds"
                  :key="index"
                  style="display: flex; justify-content: space-between; align-items: center;"
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
              <v-tabs-window-item value="device">
                <div
                  v-for="(item, index) in hiddenDeviceIds"
                  :key="index"
                  style="display: flex; justify-content: space-between; align-items: center;"
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
import { gsap } from "gsap";
export default {
  props: ["hiddenSubnetIds", "hiddenDeviceIds", "hiddenNetworkIds", "hiddenRouterIds", "hiddenBbmdIds"],
  data() {
    return {
      hiddenTabs: null,
    };
  },
  mounted() {
    gsap.from(".hidden-menu", {
      duration: 0.25,
      opacity: 0,
      // height: 0,
      // width: 50,
      y: 50,
      x: 50,
      ease: "power2.out",
    });
  },
  methods: {
    showSet(type, item) {
      this.$emit("showSet", type, item)
    },
    close() {
      this.$emit("close");
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
  }
</style>