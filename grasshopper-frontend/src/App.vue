<template>
  <v-app id="app">
    <RouterView :store="grasshopperStore" />
  </v-app>

</template>

<script setup>
import { useGrasshopperStore } from "./stores/index.js";

const grasshopperStore = useGrasshopperStore();
</script>

<style scoped>
#app {
  background: linear-gradient(to bottom right, #212121, #121212) !important;
}
header {
  line-height: 1.5;
  max-height: 100vh;
}

.logo {
  display: block;
  margin: 0 auto 2rem;
}

.main-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 20px;
}

.nav-link {
  margin: 0 1.5vw;
  padding: 0;
}
.nav-link:hover {
  color: #a6a9b2;
}

.header-btn {
  margin: 0 1.5vw;
  border-radius: 25px;
  color: #FFFD94;
}

@media (min-width: 1024px) {
  nav {
    text-align: left;
    margin-left: -1rem;
    font-size: 1rem;

    padding: 1rem 0;
    margin-top: 1rem;
  }
}
</style>
