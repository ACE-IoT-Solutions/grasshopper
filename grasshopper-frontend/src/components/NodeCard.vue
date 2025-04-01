<template>
    <div class="node-card">
        <div class="card-close">
          <v-btn
            @click="closeCard()"
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
        <p v-if="altCard" style="font-size: 14px; font-weight: 900; margin: 10px; width: 300px;">
          {{ altInfo }}
        </p>
        <v-table v-if="!altCard">
          <thead>
            <tr>
              <th v-for="item in cardInfo.filter(item => item.title.toLowerCase() !== 'label' && item.title.toLowerCase() !==  'vendor id')" :key="item" class="text-left">
                {{ item.title }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td v-for="item in cardInfo.filter(item => item.title.toLowerCase() !== 'label' && item.title.toLowerCase() !==  'vendor id')" :key="item">{{ item.value }}</td>
            </tr>
          </tbody>
        </v-table>
        <div class="card-close" v-if="selectedNodeType">
          <v-btn @click="toggleHideSelectedNode()" variant="plain" size="x-small">
            {{ showHideText }} {{ selectedNodeType }}
          </v-btn>
        </div>
      </div>
</template>

<script>
import { gsap } from "gsap";
import { vendors } from "../vendors/bacnet_vendors.json";

export default {
    props: ["altCard", "selectedNodeType", "cardInfo", "altInfo", "showHideText"],
    watch: {
      // eslint-disable-next-line no-unused-vars
      'cardInfo'(newVal, oldVal) {
        this.addVendorName();
      },
    },
    mounted() {
      gsap.from(".node-card", {
        duration: 0.25,
        opacity: 0,
        y: 50,
        x: 50,
        ease: "power2.out",
      });
      
      this.addVendorName();
    },
    methods: {
      closeCard() {
        this.$emit("closeCard")
      },
      toggleHideSelectedNode() {
        this.$emit("toggleHideSelectedNode");
      },
      matchVendor(vendorId) {
        const vendorMatch = vendors.find(v => v.vendor_id === vendorId);
        return vendorMatch ? vendorMatch.vendor_name : vendorId;
      },
      addVendorName() {
        const vendorItem = this.cardInfo.find(item => item.title.toLowerCase() === "vendor id");
        if (vendorItem) {
          const vendorName = this.matchVendor(vendorItem.value);
          // eslint-disable-next-line vue/no-mutating-props
          this.cardInfo.push({ title: "Vendor", value: vendorName });
        }
      }
    }
}
</script>

<style lang="scss" scoped>
.node-card {
  position: absolute;
  bottom: 2.5%;
  right: 1%;
  padding: 10px;
  /* width: 300px; */
  background-color: #212121;
  color: white;
  border-radius: 8px;
  z-index: 999;
  box-shadow: 0px 1px 1px rgba(0, 0, 0, 0.1);
  text-align: left;
}
.card-close {
  display: flex;
  justify-content: flex-end;
}
</style>