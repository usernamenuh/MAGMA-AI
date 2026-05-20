import { axiosInstance } from "../api/client.jsx";

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


export const fetchLogs = (page, limit) => {
    return axiosInstance.get("/logs", { params: { page, limit } });
};

export const scrapeData = (user_input, limit) => {
    return axiosInstance.get("/scrapping", { params: { user_input, limit } });
};
