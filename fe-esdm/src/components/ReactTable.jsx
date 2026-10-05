// src/components/ReactTable.jsx

import {
    Box,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableRow,
    Typography,
    Paper,
    TableContainer,
    Pagination,
    PaginationItem,
    CircularProgress,
} from '@mui/material';
import React, { useEffect } from 'react';
import { useTable, usePagination } from 'react-table';
import { LoadingButton as Button } from '@mui/lab';

const DEFAULT_PAGINATION_COUNT = 10;
const DEFAULT_PAGINATION_PAGE_NO = 0;
const noop = () => {};

const t = (key, params) => {
    if (key === 'showingPage') return `Showing ${params.length} of ${params.total} items`;
    if (key === 'Previous') return 'Previous';
    if (key === 'Next') return 'Next';
    return key;
};

const ReactTable = ({
                        data,
                        count = DEFAULT_PAGINATION_COUNT,
                        total = 0,
                        columns,
                        tableStyle,
                        tHeadStyle,
                        tBodyStyle,
                        trStyle,
                        thStyle,
                        tdStyle,
                        gotoPage: _gotoPage = noop,
                        loading = false,
                    }) => {
    const {
        getTableProps,
        getTableBodyProps,
        headerGroups,
        rows,
        prepareRow,
        pageOptions = [],
        gotoPage,
        state: { pageIndex },
    } = useTable(
        {
            columns,
            data,
            // Essential for manual (server-side) pagination
            manualPagination: true,
            pageCount: Math.ceil(total / count),
            initialState: { pageIndex: DEFAULT_PAGINATION_PAGE_NO, pageSize: count },
        },
        usePagination
    );

    useEffect(() => {
        _gotoPage(pageIndex);
    }, [pageIndex, _gotoPage]);

    return (
        <TableContainer
            component={Paper}
            elevation={0}
            sx={{
                borderRadius: '6px',
                border: '1px solid #e2e7eb',
                boxShadow: '0 1px 2px rgba(15, 23, 42, 0.03)',
                overflowX: 'auto',
                bgcolor: '#fff',
            }}
        >
            <Table {...getTableProps()} {...tableStyle} sx={{ minWidth: 920, borderCollapse: 'separate', borderSpacing: 0 }}>
                <TableHead {...tHeadStyle} sx={{ bgcolor: '#f6f8fa', ...thStyle }}>
                    {headerGroups.map(headerGroup => (
                        <TableRow
                            {...headerGroup.getHeaderGroupProps()}
                            key={headerGroup.getHeaderGroupProps().key}
                            {...trStyle}
                        >
                            {headerGroup.headers.map(column => (
                                <TableCell
                                    key={column.id}
                                    sx={{
                                        py: 1.65,
                                        fontWeight: 700,
                                        fontSize: 11,
                                        letterSpacing: 0.25,
                                        textTransform: 'uppercase',
                                        color: '#52606d',
                                        borderColor: '#e2e7eb',
                                        whiteSpace: 'nowrap',
                                    }}
                                >
                                    {column.render('Header')}
                                </TableCell>
                            ))}
                        </TableRow>
                    ))}
                </TableHead>
                <TableBody {...getTableBodyProps()} {...tBodyStyle}>
                    {loading ? (
                        <TableRow>
                            <TableCell colSpan={columns.length} sx={{ textAlign: 'center' }}>
                                <Box
                                    width="100%"
                                    display="flex"
                                    justifyContent="center"
                                    alignItems="center"
                                    py={3}
                                >
                                    <CircularProgress size={20} />
                                    <Typography ml={2}>Loading data...</Typography>
                                </Box>
                            </TableCell>
                        </TableRow>
                    ) : (
                        rows.map(row => {
                            prepareRow(row);
                            return (
                                <TableRow
                                    {...row.getRowProps()}
                                    key={row.getRowProps().key}
                                    {...trStyle}
                                    sx={{
                                        transition: 'background-color 140ms ease',
                                        '&:hover': { bgcolor: '#f8fafc' },
                                        '&:last-child td, &:last-child th': { borderBottom: 0 },
                                    }}
                                >
                                    {row.cells.map(cell => (
                                        <TableCell
                                            sx={{ py: 1.8, fontSize: 13, borderColor: '#edf0f2', ...tdStyle }}
                                            {...cell.getCellProps()}
                                            key={cell.getCellProps().key}
                                        >
                                            {cell.render('Cell')}
                                        </TableCell>
                                    ))}
                                </TableRow>
                            );
                        })
                    )}
                </TableBody>

            </Table>

            {/* Pagination control */}
            {total > 0 && (
                <Box
                    px={2}
                    py={1.25}
                    sx={{
                        borderTop: '1px solid #edf0f2',
                    }}
                >
                    <Box display="flex" alignItems="center" justifyContent="space-between">
                        <Typography variant="body2" color="text.secondary">
                            {t('showingPage', { length: rows.length, total: total })}
                        </Typography>

                        <Pagination
                            count={pageOptions.length}
                            variant="outlined"
                            color="primary"
                            size="small"
                            page={pageIndex + 1}
                            onChange={(e, value) => gotoPage(value - 1)}
                            renderItem={item => (
                                <PaginationItem
                                    components={{
                                        previous: props => (
                                            <Button
                                                {...props}
                                                sx={{ textTransform: 'none', fontSize: '0.75rem' }}
                                            >
                                                <Typography variant="body2" color="text.secondary">

                                                {t('Previous')}
                                                </Typography>
                                            </Button>
                                        ),
                                        next: props => (
                                            <Button
                                                {...props}
                                                sx={{ textTransform: 'none', fontSize: '0.75rem' }}
                                            >
                                                <Typography variant="body2" color="text.secondary">
                                                    {t('Next')}
                                                </Typography>
                                            </Button>
                                        ),
                                    }}
                                    {...item}
                                />
                            )}
                        />
                    </Box>
                </Box>
            )}
            {/* Empty state when no results and not loading */}
            {total === 0 && !loading && (
                <Box p={3} textAlign="center" color="text.secondary">
                    No document data found.
                </Box>
            )}
        </TableContainer>
    );
};

export default ReactTable;
