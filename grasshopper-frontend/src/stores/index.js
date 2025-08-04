import { defineStore } from "pinia";
import { reactive } from "vue";

export const useGrasshopperStore = defineStore("grasshopper", {
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
    currentConfig: "Default",
    configToSave: null,
    physicsConfig: {},
    defaultConfig: {
      "enabled": true,
      "barnesHut": {
        "theta": 0.5,
        "gravitationalConstant": -7000,
        "centralGravity": 0.3,
        "springLength": 95,
        "springConstant": 0.04,
        "damping": 0.07,
        "avoidOverlap": 0
      },
      "forceAtlas2Based": {
        "theta": 0.5,
        "gravitationalConstant": -50,
        "centralGravity": 0.01,
        "springConstant": 0.08,
        "springLength": 100,
        "damping": 0.4,
        "avoidOverlap": 0
      },
      "repulsion": {
        "centralGravity": 0.2,
        "springLength": 200,
        "springConstant": 0.05,
        "nodeDistance": 100,
        "damping": 0.09
      },
      "hierarchicalRepulsion": {
        "centralGravity": 0,
        "springLength": 100,
        "springConstant": 0.01,
        "nodeDistance": 120,
        "damping": 0.09
      },
      "maxVelocity": 50,
      "minVelocity": 0.75,
      "solver": "barnesHut",
      "stabilization": {
        "enabled": true,
        "iterations": 200,
        "updateInterval": 50,
        "onlyDynamicEdges": false,
        "fit": true
      },
      "timestep":0.5,
      "adaptiveTimestep":true,
      "wind":{
        "x":0,
        "y":0
      }
    },
    compareMode: false,
    fileName: null,
    reloadKey: 0,
    bbmdList: [],
    compareQueue: [],
    currentTask: null,
    legendEnabled: false,
    showBdtEdges: false,
    selectedNode: null,
    showNoteCard: false,
    loading: false,
  }),
  actions: {
    setControlMenu(type, title) {
        this.controlMenu = !this.controlMenu;

        if (this.controlMenu) {
          this.menuType = type;
          this.menuTitle = title;
        } else {
          this.menuType = null;
          this.menuTitle = null;
        }
    },
    setSetupGraphs(graphs) {
      this.setupGraphs = graphs.sort();
    },
    setReload() {
      this.diagramKey++;
    },
    setCurrentGraph(graph, name) {
      this.currentGraph = graph;
      this.fileName = name;
      this.setReload();
    },
    setIpList(ips) {
      this.ipList = ips.sort();
    },
    setCompareList(compares) {
      this.compareList = compares.sort();
    },
    setDeleteGraphs(list) {
      this.deleteList = list.sort();
    },
    setDeleteCompareGraphs(list) {
      this.deleteCompareList = list.sort();
    },
    setCompareLoad(load) {
      this.compareLoad = load;
    },
    setPhysicsConfig(config) {
      this.physicsConfig = config;
    },
    setCompareMode(isCompare) {
      this.compareMode = isCompare;
    },
    triggerReload() {
      this.reloadKey++;
    },
    setBbmdList(list) {
      this.bbmdList = list.sort();
    },
    setQueue(task, list) {
      this.currentTask = task;
      this.compareQueue = list;
    },
    setConfigList(list) {
      this.configList = list.sort();
    },
    setConfigSelect(value) {
      this.configSelect = value;
    },
    setCurrentConfig(config) {
      this.currentConfig = config;
    },
    setSavableConfig(config) {
      this.configToSave = config;
    },
    setLegend(enabled) {
      this.legendEnabled = enabled;
    },
    toggleLegend() {
      this.legendEnabled = !this.legendEnabled;
    },
    setBdtEdges(enabled) {
      this.showBdtEdges = enabled;
    },
    setSelectedNode(node) {
      this.selectedNode = node;
    },
    setShowNoteCard(show) {
      this.showNoteCard = show;
    },
    setLoading(loading) {
      this.loading = loading;
    },
  },
});
