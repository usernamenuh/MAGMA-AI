import React, { useEffect, useState, useMemo } from "react";
import {
    Box,
    Button,
    Typography,
    Tooltip,
    IconButton,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import InfoIcon from "@mui/icons-material/Info";
import { useKnowledgeBase } from "@/hooks/useKnowledgeBase";
import { useNavigate } from "react-router-dom";
import ReactTable from "@/components/ReactTable";
import {KNOWLEDGE_BASE} from "@/utils/routes.jsx";
import ConfirmationDialog from "@/components/ConfirmationDialog.jsx";
const ITEMS_PER_PAGE = 10;
const INITIAL_PAGE_INDEX = 0;

export default function KnowledgeBasePage() {
    const navigate = useNavigate();
    const { getDocuments, deleteDocument, loading } = useKnowledgeBase();
    const [confirmOpen, setConfirmOpen] = useState(false)
    const [deletedId, setDeletedId] = useState()
    const [documents, setDocuments] = useState([]);
    const [totalDocuments, setTotalDocuments] = useState(0);
    const [currentPageIndex, setCurrentPageIndex] = useState(INITIAL_PAGE_INDEX);

    useEffect(() => {
        fetchDocuments(currentPageIndex);
    }, [currentPageIndex]);


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
            Header: 'File Name',
            accessor: 'name',
            Cell: ({ value, row }) => (
                <Tooltip title={value}>
                    <Typography
                        onClick={() => navigateToDetail(row.original.id)}
                        sx={{
                            fontSize: 14,
                            maxWidth: 500,
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
            Cell: ({ value }) => (
                <Box component="span" fontWeight="bold" sx={{ color: value.toLowerCase() === 'completed' ? 'success.main' :  value.toLowerCase() === 'failed' ? 'error.main': 'warning.main' }}>
                    {value.toUpperCase()}
                </Box>
            ),
        },
        {
            Header: 'Pages',
            accessor: 'totalPages',
        },
        {
            Header: 'Actions',
            id: 'actions',
            Cell: ({ row }) => (
                <Box>
                    <Tooltip title="View Details">
                        <IconButton size="small" onClick={() => navigateToDetail(row.original.id)}>
                            <InfoIcon fontSize="small" />
                        </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete">
                        <IconButton size="small" onClick={() => handleDelete(row.original.id)} sx={{ ml: 1 }}>
                            <DeleteIcon fontSize="small" color="error" />
                        </IconButton>
                    </Tooltip>
                </Box>
            ),
        },
    ], []);


    return (
        <Box sx={{  pt: 5,
            flex: 1,
            px: 4,
            pb: 10,
            display: "flex",
            flexDirection: "column",
            height: "100vh",
            bgcolor: "#fbfbfb",
            color: "#000000",
            overflow: "hidden" }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Box>
                    <Typography variant="h5" fontWeight={600}>
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
                    sx={{ bgcolor: "#00B473", textTransform: "none" }}
                >
                    Upload Document
                </Button>
            </Box>

            <Box sx={{ mt: 3 }}>
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