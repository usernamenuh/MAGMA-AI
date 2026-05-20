import { useEffect, useState } from "react";
import {
    Box,
    Typography,
    TextField,
    Card,
    CardContent,
    Pagination,
    Stack,
} from "@mui/material";
import { fetchLogs } from "../hooks/useAnalyze.jsx";

export default function History() {
    const [logs, setLogs] = useState([]);
    const [page, setPage] = useState(1);
    const [limit, setLimit] = useState(10);
    const [total, setTotal] = useState(0);

    useEffect(() => {
        (async () => {
            try {
                const res = await fetchLogs(page, limit);
                setLogs(res.data.data || []);
                setTotal(res.data.total || 0);
            } catch (err) {
                console.error(err);
            }
        })();
    }, [page, limit]);

    const totalPages = Math.ceil(total / limit);

    return (
        <Box sx={{
            px: 4,
            flex: 1,
            display: "flex",
            flexDirection: "column",
            height: "100%",
            bgcolor: "#fbfbfb",
            color: "#000000",
            overflow: "hidden",
        }}>
            <Typography variant="h5" fontWeight="600" gutterBottom sx={{color: 'black', mt: 4}}>
                Logs History
            </Typography>

            <Box sx={{ mt: 5, mb: 3 }}>
                <TextField
                    label="Limit"
                    type="number"
                    size="small"
                    value={limit}
                    onChange={(e) => setLimit(Number(e.target.value))}
                    inputProps={{ min: 1, max: 50 }}
                    sx={{ width: 120 }}
                />
            </Box>

            <Box
                sx={{
                    flex: 1,
                    overflowY: "auto",
                    maxHeight: "calc(100vh - 200px)",
                    pr: 1,
                }}
            >
                <Stack spacing={2} mb={3}>
                    {logs.length ===0 &&(
                        <Box
                            display="flex"
                            flexDirection="column"
                            alignItems="center"
                            justifyContent="center"
                            sx={{ py: 8 }}
                        >
                            <Typography
                                variant="h6"
                                fontWeight={500}
                                color="text.secondary"
                                sx={{ mb: 1 }}
                            >
                                No histories found
                            </Typography>
                            <Typography variant="body2" color="text.disabled">
                                Your past activity will appear here once available.
                            </Typography>
                        </Box>
                    )}
                    {logs.map((log, i) => (
                        <Card key={i} variant="outlined">
                            <CardContent>
                                <Typography variant="body2">
                                    <strong>🕒 Date:</strong> {log.date}
                                </Typography>
                                <Typography variant="body2">
                                    <strong>🙋 User Input:</strong> {log.user_input}
                                </Typography>
                                <Typography variant="body2">
                                    <strong>🔗 API Call:</strong> {log.api_call}
                                </Typography>
                                <Typography variant="body2">
                                    <strong>🤖 Output:</strong> {log.output}
                                </Typography>
                            </CardContent>
                        </Card>
                    ))}
                </Stack>
            </Box>


            {totalPages > 1 && (
                <Box display="flex" justifyContent="center" mt={3}>
                    <Pagination
                        count={totalPages}
                        page={page}
                        onChange={(_, p) => setPage(p)}
                        color="primary"
                    />
                </Box>
            )}
        </Box>
    );
}
