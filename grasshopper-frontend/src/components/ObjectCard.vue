<template>
  <div class="object-card">
    <div class="card-header">
      <div class="card-title">
        <v-icon size="small" class="title-icon">mdi-information-outline</v-icon>
        <span>Object Details</span>
      </div>
      <v-btn
        @click="closeCard()"
        variant="plain"
        :ripple="false"
        icon=""
        id="no-background-hover"
        size="small"
        density="compact"
      >
        <v-icon>mdi-close</v-icon>
      </v-btn>
    </div>

    <div v-if="parsedData.length > 0" class="data-grid">
      <div v-for="item in parsedData" :key="item.key" class="data-item">
        <div class="data-label">{{ formatKey(item.key) }}</div>
        <div class="data-value">{{ item.value }}</div>
      </div>
    </div>

    <div v-else class="no-data">
      <v-icon size="large" class="no-data-icon"
        >mdi-information-off-outline</v-icon
      >
      <p>No object data available</p>
    </div>
  </div>
</template>

<script>
import { gsap } from 'gsap'
export default {
  props: ['store'],
  mounted() {
    gsap.fromTo(
      '.object-card',
      { opacity: 0, y: 20, ease: 'power2.out' },
      { opacity: 1, y: 0, duration: 0.3, ease: 'power2.out' },
    )
  },
  computed: {
    parsedData() {
      if (
        !this.store.objectCardData ||
        typeof this.store.objectCardData !== 'string'
      ) {
        return []
      }

      try {
        // Clean the string and convert single quotes to double quotes for JSON parsing
        const cleanedData = this.store.objectCardData.replace(/'/g, '"').trim()

        const dataObject = JSON.parse(cleanedData)

        // Convert to array of key-value pairs for easier rendering
        return Object.entries(dataObject).map(([key, value]) => ({
          key,
          value,
        }))
      } catch (error) {
        console.error('Error parsing object card data:', error)
        return []
      }
    },
  },
  methods: {
    closeCard() {
      gsap.to('.object-card', {
        duration: 0.25,
        opacity: 0,
        y: 50,
        ease: 'power2.in',
        onComplete: () => {
          this.store.setObjectCard(false)
        },
      })
    },
    formatKey(key) {
      return key
        .replace(/-count$/, '')
        .replace(/-/g, ' ')
        .replace(/\b\w/g, l => l.toUpperCase())
    },
  },
}
</script>

<style lang="scss" scoped>
.object-card {
  position: absolute;
  bottom: 100%;
  left: 0;
  margin-bottom: 8px;
  background-color: #212121;
  color: white;
  border-radius: 8px;
  padding: 10px;
  max-width: 400px;
  max-height: 50vh;
  overflow: hidden;
  z-index: 998;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 14px;
  color: #c1d200;

  .title-icon {
    opacity: 0.8;
  }
}

.data-grid {
  padding: 5px 5px 0 5px;
  max-height: calc(50vh - 80px);
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(193, 210, 0, 0.3) transparent;
}

.data-grid::-webkit-scrollbar {
  width: 6px;
}

.data-grid::-webkit-scrollbar-track {
  background: transparent;
}

.data-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  transition: all 0.2s ease;

  &:last-child {
    border-bottom: none;
  }
}

.data-label {
  font-size: 13px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.9);
  text-transform: capitalize;
  flex-shrink: 0;
}

.data-value {
  font-size: 13px;
  font-weight: 600;
  color: #c1d200;
  text-align: right;
  padding: 4px 12px;
  border-radius: 12px;
  min-width: 40px;
}

.no-data {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;

  .no-data-icon {
    opacity: 0.4;
    margin-bottom: 12px;
    color: rgba(255, 255, 255, 0.5);
  }

  p {
    margin: 0;
    font-size: 13px;
    color: rgba(255, 255, 255, 0.6);
    font-style: italic;
  }
}
</style>
