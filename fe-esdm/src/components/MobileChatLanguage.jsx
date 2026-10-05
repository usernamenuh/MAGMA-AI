import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { IconButton, Menu, MenuItem, useMediaQuery } from "@mui/material";

export default function MobileChatLanguage({ value, options, onChange }) {
    const isMobile = useMediaQuery("(max-width:599px)");
    const [target, setTarget] = useState(null);
    const [anchorEl, setAnchorEl] = useState(null);

    useEffect(() => {
        setTarget(isMobile ? document.getElementById("mobile-chat-language") : null);
    }, [isMobile]);

    if (!target) return null;

    return createPortal(
        <>
            <IconButton aria-label={`Bahasa: ${options.find((option) => option.code === value)?.label || value}`}
                onClick={(event) => setAnchorEl(event.currentTarget)} size="small" sx={{ width: 34, height: 34 }}>
                <span style={{ fontSize: 18, lineHeight: 1 }}>{value === "id" ? "🇮🇩" : "🇬🇧"}</span>
            </IconButton>
            <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={() => setAnchorEl(null)}
                slotProps={{ paper: { sx: { mt: 0.5, borderRadius: 2, minWidth: 160 } } }}>
                {options.map((option) => (
                    <MenuItem key={option.code} selected={option.code === value} onClick={() => { onChange(option.code); setAnchorEl(null); }}>
                        {option.label}
                    </MenuItem>
                ))}
            </Menu>
        </>, target
    );
}
