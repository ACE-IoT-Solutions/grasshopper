<template>
  <div class="note-card">
    <div class="card-close">
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
    <p style="font-size: 14px; font-weight: 900; margin: 10px; width: 300px">
      {{ store.selectedNode }}
    </p>
    <v-textarea label="Add a Note" variant="solo-filled"></v-textarea>
    <div class="card-buttons">
      <v-btn @click="closeCard()" variant="plain" size="x-small">
        cancel
      </v-btn>
      <v-btn
        @click="addNote()"
        variant="tonal"
        color="#c1d200"
        append-icon="mdi-plus"
        size="x-small"
      >
        Add Note
      </v-btn>
    </div>
  </div>
</template>

<script>
import { gsap } from 'gsap'
import { Draggable } from 'gsap/Draggable'

export default {
  props: ['store'],
  mounted() {
    gsap.registerPlugin(Draggable);

    gsap.from('.note-card', {
      duration: 0.25,
      opacity: 0,
      y: 50,
      // x: 50,
      ease: 'power2.out',
    })
    Draggable.create('.note-card', {
      type: 'x,y',
      edgeResistance: 0.5,
      bounds: 'body',
    })
  },
  methods: {
    closeCard() {
        this.store.setShowNoteCard(false);
    },
    addNote() {
      console.log('test note');
    }
  },
}
</script>

<style lang="scss" scoped>
.note-card {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  padding: 10px;
  max-width: 500px;
  height: min-content;
  //   max-height: 200px;
  background-color: #212121;
  color: white;
  border-radius: 8px;
  z-index: 999;
  box-shadow: 1px 0px 16px -5px rgba(0,0,0,0.75);
  text-align: left;
}
.card-close {
  display: flex;
  justify-content: flex-end;
}
.card-buttons {
  display: flex;
  justify-content: space-between;
}
</style>
