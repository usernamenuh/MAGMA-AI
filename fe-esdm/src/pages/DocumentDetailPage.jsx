/* eslint-disable react-hooks/exhaustive-deps */
import React, { useEffect, useRef, useState } from "react";
import {
    Box,
    Typography,
    Paper,
    Button,
    CircularProgress,
    Alert,
    Chip,
    Dialog,
    DialogContent,
    DialogTitle,
    DialogActions,
    IconButton,
    FormControlLabel,
    Radio,
    RadioGroup,
    TextField,
    useMediaQuery,
} from "@mui/material";
import { ArrowBack, Close, DescriptionOutlined, InsertDriveFileOutlined, PictureAsPdfOutlined, ReplayOutlined } from "@mui/icons-material";
import { useParams, useNavigate } from "react-router-dom";
import { useKnowledgeBase } from "@/hooks/useKnowledgeBase";

export default function DocumentDetailPage() {
    const { documentId } = useParams();
    const navigate = useNavigate();
    const { getDocumentDetails, getAnnotatedPdf, retryDocument, addManualText, loading, error } = useKnowledgeBase();
    const [document, setDocument] = useState(null);
    const [chunks, setChunks] = useState([]);
    const [pdfOpen, setPdfOpen] = useState(false);
    const [pdfUrl, setPdfUrl] = useState(null);
    const [pdfLoading, setPdfLoading] = useState(false);
    const [pdfError, setPdfError] = useState(null);
    const [pdfLetterCounts, setPdfLetterCounts] = useState(null);
    const [retryOpen, setRetryOpen] = useState(false);
    const [retryMode, setRetryMode] = useState('docling_no_ocr');
    const [retryBusy, setRetryBusy] = useState(false);
    const [retryError, setRetryError] = useState(null);
    const [manualOpen, setManualOpen] = useState(false);
    const [manualText, setManualText] = useState('');
    const [manualPage, setManualPage] = useState(1);
    const [manualBusy, setManualBusy] = useState(false);
    const [manualError, setManualError] = useState(null);
    const [showAllMissing, setShowAllMissing] = useState(false);
    const pdfRequest = useRef(0);
    const isMobile = useMediaQuery('(max-width:600px)');

    useEffect(() => {
        fetchDocumentDetails();
    }, [documentId]);

    useEffect(() => {
        const status = document?.status?.toUpperCase();
        if (status !== 'QUEUED' && status !== 'PROCESSING') return undefined;
        const timer = window.setTimeout(() => fetchDocumentDetails(true), 3000);
        return () => window.clearTimeout(timer);
    }, [document, documentId]);

    useEffect(() => () => {
        if (pdfUrl) URL.revokeObjectURL(pdfUrl);
    }, [pdfUrl]);

    const closePdf = () => {
        pdfRequest.current += 1;
        setPdfOpen(false);
        setPdfUrl(null);
        setPdfError(null);
        setPdfLetterCounts(null);
    };

    const openPdf = async () => {
        const request = ++pdfRequest.current;
        setPdfOpen(true);
        setPdfLoading(true);
        setPdfError(null);
        setPdfLetterCounts(null);
        try {
            const { blob, pdfLetters, storedLetters } = await getAnnotatedPdf(documentId);
            if (request !== pdfRequest.current) return;
            setPdfUrl(URL.createObjectURL(blob));
            if (Number.isFinite(pdfLetters) && Number.isFinite(storedLetters)) {
                setPdfLetterCounts({ pdfLetters, storedLetters });
            }
        } catch (err) {
            if (request !== pdfRequest.current) return;
            setPdfError('PDF bertanda belum dapat dibuka. Coba lagi beberapa saat.');
        } finally {
            if (request === pdfRequest.current) setPdfLoading(false);
        }
    };

    const fetchDocumentDetails = async (silent = false) => {
        try {
            const data = await getDocumentDetails(documentId, { silent });
            setDocument(data.document);
            setChunks(data.chunks);
        } catch (err) {
            console.error("Failed to fetch document details:", err);
            if (!silent) {
                setDocument(null);
                setChunks([]);
            }
        }
    };

    const submitRetry = async () => {
        setRetryBusy(true);
        setRetryError(null);
        try {
            await retryDocument(documentId, retryMode);
            setRetryOpen(false);
            await fetchDocumentDetails(true);
        } catch (err) {
            setRetryError(err.response?.data?.detail || 'Dokumen belum dapat diproses ulang. Coba lagi.');
        } finally {
            setRetryBusy(false);
        }
    };

    const openManual = (item = null) => {
        setManualText(item?.text || '');
        setManualPage(item?.page || 1);
        setManualError(null);
        setManualOpen(true);
    };

    const submitManual = async () => {
        setManualBusy(true);
        setManualError(null);
        try {
            await addManualText(documentId, manualText.trim(), Number(manualPage));
            setManualOpen(false);
            await fetchDocumentDetails(true);
            if (pdfOpen) closePdf();
        } catch (err) {
            setManualError(err.response?.data?.detail || 'Teks belum dapat disimpan. Coba lagi.');
        } finally {
            setManualBusy(false);
        }
    };

    const getStatusTone = (status) => {
        const value = (status || '').toLowerCase();
        if (value === 'completed') return { label: 'Selesai diproses', bg: '#eaf7ef', color: '#1f7a3d' };
        if (value === 'incomplete') return { label: 'Kurang lengkap', bg: '#fff4dc', color: '#9a6700' };
        if (value === 'failed') return { label: 'Gagal diproses', bg: '#fcebec', color: '#b4232c' };
        return { label: status || 'Sedang diproses', bg: '#fff4dc', color: '#9a6700' };
    };

    return (
        <Box sx={{
            pt: { xs: 2, md: 5 },
            flex: 1,
            px: { xs: 2, md: 4 },
            pb: 5,
            display: "flex",
            flexDirection: "column",
            height: "100%",
            minHeight: 0,
            boxSizing: "border-box",
            overflowY: "auto",
            overflowX: "hidden",
            bgcolor: "#f8fafc",
            color: "#000000",
        }}>
            <Button
                startIcon={<ArrowBack sx={{ fontSize: 18 }} />}
                onClick={() => navigate(-1)}
                variant="outlined"
                color="inherit"
                sx={{
                    alignSelf: 'flex-start',
                    mb: 2.5,
                    px: 1.35,
                    py: 0.65,
                    textTransform: 'none',
                    borderRadius: 1.75,
                    borderColor: '#d8e0e6',
                    color: '#425466',
                    fontSize: 13,
                    fontWeight: 600,
                    bgcolor: '#fff',
                    '&:hover': { borderColor: '#b8c6d1', bgcolor: '#f8fafc' },
                }}
            >
                Daftar dokumen
            </Button>
            <Box sx={{ mb: 3 }}>
                <Typography variant="h5" fontWeight={700} sx={{ color: '#18212b', letterSpacing: '-0.02em' }}>Detail dokumen</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>Baca teks yang benar-benar tersimpan dari dokumen ini.</Typography>
            </Box>

            <Box sx={{ width: '100%', maxWidth: 'none', pb: 3 }}>
                {loading && (
                    <Box display="flex" justifyContent="center" py={4}>
                        <CircularProgress />
                    </Box>
                )}
                {error && (
                    <Alert severity="error" sx={{ mb: 2 }}>
                        Error loading details: {error.message || String(error)}
                    </Alert>
                )}

                {document && (
                    <Box>
                        {(() => {
                            const tone = getStatusTone(document.status);
                            const hasPreview = /\.(pdf|docx?|DOCX?)$/i.test(document.filename || '');
                            const detailMetrics = [
                                { label: 'Halaman dokumen', value: document.total_pages ?? '—' },
                                { label: 'Jumlah chunk', value: chunks.length },
                                { label: 'Bagian penting belum masuk', value: document.important_text_missing ?? '—' },
                                { label: 'Cakupan audit', value: Number.isFinite(document.extraction_coverage_percent) ? `${document.extraction_coverage_percent}%` : 'Belum dapat diukur' },
                                ...(hasPreview ? [
                                    { label: 'Huruf pada dokumen', value: Number.isFinite(document.text_counts?.source_letters) ? document.text_counts.source_letters.toLocaleString('id-ID') : 'Tidak terbaca' },
                                    { label: 'Huruf dalam database', value: Number.isFinite(document.text_counts?.stored_letters) ? document.text_counts.stored_letters.toLocaleString('id-ID') : '—' },
                                ] : []),
                            ];
                            return (
                                <Paper sx={{ p: { xs: 2, md: 2.5 }, border: '1px solid #e2e7eb', borderRadius: 2.5, boxShadow: '0 1px 2px rgba(15,23,42,.02)' }}>
                                    <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1.5, mb: { xs: 2, md: 2.5 }, flexWrap: 'wrap' }}>
                                        <Box sx={{ width: 44, height: 44, borderRadius: 2.5, bgcolor: '#edf4fa', color: '#28536f', display: 'grid', placeItems: 'center', flexShrink: 0 }}><DescriptionOutlined /></Box>
                                        <Box sx={{ minWidth: 0, flex: 1 }}>
                                            <Typography variant="h6" fontWeight={700} sx={{ color: '#243b53', overflowWrap: 'anywhere' }}>{document.filename}</Typography>
                                            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.25 }}>ID Dokumen: {document.id}</Typography>
                                        </Box>
                                        <Box sx={{ display: 'flex', flexDirection: { xs: 'row', sm: 'column' }, alignItems: { xs: 'center', sm: 'flex-end' }, justifyContent: { xs: 'space-between', sm: 'flex-start' }, gap: 1, width: { xs: '100%', sm: 'auto' }, ml: { xs: 0, sm: 1 } }}>
                                            <Chip label={tone.label} size="small" sx={{ flexShrink: 0, height: 26, fontWeight: 700, fontSize: 11, borderRadius: 1.25, bgcolor: tone.bg, color: tone.color }} />
                                            {hasPreview && chunks.length > 0 && (
                                                <Button
                                                    variant="outlined"
                                                    startIcon={<PictureAsPdfOutlined />}
                                                    onClick={openPdf}
                                                    sx={{ minHeight: { xs: 44, sm: 36 }, px: 1.5, whiteSpace: 'nowrap', textTransform: 'none', borderRadius: 1.5, borderColor: '#cbd8e2', color: '#284967', fontSize: 12.5, fontWeight: 700, '&:hover': { borderColor: '#8faabe', bgcolor: '#f5f9fc' } }}
                                                >
                                                    Lihat PDF bertanda
                                                </Button>
                                            )}
                                        </Box>
                                    </Box>
                                    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: 'repeat(2, minmax(0, 1fr))', md: 'repeat(3, minmax(0, 1fr))' }, borderTop: '1px solid #e9edf0', borderBottom: '1px solid #e9edf0' }}>
                                        {detailMetrics.map((metric, index) => (
                                            <Box key={metric.label} sx={{ minWidth: 0, py: 1.75, px: { xs: index % 2 ? 1.5 : 0, md: index % 3 ? 2 : 0 }, borderLeft: { xs: index % 2 ? '1px solid #e9edf0' : 0, md: index % 3 ? '1px solid #e9edf0' : 0 }, borderTop: { xs: index >= 2 ? '1px solid #e9edf0' : 0, md: index >= 3 ? '1px solid #e9edf0' : 0 } }}>
                                                <Typography variant="caption" sx={{ color: '#657586', fontSize: 11.5, display: 'block', lineHeight: 1.4 }}>{metric.label}</Typography>
                                                <Typography sx={{ mt: 0.4, color: '#243b53', fontSize: { xs: 17, md: 19 }, lineHeight: 1.25, fontWeight: 700, fontVariantNumeric: 'tabular-nums', overflowWrap: 'anywhere' }}>{metric.value}</Typography>
                                            </Box>
                                        ))}
                                    </Box>
                                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 1, mt: 1.25 }}>
                                        <Typography variant="caption" color="text.secondary">
                                            {hasPreview ? 'Jumlah huruf tidak termasuk spasi, angka, atau tanda baca. Cakupan audit menghitung bagian teks penting, bukan persentase huruf.' : 'Chunk tersimpan dapat digunakan sebagai referensi jawaban.'}
                                        </Typography>
                                        {['COMPLETED', 'INCOMPLETE', 'FAILED'].includes(document.status?.toUpperCase()) && (
                                            <Button
                                                size="small"
                                                startIcon={<ReplayOutlined />}
                                                onClick={() => { setRetryMode('docling_no_ocr'); setRetryError(null); setRetryOpen(true); }}
                                                sx={{ textTransform: 'none', fontWeight: 700, color: '#284967', minHeight: 36, px: 1 }}
                                            >
                                                Proses lanjutan
                                            </Button>
                                        )}
                                    </Box>
                                </Paper>
                            );
                        })()}

                        {(document.important_text_missing > 0 || document.extraction_audit_status === 'OCR_REVIEW_REQUIRED') && (
                            <Alert severity="warning" sx={{ mt: 2, borderRadius: 2 }}>
                                {document.important_text_missing > 0
                                    ? `${document.important_text_missing} dari ${document.important_text_total} bagian teks penting belum terdeteksi dalam chunk tersimpan. Teks yang sudah terbaca tetap dapat digunakan.`
                                    : 'Kelengkapan teks belum dapat diverifikasi otomatis. Periksa PDF bertanda dan tambahkan teks penting bila perlu.'}
                            </Alert>
                        )}

                        {['COMPLETED', 'INCOMPLETE'].includes(document.status?.toUpperCase()) && (
                            <Paper elevation={0} sx={{ mt: 2, p: { xs: 2, md: 2.5 }, border: '1px solid #e2e7eb', borderRadius: 2.5 }}>
                                <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 2, flexWrap: 'wrap' }}>
                                    <Box>
                                        <Typography variant="subtitle1" fontWeight={700} sx={{ color: '#243b53' }}>Teks yang perlu diperiksa</Typography>
                                        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                                            Hasil perbandingan otomatis dengan dokumen sumber. Periksa sebelum menambahkan teks.
                                        </Typography>
                                    </Box>
                                    <Button variant="outlined" onClick={() => openManual()} sx={{ textTransform: 'none', borderColor: '#cbd8e2', color: '#284967' }}>
                                        Tambahkan teks manual
                                    </Button>
                                </Box>
                                {(document.missing_important_text || []).length > 0 ? (
                                    <Box sx={{ display: 'grid', gap: 1, mt: 2 }}>
                                        {(showAllMissing ? document.missing_important_text : document.missing_important_text.slice(0, 8)).map((item, index) => (
                                            <Box key={`${item.page}-${index}`} sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 2, p: 1.5, border: '1px solid #e9edf0', borderRadius: 1.5, bgcolor: '#fbfcfd' }}>
                                                <Box sx={{ minWidth: 0 }}>
                                                    <Typography variant="caption" sx={{ color: '#657586', fontWeight: 700 }}>Halaman {item.page}</Typography>
                                                    <Typography variant="body2" sx={{ mt: 0.4, color: '#263746', whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{item.text}</Typography>
                                                </Box>
                                                <Button size="small" onClick={() => openManual(item)} sx={{ flexShrink: 0, textTransform: 'none' }}>Tambahkan</Button>
                                            </Box>
                                        ))}
                                        {document.missing_important_text.length > 8 && (
                                            <Button onClick={() => setShowAllMissing((current) => !current)} sx={{ justifySelf: 'start', textTransform: 'none' }}>
                                                {showAllMissing ? 'Tampilkan lebih sedikit' : `Lihat semua ${document.missing_important_text.length} bagian`}
                                            </Button>
                                        )}
                                    </Box>
                                ) : (
                                    <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                                        {document.extraction_audit_status === 'COMPLETE' ? 'Tidak ada bagian teks penting yang tertinggal menurut audit.' : 'Daftar bagian yang tertinggal belum tersedia untuk dokumen ini.'}
                                    </Typography>
                                )}
                            </Paper>
                        )}

                        {['QUEUED', 'PROCESSING'].includes(document.status?.toUpperCase()) && (
                            <Alert severity="info" sx={{ mt: 2, borderRadius: 2 }}>
                                Ekstraksi ulang sedang berjalan. Chunk lama tetap ditampilkan sampai hasil baru siap.
                            </Alert>
                        )}

                        {document.processing_message?.startsWith('Ekstraksi ulang gagal') && (
                            <Alert severity="warning" sx={{ mt: 2, borderRadius: 2 }}>
                                {document.processing_message}
                            </Alert>
                        )}

                        <Paper elevation={0} sx={{ mt: 2, p: { xs: 2, md: 2.5 }, border: '1px solid #e2e7eb', borderRadius: 2.5 }}>
                            <Typography variant="subtitle1" fontWeight={700} sx={{ color: '#243b53' }}>Chunk dokumen</Typography>

                            {chunks.length > 0 ? (
                                <>
                                    <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                                        Potongan teks hasil ekstraksi yang tersimpan di database dan digunakan sebagai referensi jawaban.
                                    </Typography>
                                    <Box sx={{ display: 'grid', gap: 1.5, mt: 2 }}>
                                        {chunks.map((chunk, index) => (
                                            <Box
                                                component="article"
                                                key={chunk.embedding_id ?? `${chunk.page_number}-${index}`}
                                                sx={{ border: '1px solid #e2e7eb', borderRadius: 2, bgcolor: '#fff', overflow: 'hidden' }}
                                            >
                                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, px: { xs: 2, md: 2.5 }, py: 1.4, bgcolor: '#f8fafc', borderBottom: '1px solid #e9edf0' }}>
                                                    <InsertDriveFileOutlined sx={{ color: '#607d98', fontSize: 18, flexShrink: 0 }} />
                                                    <Typography variant="body2" fontWeight={700} sx={{ color: '#243b53' }}>
                                                        Halaman {chunk.page_number} <Box component="span" sx={{ mx: 0.5, color: '#9aa9b5', fontWeight: 400 }}>·</Box> Chunk {(chunk.chunk_index ?? index) + 1}
                                                    </Typography>
                                                </Box>
                                                <Typography
                                                    component="div"
                                                    sx={{ px: { xs: 2, md: 2.5 }, py: { xs: 2, md: 2.25 }, color: '#263746', fontSize: { xs: 15, sm: 16 }, lineHeight: 1.75, letterSpacing: '0.005em', whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', textWrap: 'pretty', maxWidth: '82ch' }}
                                                >
                                                    {chunk.content}
                                                </Typography>
                                            </Box>
                                        ))}
                                    </Box>
                                </>
                            ) : (
                                <Typography color="text.secondary" sx={{ mt: 1.5 }}>
                                    Belum ada teks tersimpan. Dokumen mungkin masih diproses.
                                </Typography>
                            )}
                        </Paper>
                    </Box>
                )}

                {!loading && !document && !error && (
                    <Typography align="center" py={4} color="text.secondary">
                        Document not found or failed to load.
                    </Typography>
                )}
            </Box>
            <Dialog open={retryOpen} onClose={() => { if (!retryBusy) setRetryOpen(false); }} fullWidth maxWidth="xs" aria-labelledby="retry-document-title">
                <DialogTitle id="retry-document-title" sx={{ fontWeight: 700, color: '#243b53', pb: 1 }}>Proses lanjutan dokumen</DialogTitle>
                <DialogContent sx={{ pt: 1 }}>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        Jalankan hanya bila teks penting masih belum masuk. Metode lanjutan dapat memakai CPU lebih lama. Chunk yang tersimpan tetap tersedia bila proses baru gagal.
                    </Typography>
                    <RadioGroup value={retryMode} onChange={(event) => setRetryMode(event.target.value)} aria-label="Mode ekstraksi ulang">
                        <FormControlLabel value="text" control={<Radio size="small" />} label={<Box><Typography fontSize={14} fontWeight={600}>Baca teks cepat</Typography><Typography variant="caption" color="text.secondary">Ulangi pembacaan lapisan teks tanpa analisis tata letak.</Typography></Box>} sx={{ alignItems: 'flex-start', mb: 1.5 }} />
                        <FormControlLabel value="docling_no_ocr" control={<Radio size="small" />} label={<Box><Typography fontSize={14} fontWeight={600}>Periksa tata letak dengan Docling</Typography><Typography variant="caption" color="text.secondary">Analisis lebih teliti tanpa OCR. Dapat memakai CPU cukup lama.</Typography></Box>} sx={{ alignItems: 'flex-start', mb: 1.5 }} />
                        <FormControlLabel value="ocr" control={<Radio size="small" />} label={<Box><Typography fontSize={14} fontWeight={600}>OCR untuk hasil pindai</Typography><Typography variant="caption" color="text.secondary">Baca teks dari gambar halaman. Proses paling berat.</Typography></Box>} sx={{ alignItems: 'flex-start' }} />
                    </RadioGroup>
                    {retryError && <Alert severity="error" sx={{ mt: 2 }}>{retryError}</Alert>}
                </DialogContent>
                <DialogActions sx={{ px: 3, pb: 2.5 }}>
                    <Button onClick={() => setRetryOpen(false)} disabled={retryBusy} sx={{ textTransform: 'none', color: '#425466' }}>Batal</Button>
                    <Button onClick={submitRetry} disabled={retryBusy} variant="contained" startIcon={retryBusy ? <CircularProgress size={16} color="inherit" /> : <ReplayOutlined />} sx={{ textTransform: 'none', bgcolor: '#284967', '&:hover': { bgcolor: '#1e3a55' } }}>
                        {retryBusy ? 'Memproses…' : 'Mulai ekstraksi'}
                    </Button>
                </DialogActions>
            </Dialog>
            <Dialog open={manualOpen} onClose={() => { if (!manualBusy) setManualOpen(false); }} fullWidth maxWidth="sm" aria-labelledby="manual-text-title">
                <DialogTitle id="manual-text-title" sx={{ fontWeight: 700, color: '#243b53', pb: 1 }}>Tambahkan teks ke chunk</DialogTitle>
                <DialogContent sx={{ display: 'grid', gap: 2, pt: '8px !important' }}>
                    <Typography variant="body2" color="text.secondary">
                        Salin teks yang benar dari dokumen. Teks ini akan disimpan sebagai chunk baru dan audit dijalankan ulang.
                    </Typography>
                    <TextField label="Halaman" type="number" value={manualPage} onChange={(event) => setManualPage(event.target.value)} inputProps={{ min: 1, max: document?.total_pages || undefined }} fullWidth size="small" />
                    <TextField label="Teks yang belum masuk" value={manualText} onChange={(event) => setManualText(event.target.value)} multiline minRows={5} maxRows={12} fullWidth inputProps={{ maxLength: 10000 }} helperText={`${manualText.length}/10.000 karakter`} />
                    {manualError && <Alert severity="error">{manualError}</Alert>}
                </DialogContent>
                <DialogActions sx={{ px: 3, pb: 2.5 }}>
                    <Button onClick={() => setManualOpen(false)} disabled={manualBusy} sx={{ textTransform: 'none', color: '#425466' }}>Batal</Button>
                    <Button onClick={submitManual} disabled={manualBusy || !manualText.trim() || Number(manualPage) < 1} variant="contained" sx={{ textTransform: 'none', bgcolor: '#284967', '&:hover': { bgcolor: '#1e3a55' } }}>
                        {manualBusy ? 'Menyimpan…' : 'Simpan ke chunk'}
                    </Button>
                </DialogActions>
            </Dialog>
            <Dialog
                open={pdfOpen}
                onClose={closePdf}
                fullScreen={isMobile}
                fullWidth
                maxWidth="lg"
                aria-labelledby="annotated-pdf-title"
                sx={{ '& .MuiDialog-paper': { borderRadius: isMobile ? 0 : 2.5, height: isMobile ? '100%' : 'min(90vh, 1000px)' } }}
            >
                <DialogTitle id="annotated-pdf-title" sx={{ display: 'flex', alignItems: 'center', gap: 1, px: 2.5, py: 1.5, borderBottom: '1px solid #e5ebef' }}>
                    <PictureAsPdfOutlined sx={{ color: '#ad3f46', fontSize: 21 }} />
                    <Typography component="span" fontWeight={700} sx={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 16 }}>
                        {document?.filename || 'PDF bertanda'}
                    </Typography>
                    <IconButton onClick={closePdf} aria-label="Tutup PDF" size="small"><Close /></IconButton>
                </DialogTitle>
                <Box sx={{ px: 2.5, py: 1, bgcolor: '#f8fafc', borderBottom: '1px solid #e5ebef' }}>
                    <Typography variant="body2" color="text.secondary">
                        Garis merah menunjukkan teks yang cocok dengan chunk tersimpan di database. Untuk Word, pratinjau dibuat dari PDF hasil konversi; teks tanpa lapisan teks mungkin tidak dapat ditandai.
                    </Typography>
                    {pdfLetterCounts && (
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', columnGap: 3, rowGap: 0.5, mt: 1 }}>
                            <Typography variant="body2" sx={{ color: '#425466' }}>
                                Huruf terbaca di PDF: <Box component="strong" sx={{ color: '#243b53' }}>{pdfLetterCounts.pdfLetters.toLocaleString('id-ID')}</Box>
                            </Typography>
                            <Typography variant="body2" sx={{ color: '#425466' }}>
                                Huruf tersimpan di database: <Box component="strong" sx={{ color: '#243b53' }}>{pdfLetterCounts.storedLetters.toLocaleString('id-ID')}</Box>
                            </Typography>
                        </Box>
                    )}
                    {pdfLetterCounts && (
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                            Hanya huruf yang dihitung, tanpa spasi, angka, atau tanda baca.
                        </Typography>
                    )}
                </Box>
                <DialogContent sx={{ p: 0, display: 'flex', flex: 1, minHeight: 0, bgcolor: '#e9edf1' }}>
                    {pdfLoading && <Box sx={{ m: 'auto' }}><CircularProgress aria-label="Memuat PDF" /></Box>}
                    {pdfError && <Alert severity="error" sx={{ m: 2, alignSelf: 'flex-start' }}>{pdfError}</Alert>}
                    {pdfUrl && <Box component="iframe" title="Pratinjau PDF dengan teks tersimpan bertanda merah" src={pdfUrl} sx={{ width: '100%', height: '100%', border: 0 }} />}
                </DialogContent>
            </Dialog>
        </Box>
    );
}
