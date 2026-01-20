import { defineConfig } from 'vitepress';
import { withMermaid } from 'vitepress-plugin-mermaid';
import llmstxt from 'vitepress-plugin-llms';

export default withMermaid(
  defineConfig({
    title: 'uchroma',
    description: 'RGB control for Razer Chroma peripherals',
    base: '/uchroma/',
    appearance: 'dark',

    head: [['link', { rel: 'icon', type: 'image/png', href: '/uchroma/favicon.png' }]],

    vite: {
      plugins: [llmstxt()],
      build: {
        chunkSizeWarningLimit: 1000,
      },
    },

    themeConfig: {
      nav: [
        { text: 'Guide', link: '/guide/' },
        { text: 'CLI', link: '/cli/' },
        { text: 'Effects', link: '/effects/' },
        { text: 'Reference', link: '/reference/' },
        { text: 'Developers', link: '/developers/' },
      ],

      sidebar: {
        '/guide/': [
          {
            text: 'Getting Started',
            items: [
              { text: 'Introduction', link: '/guide/' },
              { text: 'Installation', link: '/guide/installation' },
              { text: 'Quick Start', link: '/guide/quick-start' },
              { text: 'GTK App', link: '/guide/gtk-app' },
              { text: 'Configuration', link: '/guide/configuration' },
              { text: 'Troubleshooting', link: '/guide/troubleshooting' },
            ],
          },
        ],

        '/cli/': [
          {
            text: 'CLI Reference',
            items: [
              { text: 'Overview', link: '/cli/' },
              { text: 'Devices', link: '/cli/devices' },
              { text: 'Brightness', link: '/cli/brightness' },
              { text: 'Effects', link: '/cli/effects' },
              { text: 'Animations', link: '/cli/animations' },
              { text: 'Profiles', link: '/cli/profiles' },
              { text: 'Power', link: '/cli/power' },
              { text: 'Advanced', link: '/cli/advanced' },
            ],
          },
        ],

        '/effects/': [
          {
            text: 'Effects',
            items: [
              { text: 'Overview', link: '/effects/' },
              { text: 'Hardware Effects', link: '/effects/hardware' },
              { text: 'Custom Animations', link: '/effects/custom' },
            ],
          },
        ],

        '/reference/': [
          {
            text: 'Reference',
            items: [
              { text: 'Overview', link: '/reference/' },
              { text: 'Supported Devices', link: '/reference/devices' },
              { text: 'D-Bus API', link: '/reference/dbus-api' },
            ],
          },
        ],

        '/developers/': [
          {
            text: 'Developer Guide',
            items: [
              { text: 'Overview', link: '/developers/' },
              { text: 'Architecture', link: '/developers/architecture' },
              { text: 'Creating Effects', link: '/developers/creating-effects' },
              { text: 'Layer API', link: '/developers/layer-api' },
              { text: 'Traits', link: '/developers/traits' },
              { text: 'Colors', link: '/developers/colors' },
              { text: 'Advanced', link: '/developers/advanced' },
            ],
          },
        ],
      },

      search: {
        provider: 'local',
      },

      socialLinks: [{ icon: 'github', link: 'https://github.com/hyperb1iss/uchroma' }],

      footer: {
        message: 'Released under the LGPL-3.0 License.',
        copyright: 'Copyright © 2017-present Stefanie Jane',
      },
    },

    mermaid: {
      theme: 'dark',
      themeVariables: {
        primaryColor: '#e135ff',
        primaryTextColor: '#f8f8f2',
        primaryBorderColor: '#80ffea',
        lineColor: '#80ffea',
        secondaryColor: '#282a36',
        tertiaryColor: '#44475a',
        background: '#1a1b26',
        mainBkg: '#282a36',
        nodeBorder: '#80ffea',
        clusterBkg: '#282a36',
        clusterBorder: '#e135ff',
        titleColor: '#f8f8f2',
        edgeLabelBackground: '#282a36',
      },
    },
  })
);
