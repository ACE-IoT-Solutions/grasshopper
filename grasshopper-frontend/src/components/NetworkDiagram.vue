<template>
  <div class="network-page">
    <div class="network-wrapper">
      <!-- search -->
      <v-progress-circular
        v-if="store.loading"
        indeterminate
        class="load-indicator"
      ></v-progress-circular>
      <div
        v-if="loaded && !emptyGraph && !store.loading"
        class="search-icon-container"
      >
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
            @click="store.toggleTreeLayout()"
            variant="plain"
            id="no-background-hover"
            :ripple="false"
            icon=""
            size="medium"
            density="compact"
          >
            <v-tooltip
              :text="
                store.treeLayout
                  ? 'Switch to Classic Layout'
                  : 'Switch to Tree Layout'
              "
              bottom
              delay="1000"
            >
              <template v-slot:activator="{ props }">
                <v-icon v-bind="props">{{
                  store.treeLayout ? 'mdi-graph' : 'mdi-file-tree'
                }}</v-icon>
              </template>
            </v-tooltip>
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
          v-if="!store.treeLayout && showHiddenMenuButton"
          @click="(store.setHiddenMenu(true), store.setNodeCard(false))"
          variant="plain"
          >Hidden Items
        </v-btn>
        <v-btn
          v-if="store.treeLayout"
          variant="plain"
          @click="store.setMinimapToggled(true)"
          ><v-tooltip text="Minimap" bottom delay="1000">
            <template v-slot:activator="{ props }">
              <v-icon v-bind="props">mdi-map</v-icon>
            </template>
          </v-tooltip></v-btn
        >
      </div>
      <!-- Minimap for tree layout navigation -->
      <NetworkMinimap
        v-if="loaded && store.treeLayout && network && store.minimapToggled"
        :network="network"
        :treePositions="treeLayoutData?.positions"
        :store="store"
      />
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
import NetworkMinimap from '@/components/NetworkMinimap.vue'
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
    NetworkMinimap,
    // NoteCard,
  },
  mounted() {
    this.generate()
  },
  watch: {
    // eslint-disable-next-line no-unused-vars
    'store.physicsConfig'(newVal, oldVal) {
      this.network.setOptions({ physics: newVal })
    },
    'store.showBdtEdges'(visible) {
      const allEdges = this.network.body.data.edges.get()
      this.toggleBdtEdges(allEdges, visible)
    },
    'store.treeLayout'() {
      // Regenerate the graph when layout mode changes
      if (this.network) {
        this.store.setMinimapToggled(false)

        // Save hidden node IDs before regenerating (generate() creates a fresh network)
        const savedHiddenNetworkIds = [...this.hiddenNetworkIds]
        const savedHiddenRouterIds = [...this.hiddenRouterIds]
        const savedHiddenDeviceIds = [...this.hiddenDeviceIds]
        const savedHiddenBbmdIds = [...this.hiddenBbmdIds]
        const savedHiddenSubnetIds = [...this.hiddenSubnetIds]

        this.generate()

        // When returning to normal graph, re-apply the saved hidden state
        if (!this.store.treeLayout) {
          // Clear stale visibility data from the old network instance
          this.networkVisibility = {}
          this.routerVisibility = {}
          this.deviceVisibility = {}
          this.bbmdVisibility = {}
          this.subnetVisibility = {}
          this.hiddenNetworkIds = []
          this.hiddenRouterIds = []
          this.hiddenDeviceIds = []
          this.hiddenBbmdIds = []
          this.hiddenSubnetIds = []

          // Re-hide all previously hidden nodes in the new network
          savedHiddenNetworkIds.forEach(id =>
            this.hideSet(
              this.networkVisibility,
              id,
              this.hiddenNetworkIds,
              'network',
            ),
          )
          savedHiddenRouterIds.forEach(id =>
            this.hideSet(
              this.routerVisibility,
              id,
              this.hiddenRouterIds,
              'router',
            ),
          )
          savedHiddenBbmdIds.forEach(id =>
            this.hideSet(this.bbmdVisibility, id, this.hiddenBbmdIds, 'bbmd'),
          )
          savedHiddenSubnetIds.forEach(id =>
            this.hideSet(
              this.subnetVisibility,
              id,
              this.hiddenSubnetIds,
              'subnet',
            ),
          )

          // Re-hide devices (hideDevice reads this.selectedNode)
          const prevSelectedNode = this.selectedNode
          savedHiddenDeviceIds.forEach(id => {
            this.selectedNode = id
            this.hideDevice()
          })
          this.selectedNode = prevSelectedNode
        }
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
      networkRowInfo: {}, // Track multi-row device layouts per network
      collapsedNetworks: new Set(), // Track collapsed network nodes
      networkDeviceCounts: {}, // Cache device counts per network for labels
      deviceRowMap: {}, // Track which row each device is in
      selectedBbmdForTree: null, // Track selected BBMD for BDT edge highlighting in tree mode
      drawnEdgeGeometry: [], // Store edge geometry for click detection in tree mode

      // showNoteCard: false,
    }
  },
  methods: {
    toggleLayout() {
      this.store.toggleLayoutMode()
    },
    // Helper to calculate distance from point to line segment
    pointToSegmentDistance(px, py, x1, y1, x2, y2) {
      const dx = x2 - x1
      const dy = y2 - y1
      const lengthSquared = dx * dx + dy * dy

      if (lengthSquared === 0) {
        // Segment is a point
        return Math.sqrt((px - x1) ** 2 + (py - y1) ** 2)
      }

      // Project point onto line, clamped to segment
      let t = Math.max(
        0,
        Math.min(1, ((px - x1) * dx + (py - y1) * dy) / lengthSquared),
      )
      const projX = x1 + t * dx
      const projY = y1 + t * dy

      return Math.sqrt((px - projX) ** 2 + (py - projY) ** 2)
    },
    // Find edge at canvas point for tree mode click detection
    findEdgeAtPoint(canvasX, canvasY, threshold = 8) {
      if (!this.drawnEdgeGeometry || this.drawnEdgeGeometry.length === 0)
        return null

      for (const edgeGeo of this.drawnEdgeGeometry) {
        // Check each segment of the edge path
        for (let i = 0; i < edgeGeo.points.length - 1; i++) {
          const p1 = edgeGeo.points[i]
          const p2 = edgeGeo.points[i + 1]
          const dist = this.pointToSegmentDistance(
            canvasX,
            canvasY,
            p1.x,
            p1.y,
            p2.x,
            p2.y,
          )
          if (dist < threshold) {
            return edgeGeo.edge
          }
        }
      }
      return null
    },
    toggleNetworkCollapse(networkId) {
      // Toggle collapse state for a network node
      if (this.collapsedNetworks.has(networkId)) {
        this.collapsedNetworks.delete(networkId)
      } else {
        this.collapsedNetworks.add(networkId)
      }
      // Regenerate the layout
      this.generate()
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
      const maxDevicesPerRow = 12 // Wrap devices after this many per row
      const deviceRowHeight = 110 // Height for additional device rows (needs room for icon + label + bus)

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
          // eslint-disable-next-line no-unused-vars
          childLevel = fromLevel
        } else {
          return // Same level, skip
        }

        // Child picks the closest parent (highest level that's still less than child)
        if (
          !childToParent[childId] ||
          parentLevel >
            this.getNodeLevel(
              childToParent[childId],
              nodeMap[childToParent[childId]]?.data?.type,
            )
        ) {
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

      // Detect devices directly connected to subnet - move to level 2 (router level)
      // These are IP devices that don't go through a network number
      const adjustedLevel = {} // nodeId -> adjusted level
      levelGroups[4].forEach(deviceId => {
        const parentId = childToParent[deviceId]
        if (parentId && parentId.startsWith('bacnet://subnet/')) {
          // This device connects directly to a subnet - place at router level
          adjustedLevel[deviceId] = 2
          // Move from level 4 to level 2 group
          levelGroups[2].push(deviceId)
        }
      })
      // Remove moved devices from level 4
      levelGroups[4] = levelGroups[4].filter(id => !adjustedLevel[id])

      // Helper to get effective level (adjusted or original)
      const getEffectiveLevel = nodeId => {
        if (adjustedLevel[nodeId] !== undefined) return adjustedLevel[nodeId]
        return this.getNodeLevel(nodeId, nodeMap[nodeId]?.data?.type)
      }

      // BOTTOM-UP: Group all nodes by their closest parent, place groups together
      // Step 1: Group nodes at each level by their parent
      const nodesByParent = {} // parentId -> [childIds]
      const orphansByLevel = { 0: [], 1: [], 2: [], 3: [], 4: [] }

      // Categorize all nodes
      for (let level = 4; level >= 0; level--) {
        levelGroups[level].forEach(nodeId => {
          const parentId = childToParent[nodeId]
          if (parentId) {
            if (!nodesByParent[parentId]) nodesByParent[parentId] = []
            nodesByParent[parentId].push(nodeId)
          } else {
            orphansByLevel[level].push(nodeId)
          }
        })
      }

      // Step 2: Place all leaf nodes (level 4 devices) first
      let x = 0

      // Helper to get sort key for deterministic ordering
      const getSortKey = nodeId => {
        const node = nodeMap[nodeId]
        if (!node) return nodeId

        // Try device instance first (numeric sort)
        const deviceInstance = node.data?.['device-instance']
        if (deviceInstance !== undefined) {
          return String(deviceInstance).padStart(10, '0')
        }

        // Fall back to label
        if (node.label) return node.label

        // Fall back to node ID
        return nodeId
      }

      // Sort children in parentToChildren for deterministic ordering
      Object.keys(parentToChildren).forEach(parentId => {
        parentToChildren[parentId].sort((a, b) => {
          return getSortKey(a).localeCompare(getSortKey(b), undefined, {
            numeric: true,
          })
        })
      })

      // Helper to recursively get all leaf descendants (in sorted order)
      const getLeafDescendants = nodeId => {
        const children = parentToChildren[nodeId] || []
        if (children.length === 0) {
          return [nodeId]
        }
        let leaves = []
        children.forEach(childId => {
          leaves = leaves.concat(getLeafDescendants(childId))
        })
        return leaves
      }

      // Find all root nodes (nodes without parents in the layout)
      const rootNodes = []
      for (let level = 0; level <= 4; level++) {
        levelGroups[level].forEach(nodeId => {
          if (!childToParent[nodeId]) {
            rootNodes.push(nodeId)
          }
        })
      }

      // Sort root nodes for deterministic ordering
      rootNodes.sort((a, b) => {
        const levelA = getEffectiveLevel(a)
        const levelB = getEffectiveLevel(b)
        if (levelA !== levelB) return levelA - levelB
        return getSortKey(a).localeCompare(getSortKey(b), undefined, {
          numeric: true,
        })
      })

      // Track row info for each network (for multi-row device layout)
      const networkRowInfo = {} // networkId -> { rows: number, startX: number, width: number }
      const networkDeviceCounts = {} // networkId -> device count (for collapsed labels)

      // Track which row each device is in (for edge drawing)
      const deviceRowMap = {} // deviceId -> { row: number, networkId: string }

      // Helper to place devices with row wrapping
      const placeDevicesWithWrapping = (devices, baseY, startX, networkId) => {
        let currentX = startX
        let row = 0
        let rowStartX = startX
        let maxX = startX
        let maxRow = 0

        devices.forEach((deviceId, index) => {
          const col = index % maxDevicesPerRow
          if (col === 0 && index > 0) {
            row++
          }
          // Reset X for each row
          currentX = rowStartX + col * nodeSpacing

          const deviceLevel = getEffectiveLevel(deviceId)
          const yOffset = row * deviceRowHeight
          positions[deviceId] = {
            x: currentX,
            y: deviceLevel * levelHeight + yOffset,
          }

          // Track which row this device is in
          deviceRowMap[deviceId] = { row, networkId }

          maxX = Math.max(maxX, currentX)
          maxRow = Math.max(maxRow, row)
        })

        // Calculate actual width based on devices placed
        // First row width determines the network's horizontal extent
        const firstRowDevices = Math.min(devices.length, maxDevicesPerRow)
        const actualWidth = firstRowDevices * nodeSpacing

        return {
          rows: maxRow + 1,
          width: actualWidth,
          endX: startX + actualWidth,
          startX: startX,
        }
      }

      // Place each root's subtree
      rootNodes.forEach(rootId => {
        const rootLevel = getEffectiveLevel(rootId)
        const leaves = getLeafDescendants(rootId)

        if (leaves.length > 0 && leaves[0] !== rootId) {
          // Group leaves by their parent network (level 3)
          const devicesByNetwork = {}
          const nonNetworkDevices = []

          leaves.forEach(leafId => {
            const parentId = childToParent[leafId]
            const parentLevel = parentId ? getEffectiveLevel(parentId) : -1

            if (parentLevel === 3) {
              // Device under a network - group by network
              if (!devicesByNetwork[parentId]) devicesByNetwork[parentId] = []
              devicesByNetwork[parentId].push(leafId)
            } else {
              // Device not under a network (e.g., directly on subnet/router)
              nonNetworkDevices.push(leafId)
            }
          })

          // Place devices grouped by network with wrapping
          const networkIds = Object.keys(devicesByNetwork).sort((a, b) =>
            getSortKey(a).localeCompare(getSortKey(b), undefined, {
              numeric: true,
            }),
          )

          // Store device counts for all networks (for collapsed labels)
          networkIds.forEach(networkId => {
            networkDeviceCounts[networkId] = devicesByNetwork[networkId].length
          })

          networkIds.forEach(networkId => {
            const devices = devicesByNetwork[networkId]
            const isCollapsed = this.collapsedNetworks.has(networkId)

            if (isCollapsed) {
              // Collapsed network: don't place devices, just reserve minimal space
              networkRowInfo[networkId] = {
                rows: 0,
                startX: x,
                width: nodeSpacing,
                collapsed: true,
              }
              x += nodeSpacing * 1.5 // Minimal space for collapsed network
            } else {
              // Expanded network: place devices with wrapping
              const baseY = 4 // Device level
              const result = placeDevicesWithWrapping(
                devices,
                baseY,
                x,
                networkId,
              )
              networkRowInfo[networkId] = {
                rows: result.rows,
                startX: result.startX,
                width: result.width,
                collapsed: false,
              }
              x = result.endX + nodeSpacing * 0.5 // Gap between networks
            }
          })

          // Place non-network devices (on subnet/router level)
          nonNetworkDevices.forEach(leafId => {
            const leafLevel = getEffectiveLevel(leafId)
            positions[leafId] = { x: x, y: leafLevel * levelHeight }
            x += nodeSpacing
          })
        } else {
          // Root is itself a leaf or has no descendants
          positions[rootId] = { x: x, y: rootLevel * levelHeight }
          x += nodeSpacing
        }
        x += nodeSpacing * 0.5 // Gap between subtrees
      })

      // Store network row info, device counts, and row mapping for bus drawing and labels
      this.networkRowInfo = networkRowInfo
      this.networkDeviceCounts = networkDeviceCounts
      this.deviceRowMap = deviceRowMap

      // Step 3: Bottom-up - center parents over their children
      for (let level = 3; level >= 0; level--) {
        levelGroups[level].forEach(nodeId => {
          if (positions[nodeId]) return // Already positioned

          // Check if this is a collapsed network
          const isCollapsed = level === 3 && this.collapsedNetworks.has(nodeId)

          if (isCollapsed) {
            // Collapsed network: position based on reserved space in networkRowInfo
            const info = networkRowInfo[nodeId]
            if (info) {
              positions[nodeId] = {
                x: info.startX + nodeSpacing / 2,
                y: level * levelHeight,
              }
            } else {
              positions[nodeId] = { x: x, y: level * levelHeight }
              x += nodeSpacing
            }
            return
          }

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
            // No positioned children, place at current x
            positions[nodeId] = { x: x, y: level * levelHeight }
            x += nodeSpacing
          }
        })
      }

      // Step 4: Ensure ALL nodes have positions (catch any missed)
      nodes.forEach(n => {
        if (!positions[n.id]) {
          const level = getEffectiveLevel(n.id)
          positions[n.id] = { x: x, y: level * levelHeight }
          x += nodeSpacing
        }
      })

      // Step 5: Position Grasshopper next to its primary (nearest connected) subnet
      // rather than as an isolated orphan at the far edge of the layout
      const grasshopperNodes = nodes.filter(n =>
        n.id.startsWith('bacnet://Grasshopper'),
      )
      grasshopperNodes.forEach(ghNode => {
        // Find subnets connected to this Grasshopper node
        const connectedSubnets = edges
          .filter(e => e.from === ghNode.id || e.to === ghNode.id)
          .map(e => (e.from === ghNode.id ? e.to : e.from))
          .filter(id => id.startsWith('bacnet://subnet/') && positions[id])

        if (connectedSubnets.length > 0 && positions[ghNode.id]) {
          // Find the nearest connected subnet by current position
          let nearestSubnet = connectedSubnets[0]
          let nearestDist = Infinity
          connectedSubnets.forEach(subnetId => {
            const dist = Math.abs(
              positions[ghNode.id].x - positions[subnetId].x,
            )
            if (dist < nearestDist) {
              nearestDist = dist
              nearestSubnet = subnetId
            }
          })

          // Find the rightmost node in the subnet's subtree to place Grasshopper after it
          const subnetChildren = parentToChildren[nearestSubnet] || []
          let maxSubtreeX = positions[nearestSubnet].x
          const getAllDescendantPositions = nodeId => {
            if (positions[nodeId]) {
              maxSubtreeX = Math.max(maxSubtreeX, positions[nodeId].x)
            }
            const children = parentToChildren[nodeId] || []
            children.forEach(cid => getAllDescendantPositions(cid))
          }
          subnetChildren.forEach(cid => getAllDescendantPositions(cid))

          // Place Grasshopper to the right of the subnet's subtree at the subnet level
          positions[ghNode.id] = {
            x: maxSubtreeX + nodeSpacing * 1.5,
            y: positions[nearestSubnet].y,
          }
        }
      })

      // Store the parent-child relationships and adjusted levels for edge drawing
      this.layoutParentChild = {
        childToParent,
        parentToChildren,
        adjustedLevel,
      }

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
        if (
          fromLevel === 3 &&
          toLevel === 4 &&
          nodePositions[fromId] &&
          nodePositions[toId]
        ) {
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
        if (
          toLevel === 3 &&
          fromLevel === 4 &&
          nodePositions[toId] &&
          nodePositions[fromId]
        ) {
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

      // Draw network buses (horizontal lines) - one per row for multi-row networks
      canvasContext.save()
      canvasContext.strokeStyle = '#FFD700' // Gold color for buses
      canvasContext.lineWidth = 4

      const deviceRowHeight = 110 // Must match layout constant
      const padding = 35 // Padding on left/right of buses

      Object.keys(networkBuses).forEach(networkId => {
        const bus = networkBuses[networkId]
        if (bus.children.length === 0) return

        // Skip collapsed networks - they don't have visible device children
        if (this.collapsedNetworks.has(networkId)) return

        const networkInfo = this.networkRowInfo[networkId]
        const numRows = networkInfo ? networkInfo.rows : 1

        // Group children by their row
        const childrenByRow = {}
        bus.childIds.forEach((childId, idx) => {
          const deviceInfo = this.deviceRowMap[childId]
          const row = deviceInfo ? deviceInfo.row : 0
          if (!childrenByRow[row]) childrenByRow[row] = []
          childrenByRow[row].push(bus.children[idx])
        })

        // Find the leftmost X across all rows for the vertical connector
        let overallMinX = Infinity
        Object.values(childrenByRow).forEach(rowChildren => {
          rowChildren.forEach(childPos => {
            overallMinX = Math.min(overallMinX, childPos.x)
          })
        })
        const connectorX = overallMinX - padding

        // Draw a horizontal bus for each row
        const levelHeight = 100 // Must match layout constant
        const busGapAboveDevices = 55

        const rowBusYPositions = [] // Track Y positions for vertical connector

        for (let row = 0; row < numRows; row++) {
          const rowChildren = childrenByRow[row] || []
          if (rowChildren.length === 0) continue

          // Find extent of children in this row
          let minX = Infinity
          let maxX = -Infinity
          rowChildren.forEach(childPos => {
            minX = Math.min(minX, childPos.x)
            maxX = Math.max(maxX, childPos.x)
          })

          // Bus Y position: just above the devices in this row
          // Row 0: use network position (nodes will render on top)
          // Row 1+: position just above that row's devices
          let busY
          if (row === 0) {
            busY = bus.pos.y
          } else {
            // Devices in row r are at: network.y + levelHeight + r * deviceRowHeight
            // Bus should be busGapAboveDevices above the devices
            busY =
              bus.pos.y +
              levelHeight +
              row * deviceRowHeight -
              busGapAboveDevices
          }

          rowBusYPositions.push(busY)

          canvasContext.beginPath()
          canvasContext.moveTo(connectorX - 2, busY) // Extend slightly past connector to close gap
          canvasContext.lineTo(maxX + padding, busY)
          canvasContext.stroke()
        }

        // Draw vertical connector between row buses (on the left side)
        if (rowBusYPositions.length > 1) {
          const topBusY = rowBusYPositions[0]
          const bottomBusY = rowBusYPositions[rowBusYPositions.length - 1]

          canvasContext.beginPath()
          canvasContext.moveTo(connectorX, topBusY)
          canvasContext.lineTo(connectorX, bottomBusY)
          canvasContext.stroke()
        }
      })

      canvasContext.restore()

      // Store bus info for device drop connections
      this.networkBusData = networkBuses
    },
    drawOrthogonalEdges(ctx, networkInstance, edges, nodeMap) {
      // Draw orthogonal edges using actual node positions
      if (!networkInstance || !this.layoutParentChild) return

      const canvasContext = ctx
      const { childToParent, adjustedLevel } = this.layoutParentChild

      // Helper to get effective level
      const getEffectiveLevel = nodeId => {
        if (adjustedLevel && adjustedLevel[nodeId] !== undefined)
          return adjustedLevel[nodeId]
        return this.getNodeLevel(nodeId, nodeMap[nodeId]?.data?.type)
      }

      canvasContext.save()

      // Clear and prepare to store edge geometry for click detection
      this.drawnEdgeGeometry = []

      const deviceRowHeight = 110 // Must match layout constant
      const levelHeight = 100 // Must match layout constant
      const busGapAboveDevices = 55

      // Helper to store edge geometry for click detection
      const storeEdgeGeometry = (edge, points) => {
        this.drawnEdgeGeometry.push({ edge, points })
      }

      // Helper to get edge style based on edge type
      // Use consistent width (2) for all colored edges to match bus thickness
      const getEdgeStyle = edgeLabel => {
        if (!edgeLabel)
          return { color: 'rgba(140, 140, 140, 0.7)', width: 2, dash: [] }

        if (edgeLabel.includes('bbmd-broadcast-domain')) {
          return { color: 'rgb(200, 100, 200)', width: 2, dash: [] } // Purple for BBMD→Subnet
        }
        if (edgeLabel.includes('bacnet-router-on-subnet')) {
          return { color: 'rgb(220, 80, 80)', width: 2, dash: [] } // Red for Router→Subnet
        }
        if (edgeLabel.includes('device-on-subnet')) {
          return { color: 'rgb(100, 180, 100)', width: 2, dash: [] } // Green for Device→Subnet
        }
        if (edgeLabel.includes('device-on-network')) {
          return { color: 'rgba(140, 140, 140, 0.7)', width: 2, dash: [] } // Grey for Device→Network (drops to bus)
        }
        if (edgeLabel.includes('bdt-entry')) {
          return { color: 'rgb(255, 165, 0)', width: 2, dash: [5, 5] } // Orange dashed for BDT
        }
        if (edgeLabel.includes('fdr-entry')) {
          return { color: 'rgb(0, 200, 255)', width: 2, dash: [5, 5] } // Cyan dashed for FDT
        }
        return { color: 'rgba(140, 140, 140, 0.7)', width: 2, dash: [] } // Default grey
      }

      // Find edge label for a given parent-child pair
      const findEdgeLabel = (fromId, toId) => {
        const edge = edges.find(
          e =>
            (e.from === fromId && e.to === toId) ||
            (e.from === toId && e.to === fromId),
        )
        return edge?.label || ''
      }

      // Draw device connections
      Object.keys(childToParent).forEach(childId => {
        const parentId = childToParent[childId]

        // Skip devices under collapsed networks
        if (
          parentId.startsWith('bacnet://network/') &&
          this.collapsedNetworks.has(parentId)
        ) {
          return
        }

        const parentPos = networkInstance.getPosition(parentId)
        const childPos = networkInstance.getPosition(childId)

        if (!parentPos || !childPos) return

        const parentLevel = getEffectiveLevel(parentId)
        const childLevel = getEffectiveLevel(childId)

        // Get edge style based on edge type
        const edgeLabel = findEdgeLabel(parentId, childId)
        const style = getEdgeStyle(edgeLabel)
        canvasContext.strokeStyle = style.color
        canvasContext.lineWidth = style.width
        canvasContext.setLineDash(style.dash)

        // Find the actual edge object for storing geometry
        const edgeObj = edges.find(
          e =>
            (e.from === parentId && e.to === childId) ||
            (e.from === childId && e.to === parentId),
        )

        // Device to Network connections (level 3 -> 4)
        // Each device connects to the bus directly above it (no overlap)
        if (parentLevel === 3 && childLevel === 4) {
          const deviceRowInfo = this.deviceRowMap[childId]
          const row = deviceRowInfo ? deviceRowInfo.row : 0

          // Bus Y position: matches drawRiserDiagram calculation
          // Row 0: use network position
          // Row 1+: position just above that row's devices
          let busY
          if (row === 0) {
            busY = parentPos.y
          } else {
            busY =
              parentPos.y +
              levelHeight +
              row * deviceRowHeight -
              busGapAboveDevices
          }

          // Simple vertical drop from device to its row's bus
          const points = [
            { x: childPos.x, y: childPos.y - 15 },
            { x: childPos.x, y: busY },
          ]
          canvasContext.beginPath()
          canvasContext.moveTo(points[0].x, points[0].y)
          canvasContext.lineTo(points[1].x, points[1].y)
          canvasContext.stroke()
          if (edgeObj) storeEdgeGeometry(edgeObj, points)
          return
        }

        // Check if parent and child are nearly vertically aligned
        const horizontalOffset = Math.abs(parentPos.x - childPos.x)

        if (horizontalOffset < 30) {
          // Nearly aligned - draw simple vertical line
          const points = [
            { x: parentPos.x, y: parentPos.y + 20 },
            { x: childPos.x, y: childPos.y - 20 },
          ]
          canvasContext.beginPath()
          canvasContext.moveTo(points[0].x, points[0].y)
          canvasContext.lineTo(points[1].x, points[1].y)
          canvasContext.stroke()
          if (edgeObj) storeEdgeGeometry(edgeObj, points)
        } else {
          // Offset - draw orthogonal with waypoint closer to child
          const waypointY = childPos.y - 40
          const points = [
            { x: parentPos.x, y: parentPos.y + 20 },
            { x: parentPos.x, y: waypointY },
            { x: childPos.x, y: waypointY },
            { x: childPos.x, y: childPos.y - 20 },
          ]

          canvasContext.beginPath()
          canvasContext.moveTo(points[0].x, points[0].y)
          canvasContext.lineTo(points[1].x, points[1].y)
          canvasContext.lineTo(points[2].x, points[2].y)
          canvasContext.lineTo(points[3].x, points[3].y)
          canvasContext.stroke()
          if (edgeObj) storeEdgeGeometry(edgeObj, points)
        }
      })

      // Track drawn edges to avoid double-drawing in the catch-all section below
      const drawnEdges = new Set()
      Object.keys(childToParent).forEach(childId => {
        const parentId = childToParent[childId]
        drawnEdges.add(`${parentId}-${childId}`)
        drawnEdges.add(`${childId}-${parentId}`)
      })

      // Special handling for Grasshopper node - draw its subnet connection
      // Grasshopper is at level 1 (same as subnet) so it gets skipped by parent-child logic
      // Only draw to the nearest subnet (the one Grasshopper is directly on).
      // Connectivity to other subnets is via BDT entries shown through BBMD edges.
      const grasshopperSubnetEdges = edges.filter(edge => {
        const fromIsGrasshopper = edge.from.startsWith('bacnet://Grasshopper')
        const toIsGrasshopper = edge.to.startsWith('bacnet://Grasshopper')
        if (!fromIsGrasshopper && !toIsGrasshopper) return false
        const otherId = fromIsGrasshopper ? edge.to : edge.from
        return otherId.startsWith('bacnet://subnet/')
      })

      // Find the nearest subnet to Grasshopper (the one it's physically on)
      let nearestSubnetEdge = null
      let nearestDist = Infinity
      grasshopperSubnetEdges.forEach(edge => {
        const fromIsGrasshopper = edge.from.startsWith('bacnet://Grasshopper')
        const grasshopperId = fromIsGrasshopper ? edge.from : edge.to
        const subnetId = fromIsGrasshopper ? edge.to : edge.from
        const grasshopperPos = networkInstance.getPosition(grasshopperId)
        const subnetPos = networkInstance.getPosition(subnetId)
        if (!grasshopperPos || !subnetPos) return
        const dist =
          Math.abs(grasshopperPos.x - subnetPos.x) +
          Math.abs(grasshopperPos.y - subnetPos.y)
        if (dist < nearestDist) {
          nearestDist = dist
          nearestSubnetEdge = edge
        }
        // Track ALL Grasshopper-subnet edges as drawn so catch-all skips them
        drawnEdges.add(`${edge.from}-${edge.to}`)
        drawnEdges.add(`${edge.to}-${edge.from}`)
      })

      if (nearestSubnetEdge) {
        const fromIsGrasshopper = nearestSubnetEdge.from.startsWith(
          'bacnet://Grasshopper',
        )
        const grasshopperId = fromIsGrasshopper
          ? nearestSubnetEdge.from
          : nearestSubnetEdge.to
        const subnetId = fromIsGrasshopper
          ? nearestSubnetEdge.to
          : nearestSubnetEdge.from
        const grasshopperPos = networkInstance.getPosition(grasshopperId)
        const subnetPos = networkInstance.getPosition(subnetId)

        if (grasshopperPos && subnetPos) {
          // Grasshopper connections in teal/cyan
          canvasContext.strokeStyle = 'rgba(0, 180, 180, 0.9)'
          canvasContext.lineWidth = 2
          canvasContext.setLineDash([])

          // Draw horizontal line connecting Grasshopper to its nearest subnet
          const points = [
            { x: grasshopperPos.x, y: grasshopperPos.y },
            { x: subnetPos.x, y: subnetPos.y },
          ]
          canvasContext.beginPath()
          canvasContext.moveTo(points[0].x, points[0].y)
          canvasContext.lineTo(points[1].x, points[1].y)
          canvasContext.stroke()
          storeEdgeGeometry(nearestSubnetEdge, points)
        }
      }

      // Draw any edges not covered by childToParent or Grasshopper handler
      // This catches edges between nodes at the same level or edges missed by the hierarchy
      edges.forEach(edge => {
        // Skip if already drawn via childToParent or Grasshopper handler
        if (drawnEdges.has(`${edge.from}-${edge.to}`)) return

        // Skip BDT/FDT entries (BBMD connections) - handled separately when BBMD selected
        if (
          edge.label &&
          (edge.label.includes('bdt-entry') || edge.label.includes('fdr-entry'))
        )
          return

        // Skip device-on-network edges (handled by bus drawing)
        if (edge.label && edge.label.includes('device-on-network')) return

        const fromPos = networkInstance.getPosition(edge.from)
        const toPos = networkInstance.getPosition(edge.to)

        if (!fromPos || !toPos) return

        // Apply edge-type-based styling
        const style = getEdgeStyle(edge.label)
        canvasContext.strokeStyle = style.color
        canvasContext.lineWidth = style.width
        canvasContext.setLineDash(style.dash)

        const fromLevel = getEffectiveLevel(edge.from)
        const toLevel = getEffectiveLevel(edge.to)

        // Determine parent/child for drawing direction
        let parentPos, childPos
        if (fromLevel < toLevel) {
          parentPos = fromPos
          childPos = toPos
        } else if (toLevel < fromLevel) {
          parentPos = toPos
          childPos = fromPos
        } else {
          // Same level - draw simple line
          const points = [
            { x: fromPos.x, y: fromPos.y },
            { x: toPos.x, y: toPos.y },
          ]
          canvasContext.beginPath()
          canvasContext.moveTo(points[0].x, points[0].y)
          canvasContext.lineTo(points[1].x, points[1].y)
          canvasContext.stroke()
          storeEdgeGeometry(edge, points)
          return
        }

        // Draw orthogonal edge
        const horizontalOffset = Math.abs(parentPos.x - childPos.x)

        if (horizontalOffset < 30) {
          const points = [
            { x: parentPos.x, y: parentPos.y + 20 },
            { x: childPos.x, y: childPos.y - 20 },
          ]
          canvasContext.beginPath()
          canvasContext.moveTo(points[0].x, points[0].y)
          canvasContext.lineTo(points[1].x, points[1].y)
          canvasContext.stroke()
          storeEdgeGeometry(edge, points)
        } else {
          const waypointY = childPos.y - 40
          const points = [
            { x: parentPos.x, y: parentPos.y + 20 },
            { x: parentPos.x, y: waypointY },
            { x: childPos.x, y: waypointY },
            { x: childPos.x, y: childPos.y - 20 },
          ]
          canvasContext.beginPath()
          canvasContext.moveTo(points[0].x, points[0].y)
          canvasContext.lineTo(points[1].x, points[1].y)
          canvasContext.lineTo(points[2].x, points[2].y)
          canvasContext.lineTo(points[3].x, points[3].y)
          canvasContext.stroke()
          storeEdgeGeometry(edge, points)
        }
      })

      // Draw BDT/FDT edges in tree mode
      // Always show these connections; highlight edges for selected BBMD
      {
        const selectedBbmdLabel = this.selectedBbmdForTree
          ? nodeMap[this.selectedBbmdForTree]?.label
          : null

        edges.forEach(edge => {
          if (!edge.label) return
          const isBdt = edge.label.includes('bdt-entry')
          const isFdt = edge.label.includes('fdr-entry')
          if (!isBdt && !isFdt) return

          const fromPos = networkInstance.getPosition(edge.from)
          const toPos = networkInstance.getPosition(edge.to)

          if (!fromPos || !toPos) return

          // Determine if this edge connects to the selected BBMD (for highlighting)
          const fromLabel = nodeMap[edge.from]?.label
          const toLabel = nodeMap[edge.to]?.label
          const isHighlighted =
            selectedBbmdLabel &&
            (fromLabel === selectedBbmdLabel || toLabel === selectedBbmdLabel)

          const opacity = isHighlighted ? 0.9 : 0.5

          // Different styles for BDT vs FDT
          if (isBdt) {
            canvasContext.strokeStyle = `rgba(255, 165, 0, ${opacity})` // Orange for BDT
            canvasContext.setLineDash([6, 4])
          } else {
            canvasContext.strokeStyle = `rgba(0, 200, 255, ${opacity})` // Cyan for FDT
            canvasContext.setLineDash([4, 2])
          }
          canvasContext.lineWidth = 2

          // Route above both nodes with orthogonal path
          const midY = Math.min(fromPos.y, toPos.y) - 40
          const points = [
            { x: fromPos.x, y: fromPos.y - 20 },
            { x: fromPos.x, y: midY },
            { x: toPos.x, y: midY },
            { x: toPos.x, y: toPos.y - 20 },
          ]

          canvasContext.beginPath()
          canvasContext.moveTo(points[0].x, points[0].y)
          canvasContext.lineTo(points[1].x, points[1].y)
          canvasContext.lineTo(points[2].x, points[2].y)
          canvasContext.lineTo(points[3].x, points[3].y)
          canvasContext.stroke()
          storeEdgeGeometry(edge, points)
        })

        canvasContext.setLineDash([])
      }

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
          (edge.label.includes('bdt-entry') ||
            edge.label.includes('fdr-entry')) &&
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
        // eslint-disable-next-line no-unused-vars
        const isBdtOrFdt =
          edge.label.includes('bdt-entry') || edge.label.includes('fdr-entry')
        // For BDT edges, both endpoints should be BBMDs
        // For FDT edges, only one endpoint (the BBMD with the FDT) needs to be a BBMD
        const isBdtBetweenBbmds =
          edge.label.includes('bdt-entry') &&
          this.allBbmds.includes(edge.from) &&
          this.allBbmds.includes(edge.to)
        const isFdtFromBbmd =
          edge.label.includes('fdr-entry') &&
          (this.allBbmds.includes(edge.from) || this.allBbmds.includes(edge.to))

        if (
          (isBdtBetweenBbmds || isFdtFromBbmd) &&
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

      const isTreeLayout = this.store.treeLayout

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

      // Build parent lookup for collapsed network detection
      const deviceParentNetwork = {}
      if (isTreeLayout && this.layoutParentChild) {
        const { childToParent } = this.layoutParentChild
        Object.keys(childToParent).forEach(childId => {
          const parentId = childToParent[childId]
          if (parentId && parentId.startsWith('bacnet://network/')) {
            deviceParentNetwork[childId] = parentId
          }
        })
      }

      const data = {
        nodes: this.nodes.map(node => {
          const baseNode = {
            ...node,
            ...(this.store.compareMode
              ? this.getCompareConfig(node.id, node.data, file1, file2)
              : this.getNodeConfig(node.id, node.data)),
          }

          // Handle collapsed networks in tree mode
          if (isTreeLayout) {
            // Check if this is a device under a collapsed network
            const parentNetworkId = deviceParentNetwork[node.id]
            if (
              parentNetworkId &&
              this.collapsedNetworks.has(parentNetworkId)
            ) {
              // Hide this device - its network is collapsed
              baseNode.hidden = true
            }

            // Update label for collapsed network nodes
            if (
              node.id.startsWith('bacnet://network/') &&
              this.collapsedNetworks.has(node.id)
            ) {
              const deviceCount = this.networkDeviceCounts[node.id] || 0
              baseNode.label = `${baseNode.label} [▶ ${deviceCount}]`
            }
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
          // Get edge color based on type
          const getEdgeColor = (label, from, to) => {
            // Check for Grasshopper connections first (by node ID)
            const isGrasshopperEdge =
              from?.startsWith('bacnet://Grasshopper') ||
              to?.startsWith('bacnet://Grasshopper')
            if (isGrasshopperEdge) return 'rgb(0, 180, 180)'

            if (!label) return 'rgba(140, 140, 140, 0.7)'
            if (label.includes('bbmd-broadcast-domain'))
              return 'rgb(200, 100, 200)'
            if (label.includes('bacnet-router-on-subnet'))
              return 'rgb(220, 80, 80)'
            if (label.includes('device-on-subnet')) return 'rgb(100, 180, 100)'
            if (label.includes('device-on-network')) return 'rgb(140, 140, 140)'
            if (label.includes('bdt-entry')) return 'rgb(255, 165, 0)'
            if (label.includes('fdr-entry')) return 'rgb(0, 200, 255)'
            return 'rgba(140, 140, 140, 0.7)'
          }

          const edgeColor = getEdgeColor(edge.label, edge.from, edge.to)
          // eslint-disable-next-line no-unused-vars
          const isBdtOrFdt =
            edge.label?.includes('bdt-entry') ||
            edge.label?.includes('fdr-entry')

          const base = {
            ...edge,
            color: {
              color: edgeColor,
              highlight: edgeColor,
              hover: edgeColor,
            },
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

          // Handle BDT edges (BBMD-to-BBMD connections) - control visibility
          if (
            edge.label.includes('bdt-entry') &&
            this.allBbmds.includes(edge.from) &&
            this.allBbmds.includes(edge.to)
          ) {
            const isConnectedToClosest =
              edge.from === closestBbmd || edge.to === closestBbmd
            return {
              ...base,
              dashes: true,
              color: {
                color: edgeColor,
                highlight: edgeColor,
                hover: edgeColor,
                opacity: isConnectedToClosest ? 1 : 0,
              },
              physics: isConnectedToClosest,
            }
          }

          // Handle FDT edges (BBMD to foreign device connections) - control visibility
          if (
            edge.label.includes('fdr-entry') &&
            (this.allBbmds.includes(edge.from) ||
              this.allBbmds.includes(edge.to))
          ) {
            const isConnectedToClosest =
              edge.from === closestBbmd || edge.to === closestBbmd
            return {
              ...base,
              dashes: true,
              color: {
                color: edgeColor,
                highlight: edgeColor,
                hover: edgeColor,
                opacity: isConnectedToClosest ? 1 : 0,
              },
              physics: isConnectedToClosest,
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
            inherit: false,
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
          dragView: true,
          zoomView: true,
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
        this.network.on('beforeDrawing', ctx => {
          if (this.treeLayoutData) {
            // Draw orthogonal edges first (bottom layer)
            this.drawOrthogonalEdges(
              ctx,
              this.network,
              this.treeLayoutData.edges,
              this.treeLayoutData.nodeMap,
            )
            // Draw gold bus lines on top of edges (middle layer)
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

        // if (
        //   node &&
        //   !node.includes('bacnet://subnet/') &&
        //   !node.includes('bacnet://router/') &&
        //   !node.includes('bacnet://Grasshopper') &&
        //   !node.includes('bacnet://network/')
        // ) {
        //   this.store.runRouteWithCheck(() =>
        //     this.store.getDeviceInfo(node.split('bacnet://')[1]),
        //   )
        // }
      })

      this.network.on('blurNode', () => {
        this.$refs.networkContainer.style.cursor = 'default'
      })

      // Double-click on network nodes to toggle collapse (tree mode only)
      if (isTreeLayout) {
        this.network.on('doubleClick', params => {
          if (params.nodes.length > 0) {
            const nodeId = params.nodes[0]
            // Only toggle collapse for network nodes
            if (nodeId.startsWith('bacnet://network/')) {
              this.toggleNetworkCollapse(nodeId)
            }
          }
        })
      }

      this.network.on('click', params => {
        // Tree mode edge click detection (edges are drawn on canvas, not vis-network)
        if (this.store.layoutMode === 'tree' && params.nodes.length === 0) {
          // Convert DOM coordinates to canvas coordinates
          const canvasPos = this.network.DOMtoCanvas({
            x: params.pointer.DOM.x,
            y: params.pointer.DOM.y,
          })
          const clickedEdge = this.findEdgeAtPoint(canvasPos.x, canvasPos.y)

          if (clickedEdge) {
            // Show edge card like physics mode
            const cleanedLabel =
              clickedEdge.label?.replace(
                'http://data.ashrae.org/bacnet/2020#',
                '',
              ) || 'unknown'

            this.selectedEdge = clickedEdge.id
            this.edgeInfo = {
              type: cleanedLabel,
              from: clickedEdge.from,
              to: clickedEdge.to,
            }
            this.edgeOptions = [] // Simplified for now
            this.store.setNodeCard(false)
            this.store.setEdgeMenu(true)
            return
          }
        }

        if (!params.nodes.length) {
          this.unhighlightNode()

          if (!this.store.showBdtEdges) {
            this.store.setBdtEdges(false)
            this.toggleBdtEdges(this.bdtEdges, false)
          }

          // Clear selected BBMD for tree layout when clicking empty space
          if (this.store.layoutMode === 'tree' && this.selectedBbmdForTree) {
            this.selectedBbmdForTree = null
            this.network.redraw()
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
              // For tree layout, track selected BBMD to draw BDT connections
              if (this.store.layoutMode === 'tree') {
                this.selectedBbmdForTree = clickedNode.id
                this.network.redraw() // Trigger redraw to show BDT edges
              }
            } else {
              // Clear BBMD selection when clicking on non-BBMD node
              if (this.store.treeLayout && this.selectedBbmdForTree) {
                this.selectedBbmdForTree = null
                this.network.redraw()
              }

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
    this.store.setTreeLayout(false)
    this.store.setMinimapToggled(false)
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
