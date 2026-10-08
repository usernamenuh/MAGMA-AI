import React from "react";
import {Box, Card, Chip, IconButton, Tooltip, Typography} from "@mui/material";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import OpenInNewRoundedIcon from "@mui/icons-material/OpenInNewRounded";
import MarkdownRenderer from "@/components/MarkdownRenderer.jsx";
import AssistantIcon from "../assets/logo-esdm.png";
import {BASE_URL} from "@/utils/constants.jsx";

export default function ChatMessageKnowledge({ role, content, references=[] }) {
    const isUser = role === "user";
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
    return (
        <Box
            sx={{
                display: "flex",
                justifyContent: isUser ? "flex-end" : "flex-start",
                px: { xs: 0.5, sm: 2 },
                py: 1,
            }}
        >
            <Box
                sx={{
                    position: "relative",
                    width: isUser ? "auto" : "100%",
                    maxWidth: isUser ? { xs: "92%", md: "72%" } : { xs: "100%", md: "76%" },
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
                            borderRadius: "16px 16px 4px 16px",
                            px: 2,
                            py: 1.25,
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
                    <Box display="flex" alignItems="flex-start" mb={2} gap={{ xs: 1, sm: 1.5 }}>
                        <Box component="img" src={AssistantIcon} alt="ESDM Assistant" sx={{ width: 34, height: 34, mt: 0.5, objectFit: "contain" }} />

                        <Box sx={{ flex: 1 }}>
                            <Typography variant="caption" sx={{ color: "#526579", fontWeight: 700, ml: 0.5, mb: 0.5, display: "block" }}>
                                ESDM Assistant
                            </Typography>
                            <Card sx={{ backgroundColor: "#ffffff", borderRadius: "4px 16px 16px 16px", p: { xs: 1.5, sm: 2.25 }, border: "1px solid #e6ebf0", boxShadow: "0 4px 18px rgba(35,60,90,0.06)" }}>
                                {(() => {
                                    const cleanContent = typeof content === "string"
                                        ? content.replace(/<!--\s*PENDING_ACTION:[\s\S]*?-->/g, "").trim()
                                        : content;
                                    return <MarkdownRenderer content={cleanContent} />;
                                })()}
                                {groupedReferences.length > 0 && (
                                    <Box sx={{ mt: 2, pt: 1.5, borderTop: "1px solid #edf0f3" }}>
                                        <Typography variant="caption" sx={{ color: "#607386", fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.5 }}>
                                            Sumber dokumen
                                        </Typography>
                                        <Box sx={{ display: "grid", gap: 1, mt: 1 }}>
                                        {groupedReferences.map((reference) => (
                                            <Box
                                                component="button"
                                                type="button"
                                                key={reference.document_id}
                                                onClick={() => window.open(`${BASE_URL}${reference.url}#page=${reference.minPage}`, "_blank", "noopener,noreferrer")}
                                                aria-label={`Buka sumber ${reference.filename}`}
                                                title={reference.filename}
                                                sx={{
                                                    display: "flex", alignItems: "center", gap: 1.25,
                                                    width: "100%", p: 1.25, borderRadius: 2,
                                                    border: "1px solid #dce5ee", bgcolor: "#f7fafc",
                                                    color: "#233c5a", cursor: "pointer", textAlign: "left",
                                                    "&:hover": { bgcolor: "#eef5fb", borderColor: "#b7cadb" },
                                                }}
                                            >
                                                <DescriptionOutlinedIcon fontSize="small" />
                                                <Box sx={{ flex: 1, minWidth: 0 }}>
                                                    <Typography variant="body2" fontWeight={650} noWrap>{reference.filename}</Typography>
                                                    <Typography variant="caption" color="text.secondary">Halaman {reference.pages.join(", ")}</Typography>
                                                </Box>
                                                <Chip label="Dokumen" size="small" sx={{ display: { xs: "none", sm: "inline-flex" }, bgcolor: "#e5eef6", color: "#233c5a" }} />
                                                <OpenInNewRoundedIcon sx={{ fontSize: 17, color: "#6f8294" }} />
                                            </Box>
                                        ))}
                                        </Box>
                                    </Box>
                                )}

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

                    </Box>
                )}

            </Box>
        </Box>
    );
}
