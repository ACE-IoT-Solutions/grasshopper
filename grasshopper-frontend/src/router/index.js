import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/:graphName?',
      name: 'network-graph',
      component: () => import('../views/NetworkGraphView.vue'),
    },
  ],
})

export default router
