import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'start',
      component: () => import('../components/StartMenu.vue'),
    },
    {
      path: '/graphs/:graph',
      name: 'graph',
      component: () => import('../views/NetworkGraphView.vue'),
      meta: { compare: false },
    },
    {
      path: '/compares/:graph',
      name: 'compare',
      component: () => import('../views/NetworkGraphView.vue'),
      meta: { compare: true },
    },
    {
      // links from before graphs and compares had their own paths
      path: '/:graph([^/]+\\.ttl)',
      redirect: to =>
        graphRoute(to.params.graph.includes('_vs_'), to.params.graph),
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

export function graphRoute(compare, graph) {
  return {
    name: compare ? 'compare' : 'graph',
    params: { graph },
  }
}

export default router
