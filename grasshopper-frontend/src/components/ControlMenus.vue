<template>
    <div :class="(store.menuType === 'compare' || store.menuType === 'ip') ? 'alt-menu' : 'menu'" style="z-index: 1000;">
        <div class="header" :style="(store.menuType === 'compare' || store.menuType === 'ip') ? 'height: 10%;' : 'height: 20%;'">
            <v-btn variant="plain" :ripple="false" icon="" id="no-background-hover" size="small" @click="store.setControlMenu(null, null)"><v-icon>mdi-close</v-icon></v-btn>
        </div>
        <div class="menu-title">
            <p class="text">{{ store.menuTitle }}</p>
        </div>
        <div v-if="store.menuType == 'compare'" class="alt-container">
            <v-select label="Select a Graph" variant="solo-filled" density="compact"></v-select>
            <v-select label="Select a Graph" variant="solo-filled" density="compact"></v-select>
            <div style="display: flex; align-items: center; justify-content: center;">
                <v-btn variant="tonal" size="small" append-icon="mdi-compare-horizontal" color="#5FFFFF">Compare</v-btn>
            </div>
            <hr class="line" />
            <!-- <div style="display: grid; align-items: center; justify-content: center; width: 100%;">
                <p class="text">Load</p>
            </div> -->
            <div style="display: flex; align-items: center; justify-content: center; gap: 20px">
                <v-select label="Past Comparisons" variant="solo-filled" density="compact" hide-details="auto"></v-select>
                <v-btn variant="tonal" size="small" append-icon="mdi-arrow-right" color="#c1d200">Load</v-btn>
            </div>
        </div>
        <div v-if="store.menuType == 'regen'" class="container">
            <v-select label="Select a Graph" variant="solo-filled" density="compact"></v-select>
            <div style="display: flex; align-items: center; justify-content: center;">
                <v-btn variant="tonal" size="small" append-icon="mdi-autorenew" color="#5FFFFF">Regenerate</v-btn>
            </div>
        </div>
        <div v-if="store.menuType == 'delete'" class="container">
            <v-select label="Select a Graph" variant="solo-filled" density="compact"></v-select>
            <div style="display: flex; align-items: center; justify-content: center;">
                <v-btn variant="tonal" size="small" color="red">Delete</v-btn>
            </div>
        </div>
        <div v-if="store.menuType == 'ip'" class="alt-container">
            <div style="display: flex; align-items: center; justify-content: center; gap: 20px">
                <v-select label="Select an IP" variant="solo-filled" density="compact" hide-details="auto"></v-select>
                <v-btn variant="tonal" size="small" append-icon="mdi-arrow-right" color="#c1d200">Go To</v-btn>
            </div>
            <hr class="line" />
            <div style="display: flex; align-items: center; justify-content: center; gap: 20px">
                <v-text-field label="Add an IP" density="compact" hide-details="auto" variant="solo-filled"></v-text-field>
                <v-btn variant="tonal" size="small" append-icon="mdi-plus" color="#5FFFFF">Add</v-btn>
            </div>
            <hr class="line" />
            <!-- <div style="display: grid; align-items: center; justify-content: center; width: 100%;">
                <p class="text">Delete an IP</p>
            </div> -->
            <div style="display: flex; align-items: center; justify-content: center; gap: 20px">
                <v-select label="Select an IP" variant="solo-filled" density="compact" hide-details="auto"></v-select>
                <v-btn variant="tonal" size="small" color="red">Delete</v-btn>
            </div>
        </div>
        <div v-if="store.menuType == 'setup'" class="container" style="align-content: space-evenly;">
            <div style="display: flex; align-items: center; justify-content: center; gap: 20px">
                <v-select label="Select a Graph" variant="solo-filled" density="compact" hide-details="auto"></v-select>
                <v-btn variant="tonal" size="small" append-icon="mdi-arrow-right" color="#c1d200">Go To</v-btn>
            </div>
            <hr class="line" />
            <v-file-input clearable label="Upload Graph" variant="solo-filled" density="compact"></v-file-input>
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
.menu {
    height: 25vh;
    width: 30vw;
    background-color: #212121;
    border-radius: 15px;
    position: absolute;
    top: 25%;
    left: 35%;
    box-shadow: 0px 4px 1px rgba(0, 0, 0, 0.5);
}
.alt-menu {
    height: 50vh;
    width: 30vw;
    background-color: #212121;
    border-radius: 15px;
    position: absolute;
    top: 25%;
    left: 35%;
    box-shadow: 0px 4px 1px rgba(0, 0, 0, 0.5);
}
.container {
    margin: 0 20px;
    height: 85%;
    display: grid;
    align-items: center;
    align-content: center;
}
.alt-container {
    margin: 0 20px;
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
.menu-title {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 5%;
}
.text {
    color: #CDCDCD;
    font-weight: 500;
}
.line {
    width: 100%;
    color: #CDCDCD;
    opacity: 30%;
}
</style>