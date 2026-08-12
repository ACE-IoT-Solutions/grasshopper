<template>
  <div class="loader">
    <div class="close">
      <h5 class="title">Compare Queue</h5>
      <v-btn
        variant="plain"
        :ripple="false"
        icon=""
        id="no-background-hover"
        size="small"
        @click="closeMenu()"
      >
        <v-icon>mdi-close</v-icon>
      </v-btn>
    </div>
    <hr class="line" />
    <div class="queue-box">
      <h5 class="title">Processing</h5>
      <div v-if="store.processingQueue != null">
        <div class="container">
          <p class="alert-text">{{ store.processingQueue.file_name }}</p>
          <v-progress-circular
            indeterminate
            size="20"
            color="#94D8FF"
          ></v-progress-circular>
        </div>
      </div>
      <div v-else class="container">
        <h5 class="alert-text">No Items</h5>
      </div>
    </div>
    <hr class="line" />
    <div class="queue-box">
      <h5 class="title">In Queue</h5>
      <div v-if="store.inQueue.length > 0">
        <div v-for="item in store.inQueue" :key="item">
          <div class="container">
            <p class="alert-text">{{ item.file_name }}</p>
          </div>
        </div>
      </div>
      <div v-else class="container">
        <h5 class="alert-text">No Items</h5>
      </div>
    </div>
    <hr class="line" />
    <div class="queue-box">
      <h5 class="title">Finished</h5>
      <div v-if="store.finishedQueue.length > 0" class="finished-container">
        <div v-for="item in store.compareList" :key="item">
          <div class="container">
            <p class="alert-text">{{ item }}</p>
            <v-btn
              @click="store.goToGraph(true, item)"
              variant="plain"
              color="#cdcdcd"
              density="compact"
              :ripple="false"
              icon=""
              id="no-background-hover"
              size="small"
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
      <div v-else class="container">
        <h5 class="alert-text">No Items</h5>
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
      currentTask: null,
    }
  },
  mounted() {
    gsap.from('.loader', {
      duration: 0.25,
      opacity: 0,
      y: -50,
      x: 50,
      ease: 'power2.out',
    })
    this.store.fetchQueue()
  },
  methods: {
    async removeFromQueue(item) {
      console.log(item)
    },
    closeMenu() {
      gsap.to('.loader', {
        duration: 0.25,
        opacity: 0,
        y: -50,
        x: 50,
        ease: 'power2.in',
        onComplete: () => {
          this.store.setCompareLoad(false)
        },
      })
    },
  },
}
</script>

<style lang="scss" scoped>
.loader {
  position: absolute;
  top: 5%;
  right: 2%;
  background-color: #212121;
  border-radius: 15px;
  // overflow: hidden;
  z-index: 10001;
  box-shadow: -5px 10px 15px rgba(18, 18, 18, 0.5);
  max-height: 60vh;
  overflow: scroll;
}
.container {
  padding: 8px 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
}
.alert-text {
  color: #87850b;
}
.subtext {
  font-size: 12px;
  color: #cdcdcd;
}
.close {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.title {
  color: #cdcdcd;
  margin-left: 10px;
}
.none-title {
  color: #cdcdcd;
  margin: 10px;
}
.line {
  // width: 100%;
  color: #cdcdcd;
  opacity: 10%;
  margin: 10px;
}
.queue-box {
  margin-top: 10px;
}
.no-items {
  margin: 0 10px;
}
.finished-container {
  max-height: 300px;
  overflow: scroll;
}
</style>
