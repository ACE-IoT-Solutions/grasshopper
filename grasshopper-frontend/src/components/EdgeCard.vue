<template>
  <div class="edge-menu">
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
    <v-table>
      <thead>
        <tr>
          <th class="text-left">Edge Type</th>
          <th class="text-left">To</th>
          <th class="text-left">From</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>{{ formatEdgeType(edgeInfo.type) }}</td>
          <td>{{ formatNodeId(edgeInfo.to) }}</td>
          <td>{{ formatNodeId(edgeInfo.from) }}</td>
        </tr>
      </tbody>
    </v-table>
    <div class="options">
      <v-menu transition="slide-y-transition">
        <template v-slot:activator="{ props }">
          <v-btn v-bind="props" variant="plain" size="x-small"
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
import { gsap } from 'gsap'
export default {
  props: ['edgeInfo', 'edgeOptions', 'store'],
  mounted() {
    gsap.from('.edge-menu', {
      duration: 0.25,
      opacity: 0,
      y: -50,
      x: 50,
      ease: 'power2.out',
    })
  },
  methods: {
    closeMenu() {
      // this.$emit("close");
      gsap.to('.edge-menu', {
        duration: 0.25,
        opacity: 0,
        y: -50,
        x: 50,
        ease: 'power2.in',
        onComplete: () => {
          this.store.setEdgeMenu(false)
        },
      })
    },
    formatEdgeType(type) {
      if (!type) return 'Unknown'

      // Extract the fragment from full URI if present
      let edgeType = type
      if (type.includes('#')) {
        edgeType = type.split('#').pop()
      }

      // Map edge type identifiers to human-readable names
      const edgeTypeMap = {
        'device-on-network': 'Device → Network',
        'device-on-subnet': 'Device → Subnet',
        'bbmd-broadcast-domain': 'BBMD → Subnet',
        'bacnet-router-on-subnet': 'Router → Subnet',
        'bdt-entry': 'BDT Entry',
        'fdr-entry': 'FDT Entry',
        'router-for-subnet': 'Router → Subnet',
      }

      return edgeTypeMap[edgeType] || edgeType
    },
    formatNodeId(nodeId) {
      if (!nodeId) return 'Unknown'

      // Remove bacnet:// prefix
      let id = nodeId.replace('bacnet://', '')

      // Handle different node types
      if (id.startsWith('subnet/')) {
        return 'Subnet ' + id.replace('subnet/', '')
      }
      if (id.startsWith('network/')) {
        return 'Network ' + id.replace('network/', '')
      }
      if (id.startsWith('vendor/')) {
        return 'Vendor ' + id.replace('vendor/', '')
      }
      if (id.startsWith('Grasshopper/')) {
        return 'Grasshopper ' + id.replace('Grasshopper/', '')
      }

      // For device IDs (just numbers), prefix with "Device"
      if (/^\d+$/.test(id)) {
        return 'Device ' + id
      }

      // Return as-is if no pattern matches
      return id
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
.options {
  display: flex;
  justify-content: flex-end;
}
</style>
