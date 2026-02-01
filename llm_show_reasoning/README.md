```bash
uv tool install --with llm-uv-tool llm
```

```bash
# from this plugin repo
uv build
llm install dist/llm_show_reasoning-0.1.0-py3-none-any.whl
```

```bash
# test
llm plugins # has llm-show-reasoning
llm models  # has JazzReasoning
llm -m jazz hey  # shows reasoning in gray
```
