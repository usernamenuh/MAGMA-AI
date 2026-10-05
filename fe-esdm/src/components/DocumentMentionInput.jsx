import React, { useMemo, useRef, useState } from "react";
import { Box, Chip, Paper, Popper, TextField, Typography } from "@mui/material";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";

export default function DocumentMentionInput({
    prompt,
    setPrompt,
    documents,
    selectedDocumentIds,
    setSelectedDocumentIds,
    disabled,
    onSend,
    enabled,
    placeholder = "Tanyakan sesuatu...",
}) {
    const [cursorPosition, setCursorPosition] = useState(0);
    const [highlightedIndex, setHighlightedIndex] = useState(0);
    const inputContainerRef = useRef(null);

    const mention = useMemo(() => {
        if (!enabled) return null;
        const beforeCursor = prompt.slice(0, cursorPosition);
        const atIndex = beforeCursor.lastIndexOf("@");
        if (atIndex < 0) return null;
        const query = beforeCursor.slice(atIndex + 1);
        if (query.includes("\n") || query.length > 120) return null;
        const completedMention = documents.some((document) =>
            query.startsWith(`${document.filename} `)
        );
        if (completedMention) return null;
        return { atIndex, query };
    }, [documents, enabled, prompt, cursorPosition]);

    const matches = useMemo(() => {
        if (!mention) return [];
        const query = mention.query.trim().toLowerCase();
        return documents
            .filter((document) => !query || document.filename.toLowerCase().includes(query))
            .slice(0, 8);
    }, [documents, mention]);

    const syncSelectedDocuments = (nextPrompt) => {
        const ids = documents
            .filter((document) => nextPrompt.includes(`@${document.filename}`))
            .map((document) => document.id);
        setSelectedDocumentIds(ids);
    };

    const handleChange = (event) => {
        const nextPrompt = event.target.value;
        setPrompt(nextPrompt);
        setCursorPosition(event.target.selectionStart ?? nextPrompt.length);
        setHighlightedIndex(0);
        syncSelectedDocuments(nextPrompt);
    };

    const selectDocument = (document) => {
        if (!mention) return;
        const suffix = prompt.slice(cursorPosition);
        const nextPrompt = `${prompt.slice(0, mention.atIndex)}@${document.filename} ${suffix}`;
        const nextCursor = mention.atIndex + document.filename.length + 2;
        setPrompt(nextPrompt);
        setSelectedDocumentIds((current) => [...new Set([...current, document.id])]);
        setCursorPosition(nextCursor);
        setHighlightedIndex(0);
    };

    const removeDocument = (documentId) => {
        const document = documents.find((item) => item.id === documentId);
        if (!document) return;
        const nextPrompt = prompt.replaceAll(`@${document.filename}`, "").replace(/\s{2,}/g, " ");
        setPrompt(nextPrompt.trimStart());
        setSelectedDocumentIds((current) => current.filter((id) => id !== documentId));
    };

    const handleKeyDown = (event) => {
        if (mention && matches.length) {
            if (event.key === "ArrowDown") {
                event.preventDefault();
                setHighlightedIndex((current) => (current + 1) % matches.length);
                return;
            }
            if (event.key === "ArrowUp") {
                event.preventDefault();
                setHighlightedIndex((current) => (current - 1 + matches.length) % matches.length);
                return;
            }
            if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                selectDocument(matches[highlightedIndex] || matches[0]);
                return;
            }
            if (event.key === "Escape") {
                setCursorPosition(-1);
                return;
            }
        }
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            onSend();
        }
    };

    return (
        <Box ref={inputContainerRef} sx={{ position: "relative", width: "100%" }}>
            <Popper open={Boolean(mention)} anchorEl={inputContainerRef.current} placement="bottom-start"
                modifiers={[{ name: "offset", options: { offset: [0, 8] } }, { name: "flip", options: { fallbackPlacements: ["top-start"] } }, { name: "preventOverflow", options: { padding: 12 } }]}
                sx={{ zIndex: 1400 }}>
                <Paper elevation={5}
                    sx={{
                        width: "min(440px, calc(100vw - 32px))",
                        maxHeight: "min(300px, 45vh)",
                        overflowY: "auto",
                        border: "1px solid #e3e8ed",
                        borderRadius: 2.5,
                        p: 0.75,
                    }}
                >
                    {matches.length ? matches.map((document, index) => (
                        <Box
                            key={document.id}
                            onMouseDown={(event) => {
                                event.preventDefault();
                                selectDocument(document);
                            }}
                            sx={{
                                px: 1.5, py: 1.1, display: "flex", alignItems: "center", gap: 1.25,
                                cursor: "pointer",
                                borderRadius: 1.5,
                                bgcolor: index === highlightedIndex ? "#f0f3f6" : "#fff",
                                "&:hover": { bgcolor: "#f0f3f6" },
                            }}
                        >
                            <DescriptionOutlinedIcon sx={{ color: "#607d98", fontSize: 20 }} />
                            <Box sx={{ minWidth: 0 }}>
                                <Typography variant="body2" fontWeight={600} noWrap>{document.filename}</Typography>
                                <Typography variant="caption" color="text.secondary">Tekan Enter untuk memilih</Typography>
                            </Box>
                        </Box>
                    )) : (
                        <Typography variant="body2" color="text.secondary" sx={{ p: 2 }}>
                            Dokumen tidak ditemukan
                        </Typography>
                    )}
                </Paper>
            </Popper>

            {enabled && selectedDocumentIds.length > 0 && (
                <Box sx={{ display: "flex", gap: 0.75, flexWrap: "wrap", px: 2, pt: 1 }}>
                    {selectedDocumentIds.map((id) => {
                        const document = documents.find((item) => item.id === id);
                        return document ? (
                            <Chip
                                key={id}
                                size="small"
                                label={document.filename}
                                onDelete={() => removeDocument(id)}
                                icon={<DescriptionOutlinedIcon />}
                                sx={{ maxWidth: { xs: 230, sm: 420 }, bgcolor: "#eaf1f7", color: "#233c5a", "& .MuiChip-label": { overflow: "hidden", textOverflow: "ellipsis" } }}
                            />
                        ) : null;
                    })}
                </Box>
            )}

            <TextField
                fullWidth
                variant="outlined"
                multiline
                maxRows={5}
                placeholder={enabled ? "Ketik @ untuk memilih dokumen..." : placeholder}
                value={prompt}
                onChange={handleChange}
                onClick={(event) => setCursorPosition(event.target.selectionStart ?? prompt.length)}
                onKeyUp={(event) => {
                    if (!["ArrowDown", "ArrowUp", "Enter", "Escape"].includes(event.key)) {
                        setCursorPosition(event.target.selectionStart ?? prompt.length);
                    }
                }}
                onKeyDown={handleKeyDown}
                disabled={disabled}
                sx={{
                    "& .MuiOutlinedInput-root": {
                        bgcolor: "#ffffff",
                        color: "#272727",
                        borderRadius: 4,
                        px: 2,
                        py: 0,
                        minHeight: 50,
                        alignItems: "center",
                        "& fieldset": { border: "none" },
                        "&:hover fieldset": { border: "none" },
                        "&.Mui-focused fieldset": { border: "none" },
                    },
                }}
            />
        </Box>
    );
}
