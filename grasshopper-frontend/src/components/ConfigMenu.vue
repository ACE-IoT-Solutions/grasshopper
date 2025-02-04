<template>
    <div v-show="showConfig" class="config">
        <div class="config-close">
            <v-btn
                variant="plain"
                :ripple="false"
                icon=""
                id="no-background-hover"
                size="small"
                @click="close()"
                >
                    <v-icon>mdi-close</v-icon>
            </v-btn>
        </div>
        <hr class="line" />
        <h4 class="title">File: {{ store.fileName }}</h4>
        <hr class="line" />
        <div class="config-row">
            <h4 class="title">Config: {{ store.currentConfig }}</h4>
            <v-menu open-on-hover>
                <template v-slot:activator="{ props }">
                    <v-btn
                        v-if="store.fileName"
                        v-bind="props"
                        variant="plain"
                        :ripple="false"
                        id="no-background-hover"
                        size="small"
                        density="compact"
                        color="#FFFD94"
                        append-icon="mdi-cog"
                    >
                        Options
                    </v-btn>
                </template>

                <v-list>
                    <v-list-item
                    v-for="(item, index) in saveOptions"
                    :key="index"
                    @click="item.action"
                    >
                    <v-list-item-title>{{ item.title }}</v-list-item-title>
                    </v-list-item>
                </v-list>
             </v-menu>
        </div>
        <hr class="line" />
        <div ref="config"></div>
    </div>
</template>

<script>
import { gsap } from "gsap";
export default {
    props: ["store", "showConfig"],
    watch: {
        showConfig(newVal) {
            if (newVal) {
                gsap.from(".config", {
                    duration: 0.25,
                    opacity: 0,
                    y: 50,
                    x: -50,
                    ease: "power2.out",
                });
            }
        }
    },
    data() {
        return {
            saveOptions: [
                { title: "Save", action: () => this.storeConfig() } ,
                { title: "Load", action: () => this.loadConfig() },
                { title: "Reset to Last Save", action: () => this.resetConfig() },
                { title: "Reload with Default", action: () => this.defaultConfig() },
                { title: "Delete a Config", action: () => this.deleteConfig() },
            ],
        };
    },
    methods: {
        close() {
            this.$emit("close");
        },
        storeConfig() {
            this.$emit("storeConfig");
        },
        resetConfig() {
            this.store.setReload();
        },
        deleteConfig() {
            this.store.setControlMenu('delete', 'Delete')
        },
        loadConfig() {
            this.store.setControlMenu('config', 'Load Config')
        },
        defaultConfig() {
            this.store.setPhysicsConfig(this.store.defaultConfig);
            this.store.setCurrentConfig('Default');
            this.store.setReload();
        },
    },
    mounted() {
        gsap.from(".config", {
            duration: 0.25,
            opacity: 0,
            y: -50,
            x: 50,
            ease: "power2.out",
        });
    },
}
</script>

<style lang="scss" scoped>
    .config {
        position: absolute;
        background-color: #212121;
        opacity: 100%;
        z-index: 998;
        height: 95%;
        overflow: scroll;
        padding: 10px;
        border-radius: 15px;
        left: 1%;
        top: 2.5%;
    }
    .config-close {
        display: flex;
        justify-content: flex-end;
    }
    .line {
        width: 100%;
        color: #CDCDCD;
        opacity: 30%;
        margin: 8px 0px;
    }
    .title {
        color: #FFFD94;
    }
    .config-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
</style>