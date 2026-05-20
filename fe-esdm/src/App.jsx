import {Routes, Route, Navigate } from "react-router-dom";
import ChatRAG from "./pages/ChatRAG.jsx";
import History from "./pages/History.jsx";
import ScrappingData from "./pages/ScrappingData.jsx";
import APIKeysPage from "@/pages/ApiKeysPage.jsx";
import {
    API_DOCUMENTATION,
    API_KEYS,
    CHAT,
    HISTORY,
    KNOWLEDGE_BASE,
    LOGIN,
    REGISTER,
    SCRAPPING
} from "@/utils/routes.jsx";
import LoginPage from "@/pages/LoginPage.jsx";
import { PublicLayout } from "@/layouts/PublicLayout.jsx";
import { PrivateLayout } from "@/layouts/PrivateLayout.jsx";
import RegisterPage from "@/pages/RegisterPage.jsx";
import ChatRAGHistory from "@/pages/ViewChatHistory.jsx";
import { useAuth } from "@/hooks/useAuth.jsx";
import {ProtectedRoute} from "@/layouts/ProtectedRoute.jsx";
import KnowledgeBasePage from "@/pages/KnowledgeBasePage.jsx";
import UploadKnowledgePage from "@/pages/UploadKnowledgePage.jsx";
import DocumentDetailPage from "@/pages/DocumentDetailPage.jsx";
import ApiDocumentationPage from "@/pages/ApiDocumentation.jsx";

export default function App() {
    const { isAuthenticated } = useAuth();
    return (
            <Routes>
                <Route element={<PublicLayout />}>
                    <Route
                        path={LOGIN}
                        element={<LoginPage />}
                    />
                    <Route
                        path={REGISTER}
                        element={<RegisterPage />}
                    />
                </Route>


                <Route
                    path="/"
                    element={
                        isAuthenticated ? (
                            <Navigate to={CHAT} replace />
                        ) : (
                            <Navigate to={LOGIN} replace />
                        )
                    }
                />
                <Route element={<ProtectedRoute />}>
                    <Route element={<PrivateLayout />}>
                        <Route path={CHAT} element={<ChatRAG />} />
                        <Route path={`${CHAT}/:id`} element={<ChatRAGHistory />} />
                        <Route path={HISTORY} element={<History />} />
                        <Route path={API_KEYS} element={<APIKeysPage />} />
                        <Route path={KNOWLEDGE_BASE} element={<KnowledgeBasePage />} />
                        <Route path={`${KNOWLEDGE_BASE}/upload`} element={<UploadKnowledgePage />} />
                        <Route path={`${KNOWLEDGE_BASE}/documents/:documentId`} element={<DocumentDetailPage />} />
                        <Route path={`${API_DOCUMENTATION}`} element={<ApiDocumentationPage />} />

                    </Route>
                </Route>
            </Routes>
    );
}