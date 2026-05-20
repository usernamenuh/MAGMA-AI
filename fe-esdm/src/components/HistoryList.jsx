import {
    List,
    ListItem,
    ListItemText,
    IconButton,
    Box,
    Typography,
    Tooltip,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import HistoryIcon from "@mui/icons-material/History";
import { useNavigate, useParams } from "react-router-dom";
import { useHistory } from "@/hooks/useHistory.jsx";
import {CHAT} from "@/utils/routes.jsx";

export const HistoryList = ({ userId, collapsed }) => {
    const navigate = useNavigate();
    const { id } = useParams();
    const { histories, deleteHistoryById } = useHistory(userId);

    const handleView = (historyId) => {
        navigate(`${CHAT}/${historyId}`);
    };

    const handleDelete = async (historyId) => {
        await deleteHistoryById(historyId);
        navigate(`${CHAT}`);
    };

    if (collapsed) {
        return (
            <Box sx={{ mt: 5, height: "100%" }}>
                <Tooltip title="Histories" placement="right">
                    <Box textAlign="center" mb={1}>
                        <HistoryIcon color="action" />
                    </Box>
                </Tooltip>

                <Box
                    sx={{
                        maxHeight: "200px",
                        overflowY: "auto",
                        overflowX: "hidden", // Hide horizontal scroll
                    }}
                >
                    <List disablePadding>
                        {histories.map((h) => (
                            <Tooltip key={h.history_id} title={h.message || "Compliance"} placement="right">
                                <ListItem
                                    onClick={() => handleView(h.history_id)}
                                    sx={{
                                        justifyContent: 'center',
                                        p: '8px 0',
                                        mb: 1,
                                        borderRadius: 1,
                                        border: "1px solid",
                                        borderColor: "divider",
                                        "&:hover": { bgcolor: "action.hover", cursor: "pointer" },
                                    }}
                                >
                                    <HistoryIcon fontSize="small" />
                                </ListItem>
                            </Tooltip>
                        ))}
                    </List>
                </Box>
            </Box>
        );
    }

    return (
        <Box sx={{ mt: 5, height: "100%" }}>
            <Typography variant="h6" gutterBottom>
                Histories
            </Typography>
            <Box
                sx={{
                    // Use a flexible height if possible, but keeping maxHeight for internal scroll
                    maxHeight: "200px",
                    overflowY: "auto",
                    pr: 1,
                }}
            >
                <List>
                    {histories.map((h) => (
                        <ListItem
                            key={h.history_id}
                            secondaryAction={
                                <IconButton
                                    edge="end"
                                    aria-label="delete"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        handleDelete(h.history_id);
                                    }}
                                >
                                    <DeleteIcon sx={{ color: "#ff2828" }} fontSize="small" />
                                </IconButton>
                            }
                            onClick={() => handleView(h.history_id)}
                            sx={{
                                borderRadius: 1,
                                mb: 1,
                                border: "1px solid",
                                borderColor: "divider",
                                color: id === h.history_id ? "#ffffff" : "text.primary",
                                backgroundColor: id === h.history_id ? "#1976d2" : "background.paper",
                                "&:hover": { 
                                    bgcolor: id === h.history_id ? "#1565c0" : "action.hover",
                                    cursor: "pointer" 
                                },
                            }}
                        >
                            <ListItemText
                                primary={h.message || "Compliance"}
                                
                                primaryTypographyProps={{ noWrap: true, fontSize: 14 }}
                                
                            />
                        </ListItem>
                    ))}
                </List>
            </Box>

        </Box>
    );
};