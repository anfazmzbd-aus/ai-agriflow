# AI AgriFlow landing page

A standalone, responsive Vite site introducing the AgriFlow capstone concept. It is separate from the Python AgentOS framework and does not connect to live agents or weather services.

Requires Node.js 20.19+ or 22.12+.

```bash
cd landing-page
npm ci
npm run dev
```

Open the URL printed by Vite on your local machine. For a cloud machine, use your interface's forwarded port or preview facility.

```bash
npm run build
npm run preview
```

Production output is `landing-page/dist/`. Deploy that directory to a static hosting provider; pushing these source files to GitHub does not deploy a public website. Configure the hosting build command as `npm run build` with `landing-page` as its root directory.

The agent cards open explanatory dialogs. Weather values are illustrative. Graphics are local SVG assets; Google Fonts requires network access and falls back to sans-serif.
