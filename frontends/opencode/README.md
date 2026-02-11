# OpenCode frontends

## Running OpenCode against a Modal-hosted LLM

Copy the sample `opencode` config.

```bash
cp sample.opencode.json opencode.json
```

Then add your API key to your environment variables
under the name `LLM_BACKEND_API_KEY`
while running `opencode`, e.g.

```bash
LLM_BACKEND_API_KEY=your-key-here opencode
```

and you should see "GLM-5 Modal" as the model name.

## Running OpenCode on Modal

You can also run OpenCode in a Modal Sandbox
to isolate the agent -- especially nice for background agents
or running many agents in parallel.

In an environment with `modal` installed, run the provided script

```bash
python opencode_server.py
```

And follow the printed instructions.
The Sandbox will include the Modal Examples repo,
but you can pass a different repo via the CLI.
Pass `--help` to see configuration options.

Note that by default, the agent will be able to access your Modal credentials.

If you include an `opencode.json` file in this directory,
for instance set up to hit your Modal-hosted LLM,
it will be used to configure the remote OpenCode agent.
