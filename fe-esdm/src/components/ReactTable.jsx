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
    TableFooter,
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
        footerGroups,
        state: { pageIndex, pageSize },
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
                border: '1px solid',
                borderColor: 'divider',
                boxShadow: 'none',
            }}
        >
            <Table {...getTableProps()} {...tableStyle}>
                <TableHead {...tHeadStyle} sx={{ bgcolor: '#f7f7f7', ...thStyle }}>
                    {headerGroups.map(headerGroup => (
                        <TableRow
                            {...headerGroup.getHeaderGroupProps()}
                            key={headerGroup.getHeaderGroupProps().key}
                            {...trStyle}
                        >
                            {headerGroup.headers.map(column => (
                                <TableCell
                                    key={column.id}
                                    sx={{ fontWeight: 'bold', fontSize: 14 }}
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
                                    sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
                                >
                                    {row.cells.map(cell => (
                                        <TableCell
                                            sx={{ py: 1.5, fontSize: 13, ...tdStyle }}
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

                <TableFooter>
                    {footerGroups.map(footerGroup => (
                        <TableRow {...footerGroup.getFooterGroupProps()} key={footerGroup.getFooterGroupProps().key}>
                            {footerGroup.headers.map(column => (
                                <TableCell {...column.getFooterProps()} key={column.getFooterProps().key}>
                                    {column.render('Footer')}
                                </TableCell>
                            ))}
                        </TableRow>
                    ))}
                </TableFooter>
            </Table>

            {/* Pagination control */}
            {total > 0 && (
                <Box
                    p={2}
                    sx={{
                        borderTop: '1px solid',
                        borderColor: 'divider',
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