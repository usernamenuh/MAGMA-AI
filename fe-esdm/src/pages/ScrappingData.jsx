import { useState } from "react";
import {
    Box,
    TextField,
    Button,
    Typography,
    Paper,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    IconButton,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Stack,
} from "@mui/material";
import { ContentCopy, Visibility } from "@mui/icons-material";
import { scrapeData } from "../hooks/useAnalyze.jsx";

export default function ScrappingData() {
    const [keyword, setKeyword] = useState("");
    const [limit, setLimit] = useState(10);
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(false);
    const [open, setOpen] = useState(false);
    const [selectedData, setSelectedData] = useState(null);

    const handleScrape = async () => {
        try {
            setLoading(true);
            const res = await scrapeData(keyword, limit);
            if (res.data?.results?.length > 1) {
                res.data.results.forEach((result) => {
                    setResults((prev) => [...prev, result]);
                });
            } else if (res.data?.results?.length === 1 && !res.data.results[0]?.error) {
                setResults(res.data.results[0]);
            } else {
                setResults([]);
            }

        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleView = (item) => {
        setSelectedData(item);
        setOpen(true);
    };

    const handleClose = () => {
        setOpen(false);
        setSelectedData(null);
    };

    const handleCopy = () => {
        if (!selectedData) return;
        navigator.clipboard.writeText(JSON.stringify(selectedData, null, 2));
    };

    const flattenObject = (obj, prefix = '') => {
        return Object.keys(obj || {}).reduce((acc, k) => {
            const pre = prefix ? `${prefix}.` : '';
            if (typeof obj[k] === 'object' && obj[k] !== null && !Array.isArray(obj[k])) {
                Object.assign(acc, flattenObject(obj[k], pre + k));
            } else {
                acc[pre + k] = obj[k];
            }
            return acc;
        }, {});
    };

    const flattenedData = results?.map((r) => flattenObject(r.data?.data || r.data || r));
    const allKeys = [...new Set(flattenedData.flatMap(Object.keys))];


    return (
        <Box sx={{
            pt: 5,
            flex: 1,
            px: 4,
            display: "flex",
            flexDirection: "column",
            height: "100vh",
            bgcolor: "#fbfbfb",
            color: "#000000",
            overflow: "hidden",
        }}>
            <Typography variant="h5" fontWeight={600} gutterBottom sx={{color: 'black', mt: 4}}>
                Scrapping Data
            </Typography>

            {/* Input Section */}
            <Paper
                sx={{
                    p: 2,
                    mb: 4,
                    display: "flex",
                    gap: 2,
                    flexWrap: "wrap",
                    alignItems: "center",
                    backgroundColor: 'white'
                }}
                elevation={1}
            >
                <TextField
                    label="Keyword"
                    placeholder="Enter keyword..."
                    value={keyword}
                    onChange={(e) => setKeyword(e.target.value)}
                    size="small"
                    fullWidth
                    sx={{ flex: 1, minWidth: 250 }}
                />
                <TextField
                    label="Limit"
                    type="number"
                    value={limit}
                    onChange={(e) => setLimit(Number(e.target.value))}
                    size="small"
                    sx={{ width: 120 }}
                    inputProps={{ min: 1 }}
                />
                <Button
                    variant="contained"
                    color="success"
                    onClick={handleScrape}
                    sx={{ height: 40 }}
                    disabled={loading}
                >
                    {loading ? "Scrapping..." : "Scrap"}
                </Button>
            </Paper>

            {/* Data Table */}
            {results.length > 0 ? (
                <TableContainer component={Paper} elevation={1}>
                    <Table size="small">
                        <TableHead>
                            <TableRow>
                                <TableCell>No</TableCell>
                                {allKeys.map((key) => (
                                    <TableCell key={key}>{key}</TableCell>
                                ))}
                                <TableCell align="center">Action</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {flattenedData.map((row, index) => (
                                <TableRow key={index}>
                                    <TableCell>{index + 1}</TableCell>
                                    {allKeys.map((key) => (
                                        <TableCell key={key}>
                                            {row[key] ? (
                                                typeof row[key] === "string" && row[key].startsWith("http") ? (
                                                    <a href={row[key]} target="_blank" rel="noopener noreferrer">
                                                        View
                                                    </a>
                                                ) : (
                                                    row[key].toString()
                                                )
                                            ) : (
                                                "-"
                                            )}
                                        </TableCell>
                                    ))}
                                    <TableCell align="center">
                                        <IconButton onClick={() => handleView(results[index])} color="primary">
                                            <Visibility />
                                        </IconButton>
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </TableContainer>
            ) : (
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
                        No data found
                    </Typography>
                    <Typography variant="body2" color="text.disabled">
                        Please try again later
                    </Typography>
                </Box>
            )}


            {/* Dialog */}
            <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
                <DialogTitle>
                    Data Details
                </DialogTitle>
                <DialogContent dividers>
                    {selectedData ? (
                        <Box>
                            {selectedData?.data?.data ? (
                                <Stack spacing={2}>
                                    <Typography variant="h6">
                                        🌋 {selectedData.data.data.nama_gunung_api}
                                    </Typography>
                                    {selectedData.data.data.foto && (
                                        <img
                                            src={selectedData.data.data.foto}
                                            alt="eruption"
                                            style={{
                                                width: "100%",
                                                borderRadius: "8px",
                                                marginBottom: "1rem",
                                            }}
                                        />
                                    )}
                                    <Typography variant="body2">
                                        <strong>Activity Level:</strong>{" "}
                                        {selectedData.data.data.tingkat_aktivitas}
                                    </Typography>
                                    <Typography variant="body2">
                                        <strong>Date:</strong>{" "}
                                        {selectedData.data.data.local_date}{" "}
                                        {selectedData.data.data.local_time}{" "}
                                        ({selectedData.data.data.time_zone})
                                    </Typography>
                                    <Typography variant="body2">
                                        <strong>Visual:</strong>{" "}
                                        {selectedData.data.data.deskripsi?.visual}
                                    </Typography>
                                    <Typography variant="body2">
                                        <strong>Instrumental:</strong>{" "}
                                        {selectedData.data.data.deskripsi?.instrumental}
                                    </Typography>
                                    <Typography variant="body2">
                                        <strong>Reporter:</strong>{" "}
                                        {selectedData.data.data.pelapor}
                                    </Typography>
                                    <Typography variant="body2">
                                        <strong>Recommendation:</strong>
                                        <div
                                            dangerouslySetInnerHTML={{
                                                __html:
                                                selectedData.data.data.rekomendasi,
                                            }}
                                        />
                                    </Typography>
                                </Stack>
                            ) : (
                                <pre
                                    style={{
                                        background: "#f7f7f7",
                                        padding: "1rem",
                                        borderRadius: "6px",
                                        overflowX: "auto",
                                    }}
                                >
                                    {JSON.stringify(selectedData, null, 2)}
                                </pre>
                            )}
                        </Box>
                    ) : (
                        <Typography>No data available.</Typography>
                    )}
                </DialogContent>
                <DialogActions>
                    <Button onClick={handleCopy} color="primary" startIcon={<ContentCopy />}>
                        Copy JSON
                    </Button>
                    <Button onClick={handleClose} color="error">
                        Close
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
}
