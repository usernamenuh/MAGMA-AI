import {Navigate, Outlet} from 'react-router-dom';
import { Box } from '@mui/material';
import {useAuth} from "@/hooks/useAuth.jsx";
import {CHAT, LOGIN} from "@/utils/routes.jsx";

export const PublicLayout = () => {
    const { isAuthenticated } = useAuth();
    if (isAuthenticated) {
        return <Navigate to={CHAT} replace />;
    }
    return (
        <Box sx={{ minHeight: '100vh'}}>
            <Outlet />
        </Box>
    );
};
