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
                extractionDurationSeconds: item.extraction_duration_seconds,
                processingDurationSeconds: item.processing_duration_seconds,
                message: item.processing_message,
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

    const getDocumentDetails = useCallback(async (documentId, { silent = false } = {}) => {
        try {
            if (!silent) {
                setLoading(true);
                setError(null);
            }

            const res = await axiosInstance.get(`/knowledge/documents/${documentId}`);
            return res.data;

        } catch (err) {
            if (!silent) setError(err.response?.data || err.message);
            throw err;
        } finally {
            if (!silent) setLoading(false);
        }
    }, []);

    const getAnnotatedPdf = useCallback(async (documentId) => {
        const response = await axiosInstance.get(
            `/knowledge/documents/${documentId}/annotated-pdf`,
            { responseType: "blob" }
        );
        return {
            blob: response.data,
            pdfLetters: Number(response.headers["x-pdf-letters"]),
            storedLetters: Number(response.headers["x-stored-letters"]),
        };
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

    const retryDocument = useCallback(async (documentId, extractionMode = "auto") => {
        try {
            setLoading(true);
            setError(null);
            const res = await axiosInstance.post(
                `/knowledge/documents/${documentId}/retry`,
                null,
                { params: { extraction_mode: extractionMode } }
            );
            return res.data;
        } catch (err) {
            setError(err.response?.data || err.message);
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    const addManualText = useCallback(async (documentId, content, pageNumber) => {
        const res = await axiosInstance.post(
            `/knowledge/documents/${documentId}/manual-text`,
            { content, page_number: pageNumber }
        );
        return res.data;
    }, []);

    return {
        uploadChatKnowledgeBase,
        getDocuments,
        getDocumentDetails,
        getAnnotatedPdf,
        deleteDocument,
        retryDocument,
        addManualText,
        loading,
        error,
    };
}
