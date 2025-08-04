<template>
    <div class="search-card">
        <div class="card-close">
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
import { gsap } from "gsap";
export default {
  props: ["nodes"],
  mounted() {
    gsap.from(".search-card", {
      duration: 0.25,
      opacity: 0,
      y: -50,
      x: 50,
      ease: "power2.out",
    });
  },
  data() {
    return {
      nodeSearch: "",
      searchResults: [],
    };
  },
  methods: {
    triggerSearch() {
      const searchQuery = this.nodeSearch.toLowerCase().trim();

      if (searchQuery === "") {
        this.searchResults = [];
        return;
      }

      this.searchResults = this.nodes.filter((node) =>
        node.label.toLowerCase().includes(searchQuery)
      );

      if (this.searchResults.length === 0) {
        console.log("No nodes found with the label:", searchQuery);
      }
    },
    closeSearch() {
      this.$emit("closeSearch");
    },
    selectNode(result) {
      this.$emit("selectNode", result);
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
    margin: 10px 0;
    max-height: 150px;
    overflow-y: auto;
    background-color: #2A2A2A;
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
    justify-content: flex-end;
  }
</style>