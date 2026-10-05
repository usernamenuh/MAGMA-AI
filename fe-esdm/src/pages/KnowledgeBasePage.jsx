/* eslint-disable react-hooks/exhaustive-deps */
import React, { useEffect, useState, useMemo } from "react";
import {
    Box,
    Button,
    Typography,
    Tooltip,
    IconButton,
    Chip,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import InfoIcon from "@mui/icons-material/Info";
import ReplayIcon from "@mui/icons-material/Replay";
import { useKnowledgeBase } from "@/hooks/useKnowledgeBase";
import { useNavigate } from "react-router-dom";
import ReactTable from "@/components/ReactTable";
import {KNOWLEDGE_BASE} from "@/utils/routes.jsx";
import ConfirmationDialog from "@/components/ConfirmationDialog.jsx";
const ITEMS_PER_PAGE = 10;
const INITIAL_PAGE_INDEX = 0;

export default function KnowledgeBasePage() {
    const navigate = useNavigate();
    const { getDocuments, deleteDocument, retryDocument, loading } = useKnowledgeBase();
    const [confirmOpen, setConfirmOpen] = useState(false)
    const [deletedId, setDeletedId] = useState()
    const [documents, setDocuments] = useState([]);
    const [totalDocuments, setTotalDocuments] = useState(0);
    const [currentPageIndex, setCurrentPageIndex] = useState(INITIAL_PAGE_INDEX);

    useEffect(() => {
        fetchDocuments(currentPageIndex);
    }, [currentPageIndex]);

    useEffect(() => {
        const hasActiveProcessing = documents.some((document) => {
            const status = document.status?.toLowerCase();
            return status === "pending" || status === "queued" || status === "processing";
        });

        if (!hasActiveProcessing) return undefined;

        const timer = window.setTimeout(() => {
            fetchDocuments(currentPageIndex);
        }, 3000);

        return () => window.clearTimeout(timer);
    }, [documents, currentPageIndex]);


    const fetchDocuments = async (pageIndex) => {
        const page = pageIndex + 1;
        const limit = ITEMS_PER_PAGE;

        try {
            const data = await getDocuments({ page, limit });

            setDocuments(data.items);
            setTotalDocuments(data.total);

        } catch (err) {
            console.error("Failed to fetch documents:", err);
            setDocuments([]);
            setTotalDocuments(0);
        }
    };

    const onDelete = async () => {
        try {
            await deleteDocument(deletedId);
            await fetchDocuments(currentPageIndex);
        } catch (err) {
            console.error("Failed to delete document:", err);
        }
    };

    const handleDelete = (documentId) => {
        setDeletedId(documentId);
        setConfirmOpen(true);
    };

    const handleRetry = async (documentId) => {
        try {
            await retryDocument(documentId);
            await fetchDocuments(currentPageIndex);
        } catch (err) {
            console.error("Failed to retry document:", err);
        }
    };

    const navigateToUpload = () => {
        navigate(`${KNOWLEDGE_BASE}/upload`);
    };

    const navigateToDetail = (documentId) => {
        navigate(`${KNOWLEDGE_BASE}/documents/${documentId}`);
    };

    const handlePageChange = (newPageIndex) => {
        setCurrentPageIndex(newPageIndex);
    };


    const COLUMNS = useMemo(() => [
        {
            Header: 'ID',
            accessor: 'id',
            width: 80,
        },
        {
            Header: 'Dokumen',
            accessor: 'name',
            Cell: ({ value, row }) => (
                <Tooltip title={value}>
                    <Typography
                        onClick={() => navigateToDetail(row.original.id)}
                        sx={{
                            fontSize: 13,
                            fontWeight: 600,
                            color: '#243b53',
                            maxWidth: 440,
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            cursor: 'pointer',
                            '&:hover': { textDecoration: 'underline' }
                        }}
                    >
                        {value}
                    </Typography>
                </Tooltip>
            ),
        },
        {
            Header: 'Status',
            accessor: 'status',
            Cell: ({ value }) => {
                const status = (value || '').toLowerCase();
                const tone = status === 'completed' ? { label: 'Selesai', bg: '#eaf7ef', color: '#1f7a3d' }
                    : status === 'incomplete' ? { label: 'Kurang lengkap', bg: '#fff4dc', color: '#9a6700' }
                    : status === 'failed' ? { label: 'Gagal', bg: '#fcebec', color: '#b4232c' }
                        : { label: value || 'Diproses', bg: '#fff4dc', color: '#9a6700' };
                return <Chip label={tone.label} size="small" sx={{ height: 24, fontSize: 11, fontWeight: 700, bgcolor: tone.bg, color: tone.color, borderRadius: 1.25 }} />;
            },
        },
        {
            Header: 'Halaman',
            accessor: 'totalPages',
        },
        {
            Header: 'Durasi',
            accessor: 'processingDurationSeconds',
            Cell: ({ value }) => {
                if (value === null || value === undefined) return '—';
                if (value < 1) return `${Math.round(value * 1000)} ms`;
                return `${value.toFixed(2)} s`;
            },
        },
        {
            Header: 'Keterangan',
            accessor: 'message',
            Cell: ({ value }) => (
                <Tooltip title={value || ''}>
                    <Typography
                        sx={{
                            fontSize: 13,
                            color: '#607080',
                            maxWidth: 280,
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                        }}
                    >
                        {value || '—'}
                    </Typography>
                </Tooltip>
            ),
        },
        {
            Header: 'Aksi',
            id: 'actions',
            Cell: ({ row }) => (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    {row.original.status?.toLowerCase() === 'failed' && (
                        <Tooltip title="Retry processing">
                            <IconButton size="small" onClick={() => handleRetry(row.original.id)} sx={{ bgcolor: '#edf5ff', '&:hover': { bgcolor: '#dcecff' } }}>
                                <ReplayIcon fontSize="small" color="primary" />
                            </IconButton>
                        </Tooltip>
                    )}
                    <Tooltip title="View Details">
                        <IconButton size="small" onClick={() => navigateToDetail(row.original.id)} sx={{ bgcolor: '#f1f3f5', '&:hover': { bgcolor: '#e3e7eb' } }}>
                            <InfoIcon fontSize="small" />
                        </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete">
                        <IconButton size="small" onClick={() => handleDelete(row.original.id)} sx={{ bgcolor: '#fff0f0', '&:hover': { bgcolor: '#ffe0e0' } }}>
                            <DeleteIcon fontSize="small" color="error" />
                        </IconButton>
                    </Tooltip>
                </Box>
            ),
        },
    ], [currentPageIndex]);


    return (
        <Box sx={{  pt: 5,
            flex: 1,
            px: 4,
            pb: 10,
            display: "flex",
            flexDirection: "column",
            height: "100%",
            minHeight: 0,
            boxSizing: "border-box",
            bgcolor: "#fbfbfb",
            color: "#000000",
            overflowY: "auto",
            overflowX: "hidden" }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2} gap={2} flexWrap="wrap">
                <Box>
                    <Typography variant="h5" fontWeight={700} sx={{ color: '#1f2933' }}>
                        Knowledge Base Documents
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                        List of documents used as reference sources.
                    </Typography>
                </Box>
                <Button
                    variant="contained"
                    onClick={navigateToUpload}
                    startIcon={<CloudUploadIcon />}
                    sx={{ bgcolor: "#00B473", textTransform: "none", borderRadius: 2, px: 2, boxShadow: 'none', '&:hover': { bgcolor: '#009761', boxShadow: 'none' } }}
                >
                    Upload Document
                </Button>
            </Box>

            <Box sx={{ mt: 3, pb: 2 }}>
                <ReactTable
                    data={documents}
                    columns={COLUMNS}
                    count={ITEMS_PER_PAGE}
                    total={totalDocuments}
                    gotoPage={handlePageChange}
                    loading={loading}
                />
            </Box>
            <ConfirmationDialog
                children={"Are you sure you want to delete this document?"}
                open={confirmOpen}
                onClose={() => setConfirmOpen(false)}
                onOk={onDelete}
                onCancel={() => setConfirmOpen(false)}
                okText={"Delete"}
                cancelText="Cancel"
            />
        </Box>
    );
}
