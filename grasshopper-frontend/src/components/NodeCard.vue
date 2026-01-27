<template>
  <div class="node-card">
    <!-- <TimelineCard v-if="store.nodeCard && store.timelineCard && store.deviceTimeline" :store="store" ref="timelineCard" /> -->
    <ObjectCard
      v-if="store.nodeCard && store.objectCard"
      :store="store"
      ref="objectCard"
    />
    <div :class="store.deviceTimeline ? 'card-close-tl' : 'card-close'">
      <h5 class="title">
        {{ selectedNodeType.toUpperCase() }} {{ store.nodeLabel }}
      </h5>
      <v-btn
        v-if="store.deviceTimeline"
        variant="plain"
        :ripple="false"
        icon=""
        id="no-background-hover"
        size="small"
        density="compact"
        color="#c1d200"
        @click="store.setTimelineCard(true)"
      >
        <v-icon>mdi-timeline-clock-outline</v-icon>
      </v-btn>
      <v-btn
        @click="(closeCard(), $refs.objectCard?.closeCard())"
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
    <p v-if="altCard" class="alt-card">
      {{ altInfo }}
    </p>
    <v-table v-if="!altCard">
      <thead>
        <tr>
          <th
            v-for="item in cardInfo.filter(
              item =>
                item.title.toLowerCase() !== 'label' &&
                item.title.toLowerCase() !== 'vendor id' &&
                item.title.toLowerCase() !== 'total objects',
            )"
            :key="item"
            class="text-left"
          >
            {{ item.title }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td
            v-for="item in cardInfo.filter(
              item =>
                item.title.toLowerCase() !== 'label' &&
                item.title.toLowerCase() !== 'vendor id' &&
                item.title.toLowerCase() !== 'total objects',
            )"
            :key="item"
          >
            <v-tooltip
              v-if="item.title.toLowerCase() == 'object count'"
              text="Detailed Object Info"
              bottom
              delay="1000"
            >
              <template v-slot:activator="{ props }">
                <div class="count-item" v-bind="props">
                  <v-btn
                    @click="
                      store.objectCard
                        ? $refs.objectCard?.closeCard()
                        : store.setObjectCard(true)
                    "
                    variant="plain"
                    :ripple="false"
                    append-icon="mdi-information-outline"
                  >
                    {{ item.value }}
                  </v-btn>
                </div>
              </template>
            </v-tooltip>
            <div v-else>
              {{ item.value }}
            </div>
          </td>
        </tr>
      </tbody>
    </v-table>
    <div class="card-buttons" v-if="selectedNodeType">
      <!-- <v-btn @click="toggleNote()" variant="plain" append-icon="mdi-plus" size="x-small">
            Add Note
          </v-btn> -->
      <v-btn @click="toggleHideSelectedNode()" variant="plain" size="x-small">
        {{ showHideText }} {{ selectedNodeType }}
      </v-btn>
    </div>
  </div>
</template>

<script>
import { gsap } from 'gsap'
import { vendors } from '../vendors/bacnet_vendors.json'
import ObjectCard from '@/components/ObjectCard.vue'

export default {
  components: {
    ObjectCard,
  },
  props: [
    'store',
    'altCard',
    'selectedNodeType',
    'cardInfo',
    'altInfo',
    'showHideText',
  ],
  watch: {
    // eslint-disable-next-line no-unused-vars
    cardInfo(newVal, oldVal) {
      this.addVendorName()
    },
    'store.deviceKey'(newVal, oldVal) {
      if (newVal !== oldVal) {
        // this.$refs.timelineCard?.closeCard()
      }
    },
  },
  mounted() {
    gsap.from('.node-card', {
      duration: 0.25,
      opacity: 0,
      y: 50,
      x: 50,
      ease: 'power2.out',
    })

    this.addVendorName()
  },
  methods: {
    toggleHideSelectedNode() {
      this.$emit('toggleHideSelectedNode')
    },
    toggleNote() {
      this.store.setShowNoteCard(true)
    },
    matchVendor(vendorId) {
      const vendorMatch = vendors.find(v => v.vendor_id === vendorId)
      return vendorMatch ? vendorMatch.vendor_name : vendorId
    },
    addVendorName() {
      const vendorItem = this.cardInfo.find(
        item => item.title.toLowerCase() === 'vendor id',
      )
      if (vendorItem) {
        const vendorName = this.matchVendor(vendorItem.value)
        // eslint-disable-next-line vue/no-mutating-props
        this.cardInfo.push({ title: 'Vendor', value: vendorName })
      }
    },
    closeCard() {
      gsap.to('.node-card', {
        duration: 0.25,
        opacity: 0,
        y: 50,
        x: 50,
        ease: 'power2.in',
        onComplete: () => {
          // this.store.setTimelineCard(false)
          this.store.setNodeCard(false)
        },
      })
    },
  },
}
</script>

<style lang="scss" scoped>
.node-card {
  position: absolute;
  bottom: 2.5%;
  right: 1%;
  padding: 10px;
  background-color: #212121;
  color: white;
  border-radius: 8px;
  z-index: 999;
  box-shadow: 0px 1px 1px rgba(0, 0, 0, 0.1);
  text-align: left;
}
.card-close {
  display: flex;
  margin-left: 5px;
  justify-content: space-between;
  align-items: center;
}
.card-close-tl {
  display: flex;
  margin-left: 5px;
  justify-content: space-between;
}
.card-buttons {
  display: flex;
  justify-content: space-between;
  flex-direction: row-reverse;
}
.alt-card {
  font-size: 14px;
  font-weight: 900;
  margin: 5px;
  width: 300px;
}
.count-item {
  display: flex;
  align-items: center;
  color: #c1d200;
  gap: 8px;
}
.title {
  color: #c1d200;
}
</style>
