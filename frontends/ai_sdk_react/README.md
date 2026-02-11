```bash
npm install
npm run dev
npm run build
npm run deploy  # uses vercel
```

Requires `LLM_BACKEND_URL` in the `process.env`
to point to the Modal-deployed OpenAI-compatible backend
(including `/v1` suffix).

To activate web search, add an API key for
[Tavily](https://www.tavily.com/)
in the `process.env` under `TAVILY_API_KEY`.

When using Vercel, those can be added with

```bash
vercel env add LLM_BACKEND_URL
vercel env add LLM_BACKEND_API_KEY
vercel env add TAVILY_API_KEY
```
