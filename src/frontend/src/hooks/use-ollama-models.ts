/**
 * Custom React hook that loads the Ollama models available to the chatbot.
 */

import { useEffect, useState } from "react";

import { getOllamaModels } from "@/api/ollama";

export function useOllamaModels() {
  const [models, setModels] = useState<string[]>([]);
  const [defaultModel, setDefaultModel] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    getOllamaModels(controller.signal)
      .then((data) => {
        setModels(data.models);
        setDefaultModel(data.default);
      })
      .catch(() => {
        // chat still works with the backend's default model; the picker just stays hidden
      });

    return () => controller.abort();
  }, []);

  return { models, defaultModel };
}
