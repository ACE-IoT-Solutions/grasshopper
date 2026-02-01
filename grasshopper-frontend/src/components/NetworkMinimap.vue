<template>
  <div
    class="minimap-container"
    :class="{ collapsed: isCollapsed }"
    @mousedown.stop
  >
    <div class="minimap-header" @click="toggleCollapse">
      <span v-if="!isCollapsed">Minimap</span>
      <v-icon size="small">{{ isCollapsed ? 'mdi-map' : 'mdi-chevron-down' }}</v-icon>
    </div>
    <div v-show="!isCollapsed" class="minimap-content">
      <canvas
        ref="minimapCanvas"
        :width="canvasWidth"
        :height="canvasHeight"
        @mousedown="handleMouseDown"
        @mousemove="handleMouseMove"
        @mouseup="handleMouseUp"
        @mouseleave="handleMouseUp"
      ></canvas>
    </div>
  </div>
</template>

<script>
export default {
  name: 'NetworkMinimap',
  props: {
    network: {
      type: Object,
      required: true
    },
    treePositions: {
      type: Object,
      default: null
    }
  },
  data() {
    return {
      isCollapsed: false,
      canvasWidth: 200,
      canvasHeight: 150,
      isDragging: false,
      scale: 1,
      offsetX: 0,
      offsetY: 0,
      bounds: null
    }
  },
  mounted() {
    this.updateMinimap()
    // Update minimap when network view changes
    if (this.network) {
      this.network.on('afterDrawing', this.updateMinimap)
    }
  },
  beforeUnmount() {
    if (this.network) {
      this.network.off('afterDrawing', this.updateMinimap)
    }
  },
  watch: {
    treePositions: {
      handler() {
        this.$nextTick(() => this.updateMinimap())
      },
      deep: true
    }
  },
  methods: {
    toggleCollapse() {
      this.isCollapsed = !this.isCollapsed
      if (!this.isCollapsed) {
        this.$nextTick(() => this.updateMinimap())
      }
    },
    updateMinimap() {
      if (!this.network || !this.$refs.minimapCanvas) return

      const canvas = this.$refs.minimapCanvas
      const ctx = canvas.getContext('2d')

      // Clear canvas
      ctx.fillStyle = 'rgba(18, 18, 18, 0.9)'
      ctx.fillRect(0, 0, this.canvasWidth, this.canvasHeight)

      // Get network bounds
      const positions = this.network.getPositions()
      if (!positions || Object.keys(positions).length === 0) return

      // Calculate bounds of all nodes
      let minX = Infinity, maxX = -Infinity
      let minY = Infinity, maxY = -Infinity

      Object.values(positions).forEach(pos => {
        minX = Math.min(minX, pos.x)
        maxX = Math.max(maxX, pos.x)
        minY = Math.min(minY, pos.y)
        maxY = Math.max(maxY, pos.y)
      })

      // Add padding
      const padding = 50
      minX -= padding
      maxX += padding
      minY -= padding
      maxY += padding

      // Calculate scale to fit in minimap
      const networkWidth = maxX - minX
      const networkHeight = maxY - minY
      this.scale = Math.min(
        (this.canvasWidth - 20) / networkWidth,
        (this.canvasHeight - 20) / networkHeight
      )
      this.offsetX = -minX
      this.offsetY = -minY
      this.bounds = { minX, maxX, minY, maxY }

      // Draw nodes as dots
      ctx.fillStyle = 'rgba(100, 150, 255, 0.6)'
      Object.entries(positions).forEach(([nodeId, pos]) => {
        const x = (pos.x + this.offsetX) * this.scale + 10
        const y = (pos.y + this.offsetY) * this.scale + 10

        // Different colors for different node types
        if (nodeId.startsWith('bacnet://network/')) {
          ctx.fillStyle = 'rgba(255, 215, 0, 0.8)' // Gold for networks
        } else if (nodeId.startsWith('bacnet://subnet/')) {
          ctx.fillStyle = 'rgba(100, 200, 100, 0.8)' // Green for subnets
        } else if (nodeId.includes('BBMD') || nodeId.startsWith('bacnet://') && nodeId.split('/').length === 3) {
          ctx.fillStyle = 'rgba(200, 100, 200, 0.8)' // Purple for BBMDs
        } else {
          ctx.fillStyle = 'rgba(100, 150, 255, 0.6)' // Blue for devices
        }

        ctx.beginPath()
        ctx.arc(x, y, 2, 0, Math.PI * 2)
        ctx.fill()
      })

      // Draw viewport rectangle
      this.drawViewport(ctx)
    },
    drawViewport(ctx) {
      if (!this.bounds) return

      const viewBounds = this.network.getViewPosition()
      const scale = this.network.getScale()

      // Get canvas dimensions
      const container = this.network.body.container
      const canvasViewWidth = container.clientWidth / scale
      const canvasViewHeight = container.clientHeight / scale

      // Calculate viewport rectangle in minimap coordinates
      const viewX = (viewBounds.x - canvasViewWidth / 2 + this.offsetX) * this.scale + 10
      const viewY = (viewBounds.y - canvasViewHeight / 2 + this.offsetY) * this.scale + 10
      const viewWidth = canvasViewWidth * this.scale
      const viewHeight = canvasViewHeight * this.scale

      // Draw viewport rectangle
      ctx.strokeStyle = 'rgba(255, 200, 0, 0.8)'
      ctx.lineWidth = 2
      ctx.strokeRect(viewX, viewY, viewWidth, viewHeight)

      // Fill with semi-transparent overlay
      ctx.fillStyle = 'rgba(255, 200, 0, 0.1)'
      ctx.fillRect(viewX, viewY, viewWidth, viewHeight)
    },
    handleMouseDown(event) {
      this.isDragging = true
      this.panToPosition(event)
    },
    handleMouseMove(event) {
      if (this.isDragging) {
        this.panToPosition(event)
      }
    },
    handleMouseUp() {
      this.isDragging = false
    },
    panToPosition(event) {
      if (!this.bounds || !this.network) return

      const canvas = this.$refs.minimapCanvas
      const rect = canvas.getBoundingClientRect()
      const x = event.clientX - rect.left
      const y = event.clientY - rect.top

      // Convert minimap coordinates to network coordinates
      const networkX = (x - 10) / this.scale - this.offsetX
      const networkY = (y - 10) / this.scale - this.offsetY

      // Move the main network view to this position
      this.network.moveTo({
        position: { x: networkX, y: networkY },
        animation: {
          duration: 200,
          easingFunction: 'easeOutQuad'
        }
      })
    }
  }
}
</script>

<style scoped>
.minimap-container {
  position: absolute;
  bottom: 60px;
  right: 10px;
  background-color: rgba(33, 33, 33, 0.95);
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
  z-index: 998;
  overflow: hidden;
  transition: all 0.2s ease;
}

.minimap-container.collapsed {
  width: auto;
}

.minimap-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  background-color: rgba(50, 50, 50, 0.9);
  cursor: pointer;
  font-size: 12px;
  color: #ccc;
  gap: 8px;
}

.minimap-header:hover {
  background-color: rgba(70, 70, 70, 0.9);
}

.minimap-content {
  padding: 5px;
}

.minimap-content canvas {
  border-radius: 4px;
  cursor: crosshair;
}
</style>
