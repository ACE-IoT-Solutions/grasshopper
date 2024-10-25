<template>
    <div class="network-header">
        <!-- <v-select
            label="Select a Graph"
            variant="solo-filled"
            density="compact"
            class="main-select"
            hide-details="auto"
        ></v-select> -->
        <div class="buttons" style="margin-left: 1.5vw; gap: 20px; align-items: center;">
            <v-btn variant="outlined" size="small" @click="store.setControlMenu('setup', 'Setup')" color="#CDCDCD">Graph Setup</v-btn>
            <v-btn
                variant="plain"
                :ripple="false"
                icon=""
                id="no-background-hover"
                size="small"
                density="compact"
                color="#c1d200"
            >
                <v-icon>mdi-download</v-icon>
            </v-btn>
        </div>
        <div class="buttons" style="margin-right: 1.5vw;">
            <!-- <v-btn variant="tonal" size="small">Go to HTML Graph</v-btn>
            <v-btn variant="tonal" size="small">Go to TTL Graph</v-btn>
            <v-btn variant="tonal" size="small">Enable/Disable Physics Menu</v-btn> -->
            <v-btn variant="plain" size="small" @click="store.setControlMenu('compare', 'Compare Graphs')">Compare Graphs</v-btn>
            <v-btn variant="plain" size="small" @click="store.setControlMenu('regen', 'Regenerate Graph')">Regenerate Graph</v-btn>
            <v-btn variant="plain" size="small" @click="store.setControlMenu('delete', 'Delete Graph')">Delete Graph</v-btn>
            <v-btn variant="plain" size="small" @click="store.setControlMenu('ip', 'IP Menu')">IP Menu</v-btn>
        </div>
    </div>
</template>

<script>
export default {
    props: ["store"],
    setup () {
        return {}
    }
}
</script>

<style lang="scss" scoped>
.network-header {
    display: flex;
    justify-content: space-between;
    gap: 10px;
    margin: 0 20px;
    height: 50px;
    align-items: center;
}
.controls {
    display: flex;
    justify-content: space-evenly;
    width: 80%;
}
.buttons {
    display: flex;
    gap: 10px;
    // margin-right: 1.5vw;
}
.main-select {
    width: 175px;
    max-width: 200px;
    height: 28px;
    margin: 0 1.5vw;
}
</style>