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
    IconButton,
    Alert,
    Tooltip,
    Chip,
    Paper,
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
            pt: { xs: 2, md: 5 },
            flex: 1,
            px: { xs: 2, md: 4 },
            pb: 5,
            display: "flex",
            flexDirection: "column",
            height: "100%",
            minHeight: 0,
            boxSizing: "border-box",
            bgcolor: "#f8fafc",
            color: "#000000",
            overflowY: "auto",
            overflowX: "hidden",
        }}>
            <Box sx={{ mb: 3 }}>
                <Typography variant="h5" fontWeight={700} sx={{ color: '#18212b', letterSpacing: '-0.02em' }}>API Keys</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>Kelola API key untuk mengakses layanan secara aman.</Typography>
            </Box>

            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

            <Paper elevation={0} sx={{ p: { xs: 2, md: 2.5 }, mb: 2, border: '1px solid #e2e7eb', borderRadius: 2.5 }}>
            <Typography variant="subtitle1" fontWeight={700} sx={{ color: '#243b53', mb: 0.5 }}>Buat API key baru</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>Beri nama yang mudah dikenali dan tentukan masa berlaku key.</Typography>
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'minmax(220px, 1fr) 160px auto' }, gap: 1.5, alignItems: 'center' }}>
                <TextField
                    label="Nama API key"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    size="small"
                    fullWidth
                />
                <TextField
                    label="Masa berlaku (hari)"
                    value={validityPeriod}
                    type="number"
                    onChange={(e) => setValidityPeriod(e.target.value)}
                    size="small"
                    fullWidth
                    slotProps={{ htmlInput: { min: 1 } }}
                />
                <Button
                    variant="contained"
                    onClick={handleGenerate}
                    disabled={loading || !name}
                    sx={{ minHeight: 40, borderRadius: 1.75, px: 2, boxShadow: 'none', whiteSpace: 'nowrap', '&:hover': { boxShadow: 'none' } }}
                >
                    {loading ? <CircularProgress size={20} /> : "Buat key"}
                </Button>
            </Box>
            </Paper>

            {showNewKey && apiKey && (
                <Alert severity="success" sx={{ mb: 2 }}>
                    API key baru: <Box component="strong" sx={{ overflowWrap: 'anywhere' }}>{apiKey}</Box>
                </Alert>
            )}

            {loading ? (
                <CircularProgress />
            ) : apiKeys.length === 0 ? (
                <Paper elevation={0} sx={{ p: 4, border: '1px solid #e2e7eb', borderRadius: 2.5, textAlign: 'center' }}><Typography color="text.secondary">Belum ada API key.</Typography></Paper>
            ) : (
                <Paper elevation={0} sx={{ border: '1px solid #e2e7eb', borderRadius: 2.5, overflow: 'hidden' }}>
                    <Box sx={{ px: { xs: 2, md: 2.5 }, py: 1.75, borderBottom: '1px solid #e8edf1' }}><Typography variant="subtitle1" fontWeight={700} sx={{ color: '#243b53' }}>API key tersedia <Typography component="span" variant="body2" color="text.secondary">({apiKeys.length})</Typography></Typography></Box>
                <List disablePadding>
                    {apiKeys.map((keyObj, index) => {
                        const keyId = keyObj.api_key;

                        return (
                            <ListItem
                                key={keyId}
                                sx={{
                                    px: { xs: 2, md: 2.5 },
                                    py: 1.75,
                                    borderBottom: index < apiKeys.length - 1 ? '1px solid #edf0f2' : 0,
                                    display: 'flex',
                                    alignItems: { xs: 'stretch', md: 'center' },
                                    flexDirection: { xs: 'column', md: 'row' },
                                    gap: { xs: 1.25, md: 2 },
                                    '&:hover': { bgcolor: '#fbfcfd' },
                                }}
                            >
                                <ListItemText
                                    sx={{ m: 0, minWidth: 0, flex: 1 }}
                                    primary={
                                        <Box display="flex" alignItems="center" gap={1} flexWrap="wrap">
                                            <Typography variant="body2" fontWeight={700} sx={{ color: '#243b53', overflowWrap: 'anywhere' }}>
                                                {keyObj.name || `API Key #${index + 1}`}
                                            </Typography>
                                            <Chip
                                                label={keyObj.valid ? "Aktif" : "Tidak aktif"}
                                                size="small"
                                                sx={{ height: 23, fontWeight: 700, fontSize: 11, borderRadius: 1.25, bgcolor: keyObj.valid ? '#eaf7ef' : '#fcebec', color: keyObj.valid ? '#1f7a3d' : '#b4232c' }}
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
                                                    bgcolor: "#f8fafc",
                                                    p: 1.25,
                                                    borderRadius: 1.5,
                                                    border: '1px solid #edf0f2',
                                                    mt: 1,
                                                    maxWidth: '100%',
                                                    fontSize: 12,
                                                }}
                                            >
                                                {showKey[keyId]
                                                    ? keyObj.api_key
                                                    : "••••••••••••••••••••••••••••••••"}
                                            </Typography>
                                            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.75 }}>
                                                Dibuat:{" "}
                                                {new Date(keyObj.created_at + "Z").toLocaleString()}
                                                {keyObj.validity_duration && (
                                                    <> · Berlaku {keyObj.validity_duration} hari</>
                                                )}
                                            </Typography>
                                        </>
                                    }
                                />

                                <Box sx={{ display: 'flex', alignItems: 'center', flexShrink: 0, gap: 0.5, alignSelf: { xs: 'flex-end', md: 'center' } }}>
                                    <Tooltip title={showKey[keyId] ? "Sembunyikan key" : "Tampilkan key"}>
                                        <IconButton aria-label={showKey[keyId] ? 'Sembunyikan key' : 'Tampilkan key'} size="small" onClick={() => toggleShowKey(keyId)} sx={{ bgcolor: '#f1f3f5', '&:hover': { bgcolor: '#e4e9ed' } }}>
                                            {showKey[keyId] ? <VisibilityOffIcon /> : <VisibilityIcon />}
                                        </IconButton>
                                    </Tooltip>

                                    <Tooltip title={copiedKey === keyObj.api_key ? 'Tersalin' : 'Salin key'}>
                                        <IconButton aria-label="Salin key" size="small" onClick={() => handleCopy(keyObj.api_key)} sx={{ bgcolor: '#f1f3f5', '&:hover': { bgcolor: '#e4e9ed' } }}>
                                            <ContentCopyIcon
                                                color={copiedKey === keyObj.api_key ? "success" : "inherit"}
                                            />
                                        </IconButton>
                                    </Tooltip>

                                    <Tooltip title="Cabut key">
                                        <IconButton
                                            aria-label="Cabut key"
                                            disabled={!keyObj?.valid}
                                            onClick={() =>
                                                openConfirm("revoke", keyObj.api_key, keyObj.name)
                                            }
                                            size="small"
                                            sx={{ color: keyObj?.valid ? '#b45309' : 'rgba(0,0,0,0.26)', bgcolor: keyObj?.valid ? '#fff7ed' : 'transparent', '&:hover': keyObj?.valid ? { color: '#92400e', backgroundColor: '#ffedd5' } : {} }}
                                        >
                                            <BlockIcon  />
                                        </IconButton>
                                    </Tooltip>

                                    <Tooltip title="Hapus key">
                                        <IconButton
                                            aria-label="Hapus key"
                                            onClick={() =>
                                                openConfirm("delete", keyObj.api_key, keyObj.name)
                                            }
                                            size="small"
                                            sx={{ bgcolor: '#fff0f0', '&:hover': { bgcolor: '#ffe0e0' } }}>
                                            <DeleteIcon color="error" />
                                        </IconButton>
                                    </Tooltip>
                                </Box>
                            </ListItem>
                        );
                    })}
                </List>
                </Paper>
            )}

            <Typography
                variant="caption"
                color="text.secondary"
                display="block"
                textAlign="center"
                sx={{ mt: 3 }}
            >
                Simpan API key dengan aman dan jangan bagikan kepada orang lain.
            </Typography>

            <ConfirmationDialog
                open={confirmOpen}
                onClose={() => setConfirmOpen(false)}
                onOk={handleConfirmOk}
                onCancel={() => setConfirmOpen(false)}
                okText={confirmType === "delete"? "Hapus": "Cabut"}
                cancelText="Batal"
            >
                {confirmType === "delete" ? (
                    <>
                        Yakin ingin menghapus API key <strong>{textConfirmation}</strong> secara permanen?
                    </>
                ) : (
                    <>
                        Yakin ingin mencabut API key <strong>{textConfirmation}</strong>?
                    </>
                )}
            </ConfirmationDialog>
        </Box>
    );
}
