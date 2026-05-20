import React, {useState} from "react";
import {Box, Button, Card, CardContent, Collapse, IconButton, Tooltip, Typography, Chip} from "@mui/material";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import MoreVertIcon from "@mui/icons-material/MoreVert";
import MarkdownRenderer from "@/components/MarkdownRenderer.jsx";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import AssistantIcon from "../assets/logo-esdm.png";
import LocationOnRounded from "@mui/icons-material/LocationOnRounded";


export default function ChatMessage({ role, content, reference, response, geolocation}) {
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
                                        variant="contained"
                                        color="rgb(35,60,90)"
                                        sx={{ bgcolor: "rgba(35,59,89,0.2)",color:"rgb(35,60,90)",textTransform: "none", mt: 1 }}
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
