import React, {useState} from "react";
import {Box, Button, Card, CardContent, Collapse, IconButton, Tooltip, Typography} from "@mui/material";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import MoreVertIcon from "@mui/icons-material/MoreVert";
import MarkdownRenderer from "@/components/MarkdownRenderer.jsx";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import AccountCircleIcon from "@mui/icons-material/AccountCircle";
import AssistantIcon from "../assets/logo-esdm.png";
import {BASE_URL} from "@/utils/constants.jsx";

export default function ChatMessageKnowledge({ role, content, references=[] }) {
    const isUser = role === "user";
    const [showResponse, setShowResponse] = useState(false);
    const [response, setResponse] = useState()
    const [copied, setCopied] = useState(false);
    const groupedReferences = React.useMemo(() => {
        if (!references) return [];

        const map = new Map();

        references.forEach(ref => {
            if (!map.has(ref.document_id)) {
                map.set(ref.document_id, {
                    ...ref,
                    pages: new Set([ref.page]),
                });
            } else {
                map.get(ref.document_id).pages.add(ref.page);
            }
        });

        return Array.from(map.values()).map(ref => {
            const pages = Array.from(ref.pages).sort((a, b) => a - b);

            return {
                ...ref,
                pages,
                minPage: pages[0],
            };
        });
    }, [references]);

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(content);
        } catch (err) {
            console.error("Failed to copy text:", err);
        }
    };
    const handleCopyResponse = () => {
        const textToCopy = typeof response === "object"
            ? JSON.stringify(response, null, 2)
            : String(response);

        navigator.clipboard.writeText(textToCopy);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
    };
    return (
        <Box
            sx={{
                display: "flex",
                justifyContent: isUser ? "flex-end" : "flex-start",
                px: 2,
                py: 1,
            }}
        >
            <Box
                sx={{
                    position: "relative",
                    maxWidth: "80%",
                    // bgcolor: isUser ? "#2f2f2f" : "transparent",
                    color: "#fff",
                    borderRadius: isUser ? "18px" : "0",
                    p: isUser ? "6px 12px" : 0,
                    "&:hover .message-actions": { opacity: 1, visibility: "visible" },
                }}
            >

                {isUser ? (
                    <Box
                        sx={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "flex-end",
                            bgcolor: "#233C5A",
                            color: "#E1E6EB",
                            borderRadius: 2,
                            p: 1.5,
                            maxWidth: "80%",
                        }}
                    >
                        <Typography
                            variant="body1"
                            sx={{ fontSize: "0.95rem", lineHeight: 1.6, mr: 1 }}
                        >
                            {content}
                        </Typography>
                    </Box>
                ) : (
                    <Box display="flex" alignItems="flex-start" mb={2} gap={1}>
                        <Box component="img" src={AssistantIcon} alt="Assistant" sx={{ width: 32, height: 32, mt: 0.5 }} />

                        <Box sx={{ flex: 1 }}>
                            <Card sx={{ backgroundColor: "#ffffff", borderRadius: 2, p: 2, boxShadow: 1 }}>
                                <MarkdownRenderer content={content} />
                                {groupedReferences.map((reference) => {
                                    const pageLabel = `Page ${reference.pages.join(", ")}`;

                                    return (
                                        <Button
                                            key={reference.document_id}
                                            variant="contained"
                                            sx={{
                                                bgcolor: "rgba(206,212,223,0.2)",
                                                color: "rgb(35,60,90)",
                                                textTransform: "none",
                                                mt: 1,
                                                textAlign: "left",
                                                justifyContent: "flex-start",
                                            }}
                                            onClick={() =>
                                                window.open(
                                                    `${BASE_URL}${reference.url}#page=${reference.minPage}`,
                                                    "_blank"
                                                )
                                            }
                                        >
                                            {reference.filename} ({pageLabel})
                                        </Button>
                                    );
                                })}

                            </Card>


                        </Box>
                    </Box>

                )}

                {(
                    <Box
                        className="message-actions"
                        sx={{
                            position: "absolute",
                            bottom: -25,
                            right: 0,
                            display: "flex",
                            gap: 0.5,
                            opacity: 0,
                            visibility: "hidden",
                            transition: "opacity 0.2s ease, visibility 0.2s ease",
                        }}
                    >
                        <Tooltip title="Copy" placement="top">
                            <IconButton
                                size="small"
                                onClick={handleCopy}
                                sx={{
                                    color: "#777777",
                                    "&:hover": { color: "#393939" },
                                    p: "2px",
                                }}
                            >
                                <ContentCopyIcon sx={{ fontSize: 16 }} />
                            </IconButton>
                        </Tooltip>

                        <Tooltip title="More options" placement="top">
                            <IconButton
                                size="small"
                                sx={{
                                    color: "#777777",
                                    "&:hover": { color: "#393939" },
                                    p: "2px",
                                }}
                            >
                                <MoreVertIcon sx={{ fontSize: 16 }} />
                            </IconButton>
                        </Tooltip>
                    </Box>
                )}

            </Box>
        </Box>
    );
}
