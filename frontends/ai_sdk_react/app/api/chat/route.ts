import { createOpenAICompatible } from "@ai-sdk/openai-compatible";
import { convertToModelMessages, streamText } from "ai";

const provider = createOpenAICompatible({
  name: "jazz",
  baseURL:
    process.env.BASE_URL ||
    "https://modal-labs-charles-dev--jazz-backend-server.us-east.modal.direct/v1",
});

export async function POST(req: Request) {
  const { messages } = await req.json();

  const result = streamText({
    model: provider.chatModel("llm"),
    messages: await convertToModelMessages(messages),
  });

  return result.toUIMessageStreamResponse();
}
