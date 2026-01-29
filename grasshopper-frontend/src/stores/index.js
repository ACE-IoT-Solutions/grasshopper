import { defineStore } from 'pinia'
import { reactive } from 'vue'
import axios from 'axios'
import router from '@/router'
import { shallowRef } from 'vue'

export const useGrasshopperStore = defineStore('grasshopper', {
  state: () => ({
    controlMenu: false,
    menuType: null,
    menuTitle: null,
    setupGraphs: [],
    diagramKey: 0,
    currentGraph: reactive({ nodes: [], edges: [] }),
    ipList: [],
    compareList: [],
    deleteList: [],
    deleteCompareList: [],
    compareLoad: false,
    configList: [],
    configSelect: false,
    currentConfig: 'Default',
    configToSave: null,
    physicsConfig: {},
    defaultConfig: {
      enabled: true,
      barnesHut: {
        theta: 0.5,
        gravitationalConstant: -7000,
        centralGravity: 0.3,
        springLength: 95,
        springConstant: 0.04,
        damping: 0.07,
        avoidOverlap: 0,
      },
      forceAtlas2Based: {
        theta: 0.5,
        gravitationalConstant: -50,
        centralGravity: 0.01,
        springConstant: 0.08,
        springLength: 100,
        damping: 0.4,
        avoidOverlap: 0,
      },
      repulsion: {
        centralGravity: 0.2,
        springLength: 200,
        springConstant: 0.05,
        nodeDistance: 100,
        damping: 0.09,
      },
      hierarchicalRepulsion: {
        centralGravity: 0,
        springLength: 100,
        springConstant: 0.01,
        nodeDistance: 120,
        damping: 0.09,
      },
      maxVelocity: 50,
      minVelocity: 0.75,
      solver: 'barnesHut',
      stabilization: {
        enabled: true,
        iterations: 200,
        updateInterval: 50,
        onlyDynamicEdges: false,
        fit: true,
      },
      timestep: 0.5,
      adaptiveTimestep: true,
      wind: {
        x: 0,
        y: 0,
      },
    },
    compareMode: false,
    fileName: null,
    reloadKey: 0,
    bbmdList: [],
    compareQueue: [],
    currentTask: null,
    legendEnabled: false,
    showBdtEdges: false,
    layoutMode: 'force', // 'force' or 'tree'
    selectedNode: null,
    showNoteCard: false,
    isAuthenticated: false,
    loading: false,
    permissions: null,
    // gateway: null,
    globalError: false,
    errorMessage: null,
    menuError: false,
    alertType: null,
    alertTitle: null,
    host: window.location.protocol + '//' + window.location.host,
    apiPrefix: import.meta.env.DEV
      ? // ? '/api/v1'
        'http://localhost:5010'
      : `${import.meta.env.VITE_FLIGHT_DECK_API_URL}`,
    processingQueue: null,
    inQueue: [],
    finishedQueue: [],
    startMenu: true,
    recentGraphs: [],
    recentCompares: [],
    timeRange: shallowRef(null),
    gateway: sessionStorage.getItem('gateway') || null,
    gatewayList: [],
    gatewayLoad: false,
    fetchGraphLoad: false,
    fetchCompareLoad: false,
    fetchQueueLoad: false,
    graphLoad: false,
    compareGraphLoad: false,
    createCompareLoad: false,
    uploadLoad: false,
    uploadCompareLoad: false,
    deleteLoad: false,
    timelineCard: false,
    nodeCard: false,
    inputKeys: {
      setupGraph: 0,
      uploadGraph: 0,
      uploadCompare: 0,
      compareGraph: 0,
      compareGraph1: 0,
      compareGraph2: 0,
      deleteGraph: 0,
      deleteCompareGraph: 0,
    },
    edgeMenu: false,
    hiddenMenu: false,
    searchMenu: false,
    compareQueueRefresh: false,
    gatewayInfo: JSON.parse(sessionStorage.getItem('gatewayInfo')) || null,
    siteName: sessionStorage.getItem('siteName') || null,
    deviceList: JSON.parse(sessionStorage.getItem('deviceList')) || null,
    currentDeviceInfo: null,
    nextDeviceInfo:
      JSON.parse(sessionStorage.getItem('nextDeviceInfo')) || null,
    deviceKey: 0,
    deviceTimeline: false,
    graphIssues: reactive({ graph_analysis: {} }),
    objectCard: false,
    objectCardData: null,
    nodeLabel: null,
  }),
  getters: {
    isTimeRangeValid: state =>
      Array.isArray(state.timeRange) && state.timeRange.length >= 2,

    timeRangeStartEnd: state => {
      if (
        Array.isArray(state.timeRange) &&
        state.timeRange.length >= 2 &&
        state.timeRange[0] &&
        state.timeRange[state.timeRange.length - 1]
      ) {
        const start = new Date(state.timeRange[0])
        const end = new Date(state.timeRange[state.timeRange.length - 1])
        const fmt = d => d.toISOString().split('.')[0]
        return [fmt(start), fmt(end)]
      }
      return []
    },
  },
  actions: {
    setControlMenu(show, type, title) {
      this.controlMenu = show

      if (this.controlMenu) {
        this.menuType = type
        this.menuTitle = title
      } else {
        this.menuType = null
        this.menuTitle = null
      }
    },
    setSetupGraphs(graphs) {
      this.setupGraphs = graphs
    },
    setReload() {
      this.diagramKey++
    },
    setCurrentGraph(graph, name) {
      this.currentGraph = graph
      // this.graphIssues = graph.graph_analysis || {}
      // console.log(this.graphIssues);
      this.fileName = name
      this.setReload()
    },
    setIpList(ips) {
      this.ipList = ips.sort()
    },
    setCompareList(compares) {
      this.compareList = compares
    },
    setDeleteGraphs(list) {
      this.deleteList = list
    },
    setDeleteCompareGraphs(list) {
      this.deleteCompareList = list
    },
    setCompareLoad(load) {
      this.compareLoad = load
    },
    setPhysicsConfig(config) {
      this.physicsConfig = config
    },
    setCompareMode(isCompare) {
      this.compareMode = isCompare
    },
    triggerReload() {
      this.reloadKey++
    },
    setBbmdList(list) {
      this.bbmdList = list.sort()
    },
    setQueue(processing, queue, finished) {
      this.processingQueue = processing
      this.inQueue = queue
      this.finishedQueue = finished
    },
    setConfigList(list) {
      this.configList = list.sort()
    },
    setConfigSelect(value) {
      this.configSelect = value
    },
    setCurrentConfig(config) {
      this.currentConfig = config
    },
    setSavableConfig(config) {
      this.configToSave = config
    },
    setLegend(enabled) {
      this.legendEnabled = enabled
    },
    toggleLegend() {
      this.legendEnabled = !this.legendEnabled
    },
    setBdtEdges(enabled) {
      this.showBdtEdges = enabled
    },
    setLayoutMode(mode) {
      this.layoutMode = mode
    },
    toggleLayoutMode() {
      this.layoutMode = this.layoutMode === 'force' ? 'tree' : 'force'
    },
    setSelectedNode(node) {
      this.selectedNode = node
    },
    setShowNoteCard(show) {
      this.showNoteCard = show
    },
    setEdgeMenu(show) {
      this.edgeMenu = show
    },
    setHiddenMenu(show) {
      this.hiddenMenu = show
    },
    setSearchMenu(show) {
      this.searchMenu = show
    },
    setAuthenticationStatus(status) {
      this.isAuthenticated = status
    },
    setLoading(loading) {
      this.loading = loading
    },
    setPermissions(permissions) {
      this.permissions = permissions
    },
    setGateway(gateway) {
      this.gateway = gateway
      this.siteName = this.matchGatewayToSite(gateway)
      sessionStorage.setItem('siteName', this.siteName)
    },
    setGatewayInfo(value) {
      this.gatewayInfo = value
      // console.log(this.gatewayInfo)
    },
    setGlobalError(error, message, type, title) {
      this.globalError = error
      this.errorMessage = message
      this.alertType = type
      this.alertTitle = title
    },
    setMenuAlert(error, message, type) {
      this.menuAlert = error
      this.errorMessage = message
      this.alertType = type
    },
    storeToken(token, expiration) {
      const combined = 'Bearer ' + token
      const now = Math.floor(Date.now() / 1000)
      const expTime = expiration - now

      document.cookie = `access_token=${combined}; path=/; max-age=${expTime}; secure; SameSite=Strict`
    },
    tokenHandoff(data) {
      const { access_token, expiration } = data
      this.storeToken(access_token, expiration)
    },
    setStartMenu(value) {
      this.startMenu = value
    },
    setRecentGraphs(graphs) {
      this.recentGraphs = graphs
    },
    setRecentCompares(compares) {
      this.recentCompares = compares
    },
    setGatewayList(gateways) {
      this.gatewayList = gateways
    },
    setTimelineCard(value) {
      this.timelineCard = value
    },
    setNodeCard(value) {
      this.nodeCard = value
    },
    setCompareRefresh(value) {
      this.compareQueueRefresh = value
    },
    setInQueue(list) {
      this.inQueue = list
    },
    setOutQueue(list) {
      this.outQueue = list
    },
    setTimeRange(range) {
      this.timeRange = Array.isArray(range) ? range : []

      if (this.gateway) {
        this.runRouteWithCheck(() => this.refreshItems())
      }
    },
    setDeviceInfo() {
      this.incDeviceKey()
      this.currentDeviceInfo = [...this.nextDeviceInfo].sort((a, b) =>
        b.timestamp.localeCompare(a.timestamp),
      )
    },
    incDeviceKey() {
      this.deviceKey++
    },
    setDeviceTimeline(value) {
      this.deviceTimeline = value
    },
    setObjectCard(value) {
      this.objectCard = value
    },
    setObjectCardData(data) {
      this.objectCardData = data
    },
    setNodeLabel(label) {
      this.nodeLabel = label
    },
    matchGatewayToSite(gateway) {
      if (!this.gatewayInfo) return null
      const match = this.gatewayInfo.find(g => g.name === gateway)
      return match ? match.site : null
    },
    matchDeviceToId(deviceID) {
      if (!this.deviceList) return null
      const match = this.deviceList.find(d => d.device_id === deviceID)
      return match ? match.id : null
    },
    incrementKey(keys) {
      const list = Array.isArray(keys) ? keys : [keys]
      for (const name of list) {
        if (!(name in this.inputKeys)) this.inputKeys[name] = 0
        this.inputKeys[name] += 1
      }
    },
    async runAndReset(
      forms = [],
      modelNames = [],
      keyNames = [],
      route,
      ctx = null,
    ) {
      try {
        await route()
      } finally {
        // reset models
        for (const m of modelNames) {
          // for file uploads
          // nullify in parent context if provided
          if (ctx) {
            for (const m of modelNames) {
              if (typeof m === 'string' && m in ctx) ctx[m] = null
            }
          }
          if (typeof m === 'string') {
            if (m in this) {
              const val = this[m]
              if (val && typeof val === 'object' && 'value' in val) {
                val.value = null
              } else {
                this[m] = null
              }
            }
          } else if (m && typeof m === 'object' && 'value' in m) {
            m.value = null
          }
        }

        // reset forms
        for (const f of forms) {
          const inst = f?.value ?? f
          inst?.reset?.()
          inst?.resetValidation?.()
        }
        this.incrementKey(keyNames)
      }
    },
    // async refresh() {
    //   await axios
    //     .post(`${this.apiPrefix}/refresh`)
    //     .then(response => {
    //       this.tokenHandoff(response.data)
    //       this.fetchPermissions()
    //       this.fetchQueue()
    //       this.setAuthenticationStatus(true)
    //       this.triggerReload()
    //     })
    //     .catch(error => {
    //       if (error.response.status === 401) {
    //         this.logoutNoCred()
    //         this.setGlobalError(
    //           true,
    //           'Session expired. Please log in again.',
    //           'error',
    //           'Unauthorized',
    //         )
    //       } else if (error.response.status === 500) {
    //         this.setGlobalError(
    //           true,
    //           'Server error fetching permissions. Please try again later.',
    //           'error',
    //           'Server Error',
    //         )
    //       } else if (error.response.status === 404) {
    //         this.setGlobalError(
    //           true,
    //           'No information found for this resource.',
    //           'error',
    //           'Not Found',
    //         )
    //       } else {
    //         this.setGlobalError(true, 'Error fetching permissions.', 'error', 'Error')
    //       }
    //     })
    // },
    async fetchPermissions() {
      await axios
        .get(`${this.apiPrefix}/get_permissions`, {
          withCredentials: true,
        })
        .then(response => {
          this.setPermissions(response.data.permission)
        })
        .catch(error => {
          if (error.response.status === 401) {
            this.refresh()
          } else if (error.response.status === 403) {
            this.setGlobalError(
              true,
              'You do not have permission to access this application.',
              'error',
              'Forbidden',
            )
          } else if (error.response.status === 404) {
            this.setGlobalError(
              true,
              'User permissions not found. Please contact an administrator.',
              'error',
              'Error',
            )
          } else if (error.response.status === 500) {
            this.setGlobalError(
              true,
              'Server error fetching permissions. Please try again later.',
              'error',
              'Server Error',
            )
          }
        })
    },
    async logout() {
      await axios
        .post(`${this.apiPrefix}/logout`, { withCredentials: true })
        .then(() => {
          document.cookie =
            'access_token=; path=/; max-age=0; secure; SameSite=Strict'
          this.$reset()
          router.push('/')
        })
        .catch(error => {
          if (
            error.response.status === 401 ||
            error.response.status === 403 ||
            error.response.status === 500 ||
            error.response.status === 404
          ) {
            this.logoutNoCred()
          } else {
            this.setGlobalError(
              true,
              'Error during logout. Please try again.',
              'error',
              'Logout Error',
            )
          }
        })
    },
    async fetchQueue() {
      // await this.fetchCompareGraphs()
      this.fetchQueueLoad = true

      const processingItem =
        JSON.parse(sessionStorage.getItem('processingItem')) || null

      await axios
        .get(`${this.host}/api/operations/ttl_compare_queue`, {
          responseType: 'json',
        })
        .then(async response => {
          this.setQueue(
            response.data.processing_task,
            response.data.queue,
            response.data.finished,
          )
          this.fetchQueueLoad = false

          const taskCompleted =
            processingItem != null &&
            (response.data.processing_task === null ||
              response.data.processing_task?.file_name !== processingItem)

          response.data.processing_task
            ? sessionStorage.setItem(
                'processingItem',
                JSON.stringify(response.data.processing_task.file_name),
              )
            : sessionStorage.setItem('processingItem', JSON.stringify(null))
          sessionStorage.setItem('inQueue', JSON.stringify(response.data.queue))

          if (taskCompleted) {
            setTimeout(async () => {
              await this.fetchCompareGraphs()
              this.setGlobalError(
                true,
                `<strong>${processingItem}</strong> generated!`,
                'success',
                'Compare Generate Complete',
              )
            }, 1000)
          }
        })
        .catch(error => {
          this.fetchQueueLoad = false

          if (error.response.status === 403) {
            this.setGlobalError(
              true,
              'You do not have permission to access the compare queue.',
              'error',
              'Forbidden',
            )
          } else if (error.response.status === 500) {
            this.setGlobalError(
              true,
              'Server error fetching compare queue. Please try again later.',
              'error',
              'Server Error',
            )
          } else if (error.response.status === 404) {
            this.setGlobalError(
              true,
              'Compare queue not found. Please contact an administrator.',
              'error',
              'Error',
            )
          } else {
            this.setGlobalError(
              true,
              'Error fetching compare queue. Please try again later.',
              'error',
              'Error',
            )
          }
        })
    },
    async goToGraph(compare, graph) {
      compare ? (this.compareGraphLoad = true) : (this.graphLoad = true)
      this.setNodeCard(false)
      this.setEdgeMenu(false)
      this.setHiddenMenu(false)
      this.setSearchMenu(false)

      try {
        await axios
          .get(
            `${this.apiPrefix}/api/operations/${compare ? 'ttl_compare' : 'ttl_network'}/${graph}`,
            {
              responseType: 'json',
              withCredentials: true,
            },
          )
          .then(response => {
            this.setCompareLoad(false)
            this.setCompareMode(compare)
            this.setCurrentGraph(response.data, graph)
            this.setControlMenu(false, null, null)
            this.setStartMenu(false)
            compare ? (this.compareGraphLoad = false) : (this.graphLoad = false)
            router.push({
              params: { gatewayName: this.gateway, graphName: graph },
            })
          })
      } catch (error) {
        compare ? (this.compareGraphLoad = false) : (this.graphLoad = false)

        if (error.response.status === 403) {
          this.setGlobalError(
            true,
            'You do not have permission to access this graph.',
            'error',
            'Forbidden',
          )
        } else if (error.response.status === 404) {
          this.setGlobalError(
            true,
            `Graph <strong>${graph}</strong> does not exist.`,
            'error',
            'Not Found',
          )
        } else if (error.response.status === 500) {
          this.setGlobalError(
            true,
            'Server error fetching graph. Please try again later.',
            'error',
            'Server Error',
          )
        } else {
          this.setGlobalError(
            true,
            `Error loading graph <strong>${graph}</strong>.`,
            'error',
            'Graph Load Error',
          )
        }
      }
    },
    async createCompare(graph1, graph2) {
      const payload = {
        ttl_1: graph1,
        ttl_2: graph2,
      }

      this.createCompareLoad = true

      const compareItem = graph1.replace('.ttl', '') + '_vs_' + graph2

      const processingItem =
        JSON.parse(sessionStorage.getItem('processingItem')) || null
      const inQueue = JSON.parse(sessionStorage.getItem('inQueue')) || []

      await axios
        .post(`${this.apiPrefix}/api/operations/ttl_compare_queue`, payload, {
          withCredentials: true,
        })
        .then(async () => {
          this.setGlobalError(
            true,
            `<strong>${compareItem}</strong> now generating.`,
            'success',
            'Compare Generating',
          )
          this.setControlMenu(false, null, null)
          if (!this.startMenu) {
            this.setCompareLoad(true)
          }
          this.incrementKey('compareGraph1')
          this.incrementKey('compareGraph2')
          graph1 = null
          graph2 = null
          this.createCompareLoad = false

          if (inQueue.length === 0 && processingItem === null) {
            sessionStorage.setItem(
              'processingItem',
              JSON.stringify(compareItem),
            )
          }

          await this.fetchQueue()
          this.setCompareRefresh(true)
        })
        .catch(error => {
          this.createCompareLoad = false

          if (error.response.status === 403) {
            this.setGlobalError(
              true,
              'You do not have permission to create compare graphs.',
              'error',
              'Forbidden',
            )
          } else if (error.response.status === 404) {
            this.setGlobalError(
              true,
              `One of the selected graphs does not exist.`,
              'error',
              'Not Found',
            )
          } else if (error.response.status === 500) {
            this.setGlobalError(
              true,
              'Server error generating compare graph. Please try again later.',
              'error',
              'Server Error',
            )
          } else {
            this.setGlobalError(
              true,
              `Error generating compare graph <strong>${compareItem}</strong>.`,
              'error',
              'Compare Graph Error',
            )
          }
        })
    },
    async uploadGraph(compare, upload) {
      compare ? (this.uploadCompareLoad = true) : (this.uploadGraphLoad = true)
      const formData = new FormData()
      formData.append('file', upload)

      await axios
        .post(
          `${this.apiPrefix}/api/operations/${compare ? 'ttl_compare' : 'ttl'}`,
          formData,
          {
            headers: {
              'Content-Type': 'multipart/form-data',
            },
            withCredentials: true,
          },
        )
        .then(() => {
          compare
            ? (this.uploadCompareLoad = false)
            : (this.uploadGraphLoad = false)
          this.setGlobalError(
            true,
            `Graph <strong>${upload.name}</strong> uploaded.`,
            'success',
            'Success',
          )
          upload = null
          this.refreshItems()
        })
        .catch(error => {
          compare
            ? (this.uploadCompareLoad = false)
            : (this.uploadGraphLoad = false)

          if (error.response.status === 403) {
            this.setGlobalError(
              true,
              'You do not have permission to upload graphs.',
              'error',
              'Forbidden',
            )
          } else if (error.response.status === 500) {
            this.setGlobalError(
              true,
              'Server error uploading graph. Please try again later.',
              'error',
              'Server Error',
            )
          } else {
            this.setGlobalError(
              true,
              `Error uploading graph <strong>${upload.name}</strong>.`,
              'error',
              'Upload Error',
            )
          }
        })
    },
    async deleteGraph(compare, deletedGraph) {
      compare ? (this.deleteCompareLoad = true) : (this.deleteGraphLoad = true)

      let fileDeleted

      await axios
        .delete(
          `${this.apiPrefix}/api/operations/${compare ? 'ttl_compare' : 'ttl_file'}/${deletedGraph}`,
          {
            responseType: 'json',
            withCredentials: true,
          },
        )
        .then(() => {
          compare
            ? (this.deleteCompareLoad = false)
            : (this.deleteGraphLoad = false)
          fileDeleted = deletedGraph
          deletedGraph = null
          this.setGlobalError(
            true,
            `Graph <strong>${fileDeleted}</strong> deleted.`,
            'success',
            'Success',
          )
          this.refreshItems()
        })
        .catch(error => {
          compare
            ? (this.deleteCompareLoad = false)
            : (this.deleteGraphLoad = false)

          if (error.response.status === 403) {
            this.setGlobalError(
              true,
              'You do not have permission to delete graphs.',
              'error',
              'Forbidden',
            )
          } else if (error.response.status === 404) {
            this.setGlobalError(
              true,
              `Graph <strong>${fileDeleted}</strong> not found.`,
              'error',
              'Not Found',
            )
          } else if (error.response.status === 500) {
            this.setGlobalError(
              true,
              'Server error deleting graph. Please try again later.',
              'error',
              'Server Error',
            )
          } else {
            this.setGlobalError(
              true,
              `Error deleting graph <strong>${fileDeleted}</strong>.`,
              'error',
              'Delete Error',
            )
          }
        })
    },
    async fetchGraphs() {
      try {
        this.setRecentGraphs([])

        this.fetchGraphLoad = true

        const { data } = await axios.get(
          `${this.apiPrefix}/api/operations/ttl`,
          {
            responseType: 'json',
            withCredentials: true,
          },
        )

        this.setSetupGraphs(data.data.sort().reverse())
        this.setRecentGraphs(data.data.sort().slice(-5).reverse())
        this.setDeleteGraphs(data.data.sort().reverse())
        this.fetchGraphLoad = false
      } catch (error) {
        if (error.response.status === 403) {
          this.setGlobalError(
            true,
            'You do not have permission to access these graphs.',
            'error',
            'Forbidden',
          )
        } else if (error.response.status === 500) {
          this.setGlobalError(
            true,
            'Server error fetching graphs. Please try again later.',
            'error',
            'Server Error',
          )
        } else if (error.response.status === 404) {
          this.setGlobalError(
            true,
            `The current agent does not contain any graphs.`,
            'warning',
            'No Graphs Found',
          )
        } else {
          this.setGlobalError(true, 'Error fetching graphs.', 'error', 'Error')
        }
        this.fetchGraphLoad = false
      }
    },
    async fetchCompareGraphs() {
      try {
        this.setRecentCompares([])

        this.fetchCompareLoad = true

        const { data } = await axios.get(
          `${this.apiPrefix}/api/operations/ttl_compare`,
          {
            responseType: 'json',
            withCredentials: true,
          },
        )

        this.setCompareList(data.file_list.sort().reverse())
        this.setRecentCompares(data.file_list.slice(-5).reverse())
        this.setDeleteCompareGraphs(data.file_list.sort().reverse())
        this.fetchCompareLoad = false
      } catch (error) {
        this.fetchCompareLoad = false

        if (error.response.status === 403) {
          this.setGlobalError(
            true,
            'You do not have permission to access compare graphs.',
            'error',
            'Forbidden',
          )
        } else if (error.response.status === 500) {
          this.setGlobalError(
            true,
            'Server error fetching compare graphs. Please try again later.',
            'error',
            'Error',
          )
        } else if (error.response.status === 404) {
          this.setGlobalError(
            true,
            `The gateway <strong>${this.gateway}</strong> does not contain any compare graphs.`,
            'warning',
            'No Compare Graphs Found',
          )
        } else {
          this.setGlobalError(
            true,
            'Error fetching compare graphs.',
            'error',
            'Error',
          )
        }
      }
    },
    async fetchGateways() {
      const cachedGateways = sessionStorage.getItem('gatewayList')
      if (cachedGateways) {
        this.gatewayList = JSON.parse(cachedGateways)
        return
      }

      try {
        let pageIndex = 1
        const allGateways = []

        this.gatewayLoad = true

        while (true) {
          const { data } = await axios.get(`${this.apiPrefix}/gateways/items`, {
            params: { page: pageIndex },
            responseType: 'json',
            withCredentials: true,
            headers: {
              Authorization: this.accessCookie(),
            },
          })

          allGateways.push(...data.items)

          const page = data.page
          const total_pages = data.pages
          if (page == total_pages) break

          pageIndex++
        }

        this.gatewayList = allGateways.map(item => item.name).sort()
        this.setGatewayInfo(
          allGateways.map(item => ({ name: item.name, site: item.site.name })),
        )
        sessionStorage.setItem('gatewayList', JSON.stringify(this.gatewayList))
        sessionStorage.setItem('gatewayInfo', JSON.stringify(this.gatewayInfo))
        this.gatewayLoad = false
      } catch (error) {
        console.log(error)
        this.gatewayLoad = false

        if (error.response.status === 403) {
          this.setGlobalError(
            true,
            'You do not have permission to access gateways.',
            'error',
            'Forbidden',
          )
        } else if (error.response.status === 500) {
          this.setGlobalError(
            true,
            'Server error fetching gateways. Please try again later.',
            'error',
            'Server Error',
          )
        } else if (error.response.status === 404) {
          this.setGlobalError(
            true,
            'No gateways found. Please refresh the page or contact an administrator.',
            'error',
            'Error',
          )
        } else {
          this.setGlobalError(
            true,
            'Error fetching gateways.',
            'error',
            'Error',
          )
        }
      }
    },
    async refreshItems() {
      await Promise.all([
        // this.fetchDevices(),
        this.fetchGraphs(),
        this.fetchCompareGraphs(),
        // this.fetchQueue(),
        // this.runFetchCycle(),
      ])
    },
    async exportTtl(compare, fileName) {
      await axios
        .get(
          `${this.apiPrefix}/api/operations/${compare ? 'ttl_compare_file' : 'ttl_file'}/${fileName}`,
          {
            headers: {
              Accept: 'text/turtle',
            },
            responseType: 'blob',
            withCredentials: true,
          },
        )
        .then(response => {
          const blob = new Blob([response.data], { type: 'text/turtle' })

          const downloadUrl = URL.createObjectURL(blob)
          const link = document.createElement('a')
          link.href = downloadUrl

          link.setAttribute('download', `${fileName}`)

          document.body.appendChild(link)
          link.click()
          link.remove()

          URL.revokeObjectURL(downloadUrl)
        })
        .catch(error => {
          if (error.response.status === 404) {
            this.setGlobalError(
              true,
              `Graph <strong>${fileName}</strong> does not exist.`,
              'error',
              'Error',
            )
          } else if (error.response.status === 403) {
            this.setGlobalError(
              true,
              'You do not have permission to export graphs.',
              'error',
              'Forbidden',
            )
          } else if (error.response.status === 500) {
            this.setGlobalError(
              true,
              'Server error exporting TTL. Please try again later.',
              'error',
              'Server Error',
            )
          } else {
            this.setGlobalError(true, `Error exporting TTL.`, 'error', 'Error')
          }
        })
    },
    async exportCsv(compare, fileName) {
      await axios
        .get(`${this.apiPrefix}/api/operations/csv_export/${fileName}`, {
          headers: {
            Accept: 'text/csv',
          },
          responseType: 'blob',
          withCredentials: true,
        })
        .then(response => {
          const blob = new Blob([response.data], { type: 'text/csv' })

          const downloadUrl = URL.createObjectURL(blob)
          const link = document.createElement('a')
          link.href = downloadUrl

          link.setAttribute('download', `${fileName.replace('.ttl', '.csv')}`)

          document.body.appendChild(link)
          link.click()
          link.remove()

          URL.revokeObjectURL(downloadUrl)
        })
        .catch(error => {
          if (error.response.status === 404) {
            this.setGlobalError(
              true,
              `Graph <strong>${fileName}</strong> does not exist.`,
              'error',
              'Error',
            )
          } else if (error.response.status === 403) {
            this.setGlobalError(
              true,
              'You do not have permission to export graphs.',
              'error',
              'Forbidden',
            )
          } else if (error.response.status === 500) {
            this.setGlobalError(
              true,
              'Server error exporting CSV. Please try again later.',
              'error',
              'Server Error',
            )
          } else {
            this.setGlobalError(true, `Error exporting CSV.`, 'error', 'Error')
          }
        })
    },
    async exportJson(compare, fileName) {
      try {
        const response = await axios.get(
          `${this.apiPrefix}/api/operations/${compare ? 'ttl_compare' : 'ttl_network'}/${fileName}`,
          {
            headers: {
              Accept: 'application/json',
            },
            responseType: 'json',
            withCredentials: true,
          },
        )

        const jsonString = JSON.stringify(response.data, null, 2)
        const blob = new Blob([jsonString], { type: 'application/json' })

        const downloadUrl = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = downloadUrl

        link.setAttribute('download', `${fileName.replace('.ttl', '.json')}`)

        document.body.appendChild(link)
        link.click()
        link.remove()

        URL.revokeObjectURL(downloadUrl)
      } catch (error) {
        if (error.response?.status === 404) {
          this.setGlobalError(
            true,
            `Graph <strong>${fileName}</strong> does not exist.`,
            'error',
            'Error',
          )
        } else if (error.response?.status === 403) {
          this.setGlobalError(
            true,
            'You do not have permission to export graphs.',
            'error',
            'Forbidden',
          )
        } else if (error.response?.status === 500) {
          this.setGlobalError(
            true,
            'Server error exporting JSON. Please try again later.',
            'error',
            'Server Error',
          )
        } else {
          this.setGlobalError(true, `Error exporting JSON.`, 'error', 'Error')
        }
      }
    },
    async fetchDevices() {
      try {
        const { data } = await axios.get(`${this.apiPrefix}/devices`, {
          params: { site_name: this.siteName },
          headers: { Authorization: this.accessCookie() },
          withCredentials: true,
        })
        const rows =
          Array.isArray(data) && data.length === 1 && Array.isArray(data[0])
            ? data[0]
            : data

        this.deviceList = rows
          .filter(d => d?.collect_config?.device_id)
          .map(d => ({
            id: d.id,
            device_id: d.collect_config.device_id,
          }))

        sessionStorage.setItem('deviceList', JSON.stringify(this.deviceList))
      } catch (error) {
        if (error.response.status === 403) {
          this.setGlobalError(
            true,
            'You do not have permission to access devices.',
            'error',
            'Forbidden',
          )
        } else if (error.response.status === 500) {
          this.setGlobalError(
            true,
            'Server error fetching devices. Please try again later.',
            'error',
            'Server Error',
          )
        } else if (error.response.status === 404) {
          this.setGlobalError(
            true,
            `No devices found for site <strong>${this.siteName}</strong>. Please contact an administrator.`,
            'error',
            'No Devices Found',
          )
        } else {
          this.setGlobalError(true, 'Error fetching devices.', 'error', 'Error')
        }
      }
    },
    async getDeviceInfo(nodeID) {
      const match = this.matchDeviceToId(nodeID)
      try {
        const { data } = await axios.get(
          `${this.apiPrefix}/devices/${match}/observations`,
          {
            headers: { Authorization: this.accessCookie() },
            withCredentials: true,
          },
        )
        const rows =
          Array.isArray(data) && data.length === 1 && Array.isArray(data[0])
            ? data[0]
            : data
        this.nextDeviceInfo = rows.map(d => ({
          timestamp: d.ts,
          present: d.present,
        }))

        sessionStorage.setItem(
          'nextDeviceInfo',
          JSON.stringify(this.nextDeviceInfo),
        )
      } catch (error) {
        if (error.response.status === 403) {
          this.setGlobalError(
            true,
            'You do not have permission to access device information.',
            'error',
            'Forbidden',
          )
        } else if (error.response.status === 500) {
          this.setGlobalError(
            true,
            'Server error fetching device information. Please try again later.',
            'error',
            'Server Error',
          )
        } else if (error.response.status === 404) {
          this.setGlobalError(
            true,
            `No information found for device <strong>${nodeID}</strong>. Please contact an administrator.`,
            'error',
            'No Device Information Found',
          )
        } else {
          this.setGlobalError(
            true,
            'Error fetching device information.',
            'error',
            'Error',
          )
        }
      }
    },
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
    isCookieValid(cookie) {
      const token = cookie
      if (!token) {
        return false
      }

      try {
        const payloadBase64 = token.split('.')[1]
        if (!payloadBase64) {
          return false
        }

        const decodedPayload = atob(
          payloadBase64.replace(/-/g, '+').replace(/_/g, '/'),
        )
        const payload = JSON.parse(decodedPayload)

        if (typeof payload.exp !== 'number') {
          return false
        }

        const expirationTimeInSeconds = payload.exp
        const currentTimeInSeconds = Math.floor(Date.now() / 1000)

        return expirationTimeInSeconds > currentTimeInSeconds
      } catch (error) {
        console.error('Failed to parse JWT token:', error)
        return false
      }
    },
    checkFileName() {
      if (this.fileUpload && this.fileUpload.name === 'base.ttl') {
        this.setGlobalError(
          true,
          'The file <strong>base.ttl</strong> was uploaded. This will become the basis of all scans.',
          'warning',
          'Warning',
        )
      }
    },
    logoutNoCred() {
      document.cookie =
        'access_token=; path=/; max-age=0; secure; SameSite=Strict'
      this.$reset()
      router.push('/')
    },
    async runRouteWithCheck(route) {
      if (this.isCookieValid(this.accessCookie())) {
        return await route()
      } else {
        await this.refresh()
        return await route()
      }
    },
  },
})
