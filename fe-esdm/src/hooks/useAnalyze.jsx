import { axiosInstance } from "../api/client.jsx";

export const DEFAULT_CHAT_MODELS = [
    { id: "groq:qwen/qwen3.8-27b", label: "Groq — Qwen 3.8 27B (Sangat Cepat)" },
    { id: "groq:openai/gpt-oss-120b", label: "Groq — GPT-OSS 120B" },
    { id: "local", label: "Qwen2.5 1.5B Q4 — Local" },
    { id: "openrouter:openrouter/free", label: "OpenRouter Free — Otomatis" },
];

const wait = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

const requestWithStartupRetry = async (request, attempts = 12) => {
    let lastError;
    for (let attempt = 0; attempt < attempts; attempt += 1) {
        try {
            return await request();
        } catch (error) {
            lastError = error;
            const status = error?.response?.status;
            const retryable = !status || status >= 500;
            if (!retryable || attempt === attempts - 1) throw error;
            await wait(Math.min(1000 * (attempt + 1), 5000));
        }
    }
    throw lastError;
};

export const analyzeChat = (payload) => {
    return axiosInstance.post("/analyze", payload);
};

export const analyzeChatEn = (payload) => {
    return axiosInstance.post("/analyze/en", payload);
};

export const analyzeChatKnowledgeBase= (payload) => {
    return axiosInstance.post("/knowledge/analyze", payload);
};

export const analyzeChatKnowledgeBaseEn= (payload) => {
    return axiosInstance.post("/knowledge/analyze-en", payload);
};

export const getChatModels = () => requestWithStartupRetry(
    () => axiosInstance.get("/knowledge/models")
);

export const getKnowledgeDocuments = () => requestWithStartupRetry(
    () => axiosInstance.get(
        "/knowledge/documents",
        { params: { page: 1, limit: 1000 } }
    )
);

export const fetchLogs = (page, limit) => {
    return axiosInstance.get("/logs", { params: { page, limit } });
};

export const scrapeData = (user_input, limit) => {
    return axiosInstance.get("/scrapping", { params: { user_input, limit } });
};
