/**
 * Tailwind config for the offline (standalone-CLI) build.
 *
 * Compiled with the Tailwind standalone binary — no Node required:
 *   ./tailwindcss -c tailwind.config.js -i tailwind/input.css \
 *       -o static/css/styles.css --minify
 *
 * `content` must cover every place a class name can appear so the JIT scanner
 * keeps it: all templates, and .py files (some classes are built in view
 * context / template tags) and inline <script> strings in templates.
 */
module.exports = {
  content: [
    './templates/**/*.html',
    './*/templates/**/*.html',
    './**/*.py',
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};
