import React from "react";
import ReactMarkdown from "react-markdown";
import { Box } from "@mui/material";
import remarkGfm from "remark-gfm";

const MarkdownRenderer = ({ content }) => {
    return (
        <Box
            sx={{
                fontFamily: "inherit",
                fontSize: "0.95rem",
                lineHeight: 1.6,
                color: "text.primary",

                // Headings
                "& h1, & h2, & h3, & h4, & h5, & h6": {
                    fontWeight: 600,
                    marginTop: "1rem",
                    marginBottom: "0.5rem",
                },

                // Paragraphs
                "& p": {
                    margin: "0.5rem 0",
                },

                // Lists
                "& ul, & ol": {
                    paddingLeft: "1.5rem",
                    margin: "0.5rem 0",
                },

                // Code blocks
                "& pre": {
                    backgroundColor: "#f6f8fa",
                    padding: "0.75rem",
                    borderRadius: "8px",
                    overflowX: "auto",
                    fontFamily: "monospace",
                    fontSize: "0.85rem",
                },
                "& code": {
                    backgroundColor: "#f6f8fa",
                    padding: "0.15rem 0.3rem",
                    borderRadius: "4px",
                    fontFamily: "monospace",
                    fontSize: "0.85rem",
                },

                // Tables
                "& table": {
                    width: "100%",
                    borderCollapse: "collapse",
                    margin: "1rem 0",
                    fontSize: "0.9rem",
                },
                "& th, & td": {
                    border: "1px solid #ddd",
                    padding: "0.5rem 0.75rem",
                    textAlign: "left",
                },
                "& th": {
                    backgroundColor: "#f2f2f2",
                    fontWeight: 600,
                },
                "& tr:nth-of-type(even)": {
                    backgroundColor: "#fafafa",
                },
            }}
        >
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                    a: ({ node, ...props }) => {
                        void node;
                        return (
                        <a
                            {...props}
                            style={{
                                color: "#1976d2",
                                textDecoration: "underline",
                            }}
                            target="_blank"
                            rel="noopener noreferrer"
                        >
                            {props.children}
                        </a>
                        );
                    },
                }}
            >
                {content}
            </ReactMarkdown>
        </Box>
    );
};

export default MarkdownRenderer;
