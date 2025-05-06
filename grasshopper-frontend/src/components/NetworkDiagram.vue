<template>
  <div class="network-page">
    <div class="network-wrapper">
      <!-- search -->
      <div v-if="loaded" class="search-icon-container">
        <div class="zoom">
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
        <div style="display: flex; gap: 20px">
          <v-btn
            @click="
              showSearch = true;
              showEdgeMenu = false;
            "
            variant="plain"
            id="no-background-hover"
            :ripple="false"
            icon=""
            size="medium"
            density="compact"
            ><v-icon>mdi-magnify</v-icon></v-btn
          >
        </div>
      </div>
      <EdgeCard
        v-if="showEdgeMenu"
        :edgeInfo="edgeInfo"
        :edgeOptions="edgeOptions"
        @close="showEdgeMenu = false"
      />
      <!-- physics menu -->
      <ConfigMenu
        :showConfig="showConfig"
        :store="store"
        @close="showConfig = false"
        @storeConfig="storeConfig()"
        ref="configMenu"
      />
      <!-- graph -->
      <div ref="networkContainer" class="network-graph"></div>
      <!-- add note card -->
      <NoteCard v-if="store.showNoteCard" :store="store" />
      <!-- node info -->
      <NodeCard
        v-if="cardToggled"
        :altCard="altCard"
        :selectedNodeType="selectedNodeType"
        :cardInfo="cardInfo"
        :altInfo="altInfo"
        :showHideText="showHideText"
        :store="store"
        @closeCard="cardToggled = false"
        @toggleHideSelectedNode="toggleHideSelectedNode()"
      />
      <!-- search card -->
      <SearchCard
        v-if="showSearch"
        :nodes="nodes"
        @closeSearch="showSearch = false"
        @selectNode="selectNode($event)"
      />
      <!-- hidden items menu -->
      <HiddenItemsMenu
        v-if="showHiddenMenu"
        :hiddenSubnetIds="hiddenSubnetIds"
        :hiddenDeviceIds="hiddenDeviceIds"
        :hiddenNetworkIds="hiddenNetworkIds"
        :hiddenRouterIds="hiddenRouterIds"
        :hiddenBbmdIds="hiddenBbmdIds"
        @close="showHiddenMenu = false"
        @showSet="setToShow"
      />
      <!-- control buttons -->
      <div v-if="loaded" class="config-btn">
        <v-btn
          @click="showConfig = true"
          variant="plain"
          size="small"
          id="settings"
          >Config
        </v-btn>
        <v-btn
          v-if="showHiddenMenuButton"
          @click="
            showHiddenMenu = true;
            cardToggled = false;
          "
          variant="plain"
          size="small"
          >Hidden Items
        </v-btn>
      </div>
    </div>
  </div>
</template>

<script>
import { Network } from 'vis-network'
import NodeCard from '../components/NodeCard.vue'
import SearchCard from '../components/SearchCard.vue'
import HiddenItemsMenu from '../components/HiddenItemsMenu.vue'
import EdgeCard from '../components/EdgeCard.vue'
import ConfigMenu from '../components/ConfigMenu.vue'
import NoteCard from '../components/NoteCard.vue'

export default {
  props: ['store'],
  components: {
    NodeCard,
    SearchCard,
    HiddenItemsMenu,
    EdgeCard,
    ConfigMenu,
    NoteCard,
  },
  mounted() {
    this.generate()
  },
  watch: {
    // eslint-disable-next-line no-unused-vars
    'store.physicsConfig'(newVal, oldVal) {
      this.network.physics.options = newVal
    },
    'store.showBdtEdges'(visible) {
      const allEdges = this.network.body.data.edges.get()
      this.toggleBdtEdges(allEdges, visible)
    },
  },
  computed: {
    showHideText() {
      if (this.selectedNodeType === 'Network') {
        return this.hiddenNetworkIds.includes(this.selectedNode)
          ? 'Show'
          : 'Hide'
      } else if (this.selectedNodeType === 'Router') {
        return this.hiddenRouterIds.includes(this.selectedNode)
          ? 'Show'
          : 'Hide'
      } else if (this.selectedNodeType === 'Device') {
        return this.hiddenDeviceIds.includes(this.selectedNode)
          ? 'Show'
          : 'Hide'
      } else if (this.selectedNodeType === 'BBMD') {
        return this.hiddenBbmdIds.includes(this.selectedNode) ? 'Show' : 'Hide'
      } else if (this.selectedNodeType === 'Subnet') {
        return this.hiddenSubnetIds.includes(this.selectedNode)
          ? 'Show'
          : 'Hide'
      } else {
        return ''
      }
    },
    showHiddenMenuButton() {
      return (
        this.hiddenNetworkIds.length > 0 ||
        this.hiddenRouterIds.length > 0 ||
        this.hiddenDeviceIds.length > 0 ||
        this.hiddenBbmdIds.length > 0 ||
        this.hiddenSubnetIds.length > 0
      )
    },
    nodes() {
      return this.store.currentGraph?.nodes || []
    },
    edges() {
      return (
        this.store.currentGraph?.edges.map((edge, i) => ({
          ...edge,
          id: Date.now() + i,
        })) || []
      )
    },
  },
  data() {
    return {
      network: null,
      showConfig: false,
      cardInfo: [{ title: '', value: '' }],
      tableLabel: null,
      edgeInfo: {
        type: null,
        from: null,
        to: null,
      },
      edgeOptions: [
        {
          title: 'Test',
          action: () => this.hideEdge(),
        },
      ],
      altInfo: null,
      altCard: false,
      showCard: false,
      showSearch: false,
      cardToggled: false,
      nodeSearch: '',
      searchResults: [],
      networkHidden: false,
      networkColors: {},
      edgeItems: [],
      edgeFilter: null,
      showFilter: false,
      networkItems: [],
      networkFilter: null,
      networkSearch: '',
      networkSizes: {},
      networkEdgeLengths: {},
      selectedEdge: null,
      edgeVisibility: {},
      filterEdgeLengths: {},
      hiddenTabs: null,
      loading: false,
      showHiddenMenu: false,
      showEdgeMenu: false,

      loaded: false,

      allBbmds: [],
      onBbmds: [],

      selectedNode: null,

      networkVisibility: {},
      hiddenNetworkIds: [],

      routerVisibility: {},
      hiddenRouterIds: [],

      deviceVisibility: {},
      hiddenDeviceIds: [],

      bbmdVisibility: {},
      hiddenBbmdIds: [],

      subnetVisibility: {},
      hiddenSubnetIds: [],

      selectedNodeType: null,
      host: window.location.protocol + '//' + window.location.host,

      highlightedNodeId: null,
      highlightedNodeOriginalStyle: null,

      bdtEdges: [],
      closestBbmd: null,

      // showNoteCard: false,
    }
  },
  methods: {
    toggleHideSelectedNode() {
      if (this.selectedNodeType === 'Network') {
        if (this.hiddenNetworkIds.includes(this.selectedNode)) {
          this.showSet(
            this.networkVisibility,
            this.hiddenNetworkIds,
            this.selectedNode,
          )
        } else {
          this.hideSet(
            this.networkVisibility,
            this.selectedNode,
            this.hiddenNetworkIds,
            'network',
          )
        }
      } else if (this.selectedNodeType === 'Router') {
        if (this.hiddenRouterIds.includes(this.selectedNode)) {
          this.showSet(
            this.routerVisibility,
            this.hiddenRouterIds,
            this.selectedNode,
          )
        } else {
          this.hideSet(
            this.routerVisibility,
            this.selectedNode,
            this.hiddenRouterIds,
            'router',
          )
        }
      } else if (this.selectedNodeType === 'Device') {
        if (this.hiddenDeviceIds.includes(this.selectedNode)) {
          // this.showDevice(this.selectedDevice);
          this.showSet(
            this.deviceVisibility,
            this.hiddenDeviceIds,
            this.selectedNode,
          )
        } else {
          this.hideDevice()
        }
      } else if (this.selectedNodeType === 'BBMD') {
        if (this.hiddenBbmdIds.includes(this.selectedNode)) {
          this.showSet(
            this.bbmdVisibility,
            this.hiddenBbmdIds,
            this.selectedNode,
          )
        } else {
          this.hideSet(
            this.bbmdVisibility,
            this.selectedNode,
            this.hiddenBbmdIds,
            null,
          )
        }
      } else if (this.selectedNodeType === 'Subnet') {
        if (this.hiddenSubnetIds.includes(this.selectedNode)) {
          this.showSet(
            this.subnetVisibility,
            this.hiddenSubnetIds,
            this.selectedNode,
          )
        } else {
          this.hideSet(
            this.subnetVisibility,
            this.selectedNode,
            this.hiddenSubnetIds,
            'subnet',
          )
        }
      }
    },
    hideEdgeAndNetwork(edge) {
      if (!this.selectedEdge) return

      this.selectedNode = edge

      this.hideSet(
        this.networkVisibility,
        this.selectedNode,
        this.hiddenNetworkIds,
        'network',
      )
    },
    hideEverythingConnectedToRouter(edge) {
      if (!this.selectedEdge) return

      this.selectedNode = edge

      this.hideSet(
        this.routerVisibility,
        this.selectedNode,
        this.hiddenRouterIds,
        'router',
      )
    },
    hideEdgeAndDevice() {
      if (!this.selectedEdge) return

      const edgeId = this.selectedEdge
      const edgeData = this.network.body.data.edges.get(edgeId)

      this.selectedNode = edgeData.from

      this.hideDevice()
    },
    hideNetworkAndEdgeToRouter(edge) {
      if (!this.selectedEdge) return

      this.selectedNode = edge

      this.hideSet(
        this.networkVisibility,
        this.selectedNode,
        this.hiddenNetworkIds,
        'network',
      )
    },
    hideEdgeAndSubnet(edge) {
      if (!this.selectedEdge) return

      this.selectedNode = edge

      this.hideSet(
        this.subnetVisibility,
        this.selectedNode,
        this.hiddenSubnetIds,
        'subnet',
      )
    },
    hideEdgeAndBbmd(edge) {
      if (!this.selectedEdge) return

      this.selectedNode = edge

      this.hideSet(
        this.bbmdVisibility,
        this.selectedNode,
        this.hiddenBbmdIds,
        null,
      )
    },
    hideSet(setVisibility, nodeId, hiddenIds, setType) {
      if (!nodeId) return

      // init storage
      if (!setVisibility[nodeId]) {
        setVisibility[nodeId] = {
          nodes: {},
          edges: {},
        }
      }

      // current node init
      let currentNodeId

      // init traversal
      const visitedNodes = new Set()
      const visitedEdges = new Set()
      const nodesToVisit = [nodeId]

      while (nodesToVisit.length > 0) {
        currentNodeId = nodesToVisit.shift()

        if (visitedNodes.has(currentNodeId)) continue

        // exception node init
        const ignore = {
          subnet: this.allBbmds.includes(currentNodeId),
          router: currentNodeId.startsWith('bacnet://subnet/'),
          network: currentNodeId.startsWith('bacnet://router/'),
        }

        // applies node exception based on setType
        // eslint-disable-next-line no-prototype-builtins
        if (setType && ignore.hasOwnProperty(setType) && ignore[setType]) {
          continue
        }

        // ignore grasshopper node
        if (currentNodeId.startsWith('bacnet://Grasshopper')) {
          continue
        }

        visitedNodes.add(currentNodeId)

        // store/hide the current node
        const currentNodeData = this.network.body.data.nodes.get(currentNodeId)
        setVisibility[nodeId].nodes[currentNodeId] = {
          hidden: currentNodeData.hidden || false,
        }
        this.network.body.data.nodes.update({ id: currentNodeId, hidden: true })

        // get connected edges
        const connectedEdges = this.network.getConnectedEdges(currentNodeId)

        connectedEdges.forEach(edgeId => {
          if (visitedEdges.has(edgeId)) return

          const edgeData = this.network.body.data.edges.get(edgeId)

          // other node connected by this edge
          const otherNodeId =
            edgeData.from === currentNodeId ? edgeData.to : edgeData.from

          // eslint-disable-next-line no-prototype-builtins
          if (setType && ignore.hasOwnProperty(setType) && ignore[setType]) {
            return
          }

          if (otherNodeId.startsWith('bacnet://Grasshopper')) {
            return
          }

          visitedEdges.add(edgeId)

          // store/hide edge
          const edge = this.network.body.data.edges.get(edgeId)
          setVisibility[nodeId].edges[edgeId] = edge
          this.network.body.data.edges.remove(edgeId)

          if (!visitedNodes.has(otherNodeId)) {
            nodesToVisit.push(otherNodeId)
          }
        })
      }

      // add to hiddenRouterIds
      if (!hiddenIds.includes(nodeId)) {
        hiddenIds.push(nodeId)
      }
    },
    hideEdge() {
      if (!this.selectedEdge) return

      const edgeId = this.selectedEdge
      // eslint-disable-next-line no-unused-vars
      const edgeData = this.network.body.data.edges.get(edgeId)

      // Hide the edge
      this.network.body.data.edges.update({
        id: edgeId,
        hidden: true,
        length: 0,
      })
    },
    hideDevice() {
      if (!this.selectedNode) return

      const deviceNodeId = this.selectedNode

      // init storage
      if (!this.deviceVisibility[deviceNodeId]) {
        this.deviceVisibility[deviceNodeId] = {
          nodes: {},
          edges: {},
        }
      }

      const connectedEdges = this.network.getConnectedEdges(deviceNodeId)

      // hide selected device node
      const selectedNodeData = this.network.body.data.nodes.get(deviceNodeId)
      this.deviceVisibility[deviceNodeId].nodes[deviceNodeId] = {
        hidden: selectedNodeData.hidden || false,
      }
      this.network.body.data.nodes.update({ id: deviceNodeId, hidden: true })

      // hide connected edges
      connectedEdges.forEach(edgeId => {
        const edgeData = this.network.body.data.edges.get(edgeId)
        this.deviceVisibility[deviceNodeId].edges[edgeId] = edgeData
        this.network.body.data.edges.remove(edgeId)
      })

      // add to hiddenDeviceIds
      if (!this.hiddenDeviceIds.includes(deviceNodeId)) {
        this.hiddenDeviceIds.push(deviceNodeId)
      }
    },
    setToShow(type, item) {
      const setTypes = {
        device: {
          visibility: this.deviceVisibility,
          ids: this.hiddenDeviceIds,
        },
        network: {
          visibility: this.networkVisibility,
          ids: this.hiddenNetworkIds,
        },
        router: {
          visibility: this.routerVisibility,
          ids: this.hiddenRouterIds,
        },
        subnet: {
          visibility: this.subnetVisibility,
          ids: this.hiddenSubnetIds,
        },
        bbmd: { visibility: this.bbmdVisibility, ids: this.hiddenBbmdIds },
      }

      this.showSet(setTypes[type].visibility, setTypes[type].ids, item)
    },
    showSet(setVisibility, hiddenIds, showId) {
      if (!setVisibility[showId]) return

      // Restore the visibility of nodes
      Object.keys(setVisibility[showId].nodes).forEach(nodeId => {
        // const nodeVisibility = setVisibility[showId].nodes[nodeId];
        this.network.body.data.nodes.update({
          id: nodeId,
          hidden: false,
        })
      })

      // Restore the visibility of edges
      Object.keys(setVisibility[showId].edges).forEach(edgeId => {
        const original = setVisibility[showId].edges[edgeId]
        this.network.body.data.edges.add(original)
        delete setVisibility[showId].edges[edgeId]
      })

      // Remove from hiddenRouterIds
      const index = hiddenIds.indexOf(showId)
      if (index > -1) {
        hiddenIds.splice(index, 1)
      }

      // Clear stored data
      delete setVisibility[showId]
    },
    zoom(inOut) {
      const currentScale = this.network.getScale()

      if (inOut == 'in') {
        this.network.moveTo({
          scale: currentScale + 0.3,
          animation: {
            duration: 500,
          },
        })
      } else {
        this.network.moveTo({
          scale: currentScale - 0.3,
          animation: {
            duration: 500,
          },
        })
      }
    },
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
    selectNode(nodeId) {
      this.network.focus(nodeId, {
        scale: 1.5,
        animation: {
          duration: 500,
          easingFunction: 'easeInOutQuad',
        },
      })

      const params = { nodes: [nodeId], edges: [] }
      this.network.emit('click', params)

      this.searchResults = []
      this.nodeSearch = ''
    },
    createNode(label, data, nodeMap) {
      const sortedPrefixes = Object.keys(nodeMap).sort(
        (a, b) => b.length - a.length,
      )
      const prefix = sortedPrefixes.find(prefix => label.startsWith(prefix))
      const bbmdOn = '/assets/bbmd-on.svg'
      const bbmdOff = '/assets/bbmd-off.svg'

      if (prefix) {
        let config = nodeMap[prefix]

        // Check if the config is a nested object
        if (typeof config === 'object' && !config.image) {
          config = config[data.type]

          if (config) {
            if (data.type == 'BBMD') this.allBbmds.push(label)

            return {
              shape: 'image',
              image:
                data.type == 'BBMD'
                  ? this.onBbmds.includes(data.label)
                    ? bbmdOn
                    : bbmdOff
                  : config.image,
              label: label.replace(prefix, ''),
              font: { align: 'left', color: 'white', background: 'none' },
              mass: config.mass,
            }
          }
        } else {
          return {
            shape: 'image',
            image: config.image,
            label: label.replace(prefix, ''),
            font: { align: 'left', color: 'white', background: 'none' },
            mass: config.mass,
          }
        }
      }
      return {
        shape: 'dot',
        color: 'white',
        label: label,
        font: { align: 'left', color: 'white', background: 'none' },
      }
    },
    getNodeConfig(label, data) {
      // define image and mass based on prefix
      const nodeMap = {
        'bacnet://router/': { image: '/assets/router.svg', mass: 2 },
        'bacnet://network/': { image: '/assets/network.svg', mass: 2 },
        'bacnet://': {
          Device: { image: '/assets/device.svg', mass: 1 },
          BBMD: { image: '/assets/bbmd-off.svg', mass: 2 },
        },
        'bacnet://Grasshopper': {
          image: '/assets/grasshopper icon.svg',
          mass: 5,
        },
        'bacnet://subnet/': { image: '/assets/lan.svg', mass: 2 },
      }

      return this.createNode(label, data, nodeMap)
    },
    subtractConfig(label, data) {
      // #DF1219
      const nodeMap = {
        'bacnet://router/': { image: '/assets/router-sub.svg', mass: 2 },
        'bacnet://network/': { image: '/assets/network-sub.svg', mass: 2 },
        'bacnet://': {
          Device: { image: '/assets/device-sub.svg', mass: 1 },
          BBMD: { image: '/assets/bbmd-sub.svg', mass: 4 },
        },
        'bacnet://Grasshopper': {
          image: '/assets/grasshopper icon.svg',
          mass: 5,
        },
        'bacnet://subnet/': { image: '/assets/lan-sub.svg', mass: 2 },
      }

      return this.createNode(label, data, nodeMap)
    },
    addConfig(label, data) {
      // #14AE5C
      const nodeMap = {
        'bacnet://router/': { image: '/assets/router-add.svg', mass: 2 },
        'bacnet://network/': { image: '/assets/network-add.svg', mass: 2 },
        'bacnet://': {
          Device: { image: '/assets/device-add.svg', mass: 1 },
          BBMD: { image: '/assets/bbmd-add.svg', mass: 4 },
        },
        'bacnet://Grasshopper': {
          image: '/assets/grasshopper icon.svg',
          mass: 5,
        },
        'bacnet://subnet/': { image: '/assets/lan-add.svg', mass: 2 },
      }

      return this.createNode(label, data, nodeMap)
    },
    getCompareConfig(label, data, file1, file2) {
      if (data['http://data.ashrae.org/bacnet/2020#rdf_diff_source'] == file1) {
        // added
        return this.addConfig(label, data)
      } else if (
        data['http://data.ashrae.org/bacnet/2020#rdf_diff_source'] == file2
      ) {
        // subtracted
        return this.subtractConfig(label, data)
      } else {
        // unchanged
        return this.getNodeConfig(label, data)
      }
    },
    getCompareEdgeColor(data, file1, file2) {
      if (data['http://data.ashrae.org/bacnet/2020#rdf_diff_source'] == file1) {
        // added
        return {
          color: {
            color: '#14AE5C',
            highlight: '#14AE5C',
            hover: '#14AE5C',
            opacity: 1.0,
          },
        }
      } else if (
        data['http://data.ashrae.org/bacnet/2020#rdf_diff_source'] == file2
      ) {
        // removed
        return {
          color: {
            color: '#DF1219',
            highlight: '#DF1219',
            hover: '#DF1219',
            opacity: 1.0,
          },
        }
      } else {
        // unchanged
        return {
          color: {
            color: '#BFBFBF',
            highlight: '#BFBFBF',
            hover: '#BFBFBF',
            opacity: 1.0,
          },
        }
      }
    },
    storeConfig() {
      delete this.network.physics.options.repulsion.avoidOverlap

      this.store.setSavableConfig(this.network.physics.options)
      this.store.setControlMenu('config', 'Save Config')
    },
    formatData(data) {
      const formattedData = []

      Object.keys(data).forEach(originalKey => {
        let displayKey = originalKey

        // rename
        if (
          originalKey.toLowerCase() ===
          'http://data.ashrae.org/bacnet/2020#rdf_diff_source'
        ) {
          displayKey = 'source'
        }

        const words = displayKey.split(/[-_]/)

        const capitalizedWords = words.map(word => {
          if (word.toLowerCase() === 'id') {
            return 'ID'
          }
          return word.charAt(0).toUpperCase() + word.slice(1)
        })

        const title = capitalizedWords.join(' ')

        let value = data[originalKey]

        if (typeof value === 'string' && value.startsWith('bacnet://vendor/')) {
          value = value.replace(/^bacnet:\/\/vendor\//, '')
        } else if (typeof value === 'string' && value.startsWith('bacnet:')) {
          value = value.replace(/^bacnet:\//, '')
        }

        formattedData.push({ title, value })
      })

      return formattedData
    },
    highlightNode(nodeId) {
      if (this.highlightedNodeId) {
        this.unhighlightNode()
        this.toggleBdtEdges(this.bdtEdges, false)
      }

      const currentNode = this.network.body.data.nodes.get(nodeId)
      this.highlightedNodeOriginalStyle = {
        font: currentNode.font || null,
        borderWidth: currentNode.borderWidth || null,
      }

      this.network.body.data.nodes.update({
        id: nodeId,
        font: {
          color: 'white',
          background: 'rgba(193, 210, 0, 0.6)',
          borderRadius: '15px',
        },
        borderWidth: 4,
      })

      this.highlightedNodeId = nodeId
    },
    unhighlightNode() {
      if (!this.highlightedNodeId) return

      // restore
      this.network.body.data.nodes.update({
        id: this.highlightedNodeId,
        font: this.highlightedNodeOriginalStyle.font,
        borderWidth: this.highlightedNodeOriginalStyle.borderWidth,
      })

      this.highlightedNodeId = null
      this.highlightedNodeOriginalStyle = null
    },
    processEdges(closestBbmd) {
      this.onBbmds = []
      this.bdtEdges = []

      return this.edges.filter(edge => {
        if (edge.from === edge.to) {
          this.onBbmds.push(edge.from)
          return false
        } else if (
          edge.label.includes('bdt-entry') &&
          edge.from !== closestBbmd &&
          edge.to !== closestBbmd
        ) {
          this.bdtEdges.push(edge)
        }
        return true
      })
    },
    toggleBdtEdges(bdtEdges, visible) {
      bdtEdges.forEach(edge => {
        if (
          edge.label.includes('bdt-entry') &&
          this.allBbmds.includes(edge.from) &&
          this.allBbmds.includes(edge.to) &&
          edge.from !== this.closestBbmd &&
          edge.to !== this.closestBbmd
        ) {
          this.network.body.data.edges.update({
            id: edge.id,
            color: { opacity: visible ? 1 : 0 },
          })
        }
      })
    },
    findClosestBbmdInData(nodes, edges) {
      const graph = new Map()
      nodes.forEach(n => graph.set(n.id, []))
      edges.forEach(e => {
        if (graph.has(e.from) && graph.has(e.to)) {
          graph.get(e.from).push(e.to)
          graph.get(e.to).push(e.from)
        }
      })

      // find grasshopper node
      const startNode = nodes.find(node => node.id == 'bacnet://Grasshopper')
      if (!startNode) return null
      const startId = startNode.id

      // search
      const queue = [startId]
      const parent = { [startId]: null }
      const visited = new Set([startId])

      while (queue.length) {
        const current = queue.shift()

        for (const next of graph.get(current)) {
          if (visited.has(next)) continue
          visited.add(next)
          parent[next] = current

          // check if this neighbour is a BBMD
          const node = nodes.find(node => node.id === next)
          if (node?.data?.type === 'BBMD') {
            const path = []
            for (let p = next; p != null; p = parent[p]) {
              path.unshift(p)
            }
            return next
          }

          queue.push(next)
        }
      }

      return null
    },
    generate() {
      const container = this.$refs.networkContainer
      const configContainer = this.$refs.configMenu.$refs.config

      const closestBbmd = this.findClosestBbmdInData(this.nodes, this.edges)

      this.closestBbmd = closestBbmd

      const processedEdges = this.processEdges(closestBbmd)

      let file1
      let file2
      let nodeDiffSources = {}

      if (this.store.compareMode) {
        const parts = this.store.fileName.split('_vs_')

        file1 = `${parts[0]}.ttl`
        file2 = `${parts[1]}`

        this.nodes.forEach(node => {
          nodeDiffSources[node.id] =
            node.data['http://data.ashrae.org/bacnet/2020#rdf_diff_source'] ||
            null
        })
      }

      const data = {
        nodes: this.nodes.map(node => ({
          ...node,
          ...(this.store.compareMode
            ? this.getCompareConfig(node.id, node.data, file1, file2)
            : this.getNodeConfig(node.id, node.data)),
        })),
        edges: processedEdges.map(edge => {
          const base = {
            ...edge,
            ...(this.store.compareMode
              ? this.getCompareEdgeColor(edge.data, file1, file2)
              : {}),
          }

          if (
            edge.label.includes('bdt-entry') &&
            this.allBbmds.includes(edge.from) &&
            this.allBbmds.includes(edge.to)
          ) {
            return {
              ...base,
              color: {
                opacity:
                  edge.from === closestBbmd || edge.to === closestBbmd ? 1 : 0,
              },
              physics: edge.from === closestBbmd || edge.to === closestBbmd,
            }
          }

          return base
        }),
      }

      const options = {
        configure: {
          enabled: true,
          filter: ['physics'],
          container: configContainer,
        },
        edges: {
          color: {
            inherit: true,
          },
          smooth: {
            enabled: false,
            type: 'dynamic',
          },
          font: {
            size: 0,
          },
        },
        nodes: {
          shapeProperties: {
            interpolation: false,
          },
        },
        interaction: {
          dragNodes: true,
          hideEdgesOnDrag: false,
          hideNodesOnDrag: false,
        },
        physics: this.store.physicsConfig,
        layout: {
          improvedLayout: false,
        },
      }

      options.physics.enabled = true

      this.network = new Network(container, data, options)

      this.network.on('stabilizationIterationsDone', () => {
        this.loaded = true
      })

      this.network.on('click', params => {
        if (!params.nodes.length) {
          this.unhighlightNode()
          this.toggleBdtEdges(this.bdtEdges, false)
          this.store.setBdtEdges(false)
        }

        if (params.nodes.length > 0) {
          const nodeId = params.nodes[0]
          this.highlightNode(nodeId)
          const clickedNode = data.nodes.find(node => node.id === nodeId)
          this.store.setShowNoteCard(false)

          if (clickedNode) {
            // console.log(clickedNode)

            // const cleanedTitle = clickedNode.id;
            const nodeType = clickedNode.data.type
            const nodeLabel = clickedNode.data.label

            this.store.setSelectedNode(
              clickedNode.data.type + ' - ' + clickedNode.label,
            )

            this.selectedNodeType = null

            if (nodeType == 'BBMD') {
              this.cardInfo = this.formatData(clickedNode.data)
              this.tableLabel = nodeType
              this.altCard = false
              this.selectedBbmd = clickedNode.id
              this.selectedNodeType = 'BBMD'
              // show connecting bdt edges
              const matchingEdges = this.bdtEdges.filter(
                edge => edge.from === nodeLabel || edge.to === nodeLabel,
              )
              this.toggleBdtEdges(matchingEdges, true)
            } else {
              this.cardInfo = this.formatData(clickedNode.data)
              this.tableLabel = nodeType
              this.altCard = false
              this.selectedDevice = clickedNode.id
              this.selectedNodeType = nodeType

              this.selectedNode = clickedNode.id
            }

            this.showHiddenMenu = false
            this.cardToggled = true
            this.showEdgeMenu = false
          }
        }

        if (params.edges.length > 0) {
          const edgeId = params.edges[0]
          let clickedEdge = data.edges.find(edge => edge.id === edgeId)

          if (clickedEdge && params.nodes.length == 0) {
            // console.log(clickedEdge);

            const cleanedLabel = clickedEdge.label.replace(
              'http://data.ashrae.org/bacnet/2020#',
              '',
            )
            this.selectedEdge = clickedEdge.id
            this.edgeInfo = {
              type: cleanedLabel,
              from: clickedEdge.from,
              to: clickedEdge.to,
            }

            const deviceToBase = {
              'bacnet://subnet/': {
                title: 'Hide Edge and Subnet',
                action: () => this.hideEdgeAndSubnet(clickedEdge.to),
              },
              'bacnet://network/': {
                title: 'Hide Edge and Connected Network',
                action: () => this.hideEdgeAndNetwork(clickedEdge.to),
              },
              'bacnet://Grasshopper': {},
              'bacnet://': {
                title: 'Hide Edge and Device',
                action: () => this.hideEdgeAndDevice(),
              },
            }

            const deviceFromBase = {
              'bacnet://subnet/': {
                title: 'Hide Edge and Subnet',
                action: () => this.hideEdgeAndSubnet(clickedEdge.from),
              },
              'bacnet://network/': {
                title: 'Hide Edge and Connected Network',
                action: () => this.hideEdgeAndNetwork(clickedEdge.from),
              },
              'bacnet://router/': {
                title: 'Hide Edge and Router',
                action: () =>
                  this.hideEverythingConnectedToRouter(clickedEdge.from),
              },
              'bacnet://Grasshopper': {},
              'bacnet://': {
                title: 'Hide Edge and Device',
                action: () => this.hideEdgeAndDevice(),
              },
            }

            const bbmdEntriesTo = this.allBbmds.reduce((acc, bbmd) => {
              acc[bbmd] = {
                title: 'Hide Edge and BBMD',
                action: () => this.hideEdgeAndBbmd(clickedEdge.to),
              }
              return acc
            }, {})

            const bbmdEntriesFrom = this.allBbmds.reduce((acc, bbmd) => {
              acc[bbmd] = {
                title: 'Hide Edge and BBMD',
                action: () => this.hideEdgeAndBbmd(clickedEdge.from),
              }
              return acc
            }, {})

            const deviceTo = {
              ...bbmdEntriesTo,
              ...deviceToBase,
            }

            const deviceFrom = {
              ...bbmdEntriesFrom,
              ...deviceFromBase,
            }
            // set edgeOptions based on edgeInfo.type
            if (this.edgeInfo.type === 'router-to-network') {
              this.edgeOptions = [
                {
                  title: 'Hide Edge and Connected Network',
                  action: () => this.hideEdgeAndNetwork(clickedEdge.to),
                },
                {
                  title: 'Hide Edge and Router',
                  action: () =>
                    this.hideEverythingConnectedToRouter(clickedEdge.from),
                },
              ]
            } else if (this.edgeInfo.type === 'device-on-network') {
              // populate this.edgeOptions based on edge to and from node names
              const toKey = Object.keys(deviceTo).find(prefix =>
                this.edgeInfo.to.startsWith(prefix),
              )
              const fromKey = Object.keys(deviceFrom).find(prefix =>
                this.edgeInfo.from.startsWith(prefix),
              )

              this.edgeOptions = []

              // match prefix in deviceTo
              if (toKey) {
                if (deviceTo[toKey].title) {
                  this.edgeOptions.push({
                    title: deviceTo[toKey].title,
                    action: deviceTo[toKey].action,
                  })
                }
              }
              // match prefix in deviceFrom
              if (fromKey) {
                if (deviceFrom[fromKey].title) {
                  this.edgeOptions.push({
                    title: deviceFrom[fromKey].title,
                    action: deviceFrom[fromKey].action,
                  })
                }
              }
            } else {
              // Default options
              this.edgeOptions = [
                { title: 'Hide Edge', action: () => this.hideEdge() },
              ]
            }
            this.showEdgeMenu = true
            this.cardToggled = false
            this.showSearch = false
          }
        }
      })
    },
  },
  beforeUnmount() {
    this.network.destroy()
  },
}
</script>

<style scoped>
.network-page {
  display: grid;
  align-items: center;
  justify-items: center;
  width: 100%;
}
.network-wrapper {
  margin: 20px 1.5vw 0 1.5vw;
  width: 95%;
  height: 85vh;
  background-color: #121212;
  border-radius: 15px;
  position: relative;
  box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.5);
}
.network-graph {
  width: 100%;
  height: 85vh;
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
  /* width: 350px; */
  background-color: #212121;
  border-radius: 8px;
  z-index: 999;
  box-shadow: 0px 1px 1px rgba(0, 0, 0, 0.1);
}
.filter-container {
  display: grid;
  gap: 10px;
}
#hidden-menu {
  position: absolute;
  bottom: 2.5%;
  right: 1%;
  padding: 10px;
  /* width: 350px; */
  background-color: #212121;
  border-radius: 8px;
  z-index: 999;
  box-shadow: 0px 1px 1px rgba(0, 0, 0, 0.1);
}
#hidden-menu-card {
  visibility: hidden;
}
.hidden-items {
  width: 100%;
  padding: 10px;
}
.hidden-container {
  background-color: #121212;
  border-radius: 10px;
  margin-top: 10px;
}
.load-icon {
  position: absolute;
  top: 2.5%;
  left: 1%;
}
.line {
  width: 100%;
  color: #cdcdcd;
  opacity: 30%;
  margin: 8px 0px;
}
</style>
