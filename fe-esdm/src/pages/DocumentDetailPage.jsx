import React, { useEffect, useState } from "react";
import {
    Box,
    Typography,
    Paper,
    Button,
    CircularProgress,
    Alert,
} from "@mui/material";
import { ArrowBack } from "@mui/icons-material";
import { useParams, useNavigate } from "react-router-dom";
import { useKnowledgeBase } from "@/hooks/useKnowledgeBase";

export default function DocumentDetailPage() {
    const { documentId } = useParams();
    const navigate = useNavigate();
    const { getDocumentDetails, loading, error } = useKnowledgeBase();
    const [document, setDocument] = useState(null);
    const [chunks, setChunks] = useState([]);

    useEffect(() => {
        fetchDocumentDetails();
    }, [documentId]);

    const fetchDocumentDetails = async () => {
        try {
            const data = await getDocumentDetails(documentId);
            setDocument(data.document);
            setChunks(data.chunks);
        } catch (err) {
            console.error("Failed to fetch document details:", err);
            setDocument(null);
            setChunks([]);
        }
    };

    const formatStatus = (status) => status ? status.toUpperCase() : 'N/A';

    return (
        <Box sx={{
            pt: 5,
            flex: 1,
            px: 4,
            display: "flex",
            flexDirection: "column",
            height: "100%",
            bgcolor: "#fbfbfb",
            color: "#000000",
        }}>
            <Button startIcon={<ArrowBack />} onClick={() => navigate(-1)} sx={{ mb: 2, textTransform: 'none' }}>
                Back to List
            </Button>
            <Typography variant="h5" fontWeight={600} sx={{ mt: 1 }}>
                Document Detail: {document?.filename || documentId}
            </Typography>
            <Typography variant="body2" color="text.secondary" mb={3}>
                Detailed information about the uploaded document and its processing.
            </Typography>

            <Paper sx={{ p: 4 }}>
                {loading && (
                    <Box display="flex" justifyContent="center" py={4}>
                        <CircularProgress />
                    </Box>
                )}
                {error && (
                    <Alert severity="error" sx={{ mb: 2 }}>
                        Error loading details: {error.message || String(error)}
                    </Alert>
                )}

                {document && (
                    <Box>
                        <Typography variant="h6" gutterBottom>
                            {document.filename}
                        </Typography>
                        <Typography variant="body1" mb={1}>
                            Document ID: {document.id}
                        </Typography>
                        <Typography variant="body1" mb={1}>
                            File Path: {document.file_path}
                        </Typography>
                        <Typography variant="body1" mb={1}>
                            Processing Status: <Box component="span" fontWeight="bold">{formatStatus(document.status)}</Box>
                        </Typography>
                        <Typography variant="body1" mb={1}>
                            Total Pages: {document.total_pages}
                        </Typography>

                        <Box mt={4}>
                            <Typography variant="h6" fontWeight="bold" borderBottom={1} pb={1} mb={2}>
                                Data Chunks ({chunks.length})
                            </Typography>

                            {chunks.length > 0 ? (
                                <>
                                    <Typography variant="subtitle1" color="text.secondary">
                                        Showing 3 Top Chunk Samples:
                                    </Typography>
                                    {chunks.slice(0, 3).map((chunk, index) => (
                                        <Paper key={index} variant="outlined" sx={{ mt: 2, p: 2, bgcolor: '#f9f9f9', overflow: 'hidden' }}>
                                            <Typography variant="caption" color="text.secondary" fontWeight="bold">
                                                Page {chunk.page_number} / Chunk Index {chunk.chunk_index}
                                            </Typography>
                                            <Typography variant="body2" sx={{ mt: 0.5, whiteSpace: 'pre-wrap' }}>
                                                {chunk.content}
                                            </Typography>
                                            <Typography variant="caption" color="primary" sx={{ display: 'block', mt: 1 }}>
                                                Embedding ID: {chunk.embedding_id}
                                            </Typography>
                                        </Paper>
                                    ))}
                                </>
                            ) : (
                                <Typography color="text.secondary">
                                    No chunk data found or the document is still being processed.
                                </Typography>
                            )}
                        </Box>
                    </Box>
                )}

                {!loading && !document && !error && (
                    <Typography align="center" py={4} color="text.secondary">
                        Document not found or failed to load.
                    </Typography>
                )}
            </Paper>
        </Box>
    );
}