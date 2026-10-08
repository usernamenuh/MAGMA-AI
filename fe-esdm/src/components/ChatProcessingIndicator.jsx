import React from "react";
import { Box, Typography } from "@mui/material";
import { keyframes } from "@mui/system";
import { PIPELINE_TYPE } from "@/utils/constants.jsx";
import AssistantIcon from "../assets/logo-esdm.png";

const spin = keyframes`
  to { transform: rotate(360deg); }
`;

const processingSteps = {
    [PIPELINE_TYPE.API_DOCUMENTATION]: [
        "Menghubungi MAGMA",
        "Memeriksa data PVMBG",
        "Menyusun jawaban",
    ],
    [PIPELINE_TYPE.KNOWLEDGE_BASE]: [
        "Mencari dokumen",
        "Memilih bagian relevan",
        "Menyusun jawaban",
    ],
};

export default function ChatProcessingIndicator({ pipelineType }) {
    const isKnowledgeBase = pipelineType === PIPELINE_TYPE.KNOWLEDGE_BASE;
    const steps = processingSteps[pipelineType] || processingSteps[PIPELINE_TYPE.API_DOCUMENTATION];

    return (
        <Box
            role="status"
            aria-live="polite"
            sx={{ display: "flex", alignItems: "flex-start", gap: 1.25, mb: 2, px: { xs: 0.5, sm: 2 } }}
        >
            <Box
                component="img"
                src={AssistantIcon}
                alt=""
                aria-hidden="true"
                sx={{ width: 34, height: 34, objectFit: "contain", borderRadius: "50%", flexShrink: 0 }}
            />
            <Box
                sx={{
                    width: { xs: "min(330px, calc(100% - 48px))", sm: 380 },
                    p: "13px 16px",
                    bgcolor: "#fff",
                    border: "1px solid #dbe5ef",
                    borderRadius: "16px 16px 16px 4px",
                    boxShadow: "0 5px 18px rgba(25, 55, 89, 0.06)",
                }}
            >
                <Box sx={{ display: "flex", alignItems: "center", gap: 1.25 }}>
                    <Box
                        aria-hidden="true"
                        sx={{
                            width: 28,
                            height: 28,
                            flexShrink: 0,
                            borderRadius: "50%",
                            border: "2.5px solid #dce8f3",
                            borderTopColor: "#1976d2",
                            animation: `${spin} 1s linear infinite`,
                            "@media (prefers-reduced-motion: reduce)": { animation: "none" },
                        }}
                    />
                    <Box>
                        <Typography sx={{ color: "#1e3a5f", fontSize: "0.84rem", fontWeight: 700, lineHeight: 1.35 }}>
                            {isKnowledgeBase ? "NARA sedang menelusuri dokumen" : "NARA sedang memproses data geologi"}
                        </Typography>
                        <Typography sx={{ color: "#64748b", fontSize: "0.73rem", lineHeight: 1.45 }}>
                            Mohon tunggu sebentar…
                        </Typography>
                    </Box>
                </Box>
                <Box
                    sx={{
                        display: "flex",
                        flexWrap: "wrap",
                        gap: "5px 12px",
                        mt: 1.25,
                        pt: 1.1,
                        borderTop: "1px solid #e7edf3",
                    }}
                >
                    {steps.map((step, index) => (
                        <Typography
                            key={step}
                            component="span"
                            sx={{ color: "#53677e", fontSize: "0.68rem", lineHeight: 1.5, textWrap: "pretty" }}
                        >
                            <Box component="span" sx={{ color: "#1976d2", fontWeight: 700, mr: 0.45 }}>
                                {String(index + 1).padStart(2, "0")}
                            </Box>
                            {step}
                        </Typography>
                    ))}
                </Box>
            </Box>
        </Box>
    );
}
