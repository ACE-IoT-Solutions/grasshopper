<template>
    <div class="loader">
        <div class="close">
            <h5 class="title">Compare Generating</h5>
            <v-btn
                variant="plain"
                :ripple="false"
                icon=""
                id="no-background-hover"
                size="small"
                @click="store.setCompareLoad(false)"
                >
                <v-icon>mdi-close</v-icon>
            </v-btn>
        </div>
        <hr class="line" />
        <div class="container">
            <p class="alert-text">{{ store.currentTask.ttl_1.replace(".ttl", "") + "_vs_" + store.currentTask.ttl_2 }}</p>
            <v-progress-circular color="#94D8FF" indeterminate :size="25"></v-progress-circular>
        </div>
        <div
            style="margin-top: 10px;"
            v-if="store.compareQueue.length > 0"
            >
            <h5 class="title">In Queue</h5>
            <hr class="line" />
            <div v-for="item in store.compareQueue" :key="item">
                <div class="container">
                    <p class="alert-text">{{ item.ttl_1.replace(".ttl", "") }}_vs_{{ item.ttl_2 }}</p>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import { gsap } from "gsap";
export default {
    props: ["store"],
    data() {
        return {
            currentTask: null,
        };
    },
    mounted() {
        gsap.from(".loader", {
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
.loader {
    position: absolute;
    top: 5%;
    right: 2%;
    background-color: #212121;
    border-radius: 15px;
    overflow: hidden;
    z-index: 10001;
    box-shadow: -5px 10px 15px rgba(18, 18, 18, 0.5);
}
.container {
    padding: 10px;
    display: flex;
    justify-content: space-between;
    gap: 50px;
} 
.alert-text {
    color: #87850B;
}
.subtext {
    font-size: 12px;
    color: #CDCDCD;
}
.close {
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.title {
    color: #CDCDCD;
    margin-left: 10px;
}
.line {
    width: 100%;
    color: #CDCDCD;
    opacity: 10%;
    margin: 10px;
}
</style>