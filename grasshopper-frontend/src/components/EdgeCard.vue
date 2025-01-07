<template>
    <div class="edge-menu">
        <div class="card-close">
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
        <v-table>
          <thead>
            <tr>
              <th class="text-left">
                Edge Type
              </th>
              <th class="text-left">
                To
              </th>
              <th class="text-left">
                From
              </th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>{{ edgeInfo.type }}</td>
              <td>{{ edgeInfo.to }}</td>
              <td>{{ edgeInfo.from }}</td>
            </tr>
          </tbody>
        </v-table>
        <div style="display: flex; justify-content: flex-end;">
          <v-menu
            transition="slide-y-transition"
          >
            <template v-slot:activator="{ props }">
              <v-btn
                v-bind="props"
                variant="plain"
                size="x-small"
                >Hide Options
              </v-btn>
            </template>
            <v-list>
              <v-list-item
                v-for="(item, i) in edgeOptions"
                :key="i"
                @click="item.action"
              >
                <v-list-item-title>{{ item.title }}</v-list-item-title>
              </v-list-item>
            </v-list>
          </v-menu>
        </div>
    </div>
</template>

<script>
import { gsap } from "gsap";
export default {
  props: ["edgeInfo", "edgeOptions"],
  mounted() {
    gsap.from(".edge-menu", {
      duration: 0.25,
      opacity: 0,
      y: -50,
      x: 50,
      ease: "power2.out",
    });
  },
  methods: {
    close() {
      this.$emit("close");
    },
  },
}
</script>

<style lang="scss" scoped>
  .edge-menu {
    position: absolute;
    top: 2.5%;
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