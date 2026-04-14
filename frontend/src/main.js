import { mount, unmount } from "svelte";
import "./styles/app.css";

// ── Svelte Island Mounter ───────────────────────────────────────────────
// Finds elements with data-svelte-component and mounts the corresponding
// Svelte component, passing data-* attributes as props.
// Uses Svelte 5's mount() API instead of the deprecated `new Component()`.

const components = import.meta.glob("./islands/*.svelte", { eager: true });

function mountIslands() {
  document.querySelectorAll("[data-svelte-component]").forEach((el) => {
    // Skip already-mounted islands
    if (el._svelteInstance) return;

    const name = el.dataset.svelteComponent;
    const modulePath = `./islands/${name}.svelte`;
    const mod = components[modulePath];

    if (!mod) {
      console.warn(`Svelte island "${name}" not found at ${modulePath}`);
      return;
    }

    // Collect all data-prop-* attributes as props
    const props = {};
    for (const [key, value] of Object.entries(el.dataset)) {
      if (key.startsWith("prop")) {
        // data-prop-my-value → myValue (camelCase)
        const propName = key.slice(4, 5).toLowerCase() + key.slice(5);
        // Try to parse numbers and booleans
        if (value === "true") props[propName] = true;
        else if (value === "false") props[propName] = false;
        else if (!isNaN(value) && value !== "") props[propName] = Number(value);
        else props[propName] = value;
      }
    }

    // Mount with Svelte 5 API
    el._svelteInstance = mount(mod.default, { target: el, props });
  });
}

// Mount on initial load
mountIslands();

// Re-mount after HTMX swaps (so islands inside HTMX-loaded content work)
document.addEventListener("htmx:afterSwap", () => {
  mountIslands();
});
