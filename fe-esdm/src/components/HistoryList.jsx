import { useState } from "react";
import { Box, IconButton, List, ListItemButton, ListItemText, Typography } from "@mui/material";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import { useNavigate, useParams } from "react-router-dom";
import { useHistory } from "@/hooks/useHistory.jsx";
import { CHAT } from "@/utils/routes.jsx";

export const HistoryList = ({ userId, collapsed, dark = false, query = "", onNavigate }) => {
    const [historyVisible, setHistoryVisible] = useState(true);
    const navigate = useNavigate();
    const { id } = useParams();
    const { histories, deleteHistoryById } = useHistory(userId);
    const visibleHistories = histories.filter((history) =>
        (history.message || "").toLowerCase().includes(query.trim().toLowerCase())
    );

    const handleDelete = async (event, historyId) => {
        event.stopPropagation();
        await deleteHistoryById(historyId);
        navigate(CHAT);
    };

    if (collapsed) {
        return <Box sx={{ flex: 1, minHeight: 0 }} />;
    }

    return (
        <Box sx={{ mt: 2.5, flex: historyVisible ? 1 : "none", minHeight: 0, display: "flex", flexDirection: "column" }}>
            <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", px: 1.25, mb: historyVisible ? 0.75 : 0 }}>
                <Typography variant="caption" sx={{ color: dark ? "#9b9b9b" : "text.secondary", fontWeight: 600 }}>
                    Terbaru
                </Typography>
                <IconButton size="small" aria-label={historyVisible ? "Sembunyikan riwayat chat" : "Tampilkan riwayat chat"}
                    aria-expanded={historyVisible} onClick={() => setHistoryVisible((visible) => !visible)}
                    sx={{ width: 28, height: 28, color: dark ? "#9b9b9b" : "#68737d" }}>
                    {historyVisible ? <KeyboardArrowDownIcon sx={{ fontSize: 20 }} /> : <KeyboardArrowRightIcon sx={{ fontSize: 20 }} />}
                </IconButton>
            </Box>
            {historyVisible && <List disablePadding sx={{ overflowY: "auto", overflowX: "hidden", pr: 0.25, scrollbarWidth: "thin", scrollbarColor: "#555 transparent" }}>
                {visibleHistories.length === 0 && <Typography variant="body2" sx={{ px: 1.25, py: 1, color: dark ? "#777" : "text.secondary" }}>{query ? "Percakapan tidak ditemukan" : "Belum ada percakapan"}</Typography>}
                {visibleHistories.map((history) => (
                    <ListItemButton
                        key={history.history_id}
                        selected={id === String(history.history_id)}
                        onClick={() => { navigate(`${CHAT}/${history.history_id}`); onNavigate?.(); }}
                        sx={{
                            minHeight: 36, borderRadius: 2, px: 1.25, py: 0.5, color: dark ? "#d7d7d7" : "text.primary",
                            "&.Mui-selected, &.Mui-selected:hover": { bgcolor: dark ? "#2f2f2f" : "action.selected" },
                            "&:hover": { bgcolor: dark ? "#252525" : "action.hover", "& .history-delete": { opacity: 1 } },
                        }}
                    >
                        <ListItemText primary={history.message || "Percakapan baru"} primaryTypographyProps={{ noWrap: true, fontSize: 14, lineHeight: 1.4, letterSpacing: 0 }} />
                        <IconButton className="history-delete" aria-label="Hapus percakapan" size="small"
                            onClick={(event) => handleDelete(event, history.history_id)}
                            sx={{ opacity: 0, color: dark ? "#aaa" : "text.secondary", ml: 0.5, "&:hover": { color: "#ff6b6b" } }}>
                            <DeleteOutlineIcon sx={{ fontSize: 17 }} />
                        </IconButton>
                    </ListItemButton>
                ))}
            </List>}
        </Box>
    );
};
