<template>
  <div class="network-page">
    <div class="network-wrapper">
      <!-- search -->
      <div class="search-icon-container" id="search">
        <div class="zoom" id="zoom">
          <v-btn
            @click="zoom('out')"
            variant="plain"
            id="no-background-hover"
            :ripple="false"
            icon=""
            size="medium"
            density="compact"
            >
              <v-icon>mdi-minus</v-icon>
            </v-btn>
            <v-btn
              @click="zoom('in')"
              variant="plain"
              id="no-background-hover"
              :ripple="false"
              icon=""
              size="medium"
              density="compact"
            >
                <v-icon>mdi-plus</v-icon>
            </v-btn>
        </div>
        <div style="display: flex; gap: 20px;">
          <v-btn
            variant="plain"
            id="no-background-hover"
            :ripple="false"
            icon=""
            size="medium"
            density="compact"
          ><v-icon>mdi-filter</v-icon></v-btn>
          <v-btn
            @click="toggleSearch()"
            variant="plain"
            id="no-background-hover"
            :ripple="false"
            icon=""
            size="medium"
            density="compact"><v-icon>mdi-magnify</v-icon></v-btn>
        </div>
      </div>
      <!-- edge filter menu -->
      <!-- <div id="edge-menu">
        <div class="card-close">
          <v-btn
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
        <p>Filter Edges</p>
        <v-select label="Edge Name" variant="solo-filled" density="compact" hide-details="auto"></v-select>
        <p>On Network</p>
        <v-select label="Network" variant="solo-filled" density="compact" hide-details="auto"></v-select>
      </div> -->
      <!-- physics menu -->
      <div class="config" :style="showConfig ? 'visibility: visible;' : 'visibility: hidden;'">
        <div class="config-close">
          <v-btn variant="plain" :ripple="false" icon="" id="no-background-hover" size="small" @click="closeConfig()"><v-icon>mdi-close</v-icon></v-btn>
        </div>
        <div ref="config"></div>
      </div>
      <!-- graph -->
      <div ref="networkContainer" class="network-graph"></div>
      <!-- node info -->
      <div id="card" class="node-card">
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
        <p style="font-size: 14px;">
          {{ cardInfo }}
        </p>
        <div class="card-close" id="hide-network">
          <v-btn @click="showHideNetwork ? showNetwork(selectedNetwork) : hideNetwork()" variant="plain" size="x-small">{{showHideNetwork ? 'Show' : 'Hide'}} Network</v-btn>
        </div>
      </div>
      <!-- search card -->
      <div id="search-card" class="search-card" :style="showSearch ? 'visibility: visible;' : 'visibility: hidden;'">
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
          <v-text-field v-model="nodeSearch" label="Search Network" variant="solo-filled" id="no-background-hover" density="compact" hide-details="auto" @input="triggerSearch()" append-icon="mdi-magnify"></v-text-field>
        </div>
        <!-- Display search results -->
        <ul v-if="searchResults.length > 0" class="search-results">
          <li v-for="result in searchResults" :key="result.id" @click="selectNode(result.id)">
            {{ result.label }}
          </li>
        </ul>
      </div>
      <!-- control buttons -->
      <div class="config-btn" id="config-btn">
        <v-btn @click="toggleConfig()" variant="plain" size="small" id="settings">Settings</v-btn>
        <!-- <v-btn @click="toggleSearch()" variant="plain" size="small" id="search">Search Network</v-btn> -->
      </div>
    </div>
  </div>
</template>

<script>
import { Network } from "vis-network";
import { nodes, edges } from "./ExampleNodes.json";

export default {
  mounted() {
    this.generate();
    document.getElementById('card').style.visibility="hidden";
    document.getElementById('config-btn').style.visibility="hidden";
    document.getElementById('search-card').style.visibility="hidden";
    document.getElementById('search').style.visibility="hidden";
    document.getElementById('zoom').style.visibility="hidden";
  },
  computed: {
    showHideNetwork() {
      return this.hiddenNetworkIds.includes(this.selectedNetwork);
    }
  },
  data() {
    return {
      network: null,
      showConfig: false,
      cardInfo: null,
      showCard: false,
      showSearch: false,
      nodeSearch: "",
      searchResults: [],
      selectedNetwork: null,
      networkHidden: false,
      networkColors: {},
      hiddenNetworkIds: [],
      edgeItems: [],
      edgeFilter: null,
      networkItems: [],
      networkFilter: null
    };
  },
  methods: {
    grabEdgesNetworks() {},
    filterEdges() {},
    hideNetwork() {
      if (!this.selectedNetwork) return;

      // init
      if (!this.networkColors[this.selectedNetwork]) {
        this.networkColors[this.selectedNetwork] = {
          nodes: {},
        };
      }

      // get all connected edges
      const connectedEdges = this.network.getConnectedEdges(this.selectedNetwork);

      // store color of network node
      const selectedNodeData = this.network.body.data.nodes.get(this.selectedNetwork);
      if (!this.networkColors[this.selectedNetwork].nodes[this.selectedNetwork]) {
        this.networkColors[this.selectedNetwork].nodes[this.selectedNetwork] = selectedNodeData.color;
      }

      // set the network node to gray
      this.network.body.data.nodes.update({ id: this.selectedNetwork, color: '#808080' });

      // set connected nodes to gray
      connectedEdges.forEach(edgeId => {
        const edge = this.network.body.data.edges.get(edgeId);

        // get nodes connected to network node
        const connectedNodeId = edge.from === this.selectedNetwork ? edge.to : edge.from;

        // store original node color
        if (!this.networkColors[this.selectedNetwork].nodes[connectedNodeId]) {
          const connectedNodeData = this.network.body.data.nodes.get(connectedNodeId);
          this.networkColors[this.selectedNetwork].nodes[connectedNodeId] = connectedNodeData.color;
        }

        // set hidden node color
        this.network.body.data.nodes.update({ id: connectedNodeId, color: '#808080' });
      });

      // add to hiddenNetworkIds
      if (!this.hiddenNetworkIds.includes(this.selectedNetwork)) {
        this.hiddenNetworkIds.push(this.selectedNetwork);
      }
    },

    showNetwork(networkNodeId) {
      if (!this.networkColors[networkNodeId]) return;

      // restore node colors
      if (this.networkColors[networkNodeId].nodes[networkNodeId]) {
        this.network.body.data.nodes.update({
          id: networkNodeId,
          color: this.networkColors[networkNodeId].nodes[networkNodeId]
        });
      }

      const connectedEdges = this.network.getConnectedEdges(networkNodeId);

      // restore edge colors, inherited from nodes
      connectedEdges.forEach(edgeId => {
        const edge = this.network.body.data.edges.get(edgeId);

        // restore color
        const connectedNodeId = edge.from === networkNodeId ? edge.to : edge.from;
        if (this.networkColors[networkNodeId].nodes[connectedNodeId]) {
          this.network.body.data.nodes.update({ id: connectedNodeId, color: this.networkColors[networkNodeId].nodes[connectedNodeId] });
        }
      });

      // remove from hiddenNetworkIds
      const index = this.hiddenNetworkIds.indexOf(networkNodeId);
      if (index > -1) {
        this.hiddenNetworkIds.splice(index, 1);
      }

      // clear store colors
      delete this.networkColors[networkNodeId];
    },
    zoom(inOut) {
      const currentScale = this.network.getScale();
      console.log(currentScale);
      
      if (inOut == 'in') {
        this.network.moveTo({
          scale: currentScale + 0.3,
          animation: {
            duration: 500
          }
        });
      } else {
        this.network.moveTo({
          scale: currentScale - 0.3,
          animation: {
            duration: 500
          }
        });
      }
    },
    closeCard() {
      document.getElementById('card').style.visibility="hidden";
      document.getElementById('hide-network').style.visibility="hidden";
      this.cardInfo = null;
      this.selectedNetwork = null;
    },
    closeSearch() {
      document.getElementById('search-card').style.visibility="hidden";
      document.getElementById('search').style.visibility="visible";
      this.showSearch = false;
      this.nodeSearch = "";
      this.searchResults = [];
    },
    closeConfig() {
      this.showConfig = false;
      document.getElementById('settings').style.visibility="visible";
    },
    toggleConfig() {
      this.showConfig = !this.showConfig;
      if (this.showConfig) {
        document.getElementById('settings').style.visibility="hidden";
      }
    },
    toggleSearch() {
      this.showSearch = !this.showSearch;
      if (this.showSearch) {
        document.getElementById('search').style.visibility="hidden";
      }
    },
    triggerSearch() {
      const searchQuery = this.nodeSearch.toLowerCase().trim();
      if (searchQuery === "") {
        this.searchResults = [];
        return;
      }

      this.searchResults = nodes.filter((node) =>
        node.label.toLowerCase().includes(searchQuery)
      );

      if (this.searchResults.length === 0) {
        console.log("No nodes found with the label:", searchQuery);
      }
    },
    selectNode(nodeId) {
      this.network.focus(nodeId, {
        scale: 1.5,
        animation: {
          duration: 500,
          easingFunction: "easeInOutQuad",
        },
      });

      const params = { nodes: [nodeId], edges: [] };
      this.network.emit("click", params);

      this.network.selectNodes([nodeId]);

      this.searchResults = [];
      this.nodeSearch = "";
    },
    generate() {
      const container = this.$refs.networkContainer;
      const configContainer = this.$refs.config;
      const data = {
        nodes: nodes,
        edges: edges,
      };
      const options = {
        "configure": {
            "enabled": true,
            "filter": [
                "physics"
            ],
            "container": configContainer,
        },
        "edges": {
            "color": {
                "inherit": true
            },
            "smooth": {
                "enabled": false,
                "type": "dynamic"
            }
        },
        "nodes": {
          "shapeProperties": {
            "interpolation": false
          }
        },
        "interaction": {
            "dragNodes": true,
            "hideEdgesOnDrag": false,
            "hideNodesOnDrag": false
        },
        "physics": {
          "enabled": true,
          "stabilization": {
            "enabled": true,
            "fit": true,
            "iterations": 200,
            "onlyDynamicEdges": false,
            "updateInterval": 50
          },
          "barnesHut": {
            "gravitationalConstant": -4100,
            "centralGravity": 1.15,
          },
        },
        "layout": {
          "improvedLayout": false
        }
      };
      this.network = new Network(container, data, options);

      this.network.on("stabilizationIterationsDone", () => {
        document.getElementById('config-btn').style.visibility="visible";
        document.getElementById('search').style.visibility="visible";
        document.getElementById('zoom').style.visibility="visible";
      });
      this.network.on("click", (params) => {
        if (params.nodes.length > 0) {
          const nodeId = params.nodes[0];
          const clickedNode = data.nodes.find((node) => node.id === nodeId);
          
          if (clickedNode) {
            const cleanedTitle = clickedNode.title.replace(/{|}/g, "");
            this.cardInfo = cleanedTitle;
            document.getElementById('card').style.visibility="visible";
            document.getElementById('hide-network').style.visibility="hidden";

            if (cleanedTitle == 'Network Node') {
              document.getElementById('hide-network').style.visibility="visible";
              this.selectedNetwork = clickedNode.id;
            }
          }
        }
      });
    },
  },
};
</script>

<style scoped>
.network-page {
  display: grid;
    align-items: center;
    justify-items: center;
    width: 100%;
}
.network-wrapper {
  margin: 30px 1.5vw 0 1.5vw;
  width: 95%;
  height: 78vh;
  background-color: #121212;
  border-radius: 15px;
  position: relative;
  box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.5);
}
.network-graph {
  width: 100%;
  height: 78vh;
  background-color: #121212;
  border-radius: 15px;
  overflow: hidden;
  z-index: 997;
}
.config {
  position: absolute;
  background-color: #212121;
  opacity: 100%;
  z-index: 998;
  height: 95%;
  overflow: scroll;
  padding: 10px;
  border-radius: 15px;
  left: 1%;
  top: 2.5%;
}
.config-btn {
  position: absolute;
  bottom: 1%;
  left: 1%;
  display: flex;
  width: 96%;
  justify-content: space-between;
}
.config-close {
  display: flex;
  justify-content: flex-end;
}
.node-card {
  position: absolute;
  bottom: 2.5%;
  right: 1%;
  padding: 10px;
  width: 300px;
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
.search-icon-container {
  position: absolute;
  top: 2.5%;
  left: 2%;
  display: flex;
  width: 96%;
  z-index: 998;
  justify-content: space-between;
}
.zoom {
  display: flex;
  gap: 10px;
}
#edge-menu {
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
</style>