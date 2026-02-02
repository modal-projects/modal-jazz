```bash
npm install
npm run dev
npm run build
npm run deploy
```

Requires `LLM_BACKEND_URL` in the `process.env`
to point to your Modal-deployed OpenAI-compatible backend
(including `/v1` suffix).

When using Vercel, that can be added with

```bash
vercel env add LLM_BACKEND_URL
```
