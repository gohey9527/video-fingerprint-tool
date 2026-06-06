import type { Plugin } from '#/global'

const pluginConfig: Plugin.PluginConfig = {
  install() {},
  config: {
    enable: true,
    info: {
      name: 'gohey/client-usage',
      version: '1.0.0',
      author: 'gohey9527',
      description: '短视频指纹工具客户端使用统计',
    },
  },
  views: [
    {
      name: 'app:clientUsage',
      path: '/app/clientUsage',
      meta: {
        title: '客户端使用统计',
        i18n: false,
        icon: 'material-symbols:monitor-heart-outline',
        type: 'M',
        hidden: false,
        componentPath: '/plugin/gohey/client-usage/views/index.vue',
        componentName: 'plugin:gohey:client-usage:index',
      },
      component: () => import('./views/index.vue'),
    },
  ],
}

export default pluginConfig
