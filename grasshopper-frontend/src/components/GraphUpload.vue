<template>
  <div class="graph-upload">
    <!-- capture-phase drop so we handle it before Vuetify's file input does -->
    <div
      class="upload-row"
      :class="{ dragging }"
      @dragover.capture="onDragover"
      @dragleave.capture="dragging = false"
      @drop.capture="onDrop"
    >
      <v-file-input
        v-model="files"
        :key="inputKey"
        label="Upload graphs"
        variant="solo-filled"
        flat
        density="compact"
        hide-details
        multiple
        counter
        prepend-icon=""
        prepend-inner-icon="mdi-paperclip"
        accept=".ttl"
        :readonly="uploading"
        clearable
        autocomplete="off"
        @update:model-value="results = {}"
      >
        <!-- each file's chip doubles as its upload status -->
        <template v-slot:selection>
          <div class="file-chips">
            <v-chip
              v-for="row in rows"
              :key="row.name"
              size="small"
              :color="row.color"
              :variant="row.status === 'waiting' ? 'outlined' : 'tonal'"
            >
              <template v-slot:prepend>
                <v-progress-circular
                  v-if="row.status === 'uploading'"
                  indeterminate
                  size="12"
                  width="2"
                  class="chip-icon"
                ></v-progress-circular>
                <v-icon v-else-if="row.icon" size="14" class="chip-icon">{{
                  row.icon
                }}</v-icon>
              </template>
              {{ row.name }}
              <v-tooltip v-if="row.error" activator="parent" location="top">{{
                row.error
              }}</v-tooltip>
            </v-chip>
          </div>
        </template>
      </v-file-input>
      <v-btn
        variant="tonal"
        size="small"
        color="#94D8FF"
        append-icon="mdi-upload"
        :disabled="!toUpload.length || uploading"
        class="action-btn"
        :loading="uploading"
        @click="upload()"
        >Upload{{ toUpload.length > 1 ? ` ${toUpload.length}` : '' }}</v-btn
      >
    </div>
  </div>
</template>

<script>
import { isCompareGraph } from '@/utils/graphNames'

// scans are named by capture time (2025-06-01T08-12-00.ttl) but any .ttl is accepted,
// e.g. base.ttl; compares go through the Compare tab instead
function invalidReason(name) {
  if (!name.toLowerCase().endsWith('.ttl')) return 'File must be a .ttl file'
  if (isCompareGraph(name))
    return 'Compare graphs are uploaded from the Compare tab'
  return null
}

const ROW_STYLES = {
  waiting: { icon: null, color: '#cdcdcd' },
  uploading: { icon: null, color: '#94D8FF' },
  done: { icon: 'mdi-check', color: '#7bd389' },
  error: { icon: 'mdi-alert-circle-outline', color: '#ef5350' },
  invalid: { icon: 'mdi-alert-circle-outline', color: '#ef5350' },
}

export default {
  props: {
    store: { type: Object, required: true },
  },
  data() {
    return {
      files: [],
      inputKey: 0,
      dragging: false,
      uploading: false,
      // file name -> { status, error }
      results: {},
    }
  },
  computed: {
    fileList() {
      if (!this.files) return []
      return Array.isArray(this.files) ? this.files : [this.files]
    },
    // valid files not already uploaded, so a retry after failures only resends those
    toUpload() {
      return this.fileList.filter(
        file =>
          !invalidReason(file.name) &&
          this.results[file.name]?.status !== 'done',
      )
    },
    rows() {
      return this.fileList.map(file => {
        const result = this.results[file.name]
        const invalid = invalidReason(file.name)
        if (invalid) {
          return {
            name: file.name,
            status: 'invalid',
            error: invalid,
            ...ROW_STYLES.invalid,
          }
        }
        const status = result?.status || 'waiting'
        return {
          name: file.name,
          status,
          error: result?.error,
          ...ROW_STYLES[status],
        }
      })
    },
  },
  methods: {
    onDragover(event) {
      if (this.uploading) return
      event.preventDefault()
      this.dragging = true
    },
    // Read the dropped files straight from the drop event, which always lists every file.
    // Vuetify's own drop handler converts each one to a file-system entry asynchronously,
    // and dragging several files in from Finder could leave just one in the input.
    onDrop(event) {
      this.dragging = false
      if (this.uploading) return
      event.preventDefault()
      event.stopPropagation()
      const dropped = [...(event.dataTransfer?.files || [])]
      if (!dropped.length) return
      // add to the current selection, skipping files already in it
      const names = new Set(this.fileList.map(file => file.name))
      this.files = [
        ...this.fileList,
        ...dropped.filter(file => !names.has(file.name)),
      ]
      this.results = {}
    },
    async upload() {
      this.uploading = true
      try {
        await this.store.uploadGraphs(this.toUpload, (file, status, error) => {
          this.results = { ...this.results, [file.name]: { status, error } }
        })
        // keep failures in the list so they can be retried; clear a fully successful batch
        if (Object.values(this.results).every(r => r.status === 'done')) {
          this.files = []
          this.inputKey++
        }
      } finally {
        this.uploading = false
      }
    },
  },
}
</script>

<style lang="scss" scoped>
.graph-upload {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.upload-row {
  display: flex;
  align-items: center;
  gap: 16px;
  border-radius: 8px;
  outline: 1px dashed transparent;
  outline-offset: 4px;
  transition: outline-color 0.15s;
}
.upload-row.dragging {
  outline-color: #94d8ff;
}
.file-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 4px 0;
}
.chip-icon {
  margin-right: 4px;
}
</style>
