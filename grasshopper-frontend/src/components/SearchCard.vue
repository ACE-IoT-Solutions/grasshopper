<template>
  <div class="search-card">
    <div class="card-close">
      <h5 class="title">Search</h5>
      <v-btn
        @click="closeSearch()"
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
    <div class="search-container">
      <v-text-field
        v-model="nodeSearch"
        label="Search Graph"
        variant="solo-filled"
        id="no-background-hover"
        density="compact"
        hide-details="auto"
        @input="triggerSearch()"
        append-icon="mdi-magnify"
      >
      </v-text-field>
    </div>
    <!-- Display search results -->
    <ul v-if="searchResults.length > 0" class="search-results">
      <li
        v-for="result in searchResults"
        :key="result.id"
        @click="selectNode(result.id)"
      >
        {{ result.label }}
      </li>
    </ul>
  </div>
</template>

<script>
import { gsap } from 'gsap'
// import { vendors } from '../vendors/bacnet_vendors.json'
export default {
  props: ['nodes', 'store'],
  mounted() {
    gsap.from('.search-card', {
      duration: 0.25,
      opacity: 0,
      y: -50,
      x: 50,
      ease: 'power2.out',
    })
  },
  data() {
    return {
      nodeSearch: '',
      searchResults: [],
    }
  },
  methods: {
    // vendorNameById(idNum) {
    //   const idStr = String(idNum);
    //   const hit = vendors.find(v => String(v.vendor_id) === idStr);
    //   return hit?.vendor_name || idStr;
    // },
    triggerSearch() {
      const searchQuery = this.nodeSearch.toLowerCase().trim()

      if (searchQuery === '') {
        this.searchResults = []
        return
      }

      this.searchResults = this.nodes.filter(node =>
        node.label.toLowerCase().includes(searchQuery),
      )

      if (this.searchResults.length === 0) {
        console.log('No nodes found with the label:', searchQuery)
      }
    },
    closeSearch() {
      gsap.to('.search-card', {
        duration: 0.25,
        opacity: 0,
        y: -50,
        x: 50,
        ease: 'power2.in',
        onComplete: () => {
          this.store.setSearchMenu(false)
        },
      })
    },
    selectNode(result) {
      this.$emit('selectNode', result)
    },
  },
}
</script>

<style lang="scss" scoped>
.search-card {
  position: absolute;
  top: 2.5%;
  right: 1%;
  padding: 10px;
  width: 350px;
  background-color: #212121;
  border-radius: 8px;
  z-index: 999;
  box-shadow: 0px 1px 1px rgba(0, 0, 0, 0.1);
}
.search-container {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin: 10px 5px;
}
.search-results {
  list-style: none;
  padding: 0;
  margin-top: 10px;
  max-height: 150px;
  overflow-y: auto;
  background-color: #2a2a2a;
  border-radius: 8px;
  box-shadow: 0px 1px 1px rgba(0, 0, 0, 0.1);
}
.search-results li {
  padding: 8px 12px;
  cursor: pointer;
  color: white;
}
.search-results li:hover {
  background-color: #333;
}
.card-close {
  display: flex;
  justify-content: space-between;
}
.title {
  color: #cdcdcd;
  margin-left: 6px;
}
</style>
