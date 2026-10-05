import React, { useState } from "react";
import { Box, Typography, Button, IconButton, Paper, Tooltip } from "@mui/material";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import CheckIcon from "@mui/icons-material/Check";
import { BASE_URL } from "@/utils/constants.jsx";

const CodeBlock = ({ code }) => {
    const [copied, setCopied] = useState(false);

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(code);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (err) {
            console.error("Failed to copy!", err);
        }
    };

    return (
        <Box
            sx={{
                position: "relative",
                minWidth: 0,
                bgcolor: "#17212b",
                color: "#dce6ee",
                p: { xs: 1.5, md: 2 },
                pr: 6,
                borderRadius: 1.75,
                fontFamily: "'Fira Code', 'Roboto Mono', monospace",
                fontSize: "0.8rem",
                my: 1.5,
                border: "1px solid #263746",
            }}
        >
            <Tooltip title={copied ? "Kode tersalin" : "Salin kode"}>
                <IconButton
                    aria-label={copied ? "Kode tersalin" : "Salin kode"}
                    onClick={handleCopy}
                    size="small"
                    sx={{
                        position: "absolute",
                        top: 8,
                        right: 8,
                        color: copied ? "#4caf50" : "#999",
                        bgcolor: "rgba(255,255,255,0.05)",
                        "&:hover": { bgcolor: "rgba(255,255,255,0.1)" },
                    }}
                >
                    {copied ? <CheckIcon fontSize="small" /> : <ContentCopyIcon fontSize="small" />}
                </IconButton>
            </Tooltip>
            <pre style={{ margin: 0, overflowX: "auto", whiteSpace: "pre", lineHeight: 1.6 }}>
        <code>{code}</code>
      </pre>
        </Box>
    );
};

export default function ApiDocumentationPage() {
    const curlApiKey = `# Use your generated API key
API_KEY="PASTE_API_KEY"

curl -X POST "${BASE_URL}/api/analyze" \\
  -H "Authorization: $API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
  "user_input": "string",
  "session_id": "string",
  "geo_location": [null, null]
}'`;

    const curlLogin = `# 1. Login to obtain an access token
curl -X POST "${BASE_URL}/auth/login" \\
  -H "Content-Type: application/json" \\
  -d '{
    "email": "YOUR_EMAIL",
    "password": "YOUR_PASSWORD"
  }'`;

    const curlBearer = `# 2. Use the access token to call the API
ACCESS_TOKEN="PASTE_ACCESS_TOKEN"

curl -X POST "${BASE_URL}/api/analyze" \\
  -H "Authorization: Bearer $ACCESS_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
  "user_input": "string",
  "session_id": "string",
  "geo_location": [null, null]
}'`;

    const curlRAGApiDocId = `# Use your generated API key
curl -X POST "${BASE_URL}/api/analyze" \\
  -H "Authorization: $API_KEY or $ACCESS_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
  "user_input": "string",
  "session_id": "string",
  "geo_location": [null, null]
}'`;
    const curlRAGApiDocEn = `# Use your generated API key
curl -X POST "${BASE_URL}/api/analyze-en" \\
  -H "Authorization: $API_KEY or $ACCESS_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
  "user_input": "string",
  "session_id": "string",
  "geo_location": [null, null]
}'`;

    const curlRAGKBId = `# Use your generated API key
curl -X POST "${BASE_URL}/api/knowledge/analyze" \\
  -H "Authorization: $API_KEY or $ACCESS_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
  "user_input": "string",
  "session_id": "string",
  "geo_location": [null, null]
}'`;
    const curlRAGKBEn = `# Use your generated API key
curl -X POST "${BASE_URL}/api/knowledge/analyze-en" \\
  -H "Authorization: $API_KEY or $ACCESS_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
  "user_input": "string",
  "session_id": "string",
  "geo_location": [null, null]
}'`;

    return (
        <Box
            sx={{
                pt: { xs: 2, md: 2.5 },
                flex: 1,
                px: { xs: 2, md: 4 },
                pb: 5,
                bgcolor: "#f8fafc",
                color: "#1a1a1a",
                height: "100%",
                minHeight: 0,
                boxSizing: "border-box",
                overflowY: "auto",
                overflowX: "hidden",
                width: "100%",
                maxWidth: "none",
            }}
        >
            <Box sx={{ mb: 2.5 }}>
                <Typography variant="h5" fontWeight={700} sx={{ color: '#18212b', letterSpacing: '-0.02em' }}>API Documentation</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, maxWidth: 760 }}>
                    Referensi endpoint, autentikasi, dan contoh penggunaan layanan.
                </Typography>
            </Box>

            <Paper elevation={0} sx={{ p: { xs: 2, md: 2.5 }, border: '1px solid #e2e7eb', borderRadius: 2.5, mb: 2 }}>
            <Typography variant="subtitle1" fontWeight={700} sx={{ color: '#243b53', mb: 0.5 }}>Dokumentasi interaktif</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.7, mb: 2 }}>
                Gunakan Swagger UI untuk melihat skema endpoint dan mencoba request langsung.
            </Typography>
            <Box component="ol" sx={{ pl: 2.5, my: 0, mb: 1, maxWidth: 760, '& li': { pl: 0.5 } }}>
                <li>
                    <Typography variant="body2" mb={1}>
                        Buka dokumentasi FastAPI melalui tombol di bawah.
                    </Typography>
                </li>
                <li>
                    <Typography variant="body2" mb={1}>
                        Di Swagger UI, pilih endpoint yang ingin dicoba.
                    </Typography>
                </li>
                <li>
                    <Typography variant="body2" mb={1}>
                        Klik <strong>Authorize</strong> di kanan atas.
                    </Typography>
                </li>
                <li>
                    <Typography variant="body2" mb={1}>
                        Masukkan API key atau access token yang sudah dibuat.
                    </Typography>
                </li>
                <li>
                    <Typography variant="body2" mb={1}>
                        Jalankan request dan lihat respons langsung di halaman tersebut.
                    </Typography>
                </li>
            </Box>

            <Button
                variant="contained"
                disableElevation
                href={`${BASE_URL}/docs`}
                target="_blank"
                rel="noopener noreferrer"
                sx={{ borderRadius: 1.75, px: 2, boxShadow: 'none', '&:hover': { boxShadow: 'none' } }}
            >
                Buka Swagger UI
            </Button>
            </Paper>

            <Paper elevation={0} sx={{ p: { xs: 2, md: 3 }, border: '1px solid #e2e7eb', borderRadius: 2.5, mb: 2 }}>
            <Typography variant="subtitle1" fontWeight={700} sx={{ color: '#243b53' }} gutterBottom>
                Autentikasi dengan API key
            </Typography>
            <Typography variant="body2" mb={1} color="text.secondary">
                Sertakan API key pada header <code>Authorization</code> untuk request dari server.
            </Typography>
            <CodeBlock code={curlApiKey} />
            </Paper>

            <Paper elevation={0} sx={{ p: { xs: 2, md: 3 }, border: '1px solid #e2e7eb', borderRadius: 2.5, mb: 2 }}>
            <Typography variant="subtitle1" fontWeight={700} sx={{ color: '#243b53' }} gutterBottom>
                Autentikasi pengguna (JWT)
            </Typography>
            <Typography variant="body2" color="text.secondary" mb={2}>
                Pengguna yang masuk dapat memperoleh <code>access_token</code> melalui endpoint login.
            </Typography>

            <Typography variant="subtitle2" fontWeight={700}>1. Masuk</Typography>
            <CodeBlock code={curlLogin} />

            <Typography variant="subtitle2" fontWeight={700} sx={{ mt: 3 }}>2. Request dengan token</Typography>
            <CodeBlock code={curlBearer} />
            </Paper>

            <Paper elevation={0} sx={{ p: { xs: 2, md: 3 }, border: '1px solid #e2e7eb', borderRadius: 2.5, mb: 2 }}>
            <Typography variant="subtitle1" fontWeight={700} sx={{ color: '#243b53' }} gutterBottom>
                Chat dari data API
            </Typography>
            <Typography variant="subtitle2" fontWeight={700}>Bahasa Indonesia</Typography>
            <CodeBlock code={curlRAGApiDocId} />

            <Typography variant="subtitle2" fontWeight={700} sx={{ mt: 3 }}>Bahasa Inggris</Typography>
            <CodeBlock code={curlRAGApiDocEn} />
            </Paper>

            <Paper elevation={0} sx={{ p: { xs: 2, md: 3 }, border: '1px solid #e2e7eb', borderRadius: 2.5, mb: 2 }}>
            <Typography variant="subtitle1" fontWeight={700} sx={{ color: '#243b53' }} gutterBottom>
                Chat dari Knowledge Base
            </Typography>
            <Typography variant="subtitle2" fontWeight={700}>Bahasa Indonesia</Typography>
            <CodeBlock code={curlRAGKBId} />

            <Typography variant="subtitle2" fontWeight={700} sx={{ mt: 3 }}>Bahasa Inggris</Typography>
            <CodeBlock code={curlRAGKBEn} />
            </Paper>

            <Box sx={{ bgcolor: "#fff8eb", p: { xs: 2, md: 2.5 }, borderRadius: 2.5, border: '1px solid #f6dfb5' }}>
                <Typography variant="subtitle2" fontWeight={700} color="#e65100" gutterBottom>
                    Catatan penting
                </Typography>
                <Typography variant="body2" sx={{ mb: 1 }}>
                    • Buat dan kelola key di halaman <strong>API Keys</strong>.
                </Typography>
                <Typography variant="body2" sx={{ mb: 1 }}>
                    • <strong>Access token</strong> memiliki masa berlaku. Masuk kembali jika menerima respons <code>401 Unauthorized</code>.
                </Typography>
                <Typography variant="body2">
                    • Semua waktu pada respons API menggunakan <strong>UTC</strong>.
                </Typography>
            </Box>
        </Box>
    );
}
