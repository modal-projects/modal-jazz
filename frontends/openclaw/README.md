Add the contents of the `models` key of the `sample.openclaw.json` to your `openclaw.json`
-- by default, this is stored in `~/.openclaw`.

Update the `LLM_BACKEND_URL` to the URL of your Modal-hosted LLM.
If you set up an `LLM_BACKEND_API_KEY`, add that as well.
You can enter them directly in the `openclaw.json` file
or set them via environment variables, e.g. by copying
`.env.example` to a file called `.env` in the folder you
are running `openclaw` from.

To test the model setup, run

```bash
openclaw models status --probe
```

You can then select it from the model picker
or use it as your default model with

```bash
openclaw models set modal-jazz/llm
```

And run a quick end-to-end check with

```bash
openclaw tui
```
