import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { Button, Menu, MenuItem, Typography, useMediaQuery } from "@mui/material";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";

export default function MobileChatSource({ value, options, onChange, disabled }) {
    const isMobile = useMediaQuery("(max-width:599px)");
    const [anchorEl, setAnchorEl] = useState(null);
    const [target, setTarget] = useState(null);

    useEffect(() => {
        setTarget(isMobile ? document.getElementById("mobile-chat-source") : null);
    }, [isMobile]);

    if (!target) return null;

    return createPortal(
        <>
            <Button onClick={(event) => setAnchorEl(event.currentTarget)} disabled={disabled}
                endIcon={<KeyboardArrowDownIcon sx={{ fontSize: 18 }} />}
                aria-label={`Sumber jawaban: ${options.find((option) => option.code === value)?.label || "ESDM Assistant"}`}
                sx={{ p: 0.5, minWidth: 0, color: "#263746", textTransform: "none", letterSpacing: 0, "&:hover": { bgcolor: "#f0f2f4" } }}>
                <Typography variant="subtitle1" fontWeight={700} noWrap>ESDM Assistant</Typography>
            </Button>
            <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={() => setAnchorEl(null)}
                slotProps={{ paper: { sx: { mt: 0.5, borderRadius: 2, minWidth: 205, boxShadow: "0 12px 36px rgba(20,31,44,.16)" } } }}>
                {options.map((option) => (
                    <MenuItem key={option.code} selected={option.code === value} onClick={() => { onChange(option.code); setAnchorEl(null); }}>
                        {option.label}
                    </MenuItem>
                ))}
            </Menu>
        </>, target
    );
}
