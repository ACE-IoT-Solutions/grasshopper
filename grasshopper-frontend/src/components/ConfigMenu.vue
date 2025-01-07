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
        <h4 class="title">{{ store.fileName }}</h4>
        <hr class="line" />
        <div ref="config"></div>
        <div class="config-close">
            <v-btn
                variant="plain"
                color="#FFFD94"
                @click="storeConfig()"
                >Save Config
            </v-btn>
        </div>
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
    methods: {
        close() {
            this.$emit("close");
        },
        storeConfig() {
            this.$emit("storeConfig");
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
</style>