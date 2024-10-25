<template>
  <div>
    <NetworkHeader :store="store" />
    <NetworkDiagram :store="store" />
    <ControlMenus v-if="store.controlMenu" :store="store"/>
    <div v-if="store.controlMenu" class="overlay"></div>
  </div>
</template>

<script>
import NetworkHeader from '@/components/NetworkHeader.vue'
import NetworkDiagram from '@/components/NetworkDiagram.vue'
import ControlMenus from '../components/ControlMenus.vue'
import axios from 'axios';
export default {
  props: ["store"],
  components: {
    NetworkDiagram,
    NetworkHeader,
    ControlMenus,
  },
  setup() {
    return {}
  },
  mounted() {
    this.fetchAvailableGraphs();
  },
  data() {
    return {
      host: 'http://localhost:5173'
    };
  },
  methods: {
    async fetchAvailableGraphs() {
      await axios
        .get(
          `${this.host}/grasshopper_rpc/jsonrpc`,
          // { withCredentials: true,
          //   headers: { 
          //     'Access-Control-Allow-Origin' : '*',
          //   },
          //   responseType: "json"
          // },
          {
            headers: {
              "Access-Control-Allow-Origin": "*",
              "Access-Control-Allow-Methods": "GET",
              "Access-Control-Allow-Headers": "Content-Type, Authorization"
            }
          }
        )
        .then((response) => {
          console.log(response);
        })
        .catch((error) => {
          console.log(error);
        });
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
