<template>
  <div>
    <NetworkHeader :store="store" />
    <NetworkDiagram :store="store" :key="store.diagramKey" />
    <ControlMenus v-if="store.controlMenu" :store="store"/>
    <!-- <CompareLoad v-if="store.compareLoad" /> -->
    <CompareLoad v-if="store.compareLoad && store.currentTask != null" :store="store" />
    <div v-if="store.controlMenu" class="overlay"></div>
  </div>
</template>

<script>
import NetworkHeader from '@/components/NetworkHeader.vue';
import NetworkDiagram from '@/components/NetworkDiagram.vue';
import ControlMenus from '../components/ControlMenus.vue';
import axios from 'axios';
import CompareLoad from '../components/CompareLoad.vue';
export default {
  props: ["store"],
  components: {
    NetworkDiagram,
    NetworkHeader,
    ControlMenus,
    CompareLoad,
  },
  watch: {
    'store.reloadKey'(newVal, oldVal) {
      this.fetchAll();
    },
    // 'store.currentTask'(newVal, oldVal) {
    //   if (newVal != oldVal) {
    //     this.runFetchCycle();
    //   }
    // }
  },
  setup() {
    return {}
  },
  created() {
    this.runFetchCycle();
  },
  mounted() {
    // this.fetchAll();

    // this.refreshInterval = setInterval(() => {
    //   this.fetchAll();
    // }, this.refresh);
    // this.runFetchCycle();
  },
  beforeUnmount() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
    }
  },
  data() {
    return {
      host: window.location.protocol + '//' + window.location.host,
      refreshInterval: null,
      // defaultInterval: 3600000,
      defaultInterval: 300000,
      genInterval: 300000
    };
  },
  methods: {
    async runFetchCycle() {
      // if (this.refreshInterval) {
      //   clearTimeout(this.refreshInterval);
      // }
      
      await this.fetchAll();
      
      const interval = (this.store.currentTask != "None") ? this.genInterval : this.defaultInterval;
      // console.log(interval);
      
      this.refreshInterval = setTimeout(() => {
        this.runFetchCycle();
      }, interval);
    },
    async fetchGraphs() {
      await axios
        .get(
          `${this.host}/api/operations/ttl`,
          {
            responseType: "json"
          }
        )
        .then((response) => {
          this.store.setSetupGraphs(response.data.data);
          this.store.setDeleteGraphs(response.data.data);
        })
        .catch((error) => {
          console.log(error);
        });
    },
    async fetchIps() {
      await axios
        .get(
          `${this.host}/api/operations/subnets`,
          {
            responseType: "json"
          }
        )
        .then((response) => {
          this.store.setIpList(response.data.ip_address_list);
        })
        .catch((error) => {
          console.log(error);
        });
    },
    async fetchCompareGraphs() {
      await axios
        .get(
          `${this.host}/api/operations/ttl_compare`,
          {
            responseType: "json"
          }
        )
        .then((response) => {
          this.store.setCompareList(response.data.file_list);
          this.store.setDeleteCompareGraphs(response.data.file_list);
        })
        .catch((error) => {
          console.log(error);
        });
    },
    async fetchBbmds() {
      await axios
        .get(
          `${this.host}/api/operations/bbmds`,
          {
            responseType: "json"
          }
        )
        .then((response) => {
          this.store.setBbmdList(response.data.ip_address_list);
        })
        .catch((error) => {
          console.log(error);
        });
    },
    async fetchQueue() {
      await axios
        .get(
          `${this.host}/api/operations/ttl_compare_queue`,
          {
            responseType: "json"
          }
        )
        .then((response) => {
          // console.log(response);

          this.store.setQueue(response.data.processing_task, response.data.queue);

          response.data.processing_task != "None" ? this.store.setCompareLoad(true) : this.store.setCompareLoad(false);;
        })
        .catch((error) => {
          console.log(error);
        });
    },
    async fetchAll() {
      await Promise.all([
        this.fetchGraphs(),
        this.fetchIps(),
        this.fetchCompareGraphs(),
        this.fetchBbmds(),
        this.fetchQueue()
      ]);
    },
  },
}
</script>

<style lang="scss" scoped>
.overlay {
  background-color: black;
  opacity: 30%;
  position: absolute;
  top: 0;
  left: 0;
  z-index: 999;
  height: 100vh;
  width: 100vw;
}
</style>
