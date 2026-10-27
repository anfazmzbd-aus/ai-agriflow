# AgriFlow AI — Next.js web frontend

Responsive marketing website + functional farmer dashboard UI + chat API proxy. Developed as the **frontend starter** for the `agriflow-agent-platform` Python capstone. Agricultural intelligence functionality remains **planned** unless connected to a working backend and validated data providers.

## Setup (Windows 11 PowerShell)

```powershell
npm install
Copy-Item .env.example .env.local
# Leave AGRIFLOW_API_BASE_URL unset (remove or comment it in .env.local) to use the offline chat preview.
npm run dev
```

Open http://localhost:3000. Routes: `/` (landing), `/dashboard` (interactive dashboard), `/api/health` (status) and `/api/assistant` (server API proxy). `public/original-concept.html` preserves the initial landing prototype.

## Integrate with the Python FastAPI backend

Set `AGRIFLOW_API_BASE_URL=http://127.0.0.1:8000` in `.env.local`, and optionally `AGRIFLOW_CHAT_PATH=/api/v1/chat`. The Next.js server will POST to this upstream endpoint. **The current capstone's API route is not verified; implement or adapt the contract below.** The browser never sends the private token directly to the backend.

### POST /api/v1/chat request

```json
{"message":"What should I consider before planting paddy?","crop":"Paddy","location":"Kurunegala","session_id":"optional"}
```

### Expected backend response

```json
{"answer":"Check verified local weather and field conditions before planting.","sources":[{"title":"Agriculture advisory","url":"https://example.org/advisory"}],"confidence":"requires verification"}
```

The proxy adds `mode:"live"` only when the backend responds successfully with a valid `answer`. Without `AGRIFLOW_API_BASE_URL`, a clear non-generative offline demo response is returned. If the configured API fails, the UI shows an error rather than silently presenting fabricated live results. URLs in returned sources are linked only if HTTPS. The proxy uses a 15-second timeout and avoids caching results.

## Development checks

```powershell
npm run typecheck
npm run build
npm start
```

## Deployment and safety

- Keep `.env.local` uncommitted. Put any service tokens in server-side environment variables.
- Protect API endpoints with authentication, authorization, quotas and abuse protections before public deployment. This starter is **not** a complete production backend.
- Use a real farmer/field data model, verified weather and market sources, proper source attribution and domain expert review before piloting real recommendations.
- Implement audit logging, privacy consent, input validation, backend authentication and structured error handling before public launch.
- Asset artwork is original CSS/SVG. Fonts fall back to system fonts and require no external download.
- Host on a Node-compatible Next.js platform; this app includes server-side routes and is **not** a static export.
