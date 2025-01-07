<template>
    <div>
        <div class="network-header">
            <!-- <v-select
                label="Select a Graph"
                variant="solo-filled"
                density="compact"
                class="main-select"
                hide-details="auto"
            ></v-select> -->
            <RouterLink to="/" class="nav-link">
                <img style="width: 70%;"src="/assets/grasshopper.svg" alt="Grasshopper Logo" />
            </RouterLink>
            <div class="buttons" style="margin-right: 1.5vw; gap: 20px; align-items: center;">
                <v-btn variant="plain" size="small" @click="store.setControlMenu('compare', 'Compare Graphs')" style="text-decoration: none;">Compare Graphs</v-btn>
                <v-btn variant="plain" size="small" @click="store.setControlMenu('delete', 'Delete Graph')">Delete Graph</v-btn>
                <v-btn variant="plain" size="small" @click="store.setControlMenu('bbmd', 'BBMD')">BBMD</v-btn>
                <v-btn variant="plain" size="small" @click="store.setControlMenu('subnet', 'Subnet')">Subnet</v-btn>
                <v-btn variant="outlined" size="small" @click="store.setControlMenu('setup', 'Setup')" color="#CDCDCD">Graph Setup</v-btn>
                <v-btn
                    v-if="store.fileName"
                    @click="store.setReload()"
                    variant="plain"
                    :ripple="false"
                    icon=""
                    id="no-background-hover"
                    size="small"
                    density="compact"
                    color="#94D8FF"
                >
                    <v-icon>mdi-autorenew</v-icon>
                </v-btn>
                <div class="text-center">
                    <v-menu
                    open-on-hover
                    >
                    <template v-slot:activator="{ props }">
                        <v-btn
                            v-if="store.fileName"
                            v-bind="props"
                            variant="plain"
                            :ripple="false"
                            icon=""
                            id="no-background-hover"
                            size="small"
                            density="compact"
                            color="#FFFD94"
                        >
                            <v-icon>mdi-download</v-icon>
                        </v-btn>
                    </template>
    
                    <v-list>
                        <v-list-item
                        v-for="(item, index) in downloadOptions"
                        :key="index"
                        @click="item.action"
                        >
                        <v-list-item-title>{{ item.title }}</v-list-item-title>
                        </v-list-item>
                    </v-list>
                    </v-menu>
                </div>
                <v-btn
                    v-if="store.currentTask != 'None'"
                    @click="store.setCompareLoad(true)"
                    variant="plain"
                    :ripple="false"
                    icon=""
                    id="no-background-hover"
                    size="small"
                    density="compact"
                    color="#CDCDCD"
                >
                    <v-icon>mdi-tray-full</v-icon>
                </v-btn>
            </div>
        </div>
    </div>
</template>

<script>
import { excelParser } from "../parsers/parser.js";
import axios from "axios";
export default {
    props: ["store"],
    data() {
        return {
            downloadOptions: [
                {
                title: "TTL",
                action: () => this.exportTtl(),
                },
                {
                title: "JSON",
                action: () => this.exportToFile("json"),
                },
            ],
            host: window.location.protocol + '//' + window.location.host,
        };
    },
    methods: {
        exportToFile(type) {
        if (type === 'csv') {
            
            const nodes = this.store.currentGraph.nodes.map(node => ({
                id: node.id,
                label: node.label,
                color: node.color,
                shape: node.shape,
                data: node.data
            }));

            const edges = this.store.currentGraph.edges.map(edge => ({
                from: edge.from,
                label: edge.label,
                to: edge.to
            }));

            const data = [...nodes, ...edges];

            excelParser().exportDataFromJSON(
                nodes,
                `${this.store.fileName}`,
                'csv'
            );
        } else if (type === 'json') {
            excelParser().exportDataFromJSON(
                this.store.currentGraph,
                `${this.store.fileName}`,
                type
            );
        }
        },
        async exportTtl() {
            await axios
            .get(
            `${this.host}/api/operations/ttl_file/${this.store.fileName}`,
            {
                headers: {
                    Accept: 'text/turtle'
                },
                responseType: 'blob'
            })
            .then((response) => {
                const blob = new Blob([response.data], { type: 'text/turtle' });

                const downloadUrl = URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = downloadUrl;

                link.setAttribute('download', `${this.store.fileName}`);

                document.body.appendChild(link);
                link.click();
                link.remove();

                URL.revokeObjectURL(downloadUrl);
            
            })
            .catch((error) => {
                console.log(error);
            });
        }
    },
}
</script>

<style lang="scss" scoped>
.network-header {
    display: flex;
    justify-content: space-between;
    gap: 10px;
    margin: 35px 20px 0px 20px;
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
.nav-link {
    margin-left: 1.5vw;
}
.secondary-header {
    display: flex;
    margin: 0 20px;
    justify-content: flex-end;
}
</style>