import React from "react";
import {
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Paper,
    Typography,
} from "@mui/material";

export default function DataTable({ data }) {
    if (!data.length)
        return (
            <Typography variant="body2" sx={{ p: 2 }}>
                No data found.
            </Typography>
        );

    const keys = Object.keys(data[0]);

    return (
        <TableContainer component={Paper} sx={{ maxHeight: 500 }}>
            <Table stickyHeader size="small">
                <TableHead>
                    <TableRow>
                        {keys.map((key) => (
                            <TableCell
                                key={key}
                                sx={{ fontWeight: 600, backgroundColor: "grey.100" }}
                            >
                                {key}
                            </TableCell>
                        ))}
                    </TableRow>
                </TableHead>
                <TableBody>
                    {data.map((row, i) => (
                        <TableRow key={i} hover>
                            {keys.map((key) => (
                                <TableCell key={key}>{String(row[key])}</TableCell>
                            ))}
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </TableContainer>
    );
}
