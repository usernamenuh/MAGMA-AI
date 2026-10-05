import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { Box, IconButton, Popover, Switch, Typography, useMediaQuery } from "@mui/material";
import LocationOnOutlinedIcon from "@mui/icons-material/LocationOnOutlined";
import LocationOffOutlinedIcon from "@mui/icons-material/LocationOffOutlined";

export default function MobileChatLocation({ visible, enabled, onToggle, name, coordinates }) {
    const isMobile = useMediaQuery("(max-width:599px)");
    const [target, setTarget] = useState(null);
    const [anchorEl, setAnchorEl] = useState(null);

    useEffect(() => {
        setTarget(isMobile ? document.getElementById("mobile-chat-location") : null);
    }, [isMobile]);

    useEffect(() => {
        if (!visible) setAnchorEl(null);
    }, [visible]);

    if (!target || !visible) return null;

    const locationText = name || (coordinates
        ? `${coordinates[0].toFixed(4)}, ${coordinates[1].toFixed(4)}`
        : "Lokasi belum tersedia");

    return createPortal(
        <>
            <IconButton
                aria-label={enabled ? `Pengaturan lokasi: ${locationText}` : "Pengaturan lokasi: nonaktif"}
                aria-haspopup="dialog"
                aria-expanded={Boolean(anchorEl)}
                onClick={(event) => setAnchorEl(event.currentTarget)}
                sx={{ width: 40, height: 40, color: enabled ? "#233c5a" : "#6b7785", borderRadius: 2 }}
            >
                {enabled ? <LocationOnOutlinedIcon /> : <LocationOffOutlinedIcon />}
            </IconButton>
            <Popover
                open={Boolean(anchorEl)}
                anchorEl={anchorEl}
                onClose={() => setAnchorEl(null)}
                anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
                transformOrigin={{ vertical: "top", horizontal: "right" }}
                slotProps={{ paper: { sx: { width: "min(292px, calc(100vw - 24px))", mt: 0.5, p: 2, border: "1px solid #e2e7eb", borderRadius: 2, boxShadow: "0 12px 32px rgba(22, 40, 58, .14)" } } }}
            >
                <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 1 }}>
                    <Box sx={{ minWidth: 0 }}>
                        <Typography variant="subtitle2" sx={{ fontWeight: 700, color: "#233c5a" }}>Gunakan lokasi</Typography>
                        <Typography variant="body2" color="text.secondary">Untuk pertanyaan sesuai wilayah</Typography>
                    </Box>
                    <Switch checked={enabled} onChange={onToggle} inputProps={{ "aria-label": "Gunakan lokasi" }} />
                </Box>
                {enabled && (
                    <Typography variant="body2" sx={{ mt: 1.5, pt: 1.5, borderTop: "1px solid #edf0f2", color: "#425466", overflowWrap: "anywhere" }}>
                        {locationText}
                    </Typography>
                )}
            </Popover>
        </>, target
    );
}
