import React, { useEffect, useState, useRef } from "react";
import {
    Box,
    Typography,
    TextField,
    Button,
    Stack,
    CircularProgress,
    MenuItem,
    Select,
    FormControl,
    Paper,
    IconButton,
    FormControlLabel,
    Switch,
    Chip,
    Tooltip,
} from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import LocationOnIcon from "@mui/icons-material/LocationOn";
import LocationOffIcon from "@mui/icons-material/LocationOff";
import ChatMessage from "../components/ChatMessage.jsx";
import {
    analyzeChat,
    analyzeChatEn,
    analyzeChatKnowledgeBase,
    analyzeChatKnowledgeBaseEn
} from "../hooks/useAnalyze.jsx";
import useChatHistory from "../hooks/useChatHistory.jsx";
import { PIPELINE_TYPE } from "@/utils/constants.jsx";
import ChatMessageKnowledge from "@/components/ChatMessageKnowledge.jsx";
import {bounce} from "@/utils/layout.jsx";
import { useNavigate } from "react-router-dom";

export default function ChatRAG() {
    const { history, addMessage, updateLast } = useChatHistory();
    const [prompt, setPrompt] = useState("");
    const [loading, setLoading] = useState(false);
    const [geoLocation, setGeoLocation] = useState(null);
    const [isUsingIPAddress, setIsUsingIPAddress] = useState(null)
    const [geoError, setGeoError] = useState(null);
    const [language, setLanguage] = useState("id");
    const [locationEnabled, setLocationEnabled] = useState(true);
    const [locationName, setLocationName] = useState(null);
    const chatEndRef = useRef(null);
    const [pipelineType, setPipelineType] = useState(PIPELINE_TYPE.API_DOCUMENTATION);
    const [isTypeOptionDisabled, setIsTypeOptionDisabled] = useState(false);
    const languages = [
        { code: "en", label: "🇬🇧 English" },
        { code: "id", label: "🇮🇩 Indonesian" },
    ];

    const pipelineTypeOptions = [
        { code: PIPELINE_TYPE.API_DOCUMENTATION, label: "API Documentation" },
        { code: PIPELINE_TYPE.KNOWLEDGE_BASE, label: "Knowledge Base" },
    ];

    const navigate = useNavigate();

    // Auto-scroll to bottom when new message added
    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [history]);

    const fetchIPLocation = async () => {
        try {
            const res = await fetch("https://ipapi.co/json/");
            if (!res.ok) throw new Error("IP location request failed");
            const data = await res.json();
            if (data.latitude && data.longitude) {
                // Get location name from IP API response
                const name = data.city ? `${data.city}, ${data.region}, ${data.country_name}` : "Unknown Location";
                setLocationName(name);
                return [data.latitude, data.longitude];
            }
        } catch (err) {
            console.warn("❌ IP-based location failed:", err);
        }
        return null;
    };

    const reverseGeocode = async (lat, lng) => {
        try {
            const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`);
            if (!res.ok) throw new Error("Reverse geocoding failed");
            const data = await res.json();
            if (data.display_name) {
                return data.display_name;
            }
        } catch (err) {
            console.warn("❌ Reverse geocoding failed:", err);
        }
        return null;
    };

    const getLocation = async () => {
        if (!locationEnabled) {
            setGeoLocation(null);
            setLocationName(null);
            return;
        }

        if ("geolocation" in navigator) {
            const tryGetLocation = (retry = 0) => {
                navigator.geolocation.getCurrentPosition(
                    async (pos) => {
                        const { latitude, longitude } = pos.coords;
                        setGeoLocation([latitude, longitude]);

                        // Get location name
                        const name = await reverseGeocode(latitude, longitude);
                        if (name) {
                            setLocationName(name);
                        } else {
                            setLocationName(`${latitude.toFixed(4)}, ${longitude.toFixed(4)}`);
                        }
                    },
                    async (err) => {
                        if (err.code === err.POSITION_UNAVAILABLE && retry < 2) {
                            setTimeout(() => tryGetLocation(retry + 1), 2000);
                            return;
                        }
                        const ipLoc = await fetchIPLocation();
                        if (ipLoc) {
                            setGeoLocation(ipLoc);
                            setIsUsingIPAddress(true);
                        } else {
                            setGeoError(err.message);
                            setLocationName(null);
                        }
                    },
                    { enableHighAccuracy: true, timeout: 5000 }
                );
            };
            tryGetLocation();
        } else {
            fetchIPLocation().then((loc) => {
                if (loc) {
                    setGeoLocation(loc);
                } else {
                    setGeoError("Geolocation not supported and IP fallback failed.");
                    setLocationName(null);
                }
            });
        }
    };

    useEffect(() => {
        getLocation();
    }, [locationEnabled]);

    const handleLocationToggle = () => {
        setLocationEnabled(!locationEnabled);
    };

    const handleSend = async () => {
        if (!prompt.trim()) return;

        addMessage(prompt);
        setLoading(true);
        setIsTypeOptionDisabled(true);
        setPrompt("");

        try {
            const payload = pipelineType === PIPELINE_TYPE.API_DOCUMENTATION
                ? { user_input: prompt, geo_location: locationEnabled ? geoLocation : null, location_name: locationEnabled? locationName: null }
                : { user_input: prompt };

            let res;
            try {
                if (language === "en") {
                    res = pipelineType === PIPELINE_TYPE.API_DOCUMENTATION
                        ? await analyzeChatEn(payload)
                        : await analyzeChatKnowledgeBaseEn(payload);
                } else {
                    res = pipelineType === PIPELINE_TYPE.API_DOCUMENTATION
                        ? await analyzeChat(payload)
                        : await analyzeChatKnowledgeBase(payload);
                }
            } catch (apiError) {
                // Handle specific Axios network error
                if (apiError.code === 'ERR_NETWORK') {
                    // Network error - server unreachable
                    updateLast("Maaf, server magma.esdm.go.id sedang tidak dapat diakses.\n" +
                        "Silakan coba beberapa saat lagi.", true);

                    // You can also provide retry option
                    console.error("Network connection failed:", {
                        url: apiError.config?.url,
                        baseURL: apiError.config?.baseURL,
                        fullError: apiError
                    });
                }
                // Handle CORS errors specifically
                else if (apiError.message && apiError.message.includes('CORS') || apiError.message.includes('cross-origin')) {
                    updateLast("🔒 CORS Error: Cannot connect to server due to cross-origin restrictions. Please contact the administrator.", true);
                }
                // Handle timeout errors
                else if (apiError.code === 'ECONNABORTED' || apiError.message.includes('timeout')) {
                    updateLast("⏱️ Request Timeout: The server is taking too long to respond. Please try again.", true);
                }
                else if (apiError.response) {
                    // Server responded with error status
                    const { status, data } = apiError.response;

                    switch (status) {
                        case 500:
                            updateLast("❌ Internal Server Error (500): Server encountered an unexpected condition.", true);
                            break;
                        case 404:
                            updateLast("❌ Not Found (404): The requested resource was not found.", true);
                            break;
                        case 401:
                            updateLast("❌ Unauthorized (401): Please authenticate to access this resource.", true);
                            break;
                        case 403:
                            updateLast("❌ Forbidden (403): You don't have permission to access this resource.", true);
                            break;
                        case 429:
                            updateLast("⏳ Too Many Requests (429): Please wait before making more requests.", true);
                            break;
                        default:
                            updateLast(`❌ Server Error ${status}: ${data?.message || 'Please try again later.'}`, true);
                    }
                }
                else if (apiError.request) {
                    // Request was made but no response
                    updateLast("📡 No Response: Server didn't respond. It might be down or unreachable.", true);
                }
                else {
                    // Other Axios errors
                    updateLast(`⚠️ Error: ${apiError.message || 'Unknown error occurred'}`, true);
                }
                return; // Exit on error
            }

            // Handle successful response
            console.log("Response received:", res);

            if (res?.data?.session_id) {
                updateLast(res.data.response || res.data.message || "Analysis complete");
                navigate(`${res.data.session_id}`);
            } else {
                updateLast("⚠️ Warning: Response received but missing session ID.", true);
            }

        } catch (err) {
            // Catch any other unexpected errors
            console.error("Unexpected error in handleSend:", err);
            updateLast("🚨 Unexpected Error: Please refresh the page and try again.", true);
        } finally {
            setLoading(false);
            setIsTypeOptionDisabled(false);
        }
    };

    return (
        <Box
            sx={{
                pt: 5,
                flex: 1,
                px: 4,
                display: "flex",
                flexDirection: "column",
                height: "100vh",
                bgcolor: "#fbfbfb",
                color: "#000000",
                // overflow: "hidden",
            }}
        >
            {/* Header */}
            <Box
                sx={{
                    px: 3,
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    mt: 5,
                }}
            >
                <Typography variant="h5" fontWeight="600">
                    ESDM Assistant
                </Typography>
                <Box
                    sx={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        flexShrink: 0,
                        gap: 2,
                    }}
                >

                    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                        {pipelineType === PIPELINE_TYPE.API_DOCUMENTATION && (
                            <FormControlLabel
                                control={
                                    <Switch
                                        checked={locationEnabled}
                                        onChange={handleLocationToggle}
                                        color="primary"
                                    />
                                }
                                label={
                                    <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                                        {locationEnabled ? <LocationOnIcon fontSize="small" /> : <LocationOffIcon fontSize="small" />}
                                        <Typography variant="body2">
                                            Location
                                        </Typography>
                                    </Box>
                                }
                            />
                        )}

                        { pipelineType === PIPELINE_TYPE.API_DOCUMENTATION && locationEnabled && geoLocation && (
                            <Tooltip title={locationName || `Lat: ${geoLocation[0].toFixed(4)}, Lng: ${geoLocation[1].toFixed(4)}`}>
                                <Chip
                                    size="small"
                                    icon={<LocationOnIcon fontSize="small" />}
                                    label={
                                        locationName ?
                                            locationName.split(',')[0] : // Show only first part (city) for compact display
                                            `${geoLocation[0].toFixed(2)}, ${geoLocation[1].toFixed(2)}`
                                    }
                                    color="primary"
                                    variant="outlined"
                                />
                            </Tooltip>
                        )}
                    </Box>

                    {/* Language and Pipeline Selectors */}
                    <FormControl size="small" sx={{ minWidth: 140 }}>
                        <Select
                            value={language}
                            onChange={(e) => setLanguage(e.target.value)}
                            sx={{
                                color: "#020202",
                                "& .MuiOutlinedInput-notchedOutline": { borderColor: "#444" },
                                "&:hover .MuiOutlinedInput-notchedOutline": { borderColor: "#666" },
                                "& .MuiSvgIcon-root": { color: "#aaa" },
                            }}
                        >
                            {languages.map((lang) => (
                                <MenuItem key={lang.code} value={lang.code}>
                                    {lang.label}
                                </MenuItem>
                            ))}
                        </Select>
                    </FormControl>
                    <FormControl size="small" sx={{ minWidth: 140 }}>
                        <Select
                            disabled={isTypeOptionDisabled}
                            value={pipelineType}
                            onChange={(e) => setPipelineType(e.target.value)}
                            sx={{
                                color: "#020202",
                                "& .MuiOutlinedInput-notchedOutline": { borderColor: "#444" },
                                "&:hover .MuiOutlinedInput-notchedOutline": { borderColor: "#666" },
                                "& .MuiSvgIcon-root": { color: "#aaa" },
                            }}
                        >
                            {pipelineTypeOptions.map((type) => (
                                <MenuItem key={type.code} value={type.code}>
                                    {type.label}
                                </MenuItem>
                            ))}
                        </Select>
                    </FormControl>
                </Box>
            </Box>

            {/* Chat Area */}
            <Box
                sx={{
                    flexGrow: 1,
                    overflowY: "auto",
                    display: "flex",
                    flexDirection: "column",
                    px: 3,
                    py: 2,
                }}
            >
                {history.length === 0 ? (
                    <Box sx={{ textAlign: "center", mt: 10 }}>
                        <Typography variant="body2" color="text.secondary" sx={{ color: "#999", mb: 2 }}>
                            Start the conversation by typing belows 👇
                        </Typography>
                        {pipelineType === PIPELINE_TYPE.API_DOCUMENTATION && locationEnabled && geoLocation && isUsingIPAddress && (
                            <Typography variant="body2" color="text.secondary" sx={{ color: "#999", mb: 2 }}>
                                For more accurate location-based responses, please enable GPS location in your browser.
                                This will provide better accuracy for location-specific queries.
                            </Typography>
                        )}
                        {pipelineType === PIPELINE_TYPE.API_DOCUMENTATION && locationEnabled && geoLocation && (
                            <Chip
                                icon={<LocationOnIcon />}
                                label={`Location enabled: ${locationName || `${geoLocation[0].toFixed(4)}, ${geoLocation[1].toFixed(4)}`}`}
                                color="primary"
                                variant="outlined"
                                sx={{ mb: 2 }}
                            />
                        )}

                        {pipelineType === PIPELINE_TYPE.API_DOCUMENTATION && !locationEnabled && (
                            <Chip
                                icon={<LocationOffIcon />}
                                label="Location sharing is disabled"
                                variant="outlined"
                                sx={{ mb: 2 }}
                            />
                        )}
                    </Box>
                ) : (
                    history.map((chat, i) => (
                        <Box key={i} mb={2}>
                            <ChatMessage role="user" content={chat.user_input} />
                            {chat.output && pipelineType === PIPELINE_TYPE.API_DOCUMENTATION && (
                                <ChatMessage role="assistant" content={chat.output} reference={chat?.api_call} response={chat?.response} />
                            )}
                            {chat.output && pipelineType === PIPELINE_TYPE.KNOWLEDGE_BASE && (
                                <ChatMessageKnowledge role="assistant" content={chat?.output} references={chat?.references}/>
                            )}
                        </Box>
                    ))
                )}
                {loading && (
                    <Box sx={{ display: "flex", justifyContent: "flex-start", mb: 2 }}>
                        <Box
                            sx={{
                                backgroundColor: "#f3f3f3",
                                borderRadius: 2,
                                p: 2,
                                display: "flex",
                                gap: 1,
                            }}
                        >
                            <Box
                                sx={{
                                    width: 8,
                                    height: 8,
                                    borderRadius: "50%",
                                    backgroundColor: "#666",
                                    animation: `${bounce} 0.6s infinite`,
                                }}
                            />
                            <Box
                                sx={{
                                    width: 8,
                                    height: 8,
                                    borderRadius: "50%",
                                    backgroundColor: "#666",
                                    animation: `${bounce} 0.6s infinite`,
                                    animationDelay: "0.2s",
                                }}
                            />
                            <Box
                                sx={{
                                    width: 8,
                                    height: 8,
                                    borderRadius: "50%",
                                    backgroundColor: "#666",
                                    animation: `${bounce} 0.6s infinite`,
                                    animationDelay: "0.4s",
                                }}
                            />
                        </Box>
                    </Box>
                )}

                <div ref={chatEndRef} />
            </Box>

            {/* Input Bar */}
            <Paper
                sx={{
                    borderRadius: 8,
                    flexShrink: 0,
                    mb: 2,
                }}
            >
                <Stack direction="row" spacing={2} alignItems="center">
                    <TextField
                        fullWidth
                        variant="outlined"
                        multiline={true}
                        placeholder={
                            "Ask anything..."
                        }
                        value={prompt}
                        onChange={(e) => setPrompt(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
                        disabled={loading}
                        sx={{
                            "& .MuiOutlinedInput-root": {
                                bgcolor: "#fbfbfb",
                                color: "#272727",
                                borderRadius: 8,
                                px: 3,
                                py: 1.5,
                                "& fieldset": { borderColor: "#ffffff" },
                                "&:hover fieldset": { borderColor: "#ffffff" },
                            },
                        }}
                    />
                    <IconButton
                        color="primary"
                        onClick={handleSend}
                        disabled={loading}
                        sx={{
                            color: "#424343",
                            p: 1.5
                        }}
                    >
                        {loading ? (
                            <CircularProgress size={20} color="inherit" />
                        ) : (
                            <SendIcon />
                        )}
                    </IconButton>
                </Stack>
            </Paper>
        </Box>
    );
}