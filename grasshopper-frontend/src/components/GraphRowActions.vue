<template>
  <v-btn
    v-if="mode === 'pick'"
    size="small"
    :variant="picked ? 'tonal' : 'text'"
    color="#94D8FF"
    @click="$emit('pick')"
    >{{ picked ? 'Picked' : 'Pick' }}</v-btn
  >
  <template v-else>
    <v-menu location="bottom end">
      <template v-slot:activator="{ props: downloadProps }">
        <v-btn
          v-bind="downloadProps"
          icon="mdi-download"
          variant="text"
          size="small"
          density="comfortable"
          color="#FFFD94"
        ></v-btn>
      </template>
      <v-list density="compact">
        <v-list-item
          v-for="option in downloadOptions"
          :key="option.title"
          :title="option.title"
          @click="store[option.action](false, name)"
        ></v-list-item>
      </v-list>
    </v-menu>
    <v-btn
      v-if="confirmDelete"
      size="small"
      variant="tonal"
      color="red"
      :loading="store.deleteGraphLoad"
      @click="deleteGraph()"
      >Delete?</v-btn
    >
    <v-btn
      v-else
      icon="mdi-trash-can-outline"
      variant="text"
      size="small"
      density="comfortable"
      color="red"
      @click="confirmDelete = true"
    ></v-btn>
    <v-btn
      size="small"
      variant="tonal"
      color="#c1d200"
      append-icon="mdi-arrow-right"
      :loading="loading"
      @click="loadGraph()"
      >Load</v-btn
    >
  </template>
</template>

<script>
export default {
  props: {
    store: { type: Object, required: true },
    // browse: load/download/delete, pick: emit 'pick' for compare selection
    mode: { type: String, default: 'browse' },
    name: { type: String, required: true },
    picked: { type: Boolean, default: false },
  },
  emits: ['pick', 'loaded', 'deleted'],
  data() {
    return {
      confirmDelete: false,
      loading: false,
      downloadOptions: [
        { title: 'Download TTL', action: 'exportTtl' },
        { title: 'Download JSON', action: 'exportJson' },
        { title: 'Download CSV', action: 'exportCsv' },
      ],
    }
  },
  methods: {
    async loadGraph() {
      this.loading = true
      try {
        await this.store.goToGraph(false, this.name)
      } finally {
        this.loading = false
        this.$emit('loaded')
      }
    },
    async deleteGraph() {
      await this.store.deleteGraph(false, this.name)
      this.confirmDelete = false
      this.$emit('deleted')
    },
  },
}
</script>
