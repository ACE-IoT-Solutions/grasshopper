<template>
  <div
    :class="
      store.menuType === 'compare' ||
      store.menuType === 'subnet' ||
      store.menuType === 'bbmd' ||
      (store.configSelect && store.menuType == 'setup')
        ? 'alt-menu'
        : store.menuType == 'delete' ? 'delete-menu' : 'menu'
    "
    style="z-index: 1000"
  >
    <div
      class="header"
      :style="
        store.menuType === 'compare' ||
        store.menuType === 'subnet' ||
        store.menuType === 'bbmd' ||
        (store.configSelect && store.menuType == 'setup')
          ? 'height: 10%;'
          : 'height: 20%;'
      "
    >
      <v-btn
        variant="plain"
        :ripple="false"
        icon=""
        id="no-background-hover"
        size="small"
        @click="store.setControlMenu(null, null)"
        ><v-icon>mdi-close</v-icon></v-btn
      >
    </div>
    <div class="menu-title">
      <p class="text">{{ store.menuTitle }}</p>
    </div>
    <div v-if="store.menuType == 'compare'" class="alt-container">
      <v-autocomplete
        v-model="compareGraph1"
        label="Select a Graph"
        variant="solo-filled"
        density="compact"
        :items="store.setupGraphs"
        clearable
      ></v-autocomplete>
      <v-autocomplete
        v-model="compareGraph2"
        label="Select a Graph"
        variant="solo-filled"
        density="compact"
        :items="store.setupGraphs"
        clearable
      ></v-autocomplete>
      <div style="display: flex; align-items: center; justify-content: center">
        <v-btn
          @click="createCompare()"
          :loading="createCompareLoad"
          variant="tonal"
          size="small"
          append-icon="mdi-compare-horizontal"
          color="#94D8FF"
          :disabled="!compareGraph1 || !compareGraph2"
        >
          Compare
        </v-btn>
      </div>
      <hr class="line" />
      <div
        style="
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 20px;
        "
      >
        <v-autocomplete
          v-model="compareGraph"
          :items="store.compareList"
          label="Past Comparisons"
          variant="solo-filled"
          density="compact"
          hide-details="auto"
          clearable
        ></v-autocomplete>
        <v-btn
          @click="loadCompare()"
          :loading="compareLoad"
          variant="tonal"
          size="small"
          append-icon="mdi-arrow-right"
          color="#c1d200"
          :disabled="!compareGraph"
          >Load</v-btn
        >
      </div>
    </div>
    <div v-if="store.menuType == 'delete'" class="delete-container">
      <div
        style="
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 20px;
        "
      >
        <v-autocomplete
          v-model="deletedGraph"
          :items="store.deleteList"
          label="Select a Graph"
          variant="solo-filled"
          density="compact"
          hide-details="auto"
          clearable
        ></v-autocomplete>
        <v-btn
          @click="deleteGraph()"
          :loading="deleteLoad"
          variant="tonal"
          size="small"
          color="red"
          :disabled="!deletedGraph"
          >Delete</v-btn
        >
      </div>
      <hr class="line" style="margin: 15px 0px" />
      <div
        style="
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 20px;
        "
      >
        <v-autocomplete
          v-model="deletedCompareGraph"
          :items="store.deleteCompareList"
          label="Select a Compare Graph"
          variant="solo-filled"
          density="compact"
          hide-details="auto"
          clearable
        ></v-autocomplete>
        <v-btn
          @click="deleteCompareGraph()"
          :loading="deleteCompareLoad"
          variant="tonal"
          size="small"
          color="red"
          :disabled="!deletedCompareGraph"
          >Delete</v-btn
        >
      </div>
      <hr class="line" style="margin: 15px 0px" />
      <div
        style="
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 20px;
        "
      >
        <v-autocomplete
          v-model="config"
          label="Select Config"
          variant="solo-filled"
          density="compact"
          hide-details="auto"
          :items="store.configList"
          clearable
        ></v-autocomplete>
        <v-btn
          @click="deleteConfig()"
          :loading="configLoad"
          variant="tonal"
          size="small"
          color="red"
          :disabled="!config"
          >Delete</v-btn
        >
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
          <h4 style="margin: 10px 10px 0px 10px">Subnets</h4>
          <hr class="line" style="margin: 8px 8px" />
          <li
            v-for="result in store.ipList"
            :key="result"
            style="margin-left: 10px"
          >
            {{ result }}
          </li>
        </ul>
      </div>
      <hr class="line" />
      <div
        style="
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 20px;
        "
      >
        <v-text-field
          v-model="newSubnet"
          label="Add a Subnet"
          density="compact"
          hide-details="auto"
          variant="solo-filled"
          :rules="ipRules"
          clearable
        ></v-text-field>
        <v-btn
          @click="addSubnet()"
          variant="tonal"
          size="small"
          append-icon="mdi-plus"
          color="#94D8FF"
          :loading="addSubnetLoad"
          :disabled="!isNewSubnetValid"
          >Add</v-btn
        >
      </div>
      <hr class="line" />
      <div
        style="
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 20px;
        "
      >
        <v-autocomplete
          v-model="subnetToDelete"
          :items="store.ipList"
          label="Select a Subnet"
          variant="solo-filled"
          density="compact"
          hide-details="auto"
          clearable
        ></v-autocomplete>
        <v-btn
          @click="deleteSubnet()"
          variant="tonal"
          size="small"
          color="red"
          :loading="deleteSubnetLoad"
          :disabled="!subnetToDelete"
          >Delete</v-btn
        >
      </div>
      <v-alert
        v-if="subnetAdded"
        type="success"
        class="success"
        closable
        @click:close="subnetAdded = false"
      >
        Subnet added.
      </v-alert>
      <v-alert
        v-if="subnetDeleted"
        type="success"
        class="success"
        closable
        @click:close="subnetDeleted = false"
      >
        Subnet deleted.
      </v-alert>
    </div>
    <div v-if="store.menuType == 'bbmd'" class="alt-container">
      <div>
        <ul class="search-results">
          <h4 style="margin: 10px 10px 0px 10px">BBMDs</h4>
          <hr class="line" style="margin: 8px 8px" />
          <li
            v-for="result in store.bbmdList"
            :key="result"
            style="margin-left: 10px"
          >
            {{ result }}
          </li>
        </ul>
      </div>
      <hr class="line" />
      <div
        style="
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 20px;
        "
      >
        <v-text-field
          v-model="newBbmd"
          label="Add a BBMD"
          density="compact"
          hide-details="auto"
          variant="solo-filled"
          :rules="bbmdRules"
          clearable
        ></v-text-field>
        <v-btn
          @click="addBbmd()"
          variant="tonal"
          size="small"
          append-icon="mdi-plus"
          color="#94D8FF"
          :loading="addBbmdLoad"
          :disabled="!isNewBbmdValid"
          >Add</v-btn
        >
      </div>
      <hr class="line" />
      <div
        style="
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 20px;
        "
      >
        <v-autocomplete
          v-model="bbmdToDelete"
          :items="store.bbmdList"
          label="Select a BBMD"
          variant="solo-filled"
          density="compact"
          hide-details="auto"
          clearable
        ></v-autocomplete>
        <v-btn
          @click="deleteBbmd()"
          variant="tonal"
          size="small"
          color="red"
          :loading="deleteBbmdLoad"
          :disabled="!bbmdToDelete"
          >Delete</v-btn
        >
      </div>
      <v-alert
        v-if="bbmdAdded"
        type="success"
        class="success"
        closable
        @click:close="bbmdAdded = false"
      >
        BBMD added.
      </v-alert>
      <v-alert
        v-if="bbmdDeleted"
        type="success"
        class="success"
        closable
        @click:close="bbmdDeleted = false"
      >
        BBMD deleted.
      </v-alert>
    </div>
    <div
      v-if="store.menuType == 'setup'"
      class="container"
      style="align-content: space-evenly"
    >
      <div
        :class="store.configSelect ? 'setup-config' : 'setup-default'"
      >
        <v-autocomplete
          v-model="setupGraph"
          label="Select a Graph"
          variant="solo-filled"
          density="compact"
          hide-details="auto"
          :items="store.setupGraphs"
          clearable
        ></v-autocomplete>
        <v-autocomplete
          v-if="store.configSelect"
          v-model="config"
          label="Select a Config (Optional)"
          variant="solo-filled"
          density="compact"
          hide-details="auto"
          :items="store.configList"
          clearable
        ></v-autocomplete>
        <v-btn
          v-if="!store.configSelect"
          @click="goToGraph()"
          :loading="setupLoad"
          variant="tonal"
          size="small"
          append-icon="mdi-arrow-right"
          color="#c1d200"
          :disabled="!setupGraph"
          >Load</v-btn
        >
        <div v-if="store.configSelect" style="display: flex; justify-content: center;">
          <v-btn
            @click="config == null ? (goToGraph(), store.setPhysicsConfig(this.store.defaultConfig)) : graphWithConfig()"
            :loading="setupLoad"
            variant="tonal"
            size="small"
            append-icon="mdi-arrow-right"
            color="#c1d200"
            :disabled="!setupGraph"
            >Load</v-btn
          >
        </div>
      </div>
      <hr class="line" />
      <div
        style="
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 20px;
          margin-bottom: 20px;
        "
      >
        <v-file-input
          v-model="fileUpload"
          clearable
          label="Upload Graph"
          variant="solo-filled"
          density="compact"
          accept=".ttl"
          hide-details="auto"
          @change="checkFileName()"
        ></v-file-input>
        <v-btn
          @click="uploadGraph()"
          :loading="uploadLoad"
          variant="tonal"
          size="small"
          append-icon="mdi-upload"
          color="#94D8FF"
          :disabled="!fileUpload"
          >Upload</v-btn
        >
      </div>
      <v-alert
        type="warning"
        color="#94D8FF"
        v-if="showWarning"
        class="warning"
        closable
        @click:close="showWarning = false"
      >
        The file <strong>base.ttl</strong> was uploaded. This will become the
        basis of all scans.
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
    <div v-if="store.menuType == 'config'" class="container">
      <v-text-field
        v-if="store.menuTitle == 'Save Config'"
        v-model="configTitle"
        label="Config Name"
        density="compact"
        variant="solo-filled"
        :rules="configRules"
        clearable
      ></v-text-field>
      <v-autocomplete
        v-if="store.menuTitle == 'Load Config'"
        v-model="config"
        label="Select Config"
        variant="solo-filled"
        density="compact"
        :items="store.configList"
        clearable
      ></v-autocomplete>
      <div style="display: flex; justify-content: center;">
        <v-btn
          v-if="store.menuTitle == 'Save Config'"
          @click="saveConfig()"
          :loading="configLoad"
          variant="tonal"
          size="small"
          append-icon="mdi-content-save"
          color="#94D8FF"
          :disabled="!configTitle"
          >Save
        </v-btn>
        <v-btn
          v-if="store.menuTitle == 'Load Config'"
          @click="loadConfig()"
          :loading="configLoad"
          variant="tonal"
          size="small"
          append-icon="mdi-arrow-right"
          color="#c1d200"
          :disabled="!config"
          >Load
        </v-btn>
      </div>
      <v-alert
        v-if="configSuccess"
        type="success"
        class="success"
        closable
        @click:close="configSuccess = false"
      >
        Config saved.
      </v-alert>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
import { gsap } from 'gsap'
export default {
  props: ['store'],
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
      ipRules: [
        v =>
          /^((25[0-5]|2[0-4]\d|[01]?\d?\d)\.){3}(25[0-5]|2[0-4]\d|[01]?\d?\d)\/(0|[1-9]|1\d|2\d|3[0-2])$/.test(
            v,
          ) || 'IP with CIDR must be valid',
      ],
      bbmdRules: [
        v =>
          /^(?:(25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.){3}(25[0-5]|(2[0-4]|1\d|[1-9]|)\d)$|^$/.test(
            v,
          ) || 'IP must be valid',
      ],
      newBbmd: null,
      bbmdToDelete: null,
      addBbmdLoad: false,
      deleteBbmdLoad: false,
      testList: ['test', 'test', 'test', 'test', 'test', 'test'],
      showWarning: false,
      deleteSuccess: false,
      fileDeleted: null,
      uploadSuccess: false,
      subnetAdded: false,
      subnetDeleted: false,
      bbmdAdded: false,
      bbmdDeleted: false,
      valid: false,
      config: null,
      configTitle: null,
      configLoad: false,
      configRules: [
        v => !!v || 'Title cannot be empty',
        v => /^[^.]+$/.test(v) || 'Title cannot reference a file type',
      ],
      configSuccess: false,
    }
  },
  computed: {
    isNewBbmdValid() {
      if (!this.newBbmd) return false

      return this.bbmdRules.every(rule => {
        const result = rule(this.newBbmd)
        return result === true
      })
    },
    isNewSubnetValid() {
      if (!this.newSubnet) return false

      return this.ipRules.every(rule => {
        const result = rule(this.newSubnet)
        return result === true
      })
    },
  },
  watch: {
    // eslint-disable-next-line no-unused-vars
    'store.reloadKey'(newVal, oldVal) {
      this.refresh();
    },
  },
  mounted() {
    let animateClass = null

    this.store.menuType === 'compare' ||
    this.store.menuType === 'subnet' ||
    this.store.menuType === 'bbmd' ||
    (this.store.configSelect && this.store.menuType == 'setup')
      ? (animateClass = '.alt-menu')
      : this.store.menuType === 'delete'
      ? (animateClass = '.delete-menu')
      : (animateClass = '.menu')

    gsap.from(animateClass, {
      duration: 0.25,
      opacity: 0,
      y: -50,
      ease: 'power2.out',
    })

    this.decodeCookie();
    this.refresh();
  },
  methods: {
    checkFileName() {
      if (this.fileUpload && this.fileUpload.name === 'base.ttl') {
        this.showWarning = true
      } else {
        this.showWarning = false
      }
    },
    async saveConfig() {
      this.configLoad = true;

      const jsonBlob = new Blob(
        [JSON.stringify(this.store.configToSave, null, 2)],
        { type: 'application/json' }
      );

      const fileName = `${this.configTitle}.json`;

      const formData = new FormData();
      formData.append('file', jsonBlob, fileName);

      await axios
      .post(`${this.host}/api/operations/network_config`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        }
      )
      .then(() => {
        this.store.triggerReload();
        this.store.setCurrentConfig(fileName);
        this.store.setPhysicsConfig(this.store.configToSave);
        this.storeConfig(fileName);
        this.configSuccess = true;
        this.configTitle = null;
        this.configLoad = false;
      })
      .catch(error => {
        console.log(error);
      });
    },
    async loadConfig() {
      this.configLoad = true;

      await axios
        .get(`${this.host}/api/operations/network_config/${this.config}`, {
          responseType: 'json',
        })
        .then(response => {
          this.store.setCurrentConfig(this.config);
          this.store.setPhysicsConfig(response.data);
          this.store.setControlMenu(null, null);
          this.storeConfig(this.config);
          this.store.setReload();
          this.configLoad = false;
        })
        .catch(error => {
          console.log(error);
          this.configLoad = false;
        });
    },
    async deleteConfig() {
      this.configLoad = true;
      await axios
        .delete(`${this.host}/api/operations/network_config/${this.config}`)
        // eslint-disable-next-line no-unused-vars
        .then(response => {
          this.configLoad = false
          this.store.triggerReload()
          this.fileDeleted = this.config
          this.deleteSuccess = true
          this.config = null
        })
        .catch(error => {
          console.log(error)
          this.deleteLoad = false
        })
    },
    async graphWithConfig() {
      this.setupLoad = true

      await axios
        .get(`${this.host}/api/operations/network_config/${this.config}`, {
          responseType: 'json',
        })
        .then(response => {
          this.store.setPhysicsConfig(response.data);
          this.store.setCurrentConfig(this.config);
          this.storeConfig(this.config);
          this.goToGraph();
        })
        .catch(error => {
          console.log(error);
        })
    },
    async goToGraph() {
      this.setupLoad = true

      await axios
        .get(`${this.host}/api/operations/ttl_network/${this.setupGraph}`, {
          responseType: 'json',
        })
        .then(response => {
          this.store.setCompareMode(false)
          this.store.setCurrentGraph(response.data, this.setupGraph)
          this.store.setControlMenu(null, null)
          this.setupLoad = false
          this.$router.push({ params: { graphName: this.setupGraph } })

        })
        .catch(error => {
          console.log(error)
          this.setupLoad = false
        })
    },
    async createCompare() {
      const payload = {
        ttl_1: this.compareGraph1,
        ttl_2: this.compareGraph2,
      }

      await axios
        .post(`${this.host}/api/operations/ttl_compare_queue`, payload)
        // eslint-disable-next-line no-unused-vars
        .then(response => {
          this.store.setControlMenu(null, null)
          this.compareGraph1 = null
          this.compareGraph2 = null
          this.store.triggerReload()
        })
        .catch(error => {
          console.log(error)
        })
    },
    async loadCompare() {
      this.compareLoad = true

      await axios
        .get(`${this.host}/api/operations/ttl_compare/${this.compareGraph}`, {
          responseType: 'json',
        })
        .then(response => {
          this.store.setCompareMode(true)
          this.store.setCurrentGraph(response.data, this.compareGraph)
          this.store.setControlMenu(null, null)
          this.compareLoad = false
          this.$router.push({ params: { graphName: this.compareGraph } })
        })
        .catch(error => {
          console.log(error)
          this.compareLoad = false
        })
    },
    async uploadGraph() {
      this.uploadLoad = true
      const formData = new FormData()
      formData.append('file', this.fileUpload)

      await axios
        .post(`${this.host}/api/operations/ttl`, formData)
        // eslint-disable-next-line no-unused-vars
        .then(response => {
          this.uploadLoad = false
          this.store.triggerReload()
          this.fileUpload = null
          this.uploadSuccess = true
        })
        .catch(error => {
          console.log(error)
          this.uploadLoad = false
        })
    },
    async deleteGraph() {
      this.deleteLoad = true

      await axios
        .delete(`${this.host}/api/operations/ttl_file/${this.deletedGraph}`)
        // eslint-disable-next-line no-unused-vars
        .then(response => {
          this.deleteLoad = false
          this.store.triggerReload()
          this.fileDeleted = this.deletedGraph
          this.deleteSuccess = true
          this.deletedGraph = null
        })
        .catch(error => {
          console.log(error)
          this.deleteLoad = false
        })
    },
    async deleteCompareGraph() {
      this.deleteCompareLoad = true

      await axios
        .delete(
          `${this.host}/api/operations/ttl_compare/${this.deletedCompareGraph}`,
        )
        // eslint-disable-next-line no-unused-vars
        .then(response => {
          this.deleteCompareLoad = false
          this.store.triggerReload()
          this.fileDeleted = this.deletedCompareGraph
          this.deleteSuccess = true
          this.deletedCompareGraph = null
        })
        .catch(error => {
          console.log(error)
          this.deleteCompareLoad = false
        })
    },
    async addSubnet() {
      this.addSubnetLoad = true

      await axios
        .post(`${this.host}/api/operations/subnets`, {
          ip_address: this.newSubnet,
        })
        // eslint-disable-next-line no-unused-vars
        .then(response => {
          this.addSubnetLoad = false
          this.store.triggerReload()
          this.newSubnet = null
          this.subnetAdded = true
        })
        .catch(error => {
          console.log(error)
          this.addSubnetLoad = false
        })
    },
    async deleteSubnet() {
      this.deleteSubnetLoad = true

      const payload = {
        ip_address: this.subnetToDelete,
      }

      console.log(this.subnetToDelete)

      await axios
        .delete(`${this.host}/api/operations/subnets`, { data: payload })
        // eslint-disable-next-line no-unused-vars
        .then(response => {
          this.deleteSubnetLoad = false
          this.store.triggerReload()
          this.subnetToDelete = null
          this.subnetDeleted = true
        })
        .catch(error => {
          console.log(error)
          this.deleteSubnetLoad = false
        })
    },
    async addBbmd() {
      this.addBbmdLoad = true

      await axios
        .post(`${this.host}/api/operations/bbmds`, {
          ip_address: this.newBbmd,
        })
        // eslint-disable-next-line no-unused-vars
        .then(response => {
          this.addBbmdLoad = false
          this.store.triggerReload()
          this.newBbmd = null
          this.bbmdAdded = true
        })
        .catch(error => {
          console.log(error)
          this.addBbmdLoad = false
        })
    },
    async deleteBbmd() {
      this.deleteBbmdLoad = true

      const payload = {
        ip_address: this.bbmdToDelete,
      }

      console.log(this.bbmdToDelete)

      await axios
        .delete(`${this.host}/api/operations/bbmds`, { data: payload })
        // eslint-disable-next-line no-unused-vars
        .then(response => {
          this.deleteBbmdLoad = false
          this.store.triggerReload()
          this.bbmdToDelete = null
          this.bbmdDeleted = true
        })
        .catch(error => {
          console.log(error)
          this.deleteBbmdLoad = false
        })
    },
    storeConfig(config) {
      const date = new Date();
      date.setTime(date.getTime() + (30 * 24 * 60 * 60 * 1000));
      
      document.cookie = `volttron_config=${config}; expires=${date.toUTCString()} path=/`;
    },
    decodeCookie() {
      const cookie = decodeURIComponent(document.cookie);
      // console.log(cookie);

      for (const c of cookie.split(';')) {
        const [key, value] = c.trim().split('=');
        if (key === 'volttron_config') {
          this.config = value;
        }
      }
    },
    async fetchGraphs() {
      await axios
        .get(
          `${this.host}/api/operations/ttl`,
          {
            responseType: "json"
          }
        )
        .then((response) => {
          this.store.setSetupGraphs(response.data.data);
          this.store.setDeleteGraphs(response.data.data);
        })
        .catch((error) => {
          console.log(error);
        });
    },
    async fetchIps() {
      await axios
        .get(
          `${this.host}/api/operations/subnets`,
          {
            responseType: "json"
          }
        )
        .then((response) => {
          this.store.setIpList(response.data.ip_address_list);
        })
        .catch((error) => {
          console.log(error);
        });
    },
    async fetchCompareGraphs() {
      await axios
        .get(
          `${this.host}/api/operations/ttl_compare`,
          {
            responseType: "json"
          }
        )
        .then((response) => {
          this.store.setCompareList(response.data.file_list);
          this.store.setDeleteCompareGraphs(response.data.file_list);
        })
        .catch((error) => {
          console.log(error);
        });
    },
    async fetchBbmds() {
      await axios
        .get(
          `${this.host}/api/operations/bbmds`,
          {
            responseType: "json"
          }
        )
        .then((response) => {
          this.store.setBbmdList(response.data.ip_address_list);
        })
        .catch((error) => {
          console.log(error);
        });
    },
    async fetchConfig() {
      await axios
        .get(
          `${this.host}/api/operations/network_config`,
          {
            responseType: "json"
          }
        )
        .then((response) => {

          if (response.data.data.length === 0) {
            this.store.setConfigSelect(false);
            this.store.setPhysicsConfig(this.store.defaultConfig);
          } else {
            this.store.setConfigSelect(true);
            this.store.setConfigList(response.data.data);
          }
          
        })
        .catch((error) => {
          console.log(error);
        });
    },
    async refresh() {
        await Promise.all([
            this.fetchGraphs(),
            this.fetchIps(),
            this.fetchCompareGraphs(),
            this.fetchBbmds(),
            this.fetchConfig()
        ]);
    },
  },
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
  color: #cdcdcd;
  font-weight: 500;
}
.line {
  width: 100%;
  color: #cdcdcd;
  opacity: 30%;
}
.search-results {
  list-style: none;
  padding: 5px 0;
  margin: 10px 0;
  overflow-y: scroll;
  background-color: #2a2a2a;
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
  translate: 0%;
  top: 5%;
}
.alt-success {
  position: absolute;
  width: 90%;
}
.setup-default {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
}
.setup-config {
  display: contents;
}
.delete-menu {
  height: 35vh;
  width: 30vw;
  background-color: #212121;
  border-radius: 15px;
  position: absolute;
  top: 25%;
  left: 35%;
  box-shadow: 0px 4px 1px rgba(0, 0, 0, 0.5);
}
.delete-container {
  margin: 20px;
  height: 60%;
  display: grid;
  align-items: center;
  align-content: space-evenly;
  overflow: scroll;
}
</style>
