export default [
  {
    files: ["**/*.js"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: {
        window: "readonly", document: "readonly", console: "readonly", location: "readonly",
        ResizeObserver: "readonly",
        setTimeout: "readonly", clearTimeout: "readonly", setInterval: "readonly", clearInterval: "readonly",
        Promise: "readonly", JSON: "readonly", Math: "readonly", Object: "readonly", Array: "readonly",
        String: "readonly", Number: "readonly", Boolean: "readonly", Set: "readonly", Map: "readonly",
        parseInt: "readonly", parseFloat: "readonly", isNaN: "readonly", Infinity: "readonly",
        define: "readonly", dojo: "readonly", dijit: "readonly", gameui: "readonly", g_gamethemeurl: "readonly",
        _: "readonly", $: "readonly", requestAnimationFrame: "readonly", MutationObserver: "readonly",
        getComputedStyle: "readonly", localStorage: "readonly", sessionStorage: "readonly", Element: "readonly", HTMLElement: "readonly", Node: "readonly",
        CustomEvent: "readonly", Event: "readonly", navigator: "readonly", performance: "readonly",
        Intl: "readonly", Date: "readonly", RegExp: "readonly", Error: "readonly", structuredClone: "readonly",
      },
    },
    rules: { "no-undef": "error" },
  },
];
