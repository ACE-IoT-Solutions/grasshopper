<template>
    <div :class="(store.menuType === 'compare' || store.menuType === 'subnet' || store.menuType === 'bbmd') ? 'alt-menu' : 'menu'" style="z-index: 1000;">
        <div class="header" :style="(store.menuType === 'compare' || store.menuType === 'subnet' || store.menuType === 'bbmd') ? 'height: 10%;' : 'height: 20%;'">
            <v-btn variant="plain" :ripple="false" icon="" id="no-background-hover" size="small" @click="store.setControlMenu(null, null)"><v-icon>mdi-close</v-icon></v-btn>
        </div>
        <div class="menu-title">
            <p class="text">{{ store.menuTitle }}</p>
        </div>
        <div v-if="store.menuType == 'compare'" class="alt-container">
            <v-select v-model="compareGraph1" label="Select a Graph" variant="solo-filled" density="compact" :items="store.setupGraphs"></v-select>
            <v-select v-model="compareGraph2" label="Select a Graph" variant="solo-filled" density="compact" :items="store.setupGraphs"></v-select>
            <div style="display: flex; align-items: center; justify-content: center;">
                <v-btn @click="createCompare()" :loading="createCompareLoad" variant="tonal" size="small" append-icon="mdi-compare-horizontal" color="#94D8FF">Compare</v-btn>
            </div>
            <hr class="line" />
            <div style="display: flex; align-items: center; justify-content: center; gap: 20px">
                <v-select v-model="compareGraph" :items="store.compareList" label="Past Comparisons" variant="solo-filled" density="compact" hide-details="auto"></v-select>
                <v-btn @click="loadCompare()" :loading="compareLoad" variant="tonal" size="small" append-icon="mdi-arrow-right" color="#c1d200">Load</v-btn>
            </div>
        </div>
        <div v-if="store.menuType == 'delete'" class="container">
            <div style="display: flex; align-items: center; justify-content: center; gap: 20px">
                <v-select v-model="deletedGraph" :items="store.deleteList" label="Select a Graph" variant="solo-filled" density="compact" hide-details="auto"></v-select>
                <v-btn @click="deleteGraph()" :loading="deleteLoad" variant="tonal" size="small" color="red">Delete</v-btn>
            </div>
            <hr class="line" style="margin: 15px 0px;" />
            <div style="display: flex; align-items: center; justify-content: center; gap: 20px">
                <v-select v-model="deletedCompareGraph" :items="store.deleteCompareList" label="Select a Compare Graph" variant="solo-filled" density="compact" hide-details="auto"></v-select>
                <v-btn @click="deleteCompareGraph()" :loading="deleteCompareLoad" variant="tonal" size="small" color="red">Delete</v-btn>
            </div>
            <v-alert
                v-if="deleteSuccess"
                type="success"
                class="success"
                closable
                @click:close="deleteSuccess = false"
                >
                <strong>{{ fileDeleted }}</strong> successfully deleted.
            </v-alert>
        </div>
        <div v-if="store.menuType == 'subnet'" class="alt-container">
            <div>
                <ul class="search-results">
                    <h4 style="margin: 10px 10px 0px 10px;">Subnets</h4>
                    <hr class="line" style="margin: 8px 8px" />
                    <li v-for="result in store.ipList" :key="result" style="margin-left: 10px;">
                        {{ result }}
                    </li>
                </ul>
            </div>
            <hr class="line" />
            <div style="display: flex; align-items: center; justify-content: center; gap: 20px">
                <v-text-field v-model="newSubnet"label="Add a Subnet" density="compact" hide-details="auto" variant="solo-filled" :rules="ipRules"></v-text-field>
                <v-btn @click="addSubnet()" variant="tonal" size="small" append-icon="mdi-plus" color="#94D8FF" :loading="addSubnetLoad">Add</v-btn>
            </div>
            <hr class="line" />
            <div style="display: flex; align-items: center; justify-content: center; gap: 20px">
                <v-select v-model="subnetToDelete" :items="store.ipList" label="Select a Subnet" variant="solo-filled" density="compact" hide-details="auto"></v-select>
                <v-btn @click="deleteSubnet()" variant="tonal" size="small" color="red" :loading="deleteSubnetLoad">Delete</v-btn>
            </div>
            <v-alert
                v-if="subnetAdded"
                type="success"
                class="alt-success"
                style="translate: 1% 50%;"
                closable
                @click:close="subnetAdded = false"
                >
                Subnet added.
            </v-alert>
            <v-alert
                v-if="subnetDeleted"
                type="success"
                class="alt-success"
                style="translate: 1% 225%;"
                closable
                @click:close="subnetDeleted = false"
                >
                Subnet deleted.
            </v-alert>
        </div>
        <div v-if="store.menuType == 'bbmd'" class="alt-container">
            <div>
                <ul class="search-results">
                    <h4 style="margin: 10px 10px 0px 10px;">BBMDs</h4>
                    <hr class="line" style="margin: 8px 8px" />
                    <li v-for="result in store.bbmdList" :key="result" style="margin-left: 10px;">
                        {{ result }}
                    </li>
                </ul>
            </div>
            <hr class="line" />
            <div style="display: flex; align-items: center; justify-content: center; gap: 20px">
                <v-text-field v-model="newBbmd"label="Add a BBMD" density="compact" hide-details="auto" variant="solo-filled" :rules="bbmdRules"></v-text-field>
                <v-btn @click="addBbmd()" variant="tonal" size="small" append-icon="mdi-plus" color="#94D8FF" :loading="addBbmdLoad">Add</v-btn>
            </div>
            <hr class="line" />
            <div style="display: flex; align-items: center; justify-content: center; gap: 20px">
                <v-select v-model="bbmdToDelete" :items="store.bbmdList" label="Select a BBMD" variant="solo-filled" density="compact" hide-details="auto"></v-select>
                <v-btn @click="deleteBbmd()" variant="tonal" size="small" color="red" :loading="deleteBbmdLoad">Delete</v-btn>
            </div>
            <v-alert
                v-if="bbmdAdded"
                type="success"
                class="alt-success"
                style="translate: 1% 50%;"
                closable
                @click:close="bbmdAdded = false"
                >
                BBMD added.
            </v-alert>
            <v-alert
                v-if="bbmdDeleted"
                type="success"
                class="alt-success"
                style="translate: 1% 225%;"
                closable
                @click:close="bbmdDeleted = false"
                >
                BBMD deleted.
            </v-alert>
        </div>
        <div v-if="store.menuType == 'setup'" class="container" style="align-content: space-evenly;">
            <div style="display: flex; align-items: center; justify-content: center; gap: 20px">
                <v-select v-model="setupGraph" label="Select a Graph" variant="solo-filled" density="compact" hide-details="auto" :items="store.setupGraphs"></v-select>
                <v-btn @click="goToGraph()" :loading="setupLoad" variant="tonal" size="small" append-icon="mdi-arrow-right" color="#c1d200">Go To</v-btn>
            </div>
            <hr class="line" />
            <div style="display: flex; align-items: center; justify-content: center; gap: 20px; margin-bottom: 20px;">
                <v-file-input v-model="fileUpload" clearable label="Upload Graph" variant="solo-filled" density="compact" accept=".ttl" hide-details="auto" @change="checkFileName()"></v-file-input>
                <v-btn @click="uploadGraph()" :loading="uploadLoad" variant="tonal" size="small" append-icon="mdi-upload" color="#94D8FF">Upload</v-btn>
            </div>
            <v-alert
                type="warning"
                color="#94D8FF"
                v-if="showWarning"
                class="warning"
                closable
                @click:close="showWarning = false"
                >
                The file <strong>base.ttl</strong> was uploaded. This will become the basis of all scans.
            </v-alert>
            <v-alert
                v-if="uploadSuccess"
                type="success"
                class="success"
                closable
                @click:close="uploadSuccess = false"
                >
                File uploaded succesfully.
            </v-alert>
        </div>
    </div>
</template>

<script>
import axios from "axios";
import { gsap } from "gsap";
export default {
    props: ["store"],
    data() {
        return {
            setupGraph: null,
            compareGraph: null,
            host: window.location.protocol + '//' + window.location.host,
            setupLoad: false,
            comparePayload: {},
            compareLoad: false, // get
            createCompareLoad: false, // post
            compareGraph1: null,
            compareGraph2: null,
            deletedGraph: null,
            deleteLoad: false,
            deletedCompareGraph: null,
            deleteCompareLoad: false,
            fileUpload: null,
            uploadLoad: false,
            newSubnet: null,
            subnetToDelete: null,
            addSubnetLoad: false,
            deleteSubnetLoad: false,
            ipRules: [(v) => /^((25[0-5]|2[0-4]\d|[01]?\d?\d)\.){3}(25[0-5]|2[0-4]\d|[01]?\d?\d)\/(0|[1-9]|1\d|2\d|3[0-2])$/.test(v) || "IP with CIDR must be valid"],
            bbmdRules: [(v) => /^(?:(25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.){3}(25[0-5]|(2[0-4]|1\d|[1-9]|)\d)$|^$/.test(v) || "IP must be valid"],
            newBbmd: null,
            bbmdToDelete: null,
            addBbmdLoad: false,
            deleteBbmdLoad: false,
            testList: ["test", "test", "test", "test", "test", "test"],
            showWarning: false,
            deleteSuccess: false,
            fileDeleted: null,
            uploadSuccess: false,
            subnetAdded: false,
            subnetDeleted: false,
            bbmdAdded: false,
            bbmdDeleted: false,
        };
    },
    mounted() {
        let animateClass = null;

        this.store.menuType === 'compare' || this.store.menuType === 'subnet' || this.store.menuType === 'bbmd' ? animateClass = '.alt-menu' : animateClass = '.menu';

        gsap.from(animateClass, {
            duration: 0.25,
            opacity: 0,
            y: -50,
            ease: "power2.out",
        });
    },
    methods: {
        checkFileName() {
            if (this.fileUpload && this.fileUpload.name === 'base.ttl') {
                this.showWarning = true;
            } else {
                this.showWarning = false;
            }
        },
        async goToGraph() {
            this.setupLoad = true;

            await axios
                .get(
                    `${this.host}/api/operations/ttl_network/${this.setupGraph}`,
                    {
                        responseType: "json"
                    }
                )
                .then((response) => {
                    this.store.setCompareMode(false);
                    this.store.setCurrentGraph(response.data, this.setupGraph);
                    this.store.setControlMenu(null, null);
                    this.setupLoad = false;
                })
                .catch((error) => {
                    console.log(error);
                    this.setupLoad = false;
                });
        },
        async createCompare() {

            const payload = {
                "ttl_1": this.compareGraph1,
                "ttl_2": this.compareGraph2
            };

            const fileName = this.compareGraph1.replace('.ttl', '') + '_vs_' + this.compareGraph2;

            await axios
                .post(
                    `${this.host}/api/operations/ttl_compare_queue`,
                    payload,
                )
                .then((response) => {
                    this.store.setControlMenu(null, null);
                    this.compareGraph1 = null;
                    this.compareGraph2 = null;
                    this.store.triggerReload();
                })
                .catch((error) => {
                    console.log(error);
                });
        },
        async loadCompare() {
            this.compareLoad = true;

            await axios
                .get(
                    `${this.host}/api/operations/ttl_compare/${this.compareGraph}`,
                    {
                        responseType: "json"
                    }
                )
                .then((response) => {
                    this.store.setCompareMode(true);
                    this.store.setCurrentGraph(response.data, this.compareGraph);
                    this.store.setControlMenu(null, null);
                    this.compareLoad = false;
                })
                .catch((error) => {
                    console.log(error);
                    this.compareLoad = false;
                });
        },
        async uploadGraph() {
            this.uploadLoad = true;
            const formData = new FormData();
            formData.append('file', this.fileUpload);

            await axios
                .post(
                    `${this.host}/api/operations/ttl`,
                    formData,
                )
                .then((response) => {
                    // console.log(response);
                    // this.store.setControlMenu(null, null);
                    this.uploadLoad = false;
                    this.store.triggerReload();
                    this.fileUpload = null;
                    this.uploadSuccess = true;
                })
                .catch((error) => {
                    console.log(error);
                    this.uploadLoad = false;
                });
        },
        async deleteGraph() {
            this.deleteLoad = true;

            await axios
                .delete(
                    `${this.host}/api/operations/ttl_file/${this.deletedGraph}`,
                )
                .then((response) => {
                    // console.log(response);
                    // this.store.setControlMenu(null, null);
                    this.deleteLoad = false;
                    this.store.triggerReload();
                    this.fileDeleted = this.deletedGraph;
                    this.deleteSuccess = true;
                    this.deletedGraph = null;
                })
                .catch((error) => {
                    console.log(error);
                    this.deleteLoad = false;
                });
        },
        async deleteCompareGraph() {
            this.deleteCompareLoad = true;

            await axios
                .delete(
                    `${this.host}/api/operations/ttl_compare/${this.deletedCompareGraph}`,
                )
                .then((response) => {
                    // console.log(response);
                    // this.store.setControlMenu(null, null);
                    this.deleteCompareLoad = false;
                    this.store.triggerReload();
                    this.fileDeleted = this.deletedCompareGraph;
                    this.deleteSuccess = true;
                    this.deletedCompareGraph = null;
                })
                .catch((error) => {
                    console.log(error);
                    this.deleteCompareLoad = false;
                });
        },
        async addSubnet() {
            this.addSubnetLoad = true;

            await axios
                .post(
                    `${this.host}/api/operations/subnets`,
                    {
                        "ip_address": this.newSubnet,
                    }
                )
                .then((response) => {
                    // console.log(response);
                    // this.store.setControlMenu(null, null);
                    this.addSubnetLoad = false;
                    this.store.triggerReload();
                    this.newSubnet = null;
                    this.subnetAdded = true;
                })
                .catch((error) => {
                    console.log(error);
                    this.addSubnetLoad = false;
                });
        },
        async deleteSubnet() {
            this.deleteSubnetLoad = true;

            const payload = {
                "ip_address": this.subnetToDelete,
            }

            console.log(this.subnetToDelete);

            await axios
                .delete(
                    `${this.host}/api/operations/subnets`,
                    { data: payload }
                )
                .then((response) => {
                    // console.log(response);
                    // this.store.setControlMenu(null, null);
                    this.deleteSubnetLoad = false;
                    this.store.triggerReload();
                    this.subnetToDelete = null;
                    this.subnetDeleted = true;
                })
                .catch((error) => {
                    console.log(error);
                    this.deleteSubnetLoad = false;
                });
        },
        async addBbmd() {
            this.addBbmdLoad = true;

            await axios
                .post(
                    `${this.host}/api/operations/bbmds`,
                    {
                        "ip_address": this.newBbmd,
                    }
                )
                .then((response) => {
                    // console.log(response);
                    // this.store.setControlMenu(null, null);
                    this.addBbmdLoad = false;
                    this.store.triggerReload();
                    this.newBbmd = null;
                    this.bbmdAdded = true;
                })
                .catch((error) => {
                    console.log(error);
                    this.addBbmdLoad = false;
                });
        },
        async deleteBbmd() {
            this.deleteBbmdLoad = true;

            const payload = {
                "ip_address": this.bbmdToDelete,
            }

            console.log(this.bbmdToDelete);

            await axios
                .delete(
                    `${this.host}/api/operations/bbmds`,
                    { data: payload }
                )
                .then((response) => {
                    // console.log(response);
                    // this.store.setControlMenu(null, null);
                    this.deleteBbmdLoad = false;
                    this.store.triggerReload();
                    this.bbmdToDelete = null;
                    this.bbmdDeleted = true;
                })
                .catch((error) => {
                    console.log(error);
                    this.deleteBbmdLoad = false;
                });
        },
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
.search-results {
  list-style: none;
  padding: 5px 0;
  margin: 10px 0;
  overflow-y: scroll;
  background-color: #2A2A2A;
  border-radius: 8px;
  box-shadow: 0px 1px 1px rgba(0, 0, 0, 0.1);
  width: 100%;
  height: 100%;
  max-height: 160px;
}
.warning {
    position: absolute;
    // top: 95%;
    width: 90%;
    translate: 1% 125%;
}
.success {
    position: absolute;
    // top: 95%;
    width: 90%;
    translate: 1% 150%;
}
.alt-success {
    position: absolute;
    width: 90%;
}
</style>