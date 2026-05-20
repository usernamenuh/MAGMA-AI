// PrivateLayout.jsx (Fixed)
import React from "react";
import { Box, styled } from "@mui/material";
import { Outlet } from "react-router-dom";
import Sidebar from "@/components/Sidebar.jsx";
import { useApp } from "@/contexts/AppProvider.jsx";

const Main = styled("main", {
    shouldForwardProp: (prop) => prop !== "open" && prop !== "drawerwidth",
})(({ theme, open, drawerwidth }) => ({
    flexGrow: 1,
    backgroundColor: theme.palette.background.default,
    overflowY: "hidden",
    overflowX: "hidden",
    display: "flex",
    flexDirection: "column",
    "@media only screen and (min-width: 900px)": {
        ...(open && {
            marginLeft: `${drawerwidth}px`,
        }),
    },
}));

export const PrivateLayout = () => {
    const { open, drawerWidth } = useApp();
    return (
        <Box
            sx={{
                display: "flex",
                height: "100vh",
                width: "100vw",
                overflow: "visible",
            }}
        >
            <Box
                sx={{
                    overflow: "hidden",
                    height: "100vh",
                }}
            >
            <Sidebar />
            </Box>

            <Box
                sx={{
                    flex: 1,
                    display: "flex",
                    flexDirection: "column",
                    height: "100vh",
                    overflow: "visible",
                }}
            >
                <Main open={open} drawerwidth={drawerWidth} sx={{
                    flex: 1,
                    display: "flex",
                    flexDirection: "column",
                    overflow: "visible",
                    height: "100vh",

                }}>
                    <Box
                        sx={{
                            flex: 1,
                            overflowY: "auto",  // ONLY scroll here
                            overflowX: "hidden",
                            height: "100vh",
                        }}
                    >
                        <Outlet />
                    </Box>
                </Main>
            </Box>
        </Box>
    );
};