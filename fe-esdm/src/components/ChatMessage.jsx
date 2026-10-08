import React, {useState} from "react";
import {Box, Button, Card, CardContent, Collapse, IconButton, Tooltip, Typography, Chip} from "@mui/material";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import MarkdownRenderer from "@/components/MarkdownRenderer.jsx";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import AssistantIcon from "../assets/logo-esdm.png";
import LocationOnRounded from "@mui/icons-material/LocationOnRounded";


export default function ChatMessage({ role, content, reference, response, geolocation, followUps, onSelectFollowUp}) {
    const isUser = role === "user";
    const [showResponse, setShowResponse] = useState(false);
    const [copied, setCopied] = useState(false);
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
                    <Box display="flex" alignItems="flex-start" mb={2} gap={1}>
                        <Box component="img" src={AssistantIcon} alt="ESDM Assistant" sx={{ width: 34, height: 34, mt: 0.5, objectFit: "contain" }} />

                        <Box sx={{ flex: 1 }}>
                            <Typography variant="caption" sx={{ color: "#526579", fontWeight: 700, ml: 0.5, mb: 0.5, display: "block" }}>
                                ESDM Assistant
                            </Typography>
                            <Card sx={{ backgroundColor: "#ffffff", borderRadius: "4px 16px 16px 16px", p: { xs: 1.5, sm: 2.25 }, pb: { xs: 2, sm: 2.75 }, border: "1px solid #e6ebf0", boxShadow: "0 4px 18px rgba(35,60,90,0.06)" }}>
                                {(() => {
                                    const cleanContent = typeof content === "string"
                                        ? content.replace(/<!--\s*PENDING_ACTION:[\s\S]*?-->/g, "").trim()
                                        : content;
                                    return <MarkdownRenderer content={cleanContent} />;
                                })()}
                                {followUps && followUps.length > 0 && (
                                    <Box sx={{ mt: 1.5, mb: 0.75, display: "flex", flexWrap: "wrap", gap: 1 }}>
                                        {followUps.map((item, idx) => {
                                            const CANONICAL_FALLBACKS = {
                                                volcano_recommendation: {
                                                    label: "Lihat rekomendasi masyarakat",
                                                    query: "Bagaimana rekomendasi PVMBG untuk gunung api tersebut?",
                                                },
                                                volcano_status: {
                                                    label: "Cek status aktivitas",
                                                    query: "Bagaimana status aktivitas gunung api tersebut?",
                                                },
                                                volcano_eruption_history: {
                                                    label: "Lihat riwayat erupsi",
                                                    query: "Kapan erupsi terakhir gunung api tersebut?",
                                                },
                                                volcano_active_list: {
                                                    label: "Gunung api aktif di atas Normal",
                                                    query: "Gunung apa saja yang berstatus waspada, siaga, atau awas?",
                                                },
                                                volcano_status_level_explanation: {
                                                    label: "Arti tingkatan status gunung api",
                                                    query: "Jelaskan arti tingkatan status gunung api dari normal hingga awas",
                                                },
                                                location_safety: {
                                                    label: "Cek gunung api terdekat",
                                                    query: "Gunung apa yang paling dekat dengan saya?",
                                                },
                                                earthquake_list: {
                                                    label: "Daftar gempa bumi terkini",
                                                    query: "Daftar kejadian gempa bumi terkini",
                                                },
                                                earthquake_mitigation: {
                                                    label: "Panduan mitigasi gempa",
                                                    query: "Bagaimana panduan mitigasi bencana gempa bumi?",
                                                },
                                                ground_movement_list: {
                                                    label: "Laporan gerakan tanah terbaru",
                                                    query: "Laporan kejadian gerakan tanah terbaru",
                                                },
                                                knowledge_base: {
                                                    label: "Panduan mitigasi bencana geologi",
                                                    query: "Bagaimana panduan mitigasi bencana erupsi gunung api?",
                                                },
                                            };

                                            let rawLabel = typeof item === "string" ? item : (item.label || item.action || item.query || item.id || "");
                                            let rawQuery = typeof item === "string" ? item : (item.action || item.query || item.label || item.id || "");

                                            if (CANONICAL_FALLBACKS[rawLabel]) {
                                                rawLabel = CANONICAL_FALLBACKS[rawLabel].label;
                                            }
                                            if (CANONICAL_FALLBACKS[rawQuery]) {
                                                rawQuery = CANONICAL_FALLBACKS[rawQuery].query;
                                            }

                                            return (
                                                <Chip
                                                    key={idx}
                                                    label={rawLabel}
                                                    clickable
                                                    onClick={() => onSelectFollowUp && onSelectFollowUp(rawQuery)}
                                                    variant="outlined"
                                                    size="small"
                                                    sx={{
                                                        borderColor: "#2563eb",
                                                        color: "#1d4ed8",
                                                        fontWeight: 600,
                                                        fontSize: "0.82rem",
                                                        bgcolor: "rgba(37, 99, 235, 0.05)",
                                                        transition: "all 0.2s ease-in-out",
                                                        "&:hover": {
                                                            bgcolor: "rgba(37, 99, 235, 0.15)",
                                                            borderColor: "#1d4ed8",
                                                            transform: "translateY(-1px)",
                                                        }
                                                    }}
                                                />
                                            );
                                        })}
                                    </Box>
                                )}
                                {geolocation && (
                                    <Box sx={{ mt: 1, display: "flex", alignItems: "center", gap: 1 }}>
                                        <Chip
                                            icon={<LocationOnRounded/>}
                                            label={`Lat ${geolocation[0].toFixed(3)}, Lng ${geolocation[1].toFixed(3)}`}
                                            variant="outlined"
                                            size="small"
                                        />
                                        <Button
                                            size="small"
                                            variant="text"
                                            sx={{ textTransform: "none" }}
                                            href={`https://www.google.com/maps?q=${geolocation[0]},${geolocation[1]}`}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                        >
                                            View on map
                                        </Button>
                                    </Box>
                                )}


                                {reference && (
                                    <Button
                                        variant="outlined"
                                        sx={{ borderColor: "#d5e0e9", bgcolor: "#f7fafc", color:"rgb(35,60,90)", textTransform: "none", mt: 1.5, maxWidth: "100%", justifyContent: "flex-start" }}
                                        onClick={() => setShowResponse(!showResponse)}
                                        endIcon={showResponse ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                                    >
                                        {reference}
                                    </Button>
                                )}
                            </Card>

                            <Collapse in={showResponse} timeout="auto" unmountOnExit>
                                <Card sx={{ mt: 1, backgroundColor: "#fff", borderRadius: 2, boxShadow: 1 }}>
                                    <CardContent sx={{ p: 1.5, position: "relative" }}>
                                        {response ? (
                                            <Box sx={{ position: "relative", overflowX: "auto" }}>
                                                <Tooltip title={copied ? "Copied!" : "Copy"}>
                                                    <IconButton
                                                        onClick={handleCopyResponse}
                                                        size="small"
                                                        sx={{
                                                            position: "absolute",
                                                            top: 6,
                                                            right: 6,
                                                            backgroundColor: copied ? "rgba(76,175,80,0.1)" : "transparent",
                                                            "&:hover": { backgroundColor: "rgba(0,0,0,0.05)" },
                                                        }}
                                                    >
                                                        <ContentCopyIcon fontSize="small" color={copied ? "success" : "inherit"} />
                                                    </IconButton>
                                                </Tooltip>

                                                <pre
                                                    style={{
                                                        whiteSpace: "pre-wrap",
                                                        wordWrap: "break-word",
                                                        fontSize: "0.875rem",
                                                        margin: 0,
                                                    }}
                                                >
                {typeof response === "object" ? JSON.stringify(response, null, 2) : String(response)}
              </pre>
                                            </Box>
                                        ) : (
                                            <Typography variant="body2">No response data available.</Typography>
                                        )}
                                    </CardContent>
                                </Card>
                            </Collapse>
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
