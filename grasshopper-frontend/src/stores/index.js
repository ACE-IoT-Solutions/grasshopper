import { defineStore } from 'pinia'
import { reactive } from 'vue'
import axios from 'axios'
import router, { graphRoute } from '@/router'
import { isCompareGraph, monthOf, monthsWithGraphs } from '@/utils/graphNames'

// how long a generated compare keeps the queue button visible
const RECENT_COMPARE_MS = 15 * 60 * 1000

// per-viewer UI preference; storage can be unavailable (private mode, blocked site data)
function readNavCollapsed() {
  try {
    return localStorage.getItem('navCollapsed') === 'true'
  } catch {
    return false
  }
}

// the API answers errors as { detail } or, for uploads, { error }
function errorDetail(error) {
  const data = error.response?.data
  return data?.detail || data?.error || null
}

function saveBlob(blob, fileName) {
  const downloadUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = downloadUrl
  link.setAttribute('download', fileName)
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(downloadUrl)
}

export const useGrasshopperStore = defineStore('grasshopper', {
  state: () => ({
    controlMenu: false,
    menuType: null,
    menuTitle: null,
    diagramKey: 0,
    currentGraph: reactive({ nodes: [], edges: [] }),
    ipList: [],
    graphList: [],
    compareList: [],
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
    legendEnabled: false,
    showBdtEdges: false,
    selectedNode: null,
    showNoteCard: false,
    loading: false,
    globalError: false,
    errorMessage: null,
    alertType: null,
    alertTitle: null,
    // same origin in production; the Vite dev server proxies /api to the agent
    apiPrefix: '/api/operations',
    graphFormsTab: 'single',
    navCollapsed: readNavCollapsed(),
    calendarMonth: null,
    graphsFetched: false,
    fetchGraphLoad: false,
    fetchCompareLoad: false,
    graphLoad: false,
    compareGraphLoad: false,
    createCompareLoad: false,
    uploadCompareLoad: false,
    deleteGraphLoad: false,
    deleteCompareLoad: false,
    timelineCard: false,
    nodeCard: false,
    edgeMenu: false,
    hiddenMenu: false,
    searchMenu: false,
    // Grasshopper has no device observation history, so node cards never show a timeline
    deviceKey: 0,
    deviceTimeline: false,
    objectCard: false,
    objectCardData: null,
    nodeLabel: null,
    treeLayout: false,
    minimapToggled: true,
    processingQueue: null,
    inQueue: [],
    finishedQueue: [],
    // finished compare task id -> when this session first saw it finished (0 = before load)
    compareFinishedAt: null,
    refreshInterval: null,
  }),
  getters: {
    graphMonths: state => monthsWithGraphs(state.graphList),
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
    setReload() {
      this.diagramKey++
    },
    setCurrentGraph(graph, name) {
      this.currentGraph = graph
      this.fileName = name
      this.setReload()
    },
    setIpList(ips) {
      this.ipList = ips.sort()
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
    // returns the tasks that finished since the last update (none on the first load)
    setQueue(processing, queue, finished) {
      this.processingQueue = processing
      this.inQueue = queue
      this.finishedQueue = finished

      const firstLoad = this.compareFinishedAt === null
      const seen = { ...this.compareFinishedAt }
      const newlyFinished = []
      for (const task of this.finishedQueue) {
        if (task.id in seen) continue
        seen[task.id] = firstLoad ? 0 : Date.now()
        if (!firstLoad) newlyFinished.push(task)
      }
      this.compareFinishedAt = seen
      return newlyFinished
    },
    recentFinishedCompares() {
      const cutoff = Date.now() - RECENT_COMPARE_MS
      return this.finishedQueue.filter(
        task => this.compareFinishedAt?.[task.id] > cutoff,
      )
    },
    hasCompareActivity() {
      return (
        !!this.processingQueue ||
        this.inQueue.length > 0 ||
        this.recentFinishedCompares().length > 0
      )
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
    setTreeLayout(mode) {
      this.treeLayout = mode
    },
    toggleTreeLayout() {
      this.treeLayout = !this.treeLayout
    },
    setMinimapToggled(value) {
      this.minimapToggled = value
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
    setLoading(loading) {
      this.loading = loading
    },
    setGlobalError(error, message, type, title) {
      this.globalError = error
      this.errorMessage = message
      this.alertType = type
      this.alertTitle = title
    },
    setGraphFormsTab(tab) {
      this.graphFormsTab = tab
    },
    setNavCollapsed(collapsed) {
      this.navCollapsed = collapsed
      try {
        localStorage.setItem('navCollapsed', String(collapsed))
      } catch {
        // preference just won't persist
      }
    },
    setTimelineCard(value) {
      this.timelineCard = value
    },
    setNodeCard(value) {
      this.nodeCard = value
    },
    incDeviceKey() {
      this.deviceKey++
    },
    setNodeLabel(label) {
      this.nodeLabel = label
    },
    setObjectCard(value) {
      this.objectCard = value
    },
    setObjectCardData(data) {
      this.objectCardData = data
    },
    setCalendarMonth(month) {
      this.calendarMonth = month
    },
    // open the calendar at the most recent graph the first time it's shown
    async ensureCalendar() {
      if (!this.graphsFetched) await this.fetchGraphs()
      if (!this.calendarMonth) {
        this.calendarMonth = this.graphMonths.at(-1) || monthOf()
      }
    },
    async fetchQueue() {
      try {
        const { data } = await axios.get(
          `${this.apiPrefix}/ttl_compare_queue`,
          {
            responseType: 'json',
          },
        )
        const newlyFinished = this.setQueue(
          data.processing_task,
          data.queue,
          data.finished,
        )

        // the worker only marks a task finished after saving the compare file, so a newly
        // finished task means the saved list is out of date. This catches compares that
        // finish between polls without ever being seen processing.
        if (newlyFinished.length) await this.fetchCompareGraphs()
      } catch {
        this.setGlobalError(
          true,
          'Error fetching compare queue. Please try again later.',
          'error',
          'Error',
        )
      }
    },
    async runFetchCycle() {
      // keep a single polling loop no matter how many callers start it
      clearTimeout(this.refreshInterval)
      await this.fetchQueue()
      // poll faster while a compare is queued or generating so it shows up soon after finishing
      const active = !!this.processingQueue || this.inQueue.length > 0

      this.refreshInterval = setTimeout(
        () => {
          this.runFetchCycle()
        },
        active ? 3000 : 10000,
      )
    },
    async goToGraph(compare, graph, navigate = true) {
      compare ? (this.compareGraphLoad = true) : (this.graphLoad = true)
      this.setNodeCard(false)
      this.setEdgeMenu(false)
      this.setHiddenMenu(false)
      this.setSearchMenu(false)

      try {
        const { data } = await axios.get(
          `${this.apiPrefix}/${compare ? 'ttl_compare' : 'ttl_network'}/${graph}`,
          { responseType: 'json' },
        )
        this.setCompareMode(compare)
        this.setCurrentGraph(data, graph)
        this.setControlMenu(false, null, null)
        if (navigate) router.push(graphRoute(compare, graph))
        return true
      } catch (error) {
        if (error.response?.status === 404) {
          this.setGlobalError(
            true,
            `Graph <strong>${graph}</strong> does not exist.`,
            'error',
            'Not Found',
          )
        } else if (error.response?.status === 500) {
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
        return false
      } finally {
        compare ? (this.compareGraphLoad = false) : (this.graphLoad = false)
      }
    },
    async createCompare(graph1, graph2) {
      this.createCompareLoad = true

      try {
        await axios.post(`${this.apiPrefix}/ttl_compare_queue`, {
          ttl_1: graph1,
          ttl_2: graph2,
        })
        // keep the Graphs dialog open so its queue line shows the compare generating
        await this.runFetchCycle()
      } catch (error) {
        const compareItem = `${graph1.replace('.ttl', '')}_vs_${graph2}`
        if (error.response?.status === 400) {
          this.setGlobalError(
            true,
            `<strong>${compareItem}</strong> is already queued or generating.`,
            'warning',
            'Already Queued',
          )
        } else if (error.response?.status === 404) {
          this.setGlobalError(
            true,
            'One of the selected graphs does not exist.',
            'error',
            'Not Found',
          )
        } else {
          this.setGlobalError(
            true,
            `Error generating compare graph <strong>${compareItem}</strong>.`,
            'error',
            'Compare Graph Error',
          )
        }
      } finally {
        this.createCompareLoad = false
      }
    },
    // returns null on success, otherwise a short reason
    async uploadFile(compare, file) {
      const formData = new FormData()
      formData.append('file', file)

      try {
        await axios.post(
          `${this.apiPrefix}/${compare ? 'ttl_compare' : 'ttl'}`,
          formData,
          { headers: { 'Content-Type': 'multipart/form-data' } },
        )
        return null
      } catch (error) {
        return errorDetail(error) || 'Upload failed'
      }
    },
    async uploadGraph(compare, upload) {
      if (compare) this.uploadCompareLoad = true
      const error = await this.uploadFile(compare, upload)
      if (compare) this.uploadCompareLoad = false

      if (error) {
        this.setGlobalError(
          true,
          `Error uploading graph <strong>${upload.name}</strong>: ${error}.`,
          'error',
          'Upload Error',
        )
      }
      this.refreshItems()
    },
    async uploadGraphs(files, onStatus, concurrency = 3) {
      // onStatus(file, status, error) with status 'uploading' | 'done' | 'error'
      const queue = [...files]
      let failed = 0

      const worker = async () => {
        while (queue.length) {
          const file = queue.shift()
          onStatus(file, 'uploading')
          const error = await this.uploadFile(false, file)
          if (error) failed++
          onStatus(file, error ? 'error' : 'done', error)
        }
      }
      await Promise.all(
        Array.from({ length: Math.min(concurrency, files.length) }, worker),
      )

      if (files.some(file => file.name === 'base.ttl') && !failed) {
        this.setGlobalError(
          true,
          'The file <strong>base.ttl</strong> was uploaded. This will become the basis of all scans.',
          'warning',
          'Warning',
        )
      }
      this.refreshItems()
      return failed
    },
    async deleteGraph(compare, name) {
      compare ? (this.deleteCompareLoad = true) : (this.deleteGraphLoad = true)

      try {
        await axios.delete(
          `${this.apiPrefix}/${compare ? 'ttl_compare' : 'ttl_file'}/${name}`,
        )
        this.refreshItems()
      } catch (error) {
        if (error.response?.status === 404) {
          this.setGlobalError(
            true,
            `Graph <strong>${name}</strong> not found.`,
            'error',
            'Not Found',
          )
        } else {
          this.setGlobalError(
            true,
            `Error deleting graph <strong>${name}</strong>.`,
            'error',
            'Delete Error',
          )
        }
      } finally {
        compare
          ? (this.deleteCompareLoad = false)
          : (this.deleteGraphLoad = false)
      }
    },
    // the agent has no bulk endpoint, so delete one at a time; mirrors Flightdeck's
    // bulk_delete response so callers can treat both the same
    async deleteGraphs(compare, names) {
      const deleted = []
      const errors = []
      for (const name of names) {
        try {
          await axios.delete(
            `${this.apiPrefix}/${compare ? 'ttl_compare' : 'ttl_file'}/${name}`,
          )
          deleted.push(name)
        } catch (error) {
          errors.push({ name, detail: errorDetail(error) })
        }
      }
      if (errors.length) {
        this.setGlobalError(
          true,
          `${deleted.length} deleted, ${errors.length} failed: ` +
            errors.map(e => `<strong>${e.name}</strong>`).join(', '),
          'error',
          'Delete Incomplete',
        )
      }
      this.refreshItems()
      return { deleted, errors }
    },
    // no zip endpoint on the agent, so each graph downloads as its own TTL file
    async downloadGraphs(names) {
      let failed = 0
      for (const name of names) {
        try {
          const { data } = await axios.get(
            `${this.apiPrefix}/ttl_file/${name}`,
            {
              headers: { Accept: 'text/turtle' },
              responseType: 'blob',
            },
          )
          saveBlob(new Blob([data], { type: 'text/turtle' }), name)
        } catch {
          failed++
        }
      }
      if (failed) {
        this.setGlobalError(
          true,
          `${failed} of ${names.length} graphs could not be downloaded.`,
          'error',
          'Download Error',
        )
      }
      return !failed
    },
    async fetchGraphs() {
      this.fetchGraphLoad = true
      try {
        const { data } = await axios.get(`${this.apiPrefix}/ttl`, {
          responseType: 'json',
        })
        this.graphList = data.data.filter(name => !isCompareGraph(name)).sort()
        this.graphsFetched = true
      } catch {
        this.setGlobalError(true, 'Error fetching graphs.', 'error', 'Error')
      } finally {
        this.fetchGraphLoad = false
      }
    },
    async fetchCompareGraphs() {
      this.fetchCompareLoad = true
      try {
        const { data } = await axios.get(`${this.apiPrefix}/ttl_compare`, {
          responseType: 'json',
        })
        this.compareList = [...data.file_list].sort().reverse()
      } catch (error) {
        // 404 just means no compares yet; the saved list says so
        if (error.response?.status === 404) {
          this.compareList = []
        } else {
          this.setGlobalError(
            true,
            'Error fetching compare graphs.',
            'error',
            'Error',
          )
        }
      } finally {
        this.fetchCompareLoad = false
      }
    },
    async refreshItems() {
      await Promise.all([this.fetchGraphs(), this.fetchCompareGraphs()])
    },
    async exportTtl(compare, fileName) {
      try {
        const { data } = await axios.get(
          `${this.apiPrefix}/${compare ? 'ttl_compare_file' : 'ttl_file'}/${fileName}`,
          { headers: { Accept: 'text/turtle' }, responseType: 'blob' },
        )
        saveBlob(new Blob([data], { type: 'text/turtle' }), fileName)
      } catch (error) {
        this.exportError(error, fileName, 'TTL')
      }
    },
    async exportCsv(compare, fileName) {
      try {
        const { data } = await axios.get(
          `${this.apiPrefix}/csv_export/${fileName}`,
          { headers: { Accept: 'text/csv' }, responseType: 'blob' },
        )
        saveBlob(
          new Blob([data], { type: 'text/csv' }),
          fileName.replace('.ttl', '.csv'),
        )
      } catch (error) {
        this.exportError(error, fileName, 'CSV')
      }
    },
    async exportJson(compare, fileName) {
      try {
        const { data } = await axios.get(
          `${this.apiPrefix}/${compare ? 'ttl_compare' : 'ttl_network'}/${fileName}`,
          { headers: { Accept: 'application/json' }, responseType: 'json' },
        )
        saveBlob(
          new Blob([JSON.stringify(data, null, 2)], {
            type: 'application/json',
          }),
          fileName.replace('.ttl', '.json'),
        )
      } catch (error) {
        this.exportError(error, fileName, 'JSON')
      }
    },
    exportError(error, fileName, format) {
      if (error.response?.status === 404) {
        this.setGlobalError(
          true,
          `Graph <strong>${fileName}</strong> does not exist.`,
          'error',
          'Error',
        )
      } else if (error.response?.status === 500) {
        this.setGlobalError(
          true,
          `Server error exporting ${format}. Please try again later.`,
          'error',
          'Server Error',
        )
      } else {
        this.setGlobalError(
          true,
          `Error exporting ${format}.`,
          'error',
          'Error',
        )
      }
    },
  },
})
