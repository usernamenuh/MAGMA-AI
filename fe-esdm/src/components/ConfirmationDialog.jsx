import { Button, Dialog, DialogActions, DialogContent, Typography } from '@mui/material';

const ConfirmationDialog = ({
                                children,
                                okText,
                                cancelText,
                                open,
                                onClose,
                                onOk,
                                onCancel,
                            }) => {
    const handleOk = () => {
        onClose();
        onOk();
    };

    const handleCancel = () => {
        onClose();
        onCancel();
    };

    return (
        <Dialog open={open} onClose={onClose}>
            <DialogContent sx={{ marginTop: 2, mx: 2 }}>
                <Typography variant="body1" textAlign="center">
                    {children}
                </Typography>
            </DialogContent>
            <DialogActions
                sx={{ justifyContent: 'center', marginBottom: 2, gap: 3 }}
            >
                <Button
                    variant="outlined"
                    sx={{ width: '146px', height: '40px', fontSize: '11px' }}
                    onClick={handleCancel}
                >
                    {cancelText}
                </Button>
                <Button
                    variant="contained"
                    sx={{
                        width: '146px',
                        height: '40px',
                        fontSize: '11px',
                        backgroundColor: '#d32f2f',
                        '&:hover': { backgroundColor: '#b71c1c' },
                    }}
                    onClick={handleOk}
                >
                    {okText}
                </Button>
            </DialogActions>
        </Dialog>
    );
};

export default ConfirmationDialog;
