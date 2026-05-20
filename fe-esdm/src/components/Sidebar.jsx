import React, { useState } from "react";
import {
    Box,
    Button,
    Divider,
    IconButton,
    Stack,
    Tooltip,
    Typography,
} from "@mui/material";
import { ChevronLeft, ChevronRight, Chat, Key, Cloud, Book, Logout } from "@mui/icons-material";
import { useNavigate, useLocation } from "react-router-dom";
import logo from "../assets/logo.png";
import mascot from "../assets/mascot-clean.png";
import {useAuth} from "@/hooks/useAuth.jsx";
import {HistoryList} from "@/components/HistoryList.jsx";
import {API_DOCUMENTATION, API_KEYS, CHAT, KNOWLEDGE_BASE, LOGIN} from "@/utils/routes.jsx";

export default function Sidebar() {
    const {user} = useAuth();

    const [collapsed, setCollapsed] = useState(true);
    const navigate = useNavigate();
    const location = useLocation();
    const {logout} = useAuth();
    const handleLogout = async () => {
        await logout();
        navigate(LOGIN, {replace: true});

    }
    const links = [
        { label: "Chat", path: CHAT, icon: <Chat fontSize="small" /> },
        // { label: "History", path: "/history", icon: <History fontSize="small" /> },
        // { label: "Scrapping Data", path: SCRAPPING, icon: <Cloud fontSize="small" /> },
        { label: "API Keys", path: API_KEYS, icon: <Key fontSize="small" /> },
        { label: "Knowledge Base", path: KNOWLEDGE_BASE, icon: <Book fontSize="small" /> },
    ];

    const isActive = (path) => location.pathname === path;

    return (
        <Box
            sx={{
                width: collapsed ? "80px !important" : "260px !important",
                bgcolor: "white",
                height: "100%",
                display: "flex",
                flexDirection: "column",
                borderRight: "1px solid #ddd",
                px: 2,
                pt: 2,
                transition: "width 0.3s ease",
            }}
        >
            {/* Toggle Button */}
            <IconButton
                onClick={() => setCollapsed(!collapsed)}
                sx={{ alignSelf: collapsed ? "center" : "flex-end", mb: 1 }}
            >
                {collapsed ? <ChevronRight /> : <ChevronLeft />}
            </IconButton>

            {/* Logo */}
            <Box textAlign="center" mb={2}>
                <Box
                    component="img"
                    src={logo}
                    alt="Logo"
                    sx={{
                        width: collapsed ? 40 : 120,
                        height: "auto",
                        transition: "width 0.3s ease",
                        cursor: "pointer",
                    }}
                    onClick={() => navigate(CHAT)}
                />
            </Box>

            {!collapsed && (
                <Typography
                    variant="caption"
                    color="text.secondary"
                    textAlign="center"
                    mb={2}
                >
                    ESDM Chat and Knowledge Tools
                </Typography>
            )}

            <Divider sx={{ mb: 2 }} />

            <Stack spacing={1}>
                {links.map((link) => (
                    <Tooltip
                        key={link.path}
                        title={collapsed ? link.label : ""}
                        placement="right"
                    >
                        <Button
                            variant={isActive(link.path) ? "contained" : "outlined"}
                            color={isActive(link.path) ? "primary" : "inherit"}
                            startIcon={!collapsed && link.icon}
                            onClick={() => navigate(link.path)}
                            sx={{
                                justifyContent: collapsed ? "center" : "flex-start",
                                textTransform: "none",
                                borderRadius: 1,
                                borderColor: "divider",
                                color: isActive(link.path) ? "#fff" : "text.primary",
                                bgcolor: isActive(link.path) ? "primary.main" : "inherit",
                                "&:hover": {
                                    bgcolor: isActive(link.path)
                                        ? "primary.dark"
                                        : "rgba(0,0,0,0.04)",
                                },
                            }}
                        >
                            {collapsed ? link.icon : link.label}
                        </Button>
                    </Tooltip>
                ))}
                <Tooltip title="API Documentation" placement="right" disableHoverListener={!collapsed}>
                    <Button onClick={() => navigate(API_DOCUMENTATION)}
                            variant={isActive(API_DOCUMENTATION) ? "contained" : "outlined"}
                            color={isActive(API_DOCUMENTATION) ? "primary" : "inherit"}
                            startIcon={!collapsed && <Cloud fontSize="small" />}
                            sx={{
                                borderRadius: 1,
                                borderColor: 'divider',
                                textOverflow: 'ellipsis',
                                textTransform: 'none',
                                justifyContent: collapsed ? "center" : "flex-start",
                                color: isActive(API_DOCUMENTATION) ? "#fff" : "text.primary",
                                bgcolor: isActive(API_DOCUMENTATION) ? "primary.main" : "inherit",
                                "&:hover": {
                                    bgcolor: isActive(API_DOCUMENTATION)
                                        ? "primary.dark"
                                        : "rgba(0,0,0,0.04)",
                                },
                            }}
                    >
                         {!collapsed && "API Documentation"}
                    </Button>
                </Tooltip>
            </Stack>
            <HistoryList userId={user?.id ||  JSON.parse(user)?.id} collapsed={collapsed} />
            <Box>
                <Button
                    variant={"contained"}
                    onClick={handleLogout}
                    sx={{
                        width: "100%",
                        justifyContent: "center",
                        textTransform: "none",
                        borderRadius: 1,
                        bgcolor: "#233C5A",
                        color: "#ffffff",
                        "&:hover": {
                            bgcolor: "#1a2c41",
                        },
                        minWidth: 0,
                        p: collapsed ? '10px 0' : '6px 16px',
                    }}
                >
                    {collapsed ? (
                        <Logout fontSize="small" />
                    ) : (
                        <>
                            <Logout fontSize="small" sx={{ mr: 1 }} />
                            Logout
                        </>
                    )}
                </Button>
            </Box>
            <Box flexGrow={1} />
            
            <Box textAlign="center" >
                <Box
                    component="img"
                    src={mascot}
                    alt="mascot"
                    sx={{
                        width: collapsed ? 40 : 90,
                        height: "auto",
                        transition: "width 0.3s ease",
                        cursor: "pointer",
                        pb: 5,

                    }}
                />
            </Box>
        </Box>
    );
}
