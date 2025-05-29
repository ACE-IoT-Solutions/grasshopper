<template>
  <v-app id="app">
    <!-- <header class="main-header">
      <RouterLink to="/" class="nav-link">
        <img style="width: 70%;"src="/assets/grasshopper.svg" alt="Grasshopper Logo" />
      </RouterLink>
      <v-btn class="header-btn" variant="plain" size="small">Logout</v-btn>
    </header> -->
    <RouterView :store="grasshopperStore" />
  </v-app>

</template>

<script setup>
import { RouterLink, RouterView } from 'vue-router';
import { useGrasshopperStore } from "./stores/index.js";

const grasshopperStore = useGrasshopperStore();
</script>

<style scoped>
#app {
  /* background-color: #212121; */
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
  /* font-size: 1.5em; */
  /* font-weight: 100; */
  /* color: #a6a9b2; */
  /* color: #c1d200; */
  /* text-decoration: none; */
  /* color: #43354f; */
  padding: 0;
}
.nav-link:hover {
  /* color: #c1d200; */
  color: #a6a9b2;
}

.header-btn {
  margin: 0 1.5vw;
  border-radius: 25px;
  color: #FFFD94;
}

@media (min-width: 1024px) {
  /* header {
    display: flex;
    place-items: center;
    padding-right: calc(var(--section-gap) / 2);
  }

  header .wrapper {
    display: flex;
    place-items: flex-start;
    flex-wrap: wrap;
  } */

  nav {
    text-align: left;
    margin-left: -1rem;
    font-size: 1rem;

    padding: 1rem 0;
    margin-top: 1rem;
  }
}
</style>
