import { axiosInstance } from "../api/client.jsx";
import { useCallback, useState } from "react";

export function useKnowledgeBase() {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const uploadChatKnowledgeBase = useCallback(async (formData, onProgress) => {
        try {
            setLoading(true);
            setError(null);

            const res = await axiosInstance.post("/knowledge/upload", formData, {
                headers: { "Content-Type": "multipart/form-data" },
                onUploadProgress: (ev) => {
                    if (onProgress) {
                        const percent = Math.round((ev.loaded / ev.total) * 100);
                        onProgress(percent);
                    }
                }
            });

            return res;

        } catch (err) {
            setError(err.response?.data || err.message);
            throw err;

        } finally {
            setLoading(false);
        }
    }, []);

    const getDocuments = useCallback(async ({ page, limit }) => {
        try {
            setLoading(true);
            setError(null);

            const res = await axiosInstance.get("/knowledge/documents", {
                params: { page, limit }
            });

            const apiData = res.data;

            const documents = apiData.items.map(item => ({
                id: item.id,
                name: item.filename,
                status: item.processing_status,
                totalPages: item.total_pages,
            }));

            return {
                items: documents,
                total: apiData.total,
            };

        } catch (err) {
            setError(err.response?.data || err.message);
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    const getDocumentDetails = useCallback(async (documentId) => {
        try {
            setLoading(true);
            setError(null);

            const res = await axiosInstance.get(`/knowledge/documents/${documentId}`);
            return res.data;

        } catch (err) {
            setError(err.response?.data || err.message);
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    const deleteDocument = useCallback(async (documentId) => {
        try {
            setLoading(true);
            setError(null);

            await axiosInstance.delete(`/knowledge/documents/${documentId}`);
            return true;

        } catch (err) {
            setError(err.response?.data || err.message);
            throw err;

        } finally {
            setLoading(false);
        }
    }, []);

    return {
        uploadChatKnowledgeBase,
        getDocuments,
        getDocumentDetails,
        deleteDocument,
        loading,
        error,
    };
}
