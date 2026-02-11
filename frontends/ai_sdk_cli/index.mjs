import { config } from "dotenv";
import { createOpenAICompatible } from "@ai-sdk/openai-compatible";
import { streamText } from "ai";

config();

const panic = (msg) => { throw new Error(msg) };

const provider = createOpenAICompatible({
  name: "jazz",
  baseURL:
    process.env.LLM_BACKEND_URL ?? panic("provide an LLM_BACKEND_URL"),
  apiKey: process.env.LLM_BACKEND_API_KEY ?? "",
});

const result = streamText({
  model: provider.chatModel("zai-org/GLM-5-FP8"),
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
