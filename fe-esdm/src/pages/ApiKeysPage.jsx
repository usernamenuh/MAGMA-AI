import React, { useEffect, useState } from "react";
import {
    Box,
    Typography,
    Button,
    CircularProgress,
    TextField,
    List,
    ListItem,
    ListItemText,
    ListItemSecondaryAction,
    IconButton,
    Divider,
    Alert,
    Tooltip,
    Chip,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import BlockIcon from "@mui/icons-material/Block";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import VisibilityIcon from "@mui/icons-material/Visibility";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOff";
import { useApiKeys } from "@/hooks/useApiKeys.jsx";
import ConfirmationDialog from "@/components/ConfirmationDialog.jsx";

export default function APIKeysPage() {
    const {
        apiKeys,
        apiKey,
        loading,
        error,
        fetchApiKeys,
        generateApiKey,
        revokeApiKey,
        removeApiKey,
    } = useApiKeys();
    const [name, setName] = useState("");
    const [validityPeriod, setValidityPeriod] = useState(30)
    const [showNewKey, setShowNewKey] = useState(false);
    const [showKey, setShowKey] = useState({});
    const [copiedKey, setCopiedKey] = useState(null);
    const [confirmOpen, setConfirmOpen] = useState(false);
    const [confirmType, setConfirmType] = useState(null);
    const [selectedKey, setSelectedKey] = useState(null);
    const [textConfirmation, setTextConfirmation] = useState("")
    useEffect(() => {
        fetchApiKeys();
    }, [fetchApiKeys]);
    useEffect(() => {
        if (showNewKey) {
            const timer = setTimeout(() => {
                setShowNewKey(false);
            }, 3000);

            return () => clearTimeout(timer);
        }
    }, [showNewKey]);
    const handleGenerate = async () => {
        await generateApiKey(name, validityPeriod);
        setShowNewKey(true);
        setName("");
        setValidityPeriod(30)
        await fetchApiKeys();
    };

    const handleCopy = (keyValue) => {
        if (keyValue) {
            navigator.clipboard.writeText(keyValue);
            setCopiedKey(keyValue);
            setTimeout(() => setCopiedKey(null), 1500);
        }
    };

    const toggleShowKey = (keyId) => {
        setShowKey((prev) => ({ ...prev, [keyId]: !prev[keyId] }));
    };
    const openConfirm = (type, keyValue, name) => {
        setConfirmType(type);
        setSelectedKey(keyValue);
        setConfirmOpen(true);
        setTextConfirmation(name || keyValue)
    };

    const handleConfirmOk = async () => {
        if (confirmType === "delete") {
            await handleRemove(selectedKey);
        } else if (confirmType === "revoke") {
            await handleRevoke(selectedKey);
        }
        await fetchApiKeys();
    };
    const handleRevoke = async (keyValue) => {
        // if (!window.confirm("Are you sure you want to revoke this API key?")) return;
        await revokeApiKey(keyValue);
        await fetchApiKeys();
    };

    const handleRemove = async (keyValue) => {
        // if (!window.confirm("Are you sure you want to delete this API key?")) return;
        await removeApiKey(keyValue);
        await fetchApiKeys();
    };

    return (
        <Box sx={{
            pt: 5,
            flex: 1,
            px: 4,
            display: "flex",
            flexDirection: "column",
            height: "100%",
            bgcolor: "#fbfbfb",
            color: "#000000",
            overflow: "hidden",
        }}>
            <Typography variant="h5" fontWeight={600} gutterBottom sx={{color: 'black', mt: 4}}>
                API Keys Configuration
            </Typography>

            <Typography variant="body2" color="text.secondary" gutterBottom>
                Manage and secure your API keys for Compliance services.
            </Typography>

            {error && <Alert severity="error">{error}</Alert>}

            <Box my={3} display="flex" gap={2}>
                <TextField
                    label="API Key Name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    size="small"
                />
                <TextField
                    label="Validity Period (in days)"
                    value={validityPeriod}
                    type="number"
                    onChange={(e) => setValidityPeriod(e.target.value)}
                    size="small"
                />
                <Button
                    variant="contained"
                    onClick={handleGenerate}
                    disabled={loading || !name}
                >
                    {loading ? <CircularProgress size={20} /> : "Generate Key"}
                </Button>
            </Box>

            {showNewKey && apiKey && (
                <Alert severity="success" sx={{ mb: 2 }}>
                    New API Key: <strong>{apiKey}</strong>
                </Alert>
            )}

            <Divider sx={{ mb: 2 }} />

            {loading ? (
                <CircularProgress />
            ) : apiKeys.length === 0 ? (
                <Typography>No API keys found.</Typography>
            ) : (
                <List>
                    {apiKeys.map((keyObj, index) => {
                        const keyId = keyObj.api_key;

                        return (
                            <ListItem
                                key={keyId}
                                divider
                                sx={{
                                    bgcolor: "background.paper",
                                    borderRadius: 1,
                                    mb: 1,
                                }}
                            >
                                <ListItemText
                                    primary={
                                        <Box display="flex" alignItems="center" gap={1}>
                                            <Typography variant="subtitle1">
                                                {keyObj.name || `API Key #${index + 1}`}
                                            </Typography>
                                            <Chip
                                                label={keyObj.valid ? "Valid" : "Invalid"}
                                                size="small"
                                                color={keyObj.valid ? "success" : "error"}
                                            />
                                        </Box>
                                    }
                                    secondary={
                                        <>
                                            <Typography
                                                variant="body2"
                                                sx={{
                                                    fontFamily: "monospace",
                                                    wordBreak: "break-all",
                                                    bgcolor: "#f5f5f5",
                                                    p: 1,
                                                    borderRadius: 1,
                                                    mt: 1,
                                                    maxWidth: { xs: "100%", sm: "70%", md: "50%" },
                                                }}
                                            >
                                                {showKey[keyId]
                                                    ? keyObj.api_key
                                                    : "••••••••••••••••••••••••••••••••"}
                                            </Typography>
                                            <Typography variant="caption" color="text.secondary">
                                                Created:{" "}
                                                {new Date(keyObj.created_at + "Z").toLocaleString()}
                                                {keyObj.validity_duration && (
                                                    <> | Duration: {keyObj.validity_duration} days</>
                                                )}
                                            </Typography>
                                        </>
                                    }
                                />

                                <ListItemSecondaryAction>
                                    <Tooltip title={showKey[keyId] ? "Hide" : "Show"}>
                                        <IconButton onClick={() => toggleShowKey(keyId)}>
                                            {showKey[keyId] ? <VisibilityOffIcon /> : <VisibilityIcon />}
                                        </IconButton>
                                    </Tooltip>

                                    <Tooltip title="Copy">
                                        <IconButton onClick={() => handleCopy(keyObj.api_key)}>
                                            <ContentCopyIcon
                                                color={copiedKey === keyObj.api_key ? "success" : "inherit"}
                                            />
                                        </IconButton>
                                    </Tooltip>

                                    <Tooltip title="Revoke Key">
                                        <IconButton
                                            edge="end"
                                            aria-label="revoke"
                                            disabled={!keyObj?.valid}
                                            onClick={() =>
                                                openConfirm("revoke", keyObj.api_key, keyObj.name)
                                            }
                                            sx={{
                                                color: keyObj?.valid ? '#d32f2f' : 'rgba(0,0,0,0.26)',
                                                '&:hover': keyObj?.valid ? { color: '#b71c1c', backgroundColor: 'rgba(211,47,47,0.08)' } : {},
                                            }}
                                        >
                                            <BlockIcon  />
                                        </IconButton>
                                    </Tooltip>

                                    <Tooltip title="Delete Key">
                                        <IconButton
                                            edge="end"
                                            aria-label="delete"
                                            onClick={() =>
                                                openConfirm("delete", keyObj.api_key, keyObj.name)
                                            }
                                        >
                                            <DeleteIcon color="error" />
                                        </IconButton>
                                    </Tooltip>
                                </ListItemSecondaryAction>
                            </ListItem>
                        );
                    })}
                </List>
            )}

            <Typography
                variant="caption"
                color="text.secondary"
                display="block"
                textAlign="center"
                sx={{ mt: 3 }}
            >
                Keep your API keys secure and never share them publicly.
            </Typography>

            <ConfirmationDialog
                open={confirmOpen}
                onClose={() => setConfirmOpen(false)}
                onOk={handleConfirmOk}
                onCancel={() => setConfirmOpen(false)}
                okText={confirmType === "delete"? "Delete": "Revoke"}
                cancelText="Cancel"
            >
                {confirmType === "delete" ? (
                    <>
                        Are you sure you want to permanently delete API key{" "}
                        <strong>{textConfirmation}</strong>?
                    </>
                ) : (
                    <>
                        Are you sure you want to revoke API key{" "}
                        <strong>{textConfirmation}</strong>?
                    </>
                )}
            </ConfirmationDialog>
        </Box>
    );
}
