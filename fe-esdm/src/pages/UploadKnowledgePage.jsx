import React, { useEffect, useState } from "react";
import {
    Box,
    Button,
    Typography,
    Paper,
    IconButton,
    LinearProgress, Alert,
    FormControl,
    InputLabel,
    MenuItem,
    Select,
} from "@mui/material";
import { Cloud, CheckCircle, AccessTime, Error, ArrowBack } from "@mui/icons-material";
import DeleteIcon from "@mui/icons-material/Delete";
import { useKnowledgeBase } from "@/hooks/useKnowledgeBase";
import { useNavigate } from "react-router-dom";
import {KNOWLEDGE_BASE} from "@/utils/routes.jsx"; // Assuming react-router-dom for navigation

const LS_KEY = "kb_upload_progress";
const saveToStorage = (files) =>
    localStorage.setItem(LS_KEY, JSON.stringify(files));
const loadFromStorage = () =>
    JSON.parse(localStorage.getItem(LS_KEY) || "[]");

export default function UploadKnowledgePage() {
    const navigate = useNavigate();
    const [dragActive, setDragActive] = useState(false);
    const { uploadChatKnowledgeBase } = useKnowledgeBase();
    const [trainingFiles, setTrainingFiles] = useState(loadFromStorage());
    const [uploadError, setUploadError] = useState(null);
    const [extractionMode, setExtractionMode] = useState("auto");
    const MAX_FILE_SIZE_MB = 50;
    const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;
    const ALLOWED_MIMES = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"];
    const ALLOWED_EXTENSIONS = [".pdf", ".docx", ".doc"];

    useEffect(() => {
        saveToStorage(trainingFiles);
    }, [trainingFiles]);

    const handleDragOver = (e) => {
        e.preventDefault();
        setDragActive(true);
    };
    const validateFiles = (fileList) => {
        setUploadError(null);
        let validFiles = [];
        let errorMessages = [];

        for (const file of fileList) {
            const fileExtension = file.name.split('.').pop().toLowerCase();
            const isAllowedType = ALLOWED_MIMES.includes(file.type) || ALLOWED_EXTENSIONS.includes(`.${fileExtension}`);
            const isUnderSize = file.size <= MAX_FILE_SIZE_BYTES;

            if (!isAllowedType) {
                errorMessages.push(`File "${file.name}" has an unsupported format. Only PDF and DOCX are allowed.`);
            } else if (!isUnderSize) {
                errorMessages.push(`File "${file.name}" exceeds the maximum size of ${MAX_FILE_SIZE_MB}MB.`);
            } else {
                validFiles.push(file);
            }
        }

        if (errorMessages.length > 0) {
            setUploadError(errorMessages.join('\n'));
        }

        return validFiles;
    };
    const handleDragLeave = () => setDragActive(false);

    const handleDropSource = (e) => {
        e.preventDefault();
        setDragActive(false);

        const droppedFiles = Array.from(e.dataTransfer.files);
        const filesToAttach = validateFiles(droppedFiles);

        attachFiles(filesToAttach);
    };

    const handleFileUpload = (e) => {
        const selectedFiles = Array.from(e.target.files);
        const filesToAttach = validateFiles(selectedFiles);

        attachFiles(filesToAttach);
    };


    const attachFiles = (files) => {
        setTrainingFiles((prev) => {
            const existingNames = new Set(prev.map((f) =>

                f.name));

            const mapped = files
                .filter((f) => !existingNames.has(f.name))
                .map((file) => ({
                    name: file.name,
                    file,
                    status: "pending",
                    progress: 0,
                }));

            return [...prev, ...mapped];
        });
    };

    const removeAttachedFile = (name) => {
        setTrainingFiles((prev) => {
            const updated = prev.filter((f) => f.name !== name);
            saveToStorage(updated);
            return updated;
        });
    };


    const handleSubmit = async () => {
        for (const item of trainingFiles) {
            if (item.status === "success") continue;

            await uploadSingleFile(item);
        }
        localStorage.removeItem(LS_KEY)
        navigate(KNOWLEDGE_BASE);
    };

    const uploadSingleFile = async (fileItem) => {
        const formData = new FormData();
        formData.append("file", fileItem.file);
        formData.append("extraction_mode", extractionMode);

        updateStatus(fileItem.name, { status: "uploading" });

        try {
            const res = await uploadChatKnowledgeBase(formData);

            updateStatus(fileItem.name, {
                status: "pending",
                documentId: res.document_id
            });
        } catch {
            updateStatus(fileItem.name, { status: "error" });
        }
    };


    const updateStatus = (fileName, update) => {
        setTrainingFiles((prev) =>
            prev.map((item) =>
                item.name === fileName ? { ...item, ...update } : item
            )
        );
    };


    const renderStatusIcon = (status) => {
        if (status === "success")
            return <CheckCircle sx={{ color: "green", ml: 1 }} fontSize="small" />;

        if (status === "uploading")
            return <AccessTime sx={{ color: "grey", ml: 1 }} fontSize="small" />;

        if (status === "error")
            return <Error sx={{ color: "red", ml: 1 }} fontSize="small" />;

        return null;
    };

    return (
        <Box sx={{  pt: 5,
            flex: 1,
            px: 4,
            display: "flex",
            flexDirection: "column",
            height: "100%",
            minHeight: 0,
            boxSizing: "border-box",
            bgcolor: "#fbfbfb",
            color: "#000000",
            overflowY: "auto",
            overflowX: "hidden", }}>
            <Button startIcon={<ArrowBack />} onClick={() => navigate(-1)} sx={{ mb: 2, textTransform: 'none' }}>
                Back to Documents
            </Button>
            <Typography variant="h5" fontWeight={600} sx={{ mt: 1 }}>
                Upload New Documents
            </Typography>
            <Typography variant="body2" color="text.secondary">
                Upload your documents to include them as reference sources.
            </Typography>
            <FormControl sx={{ mt: 3, maxWidth: 460 }} size="small">
                <InputLabel id="extraction-mode-label">Document Processing Method</InputLabel>
                <Select
                    labelId="extraction-mode-label"
                    value={extractionMode}
                    label="Document Processing Method"
                    onChange={(event) => setExtractionMode(event.target.value)}
                >
                    <MenuItem value="auto">Automatic — PyPDF2, fallback to OCR</MenuItem>
                    <MenuItem value="text">PyPDF2 only — digital PDF</MenuItem>
                    <MenuItem value="docling_no_ocr">Docling without OCR — digital PDF with complex layout</MenuItem>
                    <MenuItem value="ocr">Docling + OCR — scanned/complex PDF</MenuItem>
                </Select>
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
                    Automatic checks the text layer first and only runs OCR when needed.
                </Typography>
            </FormControl>
            {uploadError && (
                <Alert severity="error" sx={{ mt: 3, whiteSpace: 'pre-wrap' }}>
                    {uploadError}
                </Alert>
            )}
            <Paper
                sx={{
                    mt: 5,
                    p: 4,
                    textAlign: "center",
                    border: dragActive ? "2px dashed #1976d2" : "2px dashed #ccc",
                    bgcolor: dragActive ? "#e3f2fd" : "inherit",
                    cursor: "pointer",
                }}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDropSource}
            >
                <Cloud sx={{ fontSize: 48, color: dragActive ? "#1976d2" : "#ccc" }} />
                <Typography>Drag and drop your document file here</Typography>
                <Typography variant="caption" color="text.secondary">
                    Maximum file size: 50MB (PDF, DOCX only)
                </Typography>

                <Button variant="outlined" component="label" sx={{ mt: 2, display: "block", mx: "auto" }} >
                    Browse files
                    <input
                        type="file"
                        accept=".pdf,.docx,.doc"
                        hidden
                        onChange={handleFileUpload}
                    />
                </Button>
            </Paper>

            {trainingFiles.length > 0 && (
                <Paper sx={{ p: 2, mt: 3 }}>
                    <Typography variant="subtitle1">Attached Files</Typography>

                    {trainingFiles.map((item) => (
                        <Box key={item.name} sx={{ mt: 1 }}>
                            <Box display="flex" alignItems="center" justifyContent="space-between">
                                <Box display="flex" alignItems="center">
                                    <Typography>{item.name}</Typography>
                                    {renderStatusIcon(item.status)}
                                </Box>

                                <IconButton size="small" onClick={() => removeAttachedFile(item.name)}>
                                    <DeleteIcon fontSize="small" />
                                </IconButton>
                            </Box>

                            {item.status !== "pending" && (
                                <LinearProgress
                                    variant="determinate"
                                    value={item.progress}
                                    sx={{ mt: 1 }}
                                />
                            )}
                        </Box>
                    ))}
                </Paper>
            )}

            <Button
                variant="contained"
                onClick={handleSubmit}
                disabled={trainingFiles.every(f => f.status === "success" || f.status === "uploading")}
                sx={{ mt: 3, bgcolor: "#00B473", textTransform: "none" }}
            >
                Upload Files ({trainingFiles.filter(f => f.status === "pending" || f.status === "error").length})
            </Button>
        </Box>
    );
}
