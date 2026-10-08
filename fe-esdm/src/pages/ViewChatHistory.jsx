import React, { useEffect, useState, useRef } from "react";
import {
    Box,
    Typography,
    CircularProgress,
    MenuItem,
    Select,
    FormControl,
    Paper,
    IconButton, FormControlLabel, Switch, Tooltip, Chip, ToggleButton, ToggleButtonGroup,
} from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import ChatMessage from "../components/ChatMessage.jsx";
import {
    analyzeChat,
    analyzeChatEn,
    analyzeChatKnowledgeBase,
    analyzeChatKnowledgeBaseEn,
    DEFAULT_CHAT_MODELS,
    getChatModels,
    getKnowledgeDocuments
} from "../hooks/useAnalyze.jsx";
import useChatHistory from "../hooks/useChatHistory.jsx";
import {useLocation, useParams} from "react-router-dom";
import {useAuth} from "@/hooks/useAuth.jsx";
import {useHistory} from "@/hooks/useHistory.jsx";
import {PIPELINE_TYPE} from "@/utils/constants.jsx";
import ChatMessageKnowledge from "@/components/ChatMessageKnowledge.jsx";
import { bounce, pulseGlow, shimmerGradient } from "@/utils/layout.jsx";
import LocationOnIcon from "@mui/icons-material/LocationOn";
import LocationOffIcon from "@mui/icons-material/LocationOff";
import DocumentMentionInput from "../components/DocumentMentionInput.jsx";
import MobileChatSource from "../components/MobileChatSource.jsx";
import MobileChatLanguage from "../components/MobileChatLanguage.jsx";
import MobileChatLocation from "../components/MobileChatLocation.jsx";
import AssistantIcon from "../assets/logo-esdm.png";

export default function ChatRAGHistory() {
    const { id: sessionId } = useParams();
    const location = useLocation();
    const { history, fetchSessionHistory, addMessage, updateLast } = useChatHistory();
    const [prompt, setPrompt] = useState("");
    const [geoLocation, setGeoLocation] = useState(null);
    const [isUsingIPAddress, setIsUsingIPAddress] = useState(null)
    const [loading, setLoading] = useState(false);
    const [models, setModels] = useState(DEFAULT_CHAT_MODELS);
    const [selectedModel, setSelectedModel] = useState(() =>
        location.state?.selectedModel ||
        sessionStorage.getItem(`chat_model:${sessionId}`) ||
        "local"
    );
    useEffect(() => {
        const model = location.state?.selectedModel ||
            sessionStorage.getItem(`chat_model:${sessionId}`) ||
            "local";
        setSelectedModel(model);
        if (location.state?.selectedModel) {
            sessionStorage.setItem(`chat_model:${sessionId}`, model);
        }
    }, [sessionId, location.state?.selectedModel]);
    const [knowledgeDocuments, setKnowledgeDocuments] = useState([]);
    const [selectedDocumentIds, setSelectedDocumentIds] = useState([]);
    const chatEndRef = useRef(null);
    const [locationEnabled, setLocationEnabled] = useState(true);
    const [locationName, setLocationName] = useState(null);
    const [locationAccuracy, setLocationAccuracy] = useState(null);

    useEffect(() => {
        getChatModels().then(({ data }) => {
            const availableModels = data.items?.length ? data.items : DEFAULT_CHAT_MODELS;
            const defaultModel = availableModels.some((item) => item.id === data.default)
                ? data.default
                : availableModels[0].id;
            setModels(availableModels);
            setSelectedModel((currentModel) =>
                availableModels.some((item) => item.id === currentModel)
                    ? currentModel
                    : defaultModel
            );
        }).catch((error) => console.error("Failed to load models:", error));
    }, []);
    useEffect(() => {
        getKnowledgeDocuments().then(({ data }) => {
            setKnowledgeDocuments(
                (data.items || []).filter((item) => ["COMPLETED", "INCOMPLETE"].includes(item.processing_status))
            );
        }).catch((error) => console.error("Failed to load knowledge documents:", error));
    }, []);
    const {user} = useAuth();
    const [pipelineType, setPipelineType] = useState(history[0]?.type || PIPELINE_TYPE.API_DOCUMENTATION);
    const [isTypeOptionDisabled, setIsTypeOptionDisabled] = useState(true)

    // Fetch session messages on mount
    useEffect(() => {
        if (sessionId && user) fetchSessionHistory(sessionId, user?.id || JSON.parse(user)?.id);
    }, [sessionId, user, fetchSessionHistory]);

    useEffect(() => {
        setPipelineType(history[0]?.type || PIPELINE_TYPE.API_DOCUMENTATION);
        const savedLanguage = localStorage.getItem("chat_language");
        const historyLanguage = history.find((message) => message.lang)?.lang;
        setLanguage(savedLanguage || historyLanguage || "en");
    },[history])

    // Auto-scroll to bottom when new message added or status changes
    useEffect(() => {
        const scrollToBottom = (behavior = "smooth") => {
            chatEndRef.current?.scrollIntoView({ behavior, block: "end" });
        };
        scrollToBottom("smooth");
        const t1 = setTimeout(() => scrollToBottom("smooth"), 120);
        const t2 = setTimeout(() => scrollToBottom("auto"), 350);
        return () => {
            clearTimeout(t1);
            clearTimeout(t2);
        };
    }, [history, loading]);

    const [, setGeoError] = useState(null);
    const [language, setLanguage] = useState(
        () => localStorage.getItem("chat_language") || "id"
    );
    const { refetchHistories } = useHistory(user?.id || JSON.parse(user)?.id);
    const languages = [
        { code: "en", label: "🇬🇧 English" },
        { code: "id", label: "🇮🇩 Indonesian" },
    ];

    const pipelineTypeOptions = [
        { code: PIPELINE_TYPE.API_DOCUMENTATION, label: "API Documentation" },
        { code: PIPELINE_TYPE.KNOWLEDGE_BASE, label: "Knowledge Base" },
    ]

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
            setLocationAccuracy(null);
            return;
        }

        if ("geolocation" in navigator) {
            const tryGetLocation = (retry = 0) => {
                navigator.geolocation.getCurrentPosition(
                    async (pos) => {
                        const { latitude, longitude, accuracy } = pos.coords;
                        setGeoLocation([latitude, longitude]);
                        setLocationAccuracy(accuracy);
                        setIsUsingIPAddress(false);

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
                            setLocationAccuracy(null);
                        } else {
                            setGeoError(err.message);
                            setLocationName(null);
                            setLocationAccuracy(null);
                        }
                    },
                    { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
                );
            };
            tryGetLocation();
        } else {
            fetchIPLocation().then((loc) => {
                if (loc) {
                    setGeoLocation(loc);
                    setIsUsingIPAddress(true);
                    setLocationAccuracy(null);
                } else {
                    setGeoError("Geolocation not supported and IP fallback failed.");
                    setLocationName(null);
                    setLocationAccuracy(null);
                }
            });
        }
    };

    useEffect(() => {
        getLocation();
        // getLocation intentionally reads the latest state for each toggle.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    },  [locationEnabled]);

    const handleLocationToggle = () => {
        if (locationEnabled) {
            setLocationAccuracy(null);
        }
        setLocationEnabled(!locationEnabled);
    };

    const setLanguageChoice = (nextLanguage) => {
        localStorage.setItem("chat_language", nextLanguage);
        setLanguage(nextLanguage);
    };

    const handleLanguageChange = (event) => setLanguageChoice(event.target.value);


    const handleSend = async (overridePrompt = null) => {
        const textToSend = typeof overridePrompt === "string" ? overridePrompt : prompt;
        if (!textToSend.trim()) return;
        const cleanKnowledgePrompt = knowledgeDocuments.reduce(
            (text, document) => text.replaceAll(`@${document.filename}`, " "),
            textToSend
        ).replace(/\s+/g, " ").trim();
        addMessage(textToSend);
        setLoading(true);
        setPrompt("");

        try {
            const payload = pipelineType===PIPELINE_TYPE.API_DOCUMENTATION
                ? {
                    user_input: textToSend,
                    geo_location: locationEnabled ? geoLocation : null,
                    location_name: locationEnabled? locationName: null,
                    location_accuracy: locationEnabled ? locationAccuracy : null,
                    session_id: sessionId,
                    model: selectedModel,
                }
                : {
                    user_input: cleanKnowledgePrompt || textToSend,
                    session_id: sessionId,
                    model: selectedModel,
                    document_ids: selectedDocumentIds.length ? selectedDocumentIds : null,
                };

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

                updateLast(res?.data);
                refetchHistories();
            } catch (apiError) {
            // Handle specific Axios network error
            if (apiError.code === 'ERR_NETWORK') {
                // Network error - server unreachable
                updateLast(
                    language === "en"
                        ? "Sorry, the assistant service is currently unreachable. Please try again in a few moments."
                        : "Maaf, layanan asisten sedang tidak dapat dijangkau. Silakan coba beberapa saat lagi.",
                    true
                );

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
        }

    } catch (err) {
        console.error("Unexpected error in handleSend:", err);
        updateLast("🚨 Unexpected Error: Please refresh the page and try again.", true);
    } finally {
        setLoading(false);
        setIsTypeOptionDisabled(false);
        setPrompt("");
        setSelectedDocumentIds([]);
    }
    };
    return (
        <>
        <MobileChatSource value={pipelineType} options={pipelineTypeOptions} disabled={isTypeOptionDisabled}
            onChange={setPipelineType} />
        <MobileChatLanguage value={language} options={languages} onChange={setLanguageChoice} />
        <MobileChatLocation visible={pipelineType === PIPELINE_TYPE.API_DOCUMENTATION}
            enabled={locationEnabled} onToggle={handleLocationToggle} name={locationName} coordinates={geoLocation} />
        <Box
            sx={{
                pt: { xs: 0, md: 2 },
                flex: 1,
                px: { xs: 1.5, sm: 3, md: 4 },
                display: "flex",
                flexDirection: "column",
                height: "100%",
                minHeight: 0,
                minWidth: 0,
                boxSizing: "border-box",
                bgcolor: "#fbfbfb",
                color: "#000000",
                overflow: "hidden",
            }}
        >
            {/* Header */}
            <Box
                sx={{
                    px: { xs: 0, md: 3 },
                    py: { xs: 1, md: 2 },
                    display: { xs: "none", sm: "grid" },
                    gridTemplateColumns: { sm: "minmax(0, 1fr) auto", lg: "minmax(180px, 1fr) auto minmax(320px, 1fr)" },
                    minWidth: 0,
                    alignItems: "center",
                    flexShrink: 0,
                    pt: { xs: 1, md: 1.5 },
                    columnGap: 2,
                    rowGap: 1,
                }}
            >
                <Box sx={{ minWidth: 0, gridColumn: 1, gridRow: 1 }}>
                    <Typography variant="h5" fontWeight="700">ESDM Assistant</Typography>
                    <Typography variant="caption" sx={{ color: "#607386" }}>Asisten informasi MAGMA Indonesia</Typography>
                </Box>
                <ToggleButtonGroup
                    exclusive
                    size="small"
                    value={pipelineType}
                    disabled={isTypeOptionDisabled}
                    onChange={(_, value) => value && setPipelineType(value)}
                    aria-label="Pilih sumber jawaban"
                    sx={{
                        justifySelf: "center", gridColumn: { sm: "1 / -1", lg: 2 }, gridRow: { sm: 2, lg: 1 }, bgcolor: "#eef1f4", borderRadius: 999, p: 0.4,
                        "& .MuiToggleButton-root": { px: { xs: 1.5, sm: 3 }, py: 0.7, border: 0, borderRadius: "999px !important", textTransform: "none", color: "#52606d", fontSize: { xs: 12, sm: 13 } },
                        "& .Mui-selected": { bgcolor: "#fff !important", color: "#172b3f !important", boxShadow: "0 1px 5px rgba(0,0,0,.12)" },
                    }}
                >
                    {pipelineTypeOptions.map((type) => <ToggleButton key={type.code} value={type.code}>{type.label}</ToggleButton>)}
                </ToggleButtonGroup>
                <Box
                    sx={{
                        display: "flex",
                        alignItems: "center",
                        minWidth: 0,
                        width: "auto",
                        gap: 1.25,
                        justifyContent: "flex-end",
                        justifySelf: "end",
                        gridColumn: { sm: 2, lg: 3 },
                        gridRow: 1,
                    }}
                >
                    {/* Location Toggle and Display */}
                    {pipelineType === PIPELINE_TYPE.API_DOCUMENTATION && <Box sx={{ display: "flex", alignItems: "center", minWidth: 0, gap: 0.75, whiteSpace: "nowrap" }}>
                        <FormControlLabel
                            sx={{ m: 0, flexShrink: 0, gap: 0.25, "& .MuiFormControlLabel-label": { lineHeight: 1 } }}
                            control={
                                <Switch
                                    size="small"
                                    checked={locationEnabled}
                                    onChange={handleLocationToggle}
                                    color="primary"
                                    inputProps={{ "aria-label": "Gunakan lokasi" }}
                                />
                            }
                            label={
                                <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                                    {locationEnabled ? <LocationOnIcon sx={{ fontSize: 17 }} /> : <LocationOffIcon sx={{ fontSize: 17 }} />}
                                    <Typography variant="body2" sx={{ fontSize: 12.5 }}>
                                        Lokasi
                                    </Typography>
                                </Box>
                            }
                        />
                        {locationEnabled && geoLocation && (
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
                                    sx={{ display: { sm: "none", md: "inline-flex" }, maxWidth: 125, "& .MuiChip-label": { overflow: "hidden", textOverflow: "ellipsis" } }}
                                />
                            </Tooltip>
                        )}
                    </Box>}
                    <FormControl size="small" sx={{ minWidth: 126, flexShrink: 0 }}>
                        <Select
                            value={language}
                            onChange={handleLanguageChange}
                            sx={{
                                height: 36,
                                fontSize: 13,
                                borderRadius: 2,
                                color: "#263746",
                                "& .MuiOutlinedInput-notchedOutline": { borderColor: "#d8e0e6" },
                                "&:hover .MuiOutlinedInput-notchedOutline": { borderColor: "#aebbc6" },
                                "& .MuiSvgIcon-root": { color: "#607386" },
                            }}
                        >
                            {languages.map((lang) => (
                                <MenuItem key={lang.code} value={lang.code}>
                                    {lang.label}
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
                    px: { xs: 0, sm: 2, md: 3 },
                    py: 2,
                }}
            >
                {history.length === 0 ? (
                    <Box sx={{ textAlign: "center", mt: { xs: 5, md: 10 } }}>
                        <Typography variant="h6" fontWeight={700} color="#233c5a">Lanjutkan percakapan dengan ESDM Assistant</Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>Ketik pertanyaan di bawah ini.</Typography>
                    </Box>
                ) : (
                    history.map((chat, i) => (
                        <Box key={i} mb={2}>
                            <ChatMessage role="user" content={chat.user_input} />
                            {chat.output && pipelineType === PIPELINE_TYPE.API_DOCUMENTATION && (
                                <ChatMessage
                                    role="assistant"
                                    content={chat.answer || chat.output}
                                    reference={chat?.api_call}
                                    response={chat?.response}
                                    geolocation={chat?.geoLocation}
                                    followUps={i === history.length - 1 ? (chat?.follow_ups || chat?.suggested_follow_ups) : null}
                                    onSelectFollowUp={(q) => handleSend(q)}
                                />
                            )}
                            {chat.output && pipelineType === PIPELINE_TYPE.KNOWLEDGE_BASE && (
                                <ChatMessageKnowledge role="assistant" content={chat?.output} references={chat?.references}/>

                            )}
                        </Box>
                    ))
                )}
                {loading && (
                    <Box sx={{ display: "flex", justifyContent: "flex-start", alignItems: "flex-start", gap: 1.5, mb: 2, px: { xs: 0.5, sm: 2 } }}>
                        <Box
                            component="img"
                            src={AssistantIcon}
                            alt="ESDM Assistant"
                            sx={{
                                width: 34,
                                height: 34,
                                objectFit: "contain",
                                borderRadius: "50%",
                                animation: `${pulseGlow} 2s infinite ease-in-out`,
                            }}
                        />
                        <Box
                            sx={{
                                position: "relative",
                                overflow: "hidden",
                                background: "linear-gradient(135deg, rgba(246, 250, 255, 0.95) 0%, rgba(240, 245, 252, 0.95) 100%)",
                                borderRadius: "18px 18px 18px 4px",
                                p: "12px 18px",
                                display: "flex",
                                flexDirection: "column",
                                gap: 1,
                                border: "1px solid rgba(200, 222, 245, 0.7)",
                                boxShadow: "0 6px 20px rgba(25, 118, 210, 0.07)",
                                minWidth: { xs: 260, sm: 320 },
                            }}
                        >
                            <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 1.5 }}>
                                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                                    <Box
                                        sx={{
                                            width: 8,
                                            height: 8,
                                            borderRadius: "50%",
                                            backgroundColor: "#1976d2",
                                            boxShadow: "0 0 8px #1976d2",
                                            animation: `${bounce} 1s infinite`,
                                        }}
                                    />
                                    <Typography variant="body2" sx={{ fontWeight: 600, color: "#1e3a5f", fontSize: "0.86rem" }}>
                                        {pipelineType === PIPELINE_TYPE.KNOWLEDGE_BASE
                                            ? "Menganalisis Dokumen ESDM…"
                                            : "Memproses Data Geologi MAGMA…"}
                                    </Typography>
                                </Box>
                                <Box sx={{ display: "flex", gap: "5px", alignItems: "center" }}>
                                    <Box
                                        sx={{
                                            width: 6,
                                            height: 6,
                                            borderRadius: "50%",
                                            backgroundColor: "#1976d2",
                                            animation: `${bounce} 0.8s infinite ease-in-out`,
                                        }}
                                    />
                                    <Box
                                        sx={{
                                            width: 6,
                                            height: 6,
                                            borderRadius: "50%",
                                            backgroundColor: "#0288d1",
                                            animation: `${bounce} 0.8s infinite ease-in-out`,
                                            animationDelay: "0.2s",
                                        }}
                                    />
                                    <Box
                                        sx={{
                                            width: 6,
                                            height: 6,
                                            borderRadius: "50%",
                                            backgroundColor: "#00b4d8",
                                            animation: `${bounce} 0.8s infinite ease-in-out`,
                                            animationDelay: "0.4s",
                                        }}
                                    />
                                </Box>
                            </Box>
                            <Typography variant="caption" sx={{ color: "#64748b", fontSize: "0.75rem", fontStyle: "italic" }}>
                                {pipelineType === PIPELINE_TYPE.KNOWLEDGE_BASE
                                    ? "Menghubungkan konteks dengan basis pengetahuan resmi..."
                                    : "Menghubungi API PVMBG & memverifikasi laporan terkini..."}
                            </Typography>
                            {/* Animated shimmering accent line */}
                            <Box
                                sx={{
                                    height: "2.5px",
                                    width: "100%",
                                    borderRadius: 2,
                                    background: "linear-gradient(90deg, #1976d2 0%, #00b4d8 50%, #1976d2 100%)",
                                    backgroundSize: "200% 100%",
                                    animation: `${shimmerGradient} 1.8s infinite linear`,
                                }}
                            />
                        </Box>
                    </Box>
                )}

                <Box ref={chatEndRef} sx={{ height: 48, minHeight: 48, flexShrink: 0 }} />
            </Box>

            {/* Input Bar */}
            <Paper
                sx={{
                    borderRadius: 4,
                    width: "min(760px, 100%)",
                    mx: "auto",
                    flexShrink: 0,
                    mb: { xs: "max(12px, env(safe-area-inset-bottom))", sm: 2 },
                    border: "1px solid #e0e6eb",
                    boxShadow: "0 8px 28px rgba(35,60,90,0.08)",
                }}
            >
                <Box>
                    <DocumentMentionInput
                        prompt={prompt}
                        setPrompt={setPrompt}
                        documents={knowledgeDocuments}
                        selectedDocumentIds={selectedDocumentIds}
                        setSelectedDocumentIds={setSelectedDocumentIds}
                        disabled={loading}
                        onSend={handleSend}
                        enabled={pipelineType === PIPELINE_TYPE.KNOWLEDGE_BASE}
                    />
                    <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 1, px: 1.25, pb: 1, pt: 0.25 }}>
                    <FormControl size="small" sx={{ minWidth: 0, maxWidth: "calc(100% - 64px)" }}>
                        <Select value={selectedModel} disabled={loading} onChange={(e) => {
                            setSelectedModel(e.target.value);
                            sessionStorage.setItem(`chat_model:${sessionId}`, e.target.value);
                        }}
                            aria-label="Pilih model AI"
                            sx={{ height: 34, borderRadius: 2, fontSize: 13, color: "#52606d", "& .MuiSelect-select": { py: 0.75, pl: 1.25, pr: 3.5 }, "& fieldset": { borderColor: "transparent" }, "&:hover fieldset": { borderColor: "#dce3e9" } }}>
                            {models.map((item) => <MenuItem key={item.id} value={item.id}>{item.label}</MenuItem>)}
                        </Select>
                    </FormControl>
                    <IconButton
                        color="primary"
                        onClick={handleSend}
                        disabled={loading || !prompt.trim()}
                        aria-label="Kirim pesan"
                        sx={{
                            color: "#233c5a", width: 36, height: 36,
                            "&:hover": { bgcolor: "transparent", color: "#172b42" },
                            "&.Mui-disabled": { bgcolor: "transparent", color: "#aeb8c1" },
                        }}
                    >
                        {loading ? (
                            <CircularProgress size={20} color="inherit" />
                        ) : (
                            <SendIcon />
                        )}
                    </IconButton>
                    </Box>
                </Box>
            </Paper>
        </Box>
        </>
    );
}
