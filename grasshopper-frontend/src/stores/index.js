import { defineStore } from "pinia";

export const useGrasshopperStore = defineStore("grasshopper", {
  state: () => ({
    controlMenu: false,
    menuType: null,
    menuTitle: null
  }),
  actions: {
    setControlMenu(type, title) {
        this.controlMenu = !this.controlMenu;

        if (this.controlMenu) {
          this.menuType = type;
          this.menuTitle = title;
        } else {
          this.menuType = null;
          this.menuTitle = null;
        }
    },
  },
});
