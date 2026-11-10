<template>
  <div class="graph-calendar">
    <div class="calendar-header">
      <v-btn
        icon=""
        variant="plain"
        :ripple="false"
        id="no-background-hover"
        size="small"
        density="compact"
        class="month-arrow"
        @click="shiftMonth(-1)"
        ><v-icon>mdi-chevron-left</v-icon></v-btn
      >
      <v-menu
        v-model="pickerOpen"
        :close-on-content-click="false"
        location="bottom"
      >
        <template v-slot:activator="{ props: pickerProps }">
          <button v-bind="pickerProps" type="button" class="month-label">
            {{ monthLabel }}
            <!-- <v-icon size="16" class="month-label-icon">mdi-menu-down</v-icon> -->
          </button>
        </template>
        <div class="month-picker">
          <div class="picker-year">
            <v-btn
              icon=""
              variant="plain"
              :ripple="false"
              size="small"
              density="compact"
              class="month-arrow"
              :disabled="pickerYear <= minPickerYear"
              @click="pickerYear--"
              ><v-icon>mdi-chevron-left</v-icon></v-btn
            >
            <span>{{ pickerYear }}</span>
            <v-btn
              icon=""
              variant="plain"
              :ripple="false"
              size="small"
              density="compact"
              class="month-arrow"
              :disabled="pickerYear >= currentYear"
              @click="pickerYear++"
              ><v-icon>mdi-chevron-right</v-icon></v-btn
            >
          </div>
          <div class="picker-months">
            <button
              v-for="option in pickerMonths"
              :key="option.value"
              type="button"
              class="picker-month"
              :class="{
                selected: option.value === month,
                'has-graphs': option.hasGraphs,
              }"
              :disabled="option.value > currentMonth"
              @click="pickMonth(option.value)"
            >
              {{ option.label }}
              <span class="picker-dot"></span>
            </button>
          </div>
        </div>
      </v-menu>
      <v-btn
        icon=""
        variant="plain"
        :ripple="false"
        id="no-background-hover"
        size="small"
        density="compact"
        class="month-arrow"
        :disabled="month >= currentMonth"
        @click="shiftMonth(1)"
        ><v-icon>mdi-chevron-right</v-icon></v-btn
      >
      <v-progress-circular
        v-if="store.fetchGraphLoad"
        indeterminate
        size="16"
        width="2"
        class="header-spinner"
      ></v-progress-circular>
      <div class="header-actions">
        <v-btn
          v-if="month !== currentMonth"
          variant="text"
          size="small"
          @click="setMonth(currentMonth)"
          >Today</v-btn
        >
        <v-btn
          v-if="mode === 'browse'"
          :variant="selecting ? 'tonal' : 'text'"
          :color="selecting ? '#94D8FF' : undefined"
          size="small"
          prepend-icon="mdi-checkbox-multiple-marked-outline"
          :disabled="!store.graphList.length"
          @click="toggleSelecting()"
          >Select</v-btn
        >
      </div>
    </div>

    <div class="weekdays">
      <span v-for="day in weekdays" :key="day">{{ day }}</span>
    </div>
    <div class="grid">
      <template v-for="cell in cells" :key="cell.date">
        <div v-if="!cell.inMonth" class="cell outside"></div>
        <v-menu
          v-else
          :model-value="openDay === cell.date"
          @update:model-value="open => (openDay = open ? cell.date : null)"
          :disabled="!cell.graphs.length || selecting"
          :close-on-content-click="false"
          location="bottom"
          max-width="440"
        >
          <template v-slot:activator="{ props: menuProps }">
            <v-tooltip
              :disabled="!cell.graphs.length || openDay === cell.date"
              location="top"
              open-delay="300"
            >
              <template v-slot:activator="{ props: tooltipProps }">
                <button
                  v-bind="mergeProps(menuProps, tooltipProps)"
                  type="button"
                  class="cell"
                  :class="{
                    today: cell.date === today,
                    future: cell.date > today,
                    empty: !cell.graphs.length,
                    picked: cell.graphs.some(g => picked.includes(g.ttl_name)),
                    selected:
                      cell.graphs.length &&
                      cell.graphs.every(g => selection.includes(g.ttl_name)),
                  }"
                  :disabled="!cell.graphs.length"
                  @click="selecting && toggleDay(cell)"
                >
                  <span class="day-number">{{ cell.day }}</span>
                  <span v-if="cell.graphs.length" class="dots">
                    <span
                      v-for="graph in cell.graphs.slice(0, 3)"
                      :key="graph.ttl_name"
                      class="dot"
                    ></span>
                    <span v-if="cell.graphs.length > 3" class="more"
                      >+{{ cell.graphs.length - 3 }}</span
                    >
                  </span>
                </button>
              </template>
              <div class="tooltip">
                <strong
                  >{{ cell.graphs.length }} graph{{
                    cell.graphs.length === 1 ? '' : 's'
                  }}</strong
                >
                <div
                  v-for="graph in cell.graphs.slice(0, 6)"
                  :key="graph.ttl_name"
                >
                  <span class="dot inline"></span
                  >{{ graphTime(graph.ttl_name) }}
                </div>
                <div v-if="cell.graphs.length > 6">
                  +{{ cell.graphs.length - 6 }} more
                </div>
              </div>
            </v-tooltip>
          </template>

          <div class="day-popover">
            <div class="popover-title">{{ dayLabel(cell.date) }}</div>
            <div
              v-for="graph in cell.graphs"
              :key="graph.ttl_name"
              class="graph-row"
              :class="{ picked: picked.includes(graph.ttl_name) }"
            >
              <span class="dot"></span>
              <div class="graph-info">
                <div class="graph-time">{{ graphTime(graph.ttl_name) }}</div>
                <div class="graph-detail" :title="graph.ttl_name">
                  {{ graph.ttl_name }}
                </div>
              </div>
              <GraphRowActions
                :store="store"
                :mode="mode"
                :name="graph.ttl_name"
                :picked="picked.includes(graph.ttl_name)"
                @pick="pick(graph)"
                @loaded="openDay = null"
                @deleted="onDeleted(graph.ttl_name)"
              />
            </div>
          </div>
        </v-menu>
      </template>
    </div>

    <div v-if="otherGraphs.length" class="other-graphs">
      <div class="other-title">Other graphs</div>
      <div
        v-for="name in otherGraphs"
        :key="name"
        class="graph-row"
        :class="{
          picked: picked.includes(name),
          selectable: selecting,
          selected: selection.includes(name),
        }"
        @click="selecting && toggleNames([name])"
      >
        <v-icon size="16" class="other-icon">{{
          selecting
            ? selection.includes(name)
              ? 'mdi-checkbox-marked'
              : 'mdi-checkbox-blank-outline'
            : 'mdi-file-outline'
        }}</v-icon>
        <div class="graph-info">
          <div class="graph-time">{{ name }}</div>
          <div v-if="name === 'base.ttl'" class="graph-detail">
            Basis of all scans
          </div>
        </div>
        <GraphRowActions
          v-if="!selecting"
          :store="store"
          :mode="mode"
          :name="name"
          :picked="picked.includes(name)"
          @pick="$emit('pick', name)"
          @deleted="onDeleted(name)"
        />
      </div>
    </div>

    <div class="calendar-footer">
      <template v-if="selecting">
        <span class="selection-count"
          >{{ selection.length }} selected
          <span class="hint">· click days to select their graphs</span></span
        >
        <v-btn
          variant="text"
          size="small"
          :disabled="!selection.length"
          @click="selection = []"
          >Clear</v-btn
        >
        <v-btn
          variant="tonal"
          size="small"
          color="#FFFD94"
          prepend-icon="mdi-download"
          :disabled="!selection.length"
          :loading="bulkDownloading"
          @click="bulkDownload()"
          >Download</v-btn
        >
        <v-btn
          variant="tonal"
          size="small"
          color="red"
          :disabled="!selection.length"
          :loading="bulkDeleting"
          @click="bulkDelete()"
          >{{ confirmBulk ? `Delete ${selection.length}?` : 'Delete' }}</v-btn
        >
      </template>
      <template v-else>
        <span v-if="!store.fetchGraphLoad" class="legend">
          <template v-if="monthCount">
            <span class="dot inline"></span>{{ monthCount }} graph{{
              monthCount === 1 ? '' : 's'
            }}
            this month
          </template>
          <template v-else>No graphs this month</template>
        </span>
      </template>
    </div>
  </div>
</template>

<script>
import { mergeProps } from 'vue'
import GraphRowActions from './GraphRowActions.vue'
import {
  graphTime,
  groupByDay,
  isTimestampGraph,
  monthOf,
} from '@/utils/graphNames'

export default {
  props: {
    store: { type: Object, required: true },
    // browse: load/download/delete graphs, pick: emit 'pick' for compare selection
    mode: { type: String, default: 'browse' },
    // graphs to outline: the compare picks, or the graph currently open in browse mode
    picked: { type: Array, default: () => [] },
  },
  emits: ['pick'],
  components: {
    GraphRowActions,
  },
  data() {
    return {
      weekdays: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
      openDay: null,
      selecting: false,
      selection: [],
      pickerOpen: false,
      pickerYear: new Date().getFullYear(),
      confirmBulk: false,
      bulkDeleting: false,
      bulkDownloading: false,
    }
  },
  computed: {
    currentMonth() {
      return monthOf()
    },
    today() {
      const now = new Date()
      return `${monthOf(now)}-${String(now.getDate()).padStart(2, '0')}`
    },
    month() {
      return this.store.calendarMonth || this.currentMonth
    },
    allDays() {
      return groupByDay(this.store.graphList)
    },
    days() {
      const prefix = `${this.month}-`
      return Object.fromEntries(
        Object.entries(this.allDays).filter(([date]) =>
          date.startsWith(prefix),
        ),
      )
    },
    // graphs not named by capture time (e.g. base.ttl) have no day to sit on
    otherGraphs() {
      return this.store.graphList.filter(name => !isTimestampGraph(name))
    },
    monthCount() {
      return Object.values(this.days).reduce(
        (n, graphs) => n + graphs.length,
        0,
      )
    },
    currentYear() {
      return new Date().getFullYear()
    },
    graphMonths() {
      return this.store.graphMonths
    },
    minPickerYear() {
      const earliest = this.graphMonths[0]
      return earliest
        ? Math.min(Number(earliest.slice(0, 4)), this.currentYear)
        : this.currentYear - 5
    },
    pickerMonths() {
      const withGraphs = new Set(this.graphMonths)
      return Array.from({ length: 12 }, (_, i) => {
        const value = `${this.pickerYear}-${String(i + 1).padStart(2, '0')}`
        return {
          value,
          label: new Date(this.pickerYear, i, 1).toLocaleDateString(undefined, {
            month: 'short',
          }),
          hasGraphs: withGraphs.has(value),
        }
      })
    },
    monthLabel() {
      const [year, month] = this.month.split('-').map(Number)
      return new Date(year, month - 1, 1).toLocaleDateString(undefined, {
        month: 'long',
        year: 'numeric',
      })
    },
    cells() {
      const [year, month] = this.month.split('-').map(Number)
      const first = new Date(year, month - 1, 1)
      const daysInMonth = new Date(year, month, 0).getDate()
      const cells = []
      for (let i = 0; i < first.getDay(); i++) {
        cells.push({ date: `pad-${i}`, inMonth: false })
      }
      for (let day = 1; day <= daysInMonth; day++) {
        const date = `${this.month}-${String(day).padStart(2, '0')}`
        cells.push({
          date,
          day,
          inMonth: true,
          graphs: this.days[date] || [],
        })
      }
      return cells
    },
  },
  watch: {
    pickerOpen(open) {
      if (!open) return
      this.pickerYear = Number(this.month.slice(0, 4))
    },
  },
  mounted() {
    this.store.ensureCalendar()
  },
  methods: {
    mergeProps,
    graphTime,
    dayLabel(date) {
      const [year, month, day] = date.split('-').map(Number)
      return new Date(year, month - 1, day).toLocaleDateString(undefined, {
        weekday: 'long',
        month: 'long',
        day: 'numeric',
      })
    },
    setMonth(month) {
      this.store.setCalendarMonth(month)
    },
    pickMonth(month) {
      this.pickerOpen = false
      this.setMonth(month)
    },
    shiftMonth(delta) {
      const [year, month] = this.month.split('-').map(Number)
      this.setMonth(monthOf(new Date(year, month - 1 + delta, 1)))
    },
    pick(graph) {
      this.$emit('pick', graph.ttl_name)
    },
    onDeleted(name) {
      this.selection = this.selection.filter(n => n !== name)
    },
    toggleSelecting() {
      this.selecting = !this.selecting
      this.selection = []
      this.confirmBulk = false
      this.openDay = null
    },
    toggleNames(names) {
      const allSelected = names.every(name => this.selection.includes(name))
      this.selection = allSelected
        ? this.selection.filter(name => !names.includes(name))
        : [...new Set([...this.selection, ...names])]
      this.confirmBulk = false
    },
    toggleDay(cell) {
      this.toggleNames(cell.graphs.map(g => g.ttl_name))
    },
    async bulkDownload() {
      this.bulkDownloading = true
      this.confirmBulk = false
      try {
        await this.store.downloadGraphs(this.selection)
      } finally {
        this.bulkDownloading = false
      }
    },
    async bulkDelete() {
      if (!this.confirmBulk) {
        this.confirmBulk = true
        return
      }
      this.bulkDeleting = true
      try {
        const result = await this.store.deleteGraphs(false, this.selection)
        this.selection = this.selection.filter(
          name => !result.deleted.includes(name),
        )
        if (!this.selection.length) this.selecting = false
      } finally {
        this.bulkDeleting = false
        this.confirmBulk = false
      }
    },
  },
}
</script>

<style lang="scss" scoped>
.graph-calendar {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.calendar-header {
  display: flex;
  align-items: center;
  gap: 4px;
}
.month-label {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
  min-width: 140px;
  padding: 2px 6px;
  border-radius: 6px;
  color: #e0e0e0;
  font: inherit;
  font-weight: 500;
  cursor: pointer;
}
.month-label:hover:not(:disabled) {
  background-color: #2a2a2a;
}
.month-label-icon {
  color: #8a8a8a;
}
.month-picker {
  background-color: #262626;
  border-radius: 12px;
  padding: 10px 12px 12px;
  box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.5);
  width: 260px;
}
.picker-year {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #e0e0e0;
  font-weight: 500;
  margin-bottom: 8px;
}
.picker-months {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 4px;
}
.picker-month {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  padding: 6px 0 5px;
  border-radius: 8px;
  border: 1px solid transparent;
  background: none;
  color: #8a8a8a;
  font: inherit;
  font-size: 0.8rem;
  cursor: pointer;
}
.picker-month:hover:not(:disabled) {
  background-color: #2f2f2f;
}
.picker-month:disabled {
  opacity: 0.35;
  cursor: default;
}
.picker-month.has-graphs {
  color: #e0e0e0;
}
.picker-month.selected {
  border-color: #c1d200;
  color: #c1d200;
}
.picker-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background-color: transparent;
}
.picker-month.has-graphs .picker-dot,
.picker-dot.inline {
  background-color: #94d8ff;
}
.picker-dot.inline {
  display: inline-block;
  margin-right: 4px;
  vertical-align: middle;
}
.picker-hint {
  margin-top: 8px;
  font-size: 0.7rem;
  color: #6f6f6f;
}
.month-arrow {
  width: 24px;
  min-width: 24px;
}
.header-spinner {
  margin-left: 6px;
  color: #8a8a8a;
}
.header-actions {
  margin-left: auto;
  display: flex;
  gap: 4px;
}
.weekdays,
.grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 4px;
}
.weekdays span {
  text-align: center;
  font-size: 0.7rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #6f6f6f;
}
.grid.disabled {
  opacity: 0.4;
  pointer-events: none;
}
.cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-between;
  gap: 4px;
  height: 52px;
  padding: 6px 2px;
  border-radius: 8px;
  background-color: #222;
  border: 1px solid transparent;
  color: #cdcdcd;
  font: inherit;
  cursor: pointer;
  transition:
    background-color 0.15s,
    border-color 0.15s;
}
.cell:hover:not(:disabled) {
  background-color: #2c2c2c;
}
.cell.outside {
  background: none;
  cursor: default;
}
.cell.empty {
  cursor: default;
  color: #6f6f6f;
}
.cell.future {
  opacity: 0.4;
}
.cell.today .day-number {
  color: #c1d200;
  font-weight: 600;
}
.cell.picked {
  border-color: #94d8ff;
}
.cell.selected {
  border-color: #94d8ff;
  background-color: rgba(148, 216, 255, 0.12);
}
.day-number {
  font-size: 0.8rem;
}
.dots {
  display: flex;
  align-items: center;
  gap: 3px;
  min-height: 8px;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #94d8ff;
  flex-shrink: 0;
}
.dot.inline {
  display: inline-block;
  margin-right: 4px;
}
.more {
  font-size: 0.65rem;
  color: #8a8a8a;
}
.tooltip {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 0.8rem;
}
.calendar-footer {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 14px;
  min-height: 32px;
  font-size: 0.75rem;
  color: #8a8a8a;
}
.selection-count {
  margin-right: auto;
  color: #cdcdcd;
  font-size: 0.85rem;
}
.hint {
  color: #6f6f6f;
}
.legend {
  display: inline-flex;
  align-items: center;
}
.day-popover {
  background-color: #262626;
  border-radius: 12px;
  padding: 12px;
  box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 360px;
}
.popover-title {
  color: #8a8a8a;
  font-size: 0.75rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  margin-bottom: 4px;
}
.graph-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 8px;
}
.graph-row:hover,
.graph-row.picked {
  background-color: #2f2f2f;
}
.other-graphs {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-top: 4px;
}
.other-title {
  color: #8a8a8a;
  font-size: 0.75rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  margin-bottom: 2px;
}
.other-graphs .graph-row {
  min-height: 40px;
}
.other-graphs .graph-row:hover,
.other-graphs .graph-row.picked {
  background-color: #222;
}
.graph-row.selectable {
  cursor: pointer;
}
.graph-row.selected {
  background-color: rgba(148, 216, 255, 0.12);
}
.other-icon {
  color: #8a8a8a;
}
.graph-info {
  flex: 1;
  min-width: 0;
}
.graph-time {
  color: #e0e0e0;
  font-size: 0.9rem;
}
.graph-detail {
  color: #8a8a8a;
  font-size: 0.75rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
