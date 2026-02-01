import { createOpenAICompatible } from "@ai-sdk/openai-compatible";
import { streamText } from "ai";

const provider = createOpenAICompatible({
  name: "jazz",
  baseURL:
    process.env.BASE_URL ||
    "https://modal-labs-charles-dev--jazz-backend-server.us-east.modal.direct/v1",
});

const result = streamText({
  model: provider.chatModel("llm"),
  messages: [
    { role: "system", content: "You are a helpful AI assistant." },
    { role: "user", content: process.argv[2] || "What is the capital of France?" },
  ],
});

let inReasoning = false;

for await (const part of result.fullStream) {
  if (part.type === "reasoning-delta") {
    if (!inReasoning) {
      inReasoning = true;
      process.stderr.write("\x1b[2m"); // dim
    }
    process.stderr.write(part.text);
  } else if (part.type === "text-delta") {
    if (inReasoning) {
      inReasoning = false;
      process.stderr.write("\x1b[0m\n"); // reset + newline
    }
    process.stdout.write(part.text);
  }
}

if (inReasoning) process.stderr.write("\x1b[0m");
console.log();
