<template>
  <div class="network-page">
    <div class="network-wrapper">
      <!-- search -->
      <v-progress-circular
        v-if="store.loading"
        indeterminate
        class="load-indicator"
      ></v-progress-circular>
      <div v-if="loaded && !emptyGraph" class="search-icon-container">
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
        <div class="layout-toggle">
          <v-btn
            @click="toggleLayout"
            variant="plain"
            id="no-background-hover"
            :ripple="false"
            icon=""
            size="medium"
            density="compact"
            :title="store.layoutMode === 'force' ? 'Switch to Tree Layout' : 'Switch to Force Layout'"
          >
            <v-icon>{{ store.layoutMode === 'force' ? 'mdi-file-tree' : 'mdi-graph' }}</v-icon>
          </v-btn>
        </div>
        <div class="search-icon">
          <v-btn
            @click="(store.setSearchMenu(true), store.setEdgeMenu(false))"
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
        v-if="store.edgeMenu"
        :edgeInfo="edgeInfo"
        :edgeOptions="edgeOptions"
        :store="store"
        ref="edgeCard"
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
      <!-- <NoteCard v-if="store.showNoteCard" :store="store" /> -->
      <!-- node info -->
      <NodeCard
        v-if="store.nodeCard"
        :altCard="altCard"
        :selectedNodeType="selectedNodeType"
        :cardInfo="cardInfo"
        :altInfo="altInfo"
        :showHideText="showHideText"
        :store="store"
        @toggleHideSelectedNode="toggleHideSelectedNode()"
        ref="nodeCard"
      />
      <!-- search card -->
      <SearchCard
        v-if="store.searchMenu"
        :nodes="nodes"
        :store="store"
        @selectNode="selectNode($event)"
        ref="searchCard"
      />
      <!-- hidden items menu -->
      <HiddenItemsMenu
        v-if="store.hiddenMenu"
        :hiddenSubnetIds="hiddenSubnetIds"
        :hiddenDeviceIds="hiddenDeviceIds"
        :hiddenNetworkIds="hiddenNetworkIds"
        :hiddenRouterIds="hiddenRouterIds"
        :hiddenBbmdIds="hiddenBbmdIds"
        :store="store"
        @showSet="setToShow"
        ref="hiddenItemsMenu"
      />
      <!-- control buttons -->
      <div v-if="loaded" class="config-btn">
        <!-- <v-btn
          @click="showConfig = true"
          variant="plain"
          size="small"
          id="settings"
          >Config
        </v-btn> -->
        <!-- <v-btn
          variant="plain"
          size="small">Issues Found</v-btn> -->
        <v-btn
          v-if="showHiddenMenuButton"
          @click="(store.setHiddenMenu(true), store.setNodeCard(false))"
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
// import { defineAsyncComponent } from 'vue';
import NodeCard from '@/components/NodeCard.vue'
import SearchCard from '@/components/SearchCard.vue'
import HiddenItemsMenu from '@/components/HiddenItemsMenu.vue'
import EdgeCard from '@/components/EdgeCard.vue'
import ConfigMenu from '@/components/ConfigMenu.vue'
// import NoteCard from '@/components/NoteCard.vue'

import routerSvg from '@/assets/router.svg'
import networkSvg from '@/assets/network.svg'
import deviceSvg from '@/assets/device.svg'
import bbmdOnSvg from '@/assets/bbmd-on.svg'
import bbmdOffSvg from '@/assets/bbmd-off.svg'
import subnetSvg from '@/assets/lan.svg'
import grasshopperSvg from '@/assets/grasshopper-logomark.svg'
import routerAddSvg from '@/assets/router-add.svg'
import routerSubSvg from '@/assets/router-sub.svg'
import networkAddSvg from '@/assets/network-add.svg'
import networkSubSvg from '@/assets/network-sub.svg'
import deviceAddSvg from '@/assets/device-add.svg'
import deviceSubSvg from '@/assets/device-sub.svg'
import bbmdOnAddSvg from '@/assets/bbmd-on-add.svg'
import bbmdOffAddSvg from '@/assets/bbmd-off-add.svg'
import bbmdOnSubSvg from '@/assets/bbmd-on-sub.svg'
import bbmdOffSubSvg from '@/assets/bbmd-off-sub.svg'
import subnetAddSvg from '@/assets/lan-add.svg'
import subnetSubSvg from '@/assets/lan-sub.svg'

export default {
  props: ['store'],
  components: {
    NodeCard,
    SearchCard,
    HiddenItemsMenu,
    EdgeCard,
    ConfigMenu,
    // NoteCard,
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
    'store.layoutMode'() {
      // Regenerate the graph when layout mode changes
      if (this.network) {
        this.generate()
      }
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
    emptyGraph() {
      return this.nodes.length === 0 && this.edges.length === 0
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
      // cardToggled: false,
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

      // Tree layout data for custom drawing
      treeLayoutData: null,
      layoutParentChild: null,

      // showNoteCard: false,
    }
  },
  methods: {
    toggleLayout() {
      this.store.toggleLayoutMode()
    },
    getNodeLevel(nodeId, nodeType) {
      // Assign hierarchical levels for tree layout (like a controls riser diagram)
      // Level 0: BBMDs (top of the riser - manage broadcast domains)
      // Level 1: Subnets and Grasshopper (IP subnets, scanner is at this level)
      // Level 2: Routers (connect subnets to BACnet networks)
      // Level 3: Networks (BACnet network numbers) - rendered as buses
      // Level 4: Devices (leaves - connect directly to network bus)
      if (nodeType === 'BBMD') {
        return 0
      } else if (nodeId.startsWith('bacnet://subnet/')) {
        return 1
      } else if (nodeId.startsWith('bacnet://Grasshopper')) {
        // Grasshopper/Sentinel is the scanner - put at subnet level
        return 1
      } else if (nodeId.startsWith('bacnet://router/')) {
        return 2
      } else if (nodeId.startsWith('bacnet://network/')) {
        return 3
      } else {
        // Regular devices
        return 4
      }
    },
    calculateTreeLayout(nodes, edges) {
      // Bottom-up tree layout: place devices first, then center parents over children
      const positions = {}
      const nodeSpacing = 70 // Horizontal spacing between nodes
      const levelHeight = 100 // Vertical spacing between levels

      // Build node map and group by level
      const nodeMap = {}
      const levelGroups = { 0: [], 1: [], 2: [], 3: [], 4: [] }
      nodes.forEach(n => {
        nodeMap[n.id] = n
        const level = this.getNodeLevel(n.id, n.data?.type)
        if (levelGroups[level]) {
          levelGroups[level].push(n.id)
        }
      })

      // Build child -> parents mapping (a child picks its closest parent by level)
      const childToParent = {} // childId -> parentId (closest level parent)
      const parentToChildren = {} // parentId -> [childIds]

      edges.forEach(e => {
        const fromLevel = this.getNodeLevel(e.from, nodeMap[e.from]?.data?.type)
        const toLevel = this.getNodeLevel(e.to, nodeMap[e.to]?.data?.type)

        let parentId, childId, parentLevel, childLevel
        if (fromLevel < toLevel) {
          parentId = e.from
          childId = e.to
          parentLevel = fromLevel
          childLevel = toLevel
        } else if (toLevel < fromLevel) {
          parentId = e.to
          childId = e.from
          parentLevel = toLevel
          childLevel = fromLevel
        } else {
          return // Same level, skip
        }

        // Child picks the closest parent (highest level that's still less than child)
        if (!childToParent[childId] ||
            parentLevel > this.getNodeLevel(childToParent[childId], nodeMap[childToParent[childId]]?.data?.type)) {
          childToParent[childId] = parentId
        }
      })

      // Build parentToChildren from childToParent
      Object.keys(childToParent).forEach(childId => {
        const parentId = childToParent[childId]
        if (!parentToChildren[parentId]) parentToChildren[parentId] = []
        if (!parentToChildren[parentId].includes(childId)) {
          parentToChildren[parentId].push(childId)
        }
      })

      // BOTTOM-UP: Group devices by their parent network, place groups together
      // Step 1: Group devices by their parent (network at level 3)
      const devicesByParent = {}
      const orphanDevices = []

      levelGroups[4].forEach(deviceId => {
        const parentId = childToParent[deviceId]
        if (parentId) {
          if (!devicesByParent[parentId]) devicesByParent[parentId] = []
          devicesByParent[parentId].push(deviceId)
        } else {
          orphanDevices.push(deviceId)
        }
      })

      // Step 2: Place devices grouped by parent network
      let x = 0
      const networkOrder = levelGroups[3].slice() // Networks

      // Place devices for each network
      networkOrder.forEach(networkId => {
        const devices = devicesByParent[networkId] || []
        devices.forEach(deviceId => {
          positions[deviceId] = { x: x, y: 4 * levelHeight }
          x += nodeSpacing
        })
        if (devices.length > 0) {
          x += nodeSpacing * 0.5 // Small gap between network groups
        }
      })

      // Place orphan devices at the end
      orphanDevices.forEach(deviceId => {
        positions[deviceId] = { x: x, y: 4 * levelHeight }
        x += nodeSpacing
      })

      // Step 3: For each level from 3 down to 0, center parent over its children
      for (let level = 3; level >= 0; level--) {
        levelGroups[level].forEach(nodeId => {
          const children = parentToChildren[nodeId] || []
          const childPositions = children
            .map(cid => positions[cid])
            .filter(p => p !== undefined)

          if (childPositions.length > 0) {
            // Center over children
            const minX = Math.min(...childPositions.map(p => p.x))
            const maxX = Math.max(...childPositions.map(p => p.x))
            positions[nodeId] = { x: (minX + maxX) / 2, y: level * levelHeight }
          } else {
            // No children, place at current x
            positions[nodeId] = { x: x, y: level * levelHeight }
            x += nodeSpacing
          }
        })
      }

      // Store the parent-child relationships for edge drawing
      this.layoutParentChild = { childToParent, parentToChildren }

      return positions
    },
    isNetworkNode(nodeId) {
      return nodeId.startsWith('bacnet://network/')
    },
    drawRiserDiagram(ctx, networkInstance, treePositions, edges, nodeMap) {
      // Custom drawing for riser diagram style:
      // Draw horizontal buses for network nodes

      if (!treePositions || !networkInstance) return

      const canvasContext = ctx

      // Collect network nodes and their device children for bus drawing
      const networkBuses = {}
      const nodePositions = {}

      // Get actual positions from the network
      Object.keys(treePositions).forEach(nodeId => {
        const pos = networkInstance.getPosition(nodeId)
        if (pos) {
          nodePositions[nodeId] = pos
        }
      })

      // Find device children for each network (level 3 -> level 4 connections)
      edges.forEach(edge => {
        const fromId = edge.from
        const toId = edge.to
        const fromLevel = this.getNodeLevel(fromId, nodeMap[fromId]?.data?.type)
        const toLevel = this.getNodeLevel(toId, nodeMap[toId]?.data?.type)

        // Network (level 3) to Device (level 4) connections
        if (fromLevel === 3 && toLevel === 4 && nodePositions[fromId] && nodePositions[toId]) {
          if (!networkBuses[fromId]) {
            networkBuses[fromId] = {
              pos: nodePositions[fromId],
              children: [],
              childIds: [],
            }
          }
          networkBuses[fromId].children.push(nodePositions[toId])
          networkBuses[fromId].childIds.push(toId)
        }
        if (toLevel === 3 && fromLevel === 4 && nodePositions[toId] && nodePositions[fromId]) {
          if (!networkBuses[toId]) {
            networkBuses[toId] = {
              pos: nodePositions[toId],
              children: [],
              childIds: [],
            }
          }
          networkBuses[toId].children.push(nodePositions[fromId])
          networkBuses[toId].childIds.push(fromId)
        }
      })

      // Draw network buses (horizontal lines) - only spanning their own children
      canvasContext.save()
      canvasContext.strokeStyle = '#FFD700' // Gold color for buses
      canvasContext.lineWidth = 4

      Object.keys(networkBuses).forEach(networkId => {
        const bus = networkBuses[networkId]
        if (bus.children.length === 0) return

        // Find the extent of THIS network's children only
        let minX = bus.pos.x
        let maxX = bus.pos.x

        bus.children.forEach(childPos => {
          minX = Math.min(minX, childPos.x)
          maxX = Math.max(maxX, childPos.x)
        })

        // Draw horizontal bus line from leftmost to rightmost child
        const busY = bus.pos.y
        const padding = 20

        canvasContext.beginPath()
        canvasContext.moveTo(minX - padding, busY)
        canvasContext.lineTo(maxX + padding, busY)
        canvasContext.stroke()
      })

      canvasContext.restore()

      // Store bus info for device drop connections
      this.networkBusData = networkBuses
    },
    drawOrthogonalEdges(ctx, networkInstance, edges, nodeMap) {
      // Draw orthogonal edges using actual node positions
      if (!networkInstance || !this.layoutParentChild) return

      const canvasContext = ctx
      const { childToParent } = this.layoutParentChild

      canvasContext.save()
      canvasContext.strokeStyle = 'rgba(140, 140, 140, 0.7)'
      canvasContext.lineWidth = 1

      // Draw edges for each parent-child relationship
      Object.keys(childToParent).forEach(childId => {
        const parentId = childToParent[childId]
        const parentPos = networkInstance.getPosition(parentId)
        const childPos = networkInstance.getPosition(childId)

        if (!parentPos || !childPos) return

        const parentLevel = this.getNodeLevel(parentId, nodeMap[parentId]?.data?.type)
        const childLevel = this.getNodeLevel(childId, nodeMap[childId]?.data?.type)

        // Device to Network connections (level 3 -> 4) - vertical drops to bus
        if (parentLevel === 3 && childLevel === 4) {
          canvasContext.beginPath()
          canvasContext.moveTo(childPos.x, childPos.y - 15)
          canvasContext.lineTo(childPos.x, parentPos.y)
          canvasContext.stroke()
          return
        }

        // Calculate waypoint Y as midpoint between parent and child
        const waypointY = parentPos.y + (childPos.y - parentPos.y) * 0.3

        canvasContext.beginPath()
        canvasContext.moveTo(parentPos.x, parentPos.y + 20) // Start below parent
        canvasContext.lineTo(parentPos.x, waypointY) // Down to waypoint
        canvasContext.lineTo(childPos.x, waypointY) // Horizontal to child X
        canvasContext.lineTo(childPos.x, childPos.y - 20) // Down to child
        canvasContext.stroke()
      })

      // Special handling for Grasshopper node - draw its subnet connection
      // Grasshopper is at level 1 (same as subnet) so it gets skipped by parent-child logic
      edges.forEach(edge => {
        const fromIsGrasshopper = edge.from.startsWith('bacnet://Grasshopper')
        const toIsGrasshopper = edge.to.startsWith('bacnet://Grasshopper')

        if (!fromIsGrasshopper && !toIsGrasshopper) return

        const grasshopperId = fromIsGrasshopper ? edge.from : edge.to
        const otherId = fromIsGrasshopper ? edge.to : edge.from

        // Only draw subnet connections (same level)
        if (!otherId.startsWith('bacnet://subnet/')) return

        const grasshopperPos = networkInstance.getPosition(grasshopperId)
        const subnetPos = networkInstance.getPosition(otherId)

        if (!grasshopperPos || !subnetPos) return

        // Draw horizontal line connecting Grasshopper to subnet at same level
        canvasContext.beginPath()
        canvasContext.moveTo(grasshopperPos.x, grasshopperPos.y)
        canvasContext.lineTo(subnetPos.x, subnetPos.y)
        canvasContext.stroke()
      })

      canvasContext.restore()
    },
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
      this.$refs.edgeCard?.closeMenu()
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
      this.$refs.edgeCard?.closeMenu()
    },
    hideEdgeAndDevice() {
      if (!this.selectedEdge) return

      const edgeId = this.selectedEdge
      const edgeData = this.network.body.data.edges.get(edgeId)

      this.selectedNode = edgeData.from

      this.hideDevice()
      this.$refs.edgeCard?.closeMenu()
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
      this.$refs.edgeCard?.closeMenu()
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
      this.$refs.edgeCard?.closeMenu()
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
      this.$refs.edgeCard?.closeMenu()
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

      if (prefix) {
        let config = nodeMap[prefix]

        // Check if the config is a nested object
        if (typeof config === 'object' && !config.image) {
          config = config[data.type]

          if (config) {
            if (data.type == 'BBMD') this.allBbmds.push(label)

            return {
              shape: 'image',
              image: config.image,
              label: label.replace(prefix, ''),
              font: { align: 'left', color: 'white', background: 'none' },
              mass: config.mass,
            }
          }
        } else {
          // obfuscated labels
          // if (prefix === 'bacnet://router/') {
          //   const { image, mass } = nodeMap[prefix];
          //   // Generate a random IPv4 address
          //   const randomIP = Array.from({ length: 4 }, () => Math.floor(Math.random() * 256)).join('.');
          //   return {
          //     shape: 'image',
          //     image: image,
          //     label: randomIP,  // Use the randomized IP address as the label
          //     font: { align: 'left', color: "white", background: "none" },
          //     mass: mass,
          //   };
          // }
          // if (prefix === 'bacnet://subnet/') {
          //   const { image, mass } = nodeMap[prefix];
          //   // Generate a random IPv4 address
          //   const randomIP = Array.from({ length: 4 }, () => Math.floor(Math.random() * 256)).join('.') + '/' + Math.floor(Math.random() * 100);
          //   return {
          //     shape: 'image',
          //     image: image,
          //     label: randomIP,  // Use the randomized IP address as the label
          //     font: { align: 'left', color: "white", background: "none" },
          //     mass: mass,
          //   };
          // }
          return {
            shape: 'image',
            image: config.image,
            label: label.replace(prefix, ''),
            font: { align: 'left', color: 'white', background: 'none' },
            mass: config.mass,
            size: config.size || 25,
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
        'bacnet://router/': { image: routerSvg, mass: 2 },
        'bacnet://network/': { image: networkSvg, mass: 2 },
        'bacnet://': {
          Device: { image: deviceSvg, mass: 1 },
          BBMD: {
            image: this.onBbmds.includes(label) ? bbmdOnSvg : bbmdOffSvg,
            mass: 2,
          },
        },
        'bacnet://Grasshopper': {
          image: grasshopperSvg,
          mass: 5,
        },
        'bacnet://subnet/': { image: subnetSvg, mass: 2 },
      }

      return this.createNode(label, data, nodeMap)
    },
    subtractConfig(label, data) {
      // #DF1219
      const nodeMap = {
        'bacnet://router/': { image: routerSubSvg, mass: 2 },
        'bacnet://network/': { image: networkSubSvg, mass: 2 },
        'bacnet://': {
          Device: { image: deviceSubSvg, mass: 1 },
          BBMD: {
            image: this.onBbmds.includes(label) ? bbmdOnSubSvg : bbmdOffSubSvg,
            mass: 4,
          },
        },
        'bacnet://Grasshopper': {
          image: grasshopperSvg,
          mass: 5,
        },
        'bacnet://subnet/': { image: subnetSubSvg, mass: 2 },
      }

      return this.createNode(label, data, nodeMap)
    },
    addConfig(label, data) {
      // #14AE5C
      const nodeMap = {
        'bacnet://router/': { image: routerAddSvg, mass: 2 },
        'bacnet://network/': { image: networkAddSvg, mass: 2 },
        'bacnet://': {
          Device: { image: deviceAddSvg, mass: 1 },
          BBMD: {
            image: this.onBbmds.includes(label) ? bbmdOnAddSvg : bbmdOffAddSvg,
            mass: 4,
          },
        },
        'bacnet://Grasshopper': {
          image: grasshopperSvg,
          mass: 5,
        },
        'bacnet://subnet/': { image: subnetAddSvg, mass: 2 },
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
          } else if (word.toLowerCase() === 'cidr') {
            return 'CIDR'
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

      if (data['total-objects']) {
        this.store.setObjectCardData(data['total-objects'])
      }

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
      if (this.store.currentGraph) {
        this.store.setLoading(true)
      }

      if (this.store.fileName && this.emptyGraph) {
        this.store.setLoading(false)
        this.loaded = true
        this.store.setGlobalError(
          true,
          `Graph <strong>${this.store.fileName}</strong> is empty.`,
          'warning',
          'Warning',
        )
        return
      }

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

      const isTreeLayout = this.store.layoutMode === 'tree'

      // Calculate custom tree positions if in tree mode
      let treePositions = null
      const nodeMap = {}
      this.nodes.forEach(n => {
        nodeMap[n.id] = n
      })

      if (isTreeLayout) {
        treePositions = this.calculateTreeLayout(this.nodes, processedEdges)
        // Store for custom drawing
        this.treeLayoutData = {
          positions: treePositions,
          edges: processedEdges,
          nodeMap: nodeMap,
        }
      } else {
        this.treeLayoutData = null
      }

      const data = {
        nodes: this.nodes.map(node => {
          const baseNode = {
            ...node,
            ...(this.store.compareMode
              ? this.getCompareConfig(node.id, node.data, file1, file2)
              : this.getNodeConfig(node.id, node.data)),
          }
          // Apply custom tree layout positions
          if (isTreeLayout && treePositions && treePositions[node.id]) {
            baseNode.x = treePositions[node.id].x
            baseNode.y = treePositions[node.id].y
            baseNode.fixed = { x: true, y: true } // Lock positions
          }
          return baseNode
        }),
        edges: processedEdges.map(edge => {
          const base = {
            ...edge,
            ...(this.store.compareMode
              ? this.getCompareEdgeColor(edge.data, file1, file2)
              : {}),
          }

          // Hide default edges in tree mode - we draw custom orthogonal edges
          if (isTreeLayout) {
            return {
              ...base,
              hidden: true,
            }
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
          smooth: isTreeLayout
            ? {
                enabled: true,
                type: 'cubicBezier',
                forceDirection: 'vertical',
                roundness: 0.5,
              }
            : {
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
          hover: true,
        },
        physics: isTreeLayout
          ? { enabled: false } // No physics - using custom deterministic positions
          : this.store.physicsConfig,
        layout: {
          // Don't use vis-network's hierarchical layout - we use custom positions
          improvedLayout: false,
          hierarchical: false,
        },
      }

      // Only force-enable physics for force layout
      if (!isTreeLayout) {
        options.physics.enabled = true
      }

      this.network = new Network(container, data, options)

      // For tree layout (no physics), mark as loaded immediately after render
      if (isTreeLayout) {
        // Use nextTick to ensure the network has rendered
        this.$nextTick(() => {
          this.loaded = true
          this.store.setLoading(false)
          // Fit the view to show all nodes
          this.network.fit({ animation: { duration: 300 } })
        })
      }

      this.network.on('stabilizationIterationsDone', () => {
        this.loaded = true
        this.store.setLoading(false)
      })

      // Custom drawing for tree layout (buses and orthogonal edges)
      if (isTreeLayout) {
        this.network.on('afterDrawing', ctx => {
          if (this.treeLayoutData) {
            this.drawOrthogonalEdges(
              ctx,
              this.network,
              this.treeLayoutData.edges,
              this.treeLayoutData.nodeMap,
            )
            this.drawRiserDiagram(
              ctx,
              this.network,
              this.treeLayoutData.positions,
              this.treeLayoutData.edges,
              this.treeLayoutData.nodeMap,
            )
          }
        })
      }

      // eslint-disable-next-line no-unused-vars
      this.network.on('hoverNode', ({ node }) => {
        this.$refs.networkContainer.style.cursor = 'pointer'

        // if (node && !node.includes('bacnet://subnet/') && !node.includes('bacnet://router/') && !node.includes('bacnet://Grasshopper') && !node.includes('bacnet://network/')) {
        //   this.store.runRouteWithCheck(() => this.store.getDeviceInfo(node.split('bacnet://')[1]));
        // }
      })

      this.network.on('blurNode', () => {
        this.$refs.networkContainer.style.cursor = 'default'
      })

      this.network.on('click', params => {
        if (!params.nodes.length) {
          this.unhighlightNode()

          if (!this.store.showBdtEdges) {
            this.store.setBdtEdges(false)
            this.toggleBdtEdges(this.bdtEdges, false)
          }
        }

        if (params.nodes.length > 0) {
          const nodeId = params.nodes[0]
          this.highlightNode(nodeId)
          const clickedNode = data.nodes.find(node => node.id === nodeId)
          this.store.setShowNoteCard(false)

          if (clickedNode) {
            // console.log(clickedNode.data)
            // console.log(clickedNode)
            // const cleanedTitle = clickedNode.id;
            this.store.setObjectCardData(null)
            this.$refs.nodeCard?.$refs.objectCard?.closeCard()
            const nodeType = clickedNode.data.type
            const nodeLabel = clickedNode.data.label

            this.store.setSelectedNode(
              clickedNode.data.type + ' - ' + clickedNode.label,
            )

            this.selectedNodeType = null
            this.store.incDeviceKey()

            if (nodeType == 'BBMD') {
              this.cardInfo = this.formatData(
                Object.keys(clickedNode.data)
                  .sort()
                  .reduce((obj, key) => {
                    obj[key] = clickedNode.data[key]
                    return obj
                  }, {}),
              )
              this.tableLabel = nodeType
              this.altCard = false
              this.selectedNode = clickedNode.id
              this.selectedNodeType = 'BBMD'
              this.store.setNodeLabel(clickedNode.label)
              // show connecting bdt edges
              const matchingEdges = this.bdtEdges.filter(
                edge => edge.from === nodeLabel || edge.to === nodeLabel,
              )
              this.toggleBdtEdges(matchingEdges, true)
            } else {
              this.cardInfo = this.formatData(
                Object.keys(clickedNode.data)
                  .sort()
                  .reduce((obj, key) => {
                    obj[key] = clickedNode.data[key]
                    return obj
                  }, {}),
              )
              this.tableLabel = nodeType
              this.altCard = false
              this.selectedDevice = clickedNode.id
              this.selectedNodeType = nodeType

              this.selectedNode = clickedNode.id
              this.store.setNodeLabel(clickedNode.label)

              // if (nodeType == 'Device' || nodeType == 'BBMD') {
              //   // fetch device info
              //   this.store.setDeviceTimeline(true)
              //   this.store.setDeviceInfo()
              // } else {
              //   this.store.setDeviceTimeline(false)
              // }
            }
            this.$refs.hiddenItemsMenu?.closeMenu()
            this.store.setNodeCard(true)
            this.$refs.edgeCard?.closeMenu()
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
            }
            // else if (this.edgeInfo.type === 'device-on-network') {
            //   // populate this.edgeOptions based on edge to and from node names
            //   const toKey = Object.keys(deviceTo).find(prefix =>
            //     this.edgeInfo.to.startsWith(prefix),
            //   )
            //   const fromKey = Object.keys(deviceFrom).find(prefix =>
            //     this.edgeInfo.from.startsWith(prefix),
            //   )

            //   this.edgeOptions = []

            //   // match prefix in deviceTo
            //   if (toKey) {
            //     if (deviceTo[toKey].title) {
            //       this.edgeOptions.push({
            //         title: deviceTo[toKey].title,
            //         action: deviceTo[toKey].action,
            //       })
            //     }
            //   }
            //   // match prefix in deviceFrom
            //   if (fromKey) {
            //     if (deviceFrom[fromKey].title) {
            //       this.edgeOptions.push({
            //         title: deviceFrom[fromKey].title,
            //         action: deviceFrom[fromKey].action,
            //       })
            //     }
            //   }
            // }
            else {
              // Default options
              // this.edgeOptions = [
              //   { title: 'Hide Edge', action: () => this.hideEdge() },
              // ]
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
            }
            this.store.setEdgeMenu(true)
            this.$refs.nodeCard?.closeCard()
            this.$refs.searchCard?.closeSearch()
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
.search-icon {
  display: flex;
  gap: 20px;
}
.zoom {
  display: flex;
  gap: 10px;
}
.layout-toggle {
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
.load-indicator {
  position: absolute;
  margin: 20px;
}
</style>
