<template>
  <div class="startup-page">
    <div class="startup-menu">
      <div class="startup-header">
        <img src="@/assets/grasshopper-drk-bg.svg" class="logo-image" />
      </div>
      <v-row>
        <v-col cols="6" class="startup-col">
          <v-row class="tile">
            <v-form ref="setupGraphForm" v-model="graphValid" lazy-validation>
              <div class="flex-center-gapped-container">
                <v-autocomplete
                  v-model="setupGraph"
                  label="Load Graph"
                  variant="solo-filled"
                  density="compact"
                  hide-details="auto"
                  :items="store.setupGraphs"
                  clearable
                  :disabled="store.fetchGraphLoad"
                  :loading="store.fetchGraphLoad"
                  :key="`setup-graph-${inputKeys.setupGraph}`"
                  autocomplete="off"
                ></v-autocomplete>
                <v-btn
                  @click="
                      store.goToGraph(false, setupGraph)
                  "
                  :loading="store.graphLoad"
                  variant="tonal"
                  size="small"
                  append-icon="mdi-arrow-right"
                  color="#c1d200"
                  :disabled="!setupGraph || !graphValid"
                  >Load</v-btn
                >
              </div>
            </v-form>
            <hr class="line" />
            <v-form ref="uploadGraphForm" v-model="fileValid" lazy-validation>
              <div class="flex-center-gapped-container">
                <v-file-input
                  v-model="fileUpload"
                  clearable
                  label="Upload Graph"
                  variant="solo-filled"
                  density="compact"
                  accept=".ttl"
                  hide-details="auto"
                  @change="store.checkFileName()"
                  :key="`upload-graph-${inputKeys.uploadGraph}`"
                  :rules="[
                    v => !!v || 'File is required',
                    v => v.name.endsWith('.ttl') || 'File must be a .ttl file',
                    v =>
                      !v.name.includes('_vs_') ||
                      'File cannot be a compare file',
                  ]"
                  autocomplete="off"
                ></v-file-input>
                <v-btn
                  @click="
                    store.runAndReset(
                      [
                        $refs.uploadGraphForm,
                        $refs.setupGraphForm,
                        $refs.createCompareForm,
                      ],
                      [
                        'setupGraph',
                        'fileUpload',
                        'compareGraph1',
                        'compareGraph2',
                      ],
                      [
                        'setupGraph',
                        'uploadGraph',
                        'compareGraph1',
                        'compareGraph2',
                      ],
                      () => store.uploadGraph(false, fileUpload),
                      this,
                    )
                  "
                  :loading="uploadLoad"
                  variant="tonal"
                  size="small"
                  append-icon="mdi-upload"
                  color="#94D8FF"
                  :disabled="!fileUpload || !fileValid"
                  >Upload</v-btn
                >
              </div>
            </v-form>
            <hr class="line" />
            <v-form
              ref="deleteGraphForm"
              v-model="deletedGraphValid"
              lazy-validation
            >
              <div class="flex-center-gapped-container">
                <v-autocomplete
                  v-model="deletedGraph"
                  :items="store.deleteList"
                  label="Delete Graph"
                  variant="solo-filled"
                  density="compact"
                  hide-details="auto"
                  clearable
                  :disabled="store.fetchGraphLoad"
                  :loading="store.fetchGraphLoad"
                  :key="`delete-graph-${inputKeys.deleteGraph}`"
                  autocomplete="off"
                ></v-autocomplete>
                <v-btn
                  @click="
                    store.runAndReset(
                      [
                        $refs.deleteGraphForm,
                        $refs.setupGraphForm,
                        $refs.compareGraphForm,
                      ],
                      [
                        'deletedGraph',
                        'setupGraph',
                        'compareGraph1',
                        'compareGraph2',
                      ],
                      [
                        'deleteGraph',
                        'setupGraph',
                        'compareGraph1',
                        'compareGraph2',
                      ],
                      () => store.deleteGraph(false, deletedGraph),
                    )
                  "
                  :loading="store.deleteGraphLoad"
                  variant="tonal"
                  size="small"
                  color="red"
                  :disabled="!deletedGraph"
                  >Delete</v-btn
                >
              </div>
            </v-form>
          </v-row>
          <v-row class="tile">
            <v-form
              ref="compareGraphForm"
              v-model="compareValid"
              lazy-validation
            >
              <div class="flex-center-gapped-container">
                <v-autocomplete
                  v-model="compareGraph"
                  :items="store.compareList"
                  label="Load Compare Graph"
                  variant="solo-filled"
                  density="compact"
                  hide-details="auto"
                  clearable
                  :key="`compare-graph-${inputKeys.compareGraph}`"
                  autocomplete="off"
                ></v-autocomplete>
                <v-btn
                  @click="
                      store.goToGraph(true, compareGraph)
                  "
                  :loading="store.compareGraphLoad"
                  variant="tonal"
                  size="small"
                  append-icon="mdi-arrow-right"
                  color="#c1d200"
                  :disabled="!compareGraph"
                  >Load</v-btn
                >
              </div>
            </v-form>
            <hr class="line" />
            <v-form
              ref="createCompareForm"
              v-model="compareCreateValid"
              lazy-validation
            >
              <div class="flex-center-gapped-container">
                <v-autocomplete
                  v-model="compareGraph1"
                  label="Graph 1"
                  variant="solo-filled"
                  density="compact"
                  hide-details="auto"
                  :items="store.setupGraphs"
                  clearable
                  :key="`compare-graph1-${inputKeys.compareGraph1}`"
                  autocomplete="off"
                ></v-autocomplete>
                <h5 class="list-title">vs</h5>
                <v-autocomplete
                  v-model="compareGraph2"
                  label="Graph 2"
                  variant="solo-filled"
                  density="compact"
                  hide-details="auto"
                  :items="store.setupGraphs"
                  clearable
                  :key="`compare-graph2-${inputKeys.compareGraph2}`"
                  autocomplete="off"
                ></v-autocomplete>
                <div class="flex-center-container">
                  <v-btn
                    @click="
                      store.runAndReset(
                        [
                          $refs.createCompareForm,
                          $refs.compareGraphForm,
                          $refs.deleteCompareForm,
                        ],
                        [
                          'compareGraph1',
                          'compareGraph2',
                          'compareGraph',
                          'deletedCompareGraph',
                        ],
                        [
                          'compareGraph1',
                          'compareGraph2',
                          'compareGraph',
                          'deleteCompareGraph',
                        ],
                        () => store.createCompare(compareGraph1, compareGraph2),
                      )
                    "
                    :loading="store.createCompareLoad"
                    variant="tonal"
                    size="small"
                    append-icon="mdi-compare-horizontal"
                    color="#94D8FF"
                    :disabled="!compareGraph1 || !compareGraph2"
                  >
                    Compare
                  </v-btn>
                </div>
              </div>
            </v-form>
            <hr class="line" />
            <v-form
              ref="uploadCompareForm"
              v-model="compareUploadValid"
              lazy-validation
            >
              <div class="flex-center-gapped-container">
                <v-file-input
                  v-model="compareFileUpload"
                  clearable
                  label="Upload Compare Graph"
                  variant="solo-filled"
                  density="compact"
                  accept=".ttl"
                  hide-details="auto"
                  :key="`upload-graph-${inputKeys.uploadCompare}`"
                  :rules="[
                    v => !!v || 'File is required',
                    v => v.name.endsWith('.ttl') || 'File must be a .ttl file',
                    v =>
                      v.name.includes('_vs_') || 'File must be a compare file',
                  ]"
                  autocomplete="off"
                ></v-file-input>
                <v-btn
                  @click="
                    store.runAndReset(
                      [
                        $refs.uploadCompareForm,
                        $refs.compareGraphForm,
                        $refs.deleteCompareForm,
                      ],
                      [
                        'compareFileUpload',
                        'compareGraph',
                        'deleteCompareGraph',
                      ],
                      ['uploadCompare', 'compareGraph', 'deleteCompareGraph'],
                      () => store.uploadGraph(true, compareFileUpload),
                      this,
                    )
                  "
                  :loading="store.uploadCompareLoad"
                  variant="tonal"
                  size="small"
                  append-icon="mdi-upload"
                  color="#94D8FF"
                  :disabled="!compareFileUpload || !compareUploadValid"
                  >Upload</v-btn
                >
              </div>
            </v-form>
            <hr class="line" />
            <v-form
              ref="deleteCompareForm"
              v-model="deletedCompareGraphValid"
              lazy-validation
            >
              <div class="flex-center-gapped-container">
                <v-autocomplete
                  v-model="deletedCompareGraph"
                  :items="store.deleteCompareList"
                  label="Delete Compare Graph"
                  variant="solo-filled"
                  density="compact"
                  hide-details="auto"
                  clearable
                  :disabled="store.fetchCompareLoad"
                  :loading="store.fetchCompareLoad"
                  :key="`delete-compare-graph-${inputKeys.deleteCompareGraph}`"
                  autocomplete="off"
                ></v-autocomplete>
                <v-btn
                  @click="
                    store.runAndReset(
                      [$refs.deleteCompareForm, $refs.compareGraphForm],
                      ['deletedCompareGraph', 'compareGraph'],
                      ['deleteCompareGraph', 'compareGraph'],
                      () => store.deleteGraph(true, deletedCompareGraph),
                    )
                  "
                  :loading="store.deleteCompareLoad"
                  variant="tonal"
                  size="small"
                  color="red"
                  :disabled="!deletedCompareGraph"
                  >Delete</v-btn
                >
              </div>
            </v-form>
          </v-row>
        </v-col>
        <v-col cols="6" class="startup-col">
          <v-row class="big-tile">
            <div class="list-container">
              <h4 class="list-title">Recent Graphs</h4>
              <div class="graph-list">
                <p
                  class="list-text"
                  v-if="
                    store.recentGraphs.length === 0 && !store.fetchGraphLoad
                  "
                >
                  No items
                </p>
                <v-progress-circular
                  v-if="store.fetchGraphLoad"
                  indeterminate
                  class="load-indicator"
                ></v-progress-circular>
                <div
                  v-for="(graph, index) in store.recentGraphs"
                  :key="index"
                  class="graph-item"
                >
                  <p class="list-text">
                    {{ graph }}
                  </p>
                  <div class="graph-btns">
                    <v-menu open-on-hover>
                      <template v-slot:activator="{ props }">
                        <v-btn
                          v-bind="props"
                          variant="plain"
                          :ripple="false"
                          icon=""
                          id="no-background-hover"
                          density="compact"
                          color="#FFFD94"
                        >
                          <v-icon>mdi-download</v-icon>
                        </v-btn>
                      </template>

                      <v-list>
                        <v-list-item
                          v-for="(item, index) in downloadOptions"
                          :key="index"
                          @click="item.action(false, graph)"
                        >
                          <v-list-item-title>{{
                            item.title
                          }}</v-list-item-title>
                        </v-list-item>
                      </v-list>
                    </v-menu>
                    <v-btn
                      @click="store.goToGraph(false, graph)"
                      variant="plain"
                      color="#cdcdcd"
                      density="compact"
                      :ripple="false"
                      icon=""
                      id="no-background-hover"
                    >
                      <v-tooltip text="Load Graph" bottom delay="1000">
                        <template v-slot:activator="{ props }">
                          <v-icon v-bind="props">mdi-arrow-right</v-icon>
                        </template>
                      </v-tooltip>
                    </v-btn>
                  </div>
                </div>
              </div>
            </div>
            <div class="list-container">
              <h4 class="list-title">Recent Compare Graphs</h4>
              <div class="graph-list">
                <p
                  class="list-text"
                  v-if="
                    store.recentCompares.length === 0 && !store.fetchCompareLoad
                  "
                >
                  No items
                </p>
                <v-progress-circular
                  v-if="store.fetchCompareLoad"
                  indeterminate
                  class="load-indicator"
                ></v-progress-circular>
                <div
                  v-for="(compare, index) in store.recentCompares"
                  :key="index"
                  class="graph-item"
                >
                  <p class="list-text">
                    {{ compare }}
                  </p>
                  <div class="graph-btns">
                    <v-menu open-on-hover>
                      <template v-slot:activator="{ props }">
                        <v-btn
                          v-bind="props"
                          variant="plain"
                          :ripple="false"
                          icon=""
                          id="no-background-hover"
                          density="compact"
                          color="#FFFD94"
                        >
                          <v-icon>mdi-download</v-icon>
                        </v-btn>
                      </template>

                      <v-list>
                        <v-list-item
                          v-for="(item, index) in compareDownloadOptions"
                          :key="index"
                          @click="item.action(true, compare)"
                        >
                          <v-list-item-title>{{
                            item.title
                          }}</v-list-item-title>
                        </v-list-item>
                      </v-list>
                    </v-menu>
                    <v-btn
                      @click="store.goToGraph(true, compare)"
                      variant="plain"
                      color="#cdcdcd"
                      density="compact"
                      :ripple="false"
                      icon=""
                      id="no-background-hover"
                    >
                      <v-tooltip text="Load Compare Graph" bottom delay="1000">
                        <template v-slot:activator="{ props }">
                          <v-icon v-bind="props">mdi-arrow-right</v-icon>
                        </template>
                      </v-tooltip>
                    </v-btn>
                  </div>
                </div>
              </div>
            </div>
            <div class="list-container">
              <h4 class="list-title">Compare Queue</h4>
              <div class="graph-list">
                <h4 class="title">Processing</h4>
                <div
                  v-if="store.processingQueue"
                  class="graph-item"
                >
                  <p class="list-text">
                    {{ store.processingQueue.file_name }}
                  </p>
                  <v-progress-circular
                    indeterminate
                    size="20"
                    color="#94D8FF"
                  ></v-progress-circular>
                </div>
                <p class="list-text" v-if="!store.processingQueue && !store.fetchQueueLoad">
                  No items
                </p>
                <hr class="line" />
                <h4 class="title">In Queue</h4>
                <p v-if="store.inQueue.length > 0" class="list-text">
                    {{ store.inQueue.length }} item(s)
                  </p>
                <p class="list-text" v-if="store.inQueue.length === 0 && !store.fetchQueueLoad">
                  No items
                </p>
                <v-progress-circular
                  v-if="store.fetchQueueLoad"
                  indeterminate
                  class="load-indicator"
                ></v-progress-circular>
              </div>
            </div>
          </v-row>
        </v-col>
      </v-row>
    </div>
  </div>
</template>

<script>
export default {
  props: ['store'],
  components: {
  },
  data() {
    return {
      // LOADING STATES
      gatewayLoad: false,
      setupLoad: false,
      uploadLoad: false,
      compareLoad: false,
      fetchGraphLoad: false,
      deleteLoad: false,
      deleteCompareLoad: false,

      // FORM VALIDATION
      graphValid: false,
      fileValid: false,
      compareValid: false,
      compareCreateValid: false,
      compareUploadValid: false,
      deletedGraphValid: false,
      deletedCompareGraphValid: false,

      // FORM INPUTS
      fileUpload: null,
      compareFileUpload: null,
      compareGraph1: null,
      compareGraph2: null,
      compareGraph: null,
      deletedGraph: null,
      deletedCompareGraph: null,
      fileDeleted: null,
      setupGraph: null,

      loadError: false,
      deleteSuccess: false,
      showPassword: false,
      valid: false,

      inQueue: ["test_vs_test2.ttl", "example_vs_sample.ttl", "graph1_vs_graph2.ttl", "dataA_vs_dataB.ttl", "networkX_vs_networkY.ttl"],
    }
  },
  computed: {
    timeRangeModel: {
      get() {
        return this.store.timeRange
      },
      set(v) {
        this.store.setTimeRange(v)
      },
    },
    inputKeys: {
      get() {
        return this.store.inputKeys
      },
    },
    downloadOptions() {
      return [
        {
          title: 'Download TTL',
          action: (isCompare, fileName) => this.store.exportTtl(isCompare, fileName),
        },
        {
          title: 'Download JSON',
          action: (isCompare, fileName) => this.store.exportJson(isCompare, fileName),
        },
        {
          title: 'Download CSV',
          action: (isCompare, fileName) => this.store.exportCsv(isCompare, fileName),
        },
      ]
    },
    compareDownloadOptions() {
      return this.downloadOptions.filter(
        option => option.title !== 'Download CSV',
      )
    },
  },
  watch: {
  },
  mounted() {
    this.store.refreshItems()
  },
}
</script>

<style lang="scss" scoped>
.startup-page {
  display: flex;
  height: 100vh;
  width: 100vw;
  align-items: center;
  justify-content: center;
}
.startup-menu {
  display: flex;
  flex-direction: column;
  height: 88vh;
  width: 90vw;
  padding: 20px;
  border-radius: 20px;
  background: linear-gradient(to bottom right, #212121, #242424);
  min-height: 0;
}
.startup-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.logo-image {
  height: 5vh;
  margin-left: 10px;
}
.flex-center-gapped-container {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
}
.flex-center-container {
  display: flex;
  align-items: center;
  justify-content: center;
}
.line {
  width: 100%;
  color: #cdcdcd;
  opacity: 30%;
  margin: 10px 0;
}
.tile {
  background-color: #2a2a2a;
  padding: 20px;
  border-radius: 10px;
  margin: 5px;
  display: flex;
  flex-direction: column;
  justify-content: space-around;
}
.header-inputs {
  display: flex;
  align-items: center;
  width: 37vw;
  gap: 1vw;
}
.big-tile {
  background-color: #2a2a2a;
  padding: 20px;
  border-radius: 10px;
  margin: 5px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.startup-col {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  flex: 1 1 0;
}
.graph-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.graph-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  background-color: #2a2a2a;
  padding: 10px 15px;
  border-radius: 15px;
}
.graph-btns {
  display: flex;
  align-items: center;
  gap: 20px;
}
.list-container {
  display: flex;
  flex-direction: column;
  gap: 10px;
  background-color: #212121;
  border-radius: 15px;
  padding: 10px;
}
.list-title {
  color: #cdcdcd;
  margin-left: 10px;
}
.title {
  color: #87850b;
}
.list-text {
  color: #cdcdcd;
}
.load-indicator {
  margin: 10px;
}
</style>
