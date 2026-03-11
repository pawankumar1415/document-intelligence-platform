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

- `/login`
- `/dashboard`
- `/upload`
- `/generate`
- `/outputs`

All routes except `/login` are protected and redirect to login when no token is present.

## Provider Switch

Use the top navigation provider selector to switch generation backend:

- OpenAI
- Groq
- Azure OpenAI

The selected provider is passed to backend parse/generate APIs.
