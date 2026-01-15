<template>
  <div>
    <div class="network-header">
      <RouterLink
        to="/"
        @click="
          (store.setCurrentGraph(false, null, null), store.setStartMenu(true))
        "
        class="nav-link"
      >
        <img
          class="logo"
          src="@/assets/grasshopper-drk-bg.svg"
          alt="Grasshopper Logo"
        />
      </RouterLink>
      <div class="buttons">
        <v-btn
          variant="plain"
          size="small"
          @click="store.setControlMenu(true, 'setup', 'GRAPH SETUP')"
          @mouseenter="() => store.fetchGraphs()"
          >Graph Setup</v-btn
        >
        <v-btn
          variant="plain"
          size="small"
          @click="store.setControlMenu(true, 'compare', 'COMPARE GRAPHS')"
          @mouseenter="() => store.fetchCompareGraphs()"
          >Compare Graphs</v-btn
        >
        <v-btn
          variant="plain"
          size="small"
          @click="store.setControlMenu(true, 'delete', 'DELETE')"
          @mouseenter="
            (() => store.fetchGraphs(),() => store.fetchCompareGraphs())
          "
          >Delete</v-btn
        >
        <v-btn
          v-if="store.fileName"
          @click="store.toggleLegend()"
          variant="plain"
          :ripple="false"
          icon=""
          id="no-background-hover"
          size="small"
          density="compact"
          color="#FDFD94"
          alt="Legend"
        >
          <v-tooltip text="Legend" bottom delay="1000">
            <template v-slot:activator="{ props }">
              <v-icon v-bind="props">mdi-map-legend</v-icon>
            </template>
          </v-tooltip>
        </v-btn>
        <v-btn
          v-if="store.fileName"
          @click="store.setReload()"
          variant="plain"
          :ripple="false"
          icon=""
          id="no-background-hover"
          size="small"
          density="compact"
          color="#94D8FF"
          alt="Regenerate Graph"
        >
          <v-tooltip text="Regenerate Graph" bottom delay="1000">
            <template v-slot:activator="{ props }">
              <v-icon v-bind="props">mdi-autorenew</v-icon>
            </template>
          </v-tooltip>
        </v-btn>
        <div v-if="store.fileName" class="text-center">
          <v-menu open-on-hover>
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
              </v-btn>
            </template>

            <v-list>
              <v-list-item
                v-for="(item, index) in modeOptions"
                :key="index"
                @click="item.action"
              >
                <v-list-item-title>{{ item.title }}</v-list-item-title>
              </v-list-item>
            </v-list>
          </v-menu>
        </div>
        <v-btn
          @click="store.setCompareLoad(true)"
          variant="plain"
          :ripple="false"
          icon=""
          id="no-background-hover"
          size="small"
          density="compact"
          color="#CDCDCD"
        >
          <v-tooltip text="Compare Queue" bottom delay="1000">
            <template v-slot:activator="{ props }">
              <v-icon v-bind="props">mdi-tray-full</v-icon>
            </template>
          </v-tooltip>
        </v-btn>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: ['store'],
  data() {
    return {}
  },
  computed: {
    accessCookie() {
      const cookie = decodeURIComponent(document.cookie)
      for (const c of cookie.split(';')) {
        const [key, value] = c.trim().split('=')
        if (key === 'access_token') {
          return value
        }
      }
      return null
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
    gateway: {
      get() {
        return this.store.gateway
      },
    },
  },
  methods: {},
}
</script>

<style lang="scss" scoped>
.network-header {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  margin: 35px 20px 0px 20px;
  height: 50px;
  align-items: center;
}
.controls {
  display: flex;
  justify-content: space-evenly;
  width: 80%;
}
.buttons {
  display: flex;
  margin-right: 1.5vw;
  gap: 20px;
  align-items: center;
}
.main-select {
  width: 175px;
  max-width: 200px;
  height: 28px;
  margin: 0 1.5vw;
}
.nav-link {
  margin-left: 1.5vw;
}
.secondary-header {
  display: flex;
  margin: 0 20px;
  justify-content: flex-end;
}
.logo {
  width: 70%;
}
</style>
