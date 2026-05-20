import { Box, Pagination as MuiPagination } from "@mui/material";

export default function Pagination({ total, limit, current, onChange }) {
    const totalPages = Math.ceil(total / limit) || 1;
    if (totalPages <= 1) return null;

    return (
        <Box display="flex" justifyContent="center" mt={3}>
            <MuiPagination
                count={totalPages}
                page={current}
                onChange={(_, page) => onChange(page)}
                color="primary"
                showFirstButton
                showLastButton
            />
        </Box>
    );
}
