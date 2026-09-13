# EADS

Emergency Ambulance Dispatch System dashboard.

## Vercel deployment

This project is configured as a static multi-page site with a Node serverless API:

- `vercel.json` rewrites `/api/*` to `api/index.js`.
- `api/index.js` is dependency-free and exports the Vercel function handler.
- `server.js` runs the same handler locally on port `5000`.
- `npm run check` validates both Node entry points.

Deploy from the project root:

```sh
npm install
npm run check
npx vercel
```

The frontend uses same-origin `/api` requests, so no localhost URL is required in production.

## Persistence

The included serverless API uses in-memory data so the project can deploy without native packages or database credentials. Vercel instances can restart, so records are not durable across cold starts. For production persistence, replace the state object in `api/index.js` with a managed database such as Neon, Supabase, or Vercel Postgres and configure its connection secret in the Vercel project settings.
