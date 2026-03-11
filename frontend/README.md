# BSBI Frontend

React + Vite + TypeScript UI for the BSBI Document Intelligence Platform.

## Run

```bash
npm install
npm run dev
```

## Environment

Set API base URL if needed:

```bash
VITE_API_BASE_URL=http://localhost:8000
```

Default is same-origin (`""`). In dev mode, Vite proxies `/api` and `/health` to `http://localhost:8000`.

## Routes

- `/dashboard`
- `/upload`
- `/generate`
- `/outputs`
