import React, { useState } from "react";
import { Box, Typography, Button, Divider, IconButton, Tooltip } from "@mui/material";
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
                bgcolor: "#1e1e1e",
                color: "#dcdcdc",
                p: 2,
                borderRadius: 2,
                fontFamily: "'Fira Code', 'Roboto Mono', monospace",
                fontSize: "0.875rem",
                my: 2,
                border: "1px solid #333",
            }}
        >
            <Tooltip title={copied ? "Copied!" : "Copy Code"}>
                <IconButton
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
            <pre style={{ margin: 0, overflowX: "auto", whiteSpace: "pre-wrap", wordBreak: "break-all" }}>
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
                pt: 5,
                flex: 1,
                px: { xs: 2, md: 4 },
                pb: 10,
                bgcolor: "#fbfbfb",
                color: "#1a1a1a",
                minHeight: "100vh",
                maxWidth: "900px",
            }}
        >
            {/* Header */}
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
                <Typography variant="h4" fontWeight={700}>
                    API Documentation
                </Typography>
            </Box>

            <Typography variant="body1" color="text.secondary" sx={{ lineHeight: 1.7 }}>
                This API provides an OpenAPI-compliant interface built with FastAPI.
                Explore endpoints, request/response schemas, and test live using Swagger UI.
            </Typography>

            <Divider sx={{ my: 4 }} />

            <Typography variant="h6" fontWeight={600} gutterBottom>
                Interactive API Documentation (Swagger UI)
            </Typography>

            <Box component="ol" sx={{ pl: 3 }}>
                <li>
                    <Typography variant="body1" mb={1}>
                        Open the FastAPI documentation page by clicking the button below.
                    </Typography>
                </li>
                <li>
                    <Typography variant="body1" mb={1}>
                        You will be redirected to the interactive Swagger UI.
                    </Typography>
                </li>
                <li>
                    <Typography variant="body1" mb={1}>
                        Click the <strong>Authorize</strong> button on the top-right corner.
                    </Typography>
                </li>
                <li>
                    <Typography variant="body1" mb={1}>
                        Paste your generated API key or access token and submit.
                    </Typography>
                </li>
                <li>
                    <Typography variant="body1" mb={1}>
                        You can now test protected endpoints directly from the documentation.
                    </Typography>
                </li>
            </Box>

            <Button
                variant="contained"
                disableElevation
                href={`${BASE_URL}/docs`}
                target="_blank"
                rel="noopener noreferrer"
                sx={{ borderRadius: 2, px: 4 }}
            >
                Open Swagger UI
            </Button>

            <Divider sx={{ my: 4 }} />

            {/* API Key Usage */}
            <Typography variant="h6" fontWeight={600} gutterBottom>
                Using the Generated API Key
            </Typography>
            <Typography variant="body2" mb={1} color="text.secondary">
                Include your API Key in the <code>Authorization</code> header for server-to-server requests.
            </Typography>
            <CodeBlock code={curlApiKey} />

            <Divider sx={{ my: 4 }} />

            {/* Bearer Token Usage */}
            <Typography variant="h6" fontWeight={600} gutterBottom>
                Authenticated User Access (JWT)
            </Typography>
            <Typography variant="body2" color="text.secondary" mb={2}>
                For logged-in users, obtain an <code>access_token</code> via the login endpoint.
            </Typography>

            <Typography variant="subtitle2" fontWeight={700}>1. Login</Typography>
            <CodeBlock code={curlLogin} />

            <Typography variant="subtitle2" fontWeight={700} sx={{ mt: 3 }}>2. Authorized Request</Typography>
            <CodeBlock code={curlBearer} />

            <Divider sx={{ my: 4 }} />

            <Typography variant="h6" fontWeight={600} gutterBottom>
                Chat using API Documentation
            </Typography>
            <Typography variant="subtitle2" fontWeight={700}>1. Using Indonesian Language</Typography>
            <CodeBlock code={curlRAGApiDocId} />

            <Typography variant="subtitle2" fontWeight={700} sx={{ mt: 3 }}>2. Using English Language</Typography>
            <CodeBlock code={curlRAGApiDocEn} />

            <Divider sx={{ my: 4 }} />

            <Typography variant="h6" fontWeight={600} gutterBottom>
                Chat using Knowledge Base
            </Typography>
            <Typography variant="subtitle2" fontWeight={700}>1. Using Indonesian Language</Typography>
            <CodeBlock code={curlRAGKBId} />

            <Typography variant="subtitle2" fontWeight={700} sx={{ mt: 3 }}>2. Using English Language</Typography>
            <CodeBlock code={curlRAGKBEn} />

            <Divider sx={{ my: 4 }} />

            {/* Notes */}
            <Box sx={{ bgcolor: "#fff3e0", p: 3, borderRadius: 2, borderLeft: "4px solid #ff9800" }}>
                <Typography variant="subtitle2" fontWeight={700} color="#e65100" gutterBottom>
                    Important Notes
                </Typography>
                <Typography variant="body2" sx={{ mb: 1 }}>
                    • Generate and manage keys in the <strong>API Keys</strong> dashboard.
                </Typography>
                <Typography variant="body2" sx={{ mb: 1 }}>
                    • <strong>Access tokens</strong> have a limited lifespan. Use refresh tokens or re-login if you receive a <code>401 Unauthorized</code> error.
                </Typography>
                <Typography variant="body2">
                    • All timestamps returned are in <strong>UTC</strong>.
                </Typography>
            </Box>
        </Box>
    );
}