<template>
  <div
    :class="[
      'menu-wrapper',
      store.menuType === 'compare' ? 'alt-menu' : 'menu',
    ]"
  >
    <div
      class="header"
      :class="store.menuType === 'compare' ? 'header-short' : 'header-tall'"
    >
      <v-btn
        class="close-btn"
        variant="plain"
        :ripple="false"
        icon=""
        id="no-background-hover"
        size="small"
        density="compact"
        @click="closeMenu()"
        ><v-icon>mdi-close</v-icon></v-btn
      >
    </div>
    <div class="menu-title">
      <h4 class="text">{{ store.menuTitle }}</h4>
    </div>
    <div v-if="store.menuType == 'compare'" class="alt-container">
      <div class="multiple-items">
        <v-form ref="compareGraphForm" v-model="compareValid" lazy-validation>
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
        <hr class="line divider-margin" />
        <v-form
          ref="createCompareForm"
          v-model="compareCreateValid"
          lazy-validation
        >
          <v-autocomplete
            v-model="compareGraph1"
            label="Graph 1"
            variant="solo-filled"
            density="compact"
            :items="store.setupGraphs"
            clearable
            hide-details="auto"
            :key="`compare-graph1-${inputKeys.compareGraph1}`"
            autocomplete="off"
          ></v-autocomplete>
          <h5 class="text text-spacing">VS</h5>
          <v-autocomplete
            v-model="compareGraph2"
            label="Graph 2"
            variant="solo-filled"
            density="compact"
            :items="store.setupGraphs"
            clearable
            :key="`compare-graph2-${inputKeys.compareGraph2}`"
            autocomplete="off"
          ></v-autocomplete>
          <div class="flex-center-container">
            <v-btn
              @click="
                  store.createCompare(compareGraph1, compareGraph2)
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
        </v-form>
        <hr class="line divider-margin" />
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
                v => v.name.includes('_vs_') || 'File must be a compare file',
              ]"
              autocomplete="off"
            ></v-file-input>
            <v-btn
              @click="
                store.runAndReset(
                  [
                    $refs.uploadCompareForm,
                    $refs.compareGraphForm
                  ],
                  [
                    'compareFileUpload',
                    'compareGraph'
                  ],
                  [
                    'uploadCompare',
                    'compareGraph'
                  ],
                  () => store.uploadGraph(true, compareFileUpload),
                  this
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
      </div>
    </div>
    <div v-if="store.menuType == 'delete'" class="delete-container">
      <div class="multiple-items">
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
                  [$refs.deleteGraphForm],
                  ['deletedGraph'],
                  ['deleteGraph'],
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
        <hr class="line-delete" />
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
              :key="`delete-compare-graph-${store.selectKey}`"
              autocomplete="off"
            ></v-autocomplete>
            <v-btn
              @click="
                store.runAndReset(
                  [$refs.deleteCompareForm],
                  ['deletedCompareGraph'],
                  ['deleteCompareGraph'],
                  () => store.deleteGraph(true, deletedCompareGraph),
                )
              "
              :loading="store.deleteCompareLoad"
              variant="tonal"
              size="small"
              color="red"
              :disabled="!deletedCompareGraph || !deletedCompareGraphValid"
              >Delete</v-btn
            >
          </div>
        </v-form>
      </div>
    </div>
    <div v-if="store.menuType == 'setup'" class="container setup-container">
      <div class="multiple-items">
        <v-form ref="setupGraphForm" v-model="graphValid" lazy-validation>
          <div :class="store.configSelect ? 'setup-config' : 'setup-default'">
            <v-autocomplete
              v-model="setupGraph"
              label="Load Graph"
              variant="solo-filled"
              density="compact"
              :hide-details="!store.configSelect"
              :items="store.setupGraphs"
              clearable
              :disabled="store.fetchGraphLoad"
              :loading="store.fetchGraphLoad"
              :key="`setup-graph-${inputKeys.setupGraph}`"
              autocomplete="off"
            ></v-autocomplete>
            <v-btn
              v-if="!store.configSelect"
              @click="
                  store.goToGraph(false, setupGraph)
              "
              :loading="store.graphLoad"
              variant="tonal"
              size="small"
              append-icon="mdi-arrow-right"
              color="#c1d200"
              :disabled="!setupGraph"
              >Load</v-btn
            >
          </div>
        </v-form>
        <hr class="line divider-margin" />
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
                  !v.name.includes('_vs_') || 'File cannot be a compare file',
              ]"
              autocomplete="off"
            ></v-file-input>
            <v-btn
              @click="
                store.runAndReset(
                  [$refs.uploadGraphForm, $refs.setupGraphForm],
                  ['fileUpload', 'setupGraph'],
                  ['uploadGraph', 'setupGraph'],
                  () => store.uploadGraph(false, fileUpload),
                  this
                )
              "
              :loading="store.uploadGraphLoad"
              variant="tonal"
              size="small"
              append-icon="mdi-upload"
              color="#94D8FF"
              :disabled="!fileUpload || !fileValid"
              >Upload</v-btn
            >
          </div>
        </v-form>
      </div>
    </div>
    <div v-if="store.menuType == 'config'" class="container">
      <v-text-field
        v-if="store.menuTitle == 'Save Config'"
        v-model="configTitle"
        label="Config Name"
        density="compact"
        variant="solo-filled"
        :rules="configRules"
        clearable
      ></v-text-field>
      <v-autocomplete
        v-if="store.menuTitle == 'Load Config'"
        v-model="config"
        label="Select Config"
        variant="solo-filled"
        density="compact"
        :items="store.configList"
        clearable
      ></v-autocomplete>
      <div class="flex-center-container">
        <v-btn
          v-if="store.menuTitle == 'Save Config'"
          @click="saveConfig()"
          :loading="configLoad"
          variant="tonal"
          size="small"
          append-icon="mdi-content-save"
          color="#94D8FF"
          :disabled="!configTitle"
          >Save
        </v-btn>
        <v-btn
          v-if="store.menuTitle == 'Load Config'"
          @click="loadConfig()"
          :loading="configLoad"
          variant="tonal"
          size="small"
          append-icon="mdi-arrow-right"
          color="#c1d200"
          :disabled="!config"
          >Load
        </v-btn>
      </div>
    </div>
  </div>
</template>

<script>
import { gsap } from 'gsap'
export default {
  props: ['store'],
  data() {
    return {
      //FORM INPUTS
      compareGraph: null,
      compareGraph1: null,
      compareGraph2: null,
      compareFileUpload: null,
      deletedGraph: null,
      deletedCompareGraph: null,
      setupGraph: null,
      fileUpload: null,

      // FORM VALIDATION
      graphValid: false,
      fileValid: false,
      compareValid: false,
      compareCreateValid: false,
      compareUploadValid: false,
      deletedGraphValid: false,
      deletedCompareGraphValid: false,
    }
  },
  computed: {
    gateway: {
      get() {
        return this.store.gateway
      },
      set(value) {
        this.store.setGateway(value)
      },
    },
    inputKeys: {
      get() {
        return this.store.inputKeys
      },
    },
    timeRangeModel: {
      get() {
        return this.store.timeRange
      },
      set(v) {
        this.store.setTimeRange(v)
      },
    },
    animateClass() {
      return this.store.menuType === 'compare' ? '.alt-menu' : '.menu'
    },
  },
  watch: {
    // gateway(newVal, oldVal) {
    //   if (this.store.gateway) {
    //     this.store.runRouteWithCheck(() => this.store.refreshItems())
    //     sessionStorage.setItem('gateway', this.store.gateway)
    //   }
    // },
  },
  mounted() {
    this.store.refreshItems()
    gsap.from(this.animateClass, {
      duration: 0.25,
      opacity: 0,
      y: 50,
      ease: 'power2.out',
    })

    // this.store.runRouteWithCheck(() => this.store.fetchGateways())
    // if (this.gateway) {
    //   this.store.runRouteWithCheck(() => this.store.refreshItems())
    // }
  },
  methods: {
    closeMenu() {
      gsap.to(this.animateClass, {
        duration: 0.25,
        opacity: 0,
        y: 50,
        ease: 'power2.in',
        onComplete: () => {
          this.store.setControlMenu(false, null, null)
        },
      })
    },
  },
}
</script>

<style lang="scss" scoped>
.menu-wrapper {
  z-index: 1000;
}
.menu {
  width: 30vw;
  background-color: #212121;
  border-radius: 15px;
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  box-shadow: 0px 4px 1px rgba(0, 0, 0, 0.5);
}
.alt-menu {
  width: 30vw;
  background-color: #212121;
  border-radius: 15px;
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  box-shadow: 0px 4px 1px rgba(0, 0, 0, 0.5);
}
.container {
  height: 85%;
  display: grid;
  align-items: center;
  align-content: center;
}
.setup-container {
  align-content: space-evenly;
}
.alt-container {
  height: 80%;
  display: grid;
  align-items: center;
}
.header {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  width: 100%;
  padding: 5px;
}
.header-short {
  height: 10%;
}
.header-tall {
  height: 20%;
}
.menu-title {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 5%;
}
.text {
  color: #cdcdcd;
  width: 100%;
  text-align: center;
}
.text-spacing {
  margin: 10px 0;
}
.line {
  width: 100%;
  color: #cdcdcd;
  opacity: 30%;
}
.line-delete {
  width: 100%;
  color: #cdcdcd;
  opacity: 30%;
  margin: 10px 0;
}
.divider-margin {
  margin: 15px 0px;
}
.list-divider {
  margin: 8px 8px;
}
.search-results {
  list-style: none;
  padding: 5px 0;
  margin: 10px 0;
  overflow-y: scroll;
  background-color: #2a2a2a;
  border-radius: 8px;
  box-shadow: 0px 1px 1px rgba(0, 0, 0, 0.1);
  width: 100%;
  height: 100%;
  max-height: 160px;
}
.list-header {
  margin: 10px 10px 0px 10px;
}
.list-item {
  margin-left: 10px;
}
.warning {
  position: absolute;
  width: 90%;
  translate: 1% 125%;
}
.success {
  position: absolute;
  width: 90%;
  translate: 0%;
  top: 5%;
}
.alt-success {
  position: absolute;
  width: 90%;
}
.setup-default {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
}
.setup-config {
  display: contents;
}
.delete-menu {
  width: 30vw;
  background-color: #212121;
  border-radius: 15px;
  position: absolute;
  top: 25%;
  left: 35%;
  box-shadow: 0px 4px 1px rgba(0, 0, 0, 0.5);
}
.delete-container {
  height: 60%;
  display: grid;
  align-items: center;
  align-content: space-evenly;
  overflow: scroll;
}
.multiple-items {
  background-color: #121212;
  padding: 15px;
  margin: 10px;
  border-radius: 15px;
}
.gateway-container {
  margin: 10px;
  padding: 15px;
  background-color: #121212;
  border-radius: 15px;
}
.menu-alert {
  position: absolute;
  width: 90%;
  left: 50%;
  transform: translateX(-50%);
  top: 5%;
  z-index: 1000;
  border-radius: 15px;
}
.flex-center-container {
  display: flex;
  align-items: center;
  justify-content: center;
}
.flex-center-gapped-container {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
}
.close-btn {
  margin: 5px 5px 0 0;
}
</style>
