<template>
  <div class="graph-forms">
    <v-tabs v-model="tab" density="compact" color="#c1d200" grow class="tabs">
      <v-tab value="single">Single</v-tab>
      <v-tab value="compare">Compare</v-tab>
    </v-tabs>
    <v-tabs-window v-model="tab">
      <v-tabs-window-item value="single">
        <div class="tile">
          <GraphCalendar :store="store" :picked="openGraph" />
          <hr class="line" />
          <GraphUpload :store="store" />
        </div>
      </v-tabs-window-item>
      <v-tabs-window-item value="compare">
        <div class="compare-columns">
          <div class="tile">
            <div class="section-title">New compare</div>
            <GraphCalendar
              :store="store"
              mode="pick"
              :picked="comparePicks"
              @pick="togglePick"
            />
            <div class="flex-center-gapped-container">
              <div class="picks">
                <v-chip
                  v-for="(pick, index) in [compareGraph1, compareGraph2]"
                  :key="`${index}-${pick}`"
                  :closable="!!pick"
                  :variant="pick ? 'tonal' : 'outlined'"
                  color="#94D8FF"
                  size="small"
                  @click:close="togglePick(pick)"
                  >{{
                    pick ? graphLabel(pick) : `Pick graph ${index + 1}`
                  }}</v-chip
                >
              </div>
              <v-btn
                @click="createCompare()"
                class="action-btn"
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

          <div class="tile saved-tile">
            <div class="saved-header">
              <span class="section-title">Saved compares</span>
              <v-progress-circular
                v-if="store.fetchCompareLoad"
                indeterminate
                size="14"
                width="2"
                color="#8a8a8a"
              ></v-progress-circular>
              <v-text-field
                v-model="compareSearch"
                class="compare-search"
                placeholder="Search"
                prepend-inner-icon="mdi-magnify"
                variant="solo-filled"
                flat
                density="compact"
                hide-details
                clearable
              ></v-text-field>
            </div>
            <div class="saved-list">
              <p v-if="!filteredCompares.length" class="list-text empty-text">
                {{ compareSearch ? 'No matches' : 'No saved compares' }}
              </p>
              <div
                v-for="name in filteredCompares"
                :key="name"
                class="saved-row"
                :class="{
                  active: store.compareMode && store.fileName === name,
                }"
              >
                <div class="saved-name" :title="name">
                  <span>{{ compareLabel(name)[0] }}</span>
                  <v-icon size="14" color="#6f6f6f">mdi-arrow-right</v-icon>
                  <span>{{ compareLabel(name)[1] }}</span>
                </div>
                <v-menu location="bottom end">
                  <template v-slot:activator="{ props }">
                    <v-btn
                      v-bind="props"
                      icon="mdi-download"
                      variant="text"
                      size="small"
                      density="comfortable"
                      color="#FFFD94"
                    ></v-btn>
                  </template>
                  <v-list density="compact">
                    <v-list-item
                      title="Download TTL"
                      @click="download('exportTtl', name)"
                    ></v-list-item>
                    <v-list-item
                      title="Download JSON"
                      @click="download('exportJson', name)"
                    ></v-list-item>
                  </v-list>
                </v-menu>
                <v-btn
                  v-if="confirmDeleteCompare === name"
                  size="small"
                  variant="tonal"
                  color="red"
                  :loading="store.deleteCompareLoad"
                  @click="deleteCompare(name)"
                  >Delete?</v-btn
                >
                <v-btn
                  v-else
                  icon="mdi-trash-can-outline"
                  variant="text"
                  size="small"
                  density="comfortable"
                  color="red"
                  @click="confirmDeleteCompare = name"
                ></v-btn>
                <v-btn
                  size="small"
                  variant="tonal"
                  color="#c1d200"
                  append-icon="mdi-arrow-right"
                  :loading="loadingCompare === name"
                  @click="loadCompare(name)"
                  >Load</v-btn
                >
              </div>
            </div>
            <hr class="line" />
            <v-form
              ref="uploadCompareForm"
              v-model="compareUploadValid"
              lazy-validation
            >
              <div class="flex-center-gapped-container">
                <v-file-input
                  v-model="compareFileUpload"
                  :key="`upload-compare-${uploadCompareKey}`"
                  prepend-icon=""
                  prepend-inner-icon="mdi-paperclip"
                  clearable
                  label="Upload compare graph"
                  variant="solo-filled"
                  flat
                  density="compact"
                  accept=".ttl"
                  hide-details="auto"
                  :rules="[
                    v =>
                      !v ||
                      v.name.endsWith('.ttl') ||
                      'File must be a .ttl file',
                    v =>
                      !v ||
                      v.name.includes('_vs_') ||
                      'File must be a compare file',
                  ]"
                  autocomplete="off"
                ></v-file-input>
                <v-btn
                  @click="uploadCompare()"
                  class="action-btn"
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

        <div v-if="store.hasCompareActivity()" class="queue-line">
          <v-icon size="16" color="#8a8a8a">mdi-tray-full</v-icon>
          <template v-if="store.processingQueue">
            <v-progress-circular
              indeterminate
              size="12"
              width="2"
              color="#94D8FF"
            ></v-progress-circular>
            <span
              >Generating
              <strong>{{
                compareLabel(store.processingQueue.file_name).join(' → ')
              }}</strong></span
            >
          </template>
          <span v-if="store.inQueue.length"
            >{{ store.inQueue.length }} queued</span
          >
          <template v-if="store.recentFinishedCompares().length">
            <span>Finished:</span>
            <v-chip
              v-for="task in store.recentFinishedCompares()"
              :key="task.id"
              size="x-small"
              variant="tonal"
              color="#c1d200"
              append-icon="mdi-arrow-right"
              @click="loadCompare(task.file_name)"
              >{{ compareLabel(task.file_name).join(' → ') }}</v-chip
            >
          </template>
        </div>
      </v-tabs-window-item>
    </v-tabs-window>
  </div>
</template>

<script>
import GraphCalendar from './GraphCalendar.vue'
import GraphUpload from './GraphUpload.vue'
import { compareLabel, graphLabel } from '@/utils/graphNames'
export default {
  props: {
    store: { type: Object, required: true },
  },
  components: {
    GraphCalendar,
    GraphUpload,
  },
  data() {
    return {
      tab: this.store.graphFormsTab,
      compareGraph1: null,
      compareGraph2: null,
      compareSearch: '',
      confirmDeleteCompare: null,
      loadingCompare: null,
      compareFileUpload: null,
      compareUploadValid: false,
      uploadCompareKey: 0,
    }
  },
  computed: {
    openGraph() {
      return this.store.fileName && !this.store.compareMode
        ? [this.store.fileName]
        : []
    },
    comparePicks() {
      return [this.compareGraph1, this.compareGraph2].filter(Boolean)
    },
    filteredCompares() {
      const query = (this.compareSearch || '').trim().toLowerCase()
      const compares = this.store.compareList
      if (!query) return compares
      return compares.filter(
        name =>
          this.compareLabel(name).join(' ').toLowerCase().includes(query) ||
          name.toLowerCase().includes(query),
      )
    },
  },
  watch: {
    tab(value) {
      this.store.setGraphFormsTab(value)
    },
  },
  methods: {
    graphLabel,
    compareLabel,
    // picks keep their slot so the compare runs in the order they were picked:
    // removing one empties that slot, and the next pick fills the first empty slot
    togglePick(name) {
      if (this.compareGraph1 === name) {
        this.compareGraph1 = null
      } else if (this.compareGraph2 === name) {
        this.compareGraph2 = null
      } else if (!this.compareGraph1) {
        this.compareGraph1 = name
      } else {
        this.compareGraph2 = name
      }
    },
    async createCompare() {
      await this.store.createCompare(this.compareGraph1, this.compareGraph2)
      this.compareGraph1 = null
      this.compareGraph2 = null
    },
    async loadCompare(name) {
      this.loadingCompare = name
      try {
        await this.store.goToGraph(true, name)
      } finally {
        this.loadingCompare = null
      }
    },
    async deleteCompare(name) {
      await this.store.deleteGraph(true, name)
      this.confirmDeleteCompare = null
    },
    download(action, name) {
      this.store[action](true, name)
    },
    async uploadCompare() {
      await this.store.uploadGraph(true, this.compareFileUpload)
      this.compareFileUpload = null
      this.uploadCompareKey++
    },
  },
}
</script>

<style lang="scss" scoped>
.graph-forms {
  display: flex;
  flex-direction: column;
}
.tile {
  background-color: #181818;
  padding: 16px 20px;
  border-radius: 12px;
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
/* keep the main action buttons the same width so rows line up */
.tile :deep(.action-btn) {
  min-width: 112px;
}
.flex-center-gapped-container {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
}
.line {
  width: 100%;
  border: none;
  border-top: 1px solid rgba(205, 205, 205, 0.12);
  margin: 12px 0;
}
.section-title {
  color: #8a8a8a;
  font-size: 0.75rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.picks {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  flex: 1;
  min-width: 0;
}
.compare-columns {
  display: grid;
  gap: 12px;
}
/* side by side once the card can widen (see .wide in StartMenu / ControlMenus); keyed to
   the viewport rather than the card so the layout doesn't flip while the card resizes */
@media (min-width: 900px) {
  .compare-columns {
    grid-template-columns: 1fr 1fr;
    /* lay out at (nearly) the widened card's content width from the first frame, so text
       doesn't re-wrap and change the height while the card animates wider; the tab window
       clips the overflow. Card is min(1080px, 100vw - 32px) wide with 24px padding a side,
       less 24px slack for a scrollbar. */
    min-width: calc(min(1080px, 100vw - 32px) - 48px - 24px);
  }
}
.compare-columns > .tile {
  margin-top: 12px;
}
.saved-tile {
  /* fill the row height set by the calendar column and scroll the list inside */
  min-height: 0;
}
.saved-header {
  display: flex;
  align-items: center;
  gap: 8px;
}
.compare-search {
  margin-left: auto;
  max-width: 180px;
}
.saved-list {
  flex: 1 1 0;
  min-height: 160px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-top: 4px;
}
.saved-row {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 4px 4px 10px;
  border-radius: 8px;
}
.saved-row:hover,
.saved-row.active {
  background-color: #2a2a2a;
}
.saved-name {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 6px;
  color: #cdcdcd;
  font-size: 0.85rem;
  white-space: nowrap;
  overflow: hidden;
}
.empty-text {
  color: #6f6f6f;
  font-size: 0.85rem;
  margin: 8px 10px;
}
.queue-line {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  padding: 8px 12px;
  border-radius: 10px;
  background-color: #181818;
  color: #8a8a8a;
  font-size: 0.8rem;
}
.tabs {
  border-bottom: 1px solid rgba(205, 205, 205, 0.12);
}
.list-text {
  color: #cdcdcd;
}
.title {
  color: #87850b;
}
</style>
