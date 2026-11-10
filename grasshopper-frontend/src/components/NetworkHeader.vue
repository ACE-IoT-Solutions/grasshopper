<template>
  <div>
    <transition name="pill">
      <div v-if="store.navCollapsed" class="nav-pill">
        <v-btn
          icon=""
          variant="plain"
          size="medium"
          density="comfortable"
          @click="store.setNavCollapsed(false)"
        >
          <v-icon>mdi-chevron-down</v-icon>
          <v-tooltip activator="parent" location="bottom" open-delay="500"
            >Show navbar (H)</v-tooltip
          >
        </v-btn>
        <RouterLink :to="{ name: 'start' }" class="pill-logo">
          <img src="@/assets/grasshopper-logomark.svg" alt="Grasshopper" />
        </RouterLink>
        <span
          v-if="store.fileName"
          class="pill-graph"
          :title="store.fileName"
          >{{ store.fileName }}</span
        >
        <v-btn
          variant="plain"
          size="small"
          prepend-icon="mdi-graph-outline"
          @click="toggleGraphs()"
          >Graphs
          <v-tooltip activator="parent" location="bottom" open-delay="500"
            >Graphs (G)</v-tooltip
          ></v-btn
        >
      </div>
    </transition>
    <div class="header-shell" :class="{ collapsed: store.navCollapsed }">
      <div class="network-header">
        <RouterLink :to="{ name: 'start' }" class="nav-link">
          <img
            class="logo"
            src="@/assets/grasshopper-drk-bg.svg"
            alt="Grasshopper Logo"
          />
        </RouterLink>
        <div v-if="store.fileName" class="context">
          <span class="context-graph">{{ store.fileName }}</span>
          <v-chip
            v-if="store.compareMode"
            size="small"
            color="#94D8FF"
            variant="tonal"
            >Compare</v-chip
          >
        </div>
        <div class="buttons">
          <v-btn
            variant="plain"
            size="small"
            @click="toggleGraphs()"
            @mouseenter="store.refreshItems()"
            prepend-icon="mdi-graph-outline"
            >Graphs
            <v-tooltip activator="parent" location="bottom" open-delay="500"
              >Graphs (G)</v-tooltip
            ></v-btn
          >
          <div class="divider"></div>
          <template v-if="store.fileName">
            <v-btn
              v-for="action in graphActions"
              :key="action.key"
              @click="action.run()"
              variant="plain"
              :ripple="false"
              icon=""
              id="no-background-hover"
              size="small"
              density="compact"
              :color="action.color"
            >
              <v-icon>{{ action.icon }}</v-icon>
              <v-tooltip activator="parent" location="bottom" open-delay="500"
                >{{ action.label }} ({{ action.key.toUpperCase() }})</v-tooltip
              >
            </v-btn>
            <v-menu v-model="downloadMenu" location="bottom end">
              <template v-slot:activator="{ props }">
                <v-btn
                  v-bind="props"
                  variant="plain"
                  :ripple="false"
                  icon=""
                  id="no-background-hover"
                  size="small"
                  density="compact"
                  color="#FFFD94"
                >
                  <v-icon>mdi-download</v-icon>
                  <v-tooltip
                    activator="parent"
                    location="bottom"
                    open-delay="500"
                    >Download (D)</v-tooltip
                  >
                </v-btn>
              </template>
              <v-list density="compact">
                <v-list-item
                  v-for="(item, index) in modeOptions"
                  :key="index"
                  @click="item.action"
                >
                  <v-list-item-title>{{ item.title }}</v-list-item-title>
                </v-list-item>
              </v-list>
            </v-menu>
          </template>
          <v-btn
            v-if="store.hasCompareActivity()"
            @click="openQueue()"
            variant="plain"
            :ripple="false"
            icon=""
            id="no-background-hover"
            size="small"
            density="compact"
            color="#CDCDCD"
          >
            <v-badge
              :model-value="!!store.processingQueue || store.inQueue.length > 0"
              dot
              color="#94D8FF"
            >
              <v-icon>mdi-tray-full</v-icon>
            </v-badge>
            <v-tooltip activator="parent" location="bottom" open-delay="500"
              >Compare queue (Q)</v-tooltip
            >
          </v-btn>
          <div class="divider"></div>
          <v-btn
            variant="plain"
            :ripple="false"
            icon=""
            id="no-background-hover"
            size="medium"
            density="compact"
            color="#CDCDCD"
            @click="store.setNavCollapsed(true)"
          >
            <v-icon>mdi-chevron-up</v-icon>
            <v-tooltip activator="parent" location="bottom" open-delay="500"
              >Hide navbar (H)</v-tooltip
            >
          </v-btn>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: ['store'],
  data() {
    return {
      downloadMenu: false,
    }
  },
  computed: {
    graphActions() {
      return [
        {
          key: 'l',
          label: 'Legend',
          icon: 'mdi-map-legend',
          color: '#FDFD94',
          run: () => this.store.toggleLegend(),
        },
        {
          key: 'r',
          label: 'Regenerate graph',
          icon: 'mdi-autorenew',
          color: '#94D8FF',
          run: () => this.store.setReload(),
        },
      ]
    },
    downloadOptions() {
      return [
        {
          title: 'Download TTL',
          action: () =>
            this.store.exportTtl(this.store.compareMode, this.store.fileName),
        },
        {
          title: 'Download JSON',
          action: () =>
            this.store.exportJson(this.store.compareMode, this.store.fileName),
        },
        {
          title: 'Download CSV',
          action: () =>
            this.store.exportCsv(this.store.compareMode, this.store.fileName),
        },
      ]
    },
    compareDownloadOptions() {
      return this.downloadOptions.filter(
        option => option.title !== 'Download CSV',
      )
    },
    modeOptions() {
      return this.store.compareMode
        ? this.compareDownloadOptions
        : this.downloadOptions
    },
  },
  mounted() {
    window.addEventListener('keydown', this.onKeydown)
  },
  beforeUnmount() {
    window.removeEventListener('keydown', this.onKeydown)
  },
  methods: {
    toggleGraphs() {
      this.store.setControlMenu(!this.store.controlMenu, 'graphs', 'GRAPHS')
    },
    // the compare queue lives in the Graphs dialog's Compare tab
    openQueue() {
      this.store.setGraphFormsTab('compare')
      this.store.setControlMenu(true, 'graphs', 'GRAPHS')
    },
    onKeydown(event) {
      // single-key shortcuts, ignored while typing in a field or with modifiers held
      const target = event.target
      if (
        event.ctrlKey ||
        event.metaKey ||
        event.altKey ||
        event.repeat ||
        target.isContentEditable ||
        ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)
      ) {
        return
      }

      const key = event.key.toLowerCase()
      const graphAction = this.graphActions.find(action => action.key === key)
      if (key === 'h') {
        this.store.setNavCollapsed(!this.store.navCollapsed)
      } else if (key === 'g') {
        this.toggleGraphs()
      } else if (key === 'q') {
        this.openQueue()
      } else if (key === 't' && this.store.fileName) {
        this.store.toggleTreeLayout()
      } else if (key === 'd' && this.store.fileName) {
        // the download menu lives in the navbar, so bring it back first
        this.store.setNavCollapsed(false)
        this.downloadMenu = !this.downloadMenu
      } else if (graphAction && this.store.fileName) {
        graphAction.run()
      } else {
        return
      }
      event.preventDefault()
    },
  },
}
</script>

<style lang="scss" scoped>
.header-shell {
  margin-top: 12px;
  max-height: 50px;
  overflow: hidden;
  transition:
    max-height 0.25s ease,
    margin-top 0.25s ease,
    opacity 0.2s ease;
}
.header-shell.collapsed {
  max-height: 0;
  margin-top: 0;
  opacity: 0;
  pointer-events: none;
}
.network-header {
  display: flex;
  gap: 16px;
  margin: 0 12px;
  padding: 0 8px 0 16px;
  height: 50px;
  align-items: center;
  background-color: #121212;
  border-radius: 12px;
  box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.3);
}
.context {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  color: #cdcdcd;
  font-size: 0.9rem;
}
.context-graph {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.nav-pill {
  position: absolute;
  top: 12px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 999;
  display: flex;
  align-items: center;
  gap: 8px;
  max-width: calc(100vw - 280px);
  padding: 4px 6px 4px 4px;
  border-radius: 999px;
  background-color: rgba(33, 33, 33, 0.92);
  box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.5);
}
.pill-logo {
  display: flex;
  flex-shrink: 0;
}
.pill-logo img {
  height: 22px;
}
.pill-graph {
  color: #cdcdcd;
  font-size: 0.9rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}
.pill-enter-active {
  transition:
    opacity 0.2s ease 0.15s,
    transform 0.2s ease 0.15s;
}
.pill-leave-active {
  transition:
    opacity 0.15s ease,
    transform 0.15s ease;
}
.pill-enter-from,
.pill-leave-to {
  opacity: 0;
  transform: translate(-50%, -8px);
}
.divider {
  width: 1px;
  height: 20px;
  background-color: rgba(205, 205, 205, 0.15);
}
.buttons {
  display: flex;
  margin-left: auto;
  gap: 16px;
  align-items: center;
}
.nav-link {
  display: flex;
  flex-shrink: 0;
}
.logo {
  height: 32px;
}
</style>
