```bash
npm install
node index.mjs
```

Requires `LLM_BACKEND_URL` in the `process.env`
to point to your Modal-deployed OpenAI-compatible backend
(including `/v1` suffix).

You can add it via a `.env` file. Copy the `.env.example`
file and update the value of `LLM_BACKEND_URL`.
