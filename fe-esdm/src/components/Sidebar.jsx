import React, { useEffect, useState } from "react";
import { Box, Button, Dialog, IconButton, InputBase, Stack, SvgIcon, Tooltip, Typography, useMediaQuery } from "@mui/material";
import { Close, DescriptionOutlined, EditOutlined, KeyOutlined, Logout, MenuBookOutlined, Search, ChatBubbleOutline } from "@mui/icons-material";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth.jsx";
import { HistoryList } from "@/components/HistoryList.jsx";
import { useHistory } from "@/hooks/useHistory.jsx";
import { API_DOCUMENTATION, API_KEYS, CHAT, KNOWLEDGE_BASE, LOGIN } from "@/utils/routes.jsx";
import logo from "../assets/logo.png";
import logoEsdm from "../assets/logo-esdm.png";
import mascot from "../assets/mascot-clean.png";

const SidebarToggleIcon = (props) => (
    <SvgIcon {...props} viewBox="0 0 24 24">
        <rect x="3.25" y="4.25" width="17.5" height="15.5" rx="2.25" fill="none" stroke="currentColor" strokeWidth="1.5" />
        <path d="M9 4.75v14.5" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </SvgIcon>
);

export default function Sidebar({ drawerMode = false, onNavigate }) {
    const isMobile = useMediaQuery("(max-width:899px)");
    const [collapsed, setCollapsed] = useState(drawerMode ? false : isMobile);
    const [searchOpen, setSearchOpen] = useState(false);
    const [searchQuery, setSearchQuery] = useState("");
    const navigate = useNavigate();
    const location = useLocation();
    const chatActive = location.pathname === CHAT || location.pathname.startsWith(`${CHAT}/`);
    const { user, logout } = useAuth();
    const { histories } = useHistory(user?.id);
    const searchResults = histories.filter((history) =>
        (history.message || "").toLowerCase().includes(searchQuery.trim().toLowerCase())
    );

    const openHistory = (historyId) => {
        setSearchOpen(false);
        setSearchQuery("");
        navigate(`${CHAT}/${historyId}`);
        onNavigate?.();
    };

    const goTo = (path) => {
        navigate(path);
        onNavigate?.();
    };

    useEffect(() => {
        if (isMobile && !drawerMode) setCollapsed(true);
    }, [isMobile, drawerMode]);

    const links = [
        { label: "API Keys", path: API_KEYS, icon: <KeyOutlined /> },
        { label: "Knowledge Base", path: KNOWLEDGE_BASE, icon: <MenuBookOutlined /> },
        { label: "API Documentation", path: API_DOCUMENTATION, icon: <DescriptionOutlined /> },
    ];

    const handleLogout = async () => {
        await logout();
        navigate(LOGIN, { replace: true });
    };

    const navButtonSx = (active = false) => ({
        width: collapsed ? 40 : "100%", minWidth: 0, minHeight: collapsed ? 40 : 36, px: collapsed ? 0 : 1.25,
        justifyContent: collapsed ? "center" : "flex-start",
        borderRadius: 2, textTransform: "none", fontWeight: 400,
        fontSize: 14, lineHeight: 1.4, letterSpacing: 0,
        color: "#252525",
        bgcolor: active ? "#e7e9ec" : "transparent",
        border: "none",
        outline: "none",
        "&:hover": { bgcolor: active ? "#dfe2e5" : "#f0f2f4" },
        "&:focus, &:focus-visible": { outline: "none" },
        "& .MuiButton-startIcon": { mr: collapsed ? 0 : 1.25, ml: 0, "& svg": { fontSize: 21 } },
    });

    return (
        <Box component="aside" sx={{
            width: drawerMode ? "100%" : collapsed ? 60 : 260, height: "100%", boxSizing: "border-box", flexShrink: 0,
            bgcolor: "#fff", color: "#252525", display: "flex", flexDirection: "column",
            px: collapsed ? 0.75 : 1, py: 1.25, overflow: "hidden", borderRight: "1px solid #eceff1",
            transition: "width 180ms ease",
        }}>
            <Box sx={{ display: "flex", alignItems: "center", justifyContent: collapsed ? "center" : "space-between", minHeight: 42, width: "100%", px: collapsed ? 0 : 1 }}>
                {!collapsed && <Box component="img" src={logo} alt="Kementerian ESDM" onClick={() => goTo(CHAT)} sx={{ width: 108, height: "auto", cursor: "pointer", transition: "width 180ms ease" }} />}
                {collapsed && (
                    <Tooltip title="Buka sidebar" placement="right">
                        <IconButton
                            onClick={() => setCollapsed(false)}
                            size="small"
                            sx={{
                                width: 42, height: 42, position: "relative", color: "#333", borderRadius: 2.25,
                                "& .sidebar-toggle-icon": { opacity: 0 },
                                "&:hover .sidebar-brand-logo": { opacity: 0 },
                                "&:hover .sidebar-toggle-icon": { opacity: 1 },
                            }}
                        >
                            <Box className="sidebar-brand-logo" component="img" src={logoEsdm} alt="Logo ESDM" sx={{ width: 28, height: 28, objectFit: "contain", transition: "opacity 120ms ease" }} />
                            <SidebarToggleIcon className="sidebar-toggle-icon" sx={{ position: "absolute", fontSize: 22, transition: "opacity 120ms ease" }} />
                        </IconButton>
                    </Tooltip>
                )}
                <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", gap: collapsed ? 0.5 : 0.25 }}>
                    {!collapsed && <Tooltip title="Cari percakapan">
                        <IconButton
                            onClick={() => setSearchOpen(true)}
                            size="small"
                            sx={{ color: "#333", width: 32, height: 32 }}
                        >
                            <Search sx={{ fontSize: 19 }} />
                        </IconButton>
                    </Tooltip>}
                    {!collapsed && (
                        <Tooltip title={drawerMode ? "Tutup menu" : "Tutup sidebar"}>
                            <IconButton onClick={drawerMode ? onNavigate : () => setCollapsed(true)} size="small" sx={{ color: "#333", width: 32, height: 32 }}>
                                {drawerMode ? <Close sx={{ fontSize: 20 }} /> : <SidebarToggleIcon sx={{ fontSize: 19 }} />}
                            </IconButton>
                        </Tooltip>
                    )}
                </Box>
            </Box>
            {!collapsed && <Typography variant="caption" sx={{ px: 1, mt: 0.5, color: "#78828c" }}>Asisten informasi MAGMA Indonesia</Typography>}

            <Box
                sx={{
                    flex: 1,
                    minHeight: 0,
                    display: "flex",
                    flexDirection: "column",
                    overflowY: "auto",
                    overflowX: "hidden",
                    mt: collapsed ? 0 : 0.25,
                    pr: 0.25,
                    scrollbarWidth: "thin",
                    scrollbarColor: "#c7cdd3 transparent",
                }}
            >
                <Tooltip title={collapsed ? "Chat baru" : ""} placement="right">
                    <Button startIcon={<EditOutlined />} onClick={() => goTo(CHAT)}
                        sx={{ ...navButtonSx(chatActive), mt: collapsed ? 3 : 1.5, alignSelf: "center" }}>
                        {!collapsed && "Chat baru"}
                    </Button>
                </Tooltip>

                {collapsed && (
                    <Tooltip title="Cari percakapan" placement="right">
                        <Button aria-label="Cari percakapan" startIcon={<Search />} onClick={() => setSearchOpen(true)}
                            sx={{ ...navButtonSx(), alignSelf: "center", mt: 0.75 }} />
                    </Tooltip>
                )}

                <Stack spacing={collapsed ? 0.75 : 0.5} sx={{ mt: 0.5, alignItems: collapsed ? "center" : "stretch" }}>
                    {links.map((link) => (
                        <Tooltip key={link.path} title={collapsed ? link.label : ""} placement="right">
                            <Button startIcon={link.icon} onClick={() => goTo(link.path)} sx={navButtonSx(location.pathname === link.path)}>
                                {!collapsed && link.label}
                            </Button>
                        </Tooltip>
                    ))}
                </Stack>

                <HistoryList userId={user?.id} collapsed={collapsed} onNavigate={onNavigate} />
            </Box>

            <Box sx={{ mt: "auto", pt: 1, borderTop: "1px solid #e1e4e7" }}>
                <Tooltip title={collapsed ? "Logout" : ""} placement="right">
                    <Button onClick={handleLogout} sx={{ width: collapsed ? 44 : "100%", mx: "auto", minWidth: 0, minHeight: 44, p: collapsed ? 0 : undefined, justifyContent: "center", textTransform: "none", fontSize: 14, letterSpacing: 0, borderRadius: 2.25, bgcolor: "#233c5a", color: "#fff", border: "none", outline: "none", "&:hover": { bgcolor: "#1b3048" }, "&:focus, &:focus-visible": { outline: "none" } }}>
                        <Logout sx={{ fontSize: 19, mr: collapsed ? 0 : 1 }} />
                        {!collapsed && "Logout"}
                    </Button>
                </Tooltip>
                <Box sx={{ display: "flex", justifyContent: "center", pt: 1 }}>
                    <Box component="img" src={mascot} alt="Maskot ESDM" sx={{ width: collapsed ? 32 : 70, height: "auto", maxHeight: 72, objectFit: "contain", transition: "width 180ms ease" }} />
                </Box>
            </Box>
            <Dialog open={searchOpen} onClose={() => setSearchOpen(false)} fullWidth maxWidth="sm"
                slotProps={{ paper: { sx: { m: { xs: 1.5, sm: 3 }, width: "calc(100% - 24px)", height: { xs: "min(620px, calc(100dvh - 24px))", sm: 560 }, maxHeight: "calc(100dvh - 24px)", borderRadius: 3, boxShadow: "0 20px 70px rgba(20, 31, 44, 0.18)" } } }}>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, px: 2.5, py: 2, borderBottom: "1px solid #edf0f2" }}>
                    <Search sx={{ color: "#65717d", fontSize: 21 }} />
                    <InputBase autoFocus value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)}
                        placeholder="Cari percakapan..." inputProps={{ "aria-label": "Cari percakapan" }}
                        sx={{ flex: 1, fontSize: 15 }} />
                    <IconButton aria-label="Tutup pencarian" onClick={() => setSearchOpen(false)} size="small"><Close fontSize="small" /></IconButton>
                </Box>
                <Box sx={{ px: 1.5, py: 2, overflowY: "auto", flex: 1 }}>
                    <Typography variant="body2" sx={{ px: 1.5, mb: 1, color: "text.secondary" }}>
                        {searchQuery.trim() ? "Hasil pencarian" : "Percakapan terbaru"}
                    </Typography>
                    {searchResults.length === 0 && <Typography variant="body2" color="text.secondary" sx={{ px: 1.5, py: 2 }}>
                        {searchQuery.trim() ? "Percakapan tidak ditemukan." : "Belum ada percakapan."}
                    </Typography>}
                    {searchResults.map((history) => (
                        <Button key={history.history_id} fullWidth onClick={() => openHistory(history.history_id)}
                            startIcon={<ChatBubbleOutline sx={{ fontSize: 19 }} />}
                            sx={{ justifyContent: "flex-start", textAlign: "left", color: "#252525", fontWeight: 400, fontSize: 14, letterSpacing: 0, px: 1.5, py: 1.25, borderRadius: 1.75, "&:hover": { bgcolor: "#f2f4f6" }, "& .MuiButton-startIcon": { mr: 1.5 } }}>
                            <Box component="span" sx={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                                {history.message || "Percakapan baru"}
                            </Box>
                        </Button>
                    ))}
                </Box>
            </Dialog>
        </Box>
    );
}
