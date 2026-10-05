// PrivateLayout.jsx (Fixed)
import React, { useState } from "react";
import { Box, Drawer, IconButton, Typography, styled, useMediaQuery } from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import { Outlet, useLocation } from "react-router-dom";
import Sidebar from "@/components/Sidebar.jsx";
import logoEsdm from "@/assets/logo-esdm.png";
import { CHAT } from "@/utils/routes.jsx";

const Main = styled("main")(({ theme }) => ({
    flexGrow: 1,
    minWidth: 0,
    minHeight: 0,
    backgroundColor: theme.palette.background.default,
    overflow: "hidden",
    display: "flex",
    flexDirection: "column",
}));

export const PrivateLayout = () => {
    const isMobile = useMediaQuery("(max-width:599px)");
    const [menuOpen, setMenuOpen] = useState(false);
    const location = useLocation();
    const isChatPage = location.pathname === CHAT || location.pathname.startsWith(`${CHAT}/`);
    return (
        <Box
            sx={{
                display: "flex",
                height: "100dvh",
                width: "100%",
                maxWidth: "100%",
                overflow: "hidden",
            }}
        >
            {!isMobile && <Box
                sx={{
                    overflow: "hidden",
                    height: "100vh",
                    flexShrink: 0,
                }}
            >
            <Sidebar />
            </Box>}

            {isMobile && <Drawer anchor="left" open={menuOpen} onClose={() => setMenuOpen(false)}
                slotProps={{ paper: { sx: { width: "min(280px, 86vw)", height: "100dvh" } } }}>
                <Sidebar drawerMode onNavigate={() => setMenuOpen(false)} />
            </Drawer>}

            <Box
                sx={{
                    flex: 1,
                    display: "flex",
                    flexDirection: "column",
                    height: "100dvh",
                    overflow: "hidden",
                    minWidth: 0,
                    minHeight: 0,
                }}
            >
                {isMobile && <Box component="header" sx={{ minHeight: 56, px: 1, pt: "env(safe-area-inset-top)", display: "flex", alignItems: "center", gap: 0.25, flexShrink: 0, bgcolor: "#fbfbfb" }}>
                    <IconButton aria-label="Buka menu" onClick={() => setMenuOpen(true)} sx={{ color: "#263746", width: 40, height: 40 }}><MenuIcon /></IconButton>
                    <Box component="img" src={logoEsdm} alt="ESDM" sx={{ width: 25, height: 25, objectFit: "contain", display: "none", "@media (min-width:360px)": { display: "block" } }} />
                    {isChatPage ? <Box id="mobile-chat-source" sx={{ minWidth: 0, flex: 1 }} /> : <Typography variant="subtitle1" fontWeight={700} sx={{ color: "#263746", flex: 1 }}>ESDM Assistant</Typography>}
                    {isChatPage && <Box id="mobile-chat-location" sx={{ flexShrink: 0 }} />}
                    {isChatPage && <Box id="mobile-chat-language" sx={{ flexShrink: 0 }} />}
                </Box>}
                <Main sx={{
                    flex: 1,
                    display: "flex",
                    flexDirection: "column",
                    overflow: "hidden",
                    height: "100%",

                }}>
                    <Box
                        sx={{
                            flex: 1,
                            overflowY: "hidden",
                            overflowX: "hidden",
                            height: "100%",
                            minHeight: 0,
                            minWidth: 0,
                        }}
                    >
                        <Outlet />
                    </Box>
                </Main>
            </Box>
        </Box>
    );
};
