import { useAuth } from "@/hooks/useAuth.jsx";
import { Navigate, Outlet } from "react-router-dom";
import { LOGIN } from "@/utils/routes.jsx";

export const ProtectedRoute = () => {
    const { isAuthenticated } = useAuth();
    if (!isAuthenticated) {
        return <Navigate to={LOGIN} replace />;
    }

    return <Outlet />;
};