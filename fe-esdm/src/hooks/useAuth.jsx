import { useState, useCallback, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { axiosInstance, setRefreshHandler } from "@/api/client.jsx";
import { LOGIN } from "@/utils/routes.jsx";
import { AUTH_BASE_URL } from "@/utils/constants.jsx";

export function useAuth() {
    const navigate = useNavigate();

    const [user, setUser] = useState(() => {
        const data = localStorage.getItem("userinfo");
        return data ? JSON.parse(data) : null;
    });

    const [token, setToken] = useState(localStorage.getItem("access_token"));
    const [refreshToken, setRefreshToken] = useState(localStorage.getItem("refresh_token"));
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem("access_token"));

    const isRefreshing = useRef(false);
    const refreshQueue = useRef([]);

    const processQueue = (error, newToken = null) => {
        refreshQueue.current.forEach((p) => {
            if (error) p.reject(error);
            else p.resolve(newToken);
        });
        refreshQueue.current = [];
    };

    const logout = useCallback(async () => {
        const t = localStorage.getItem("access_token");
        if (t) {
            try {
                await axios.post(`${AUTH_BASE_URL}/auth/logout`, {}, {
                    headers: { Authorization: `Bearer ${t}` },
                });
            } catch (_) {}
        }
        localStorage.clear();
        setUser(null);
        setToken(null);
        setRefreshToken(null);
        setIsAuthenticated(false);
        navigate(LOGIN);
    }, [navigate]);

    const login = useCallback(async (username, password) => {
        setLoading(true);
        setError(null);
        try {
            const { data } = await axios.post(`${AUTH_BASE_URL}/auth/login`, { username, password });
            const accessToken = data.accessToken ?? data.data?.accessToken ?? data.data?.access_token;
            const refreshTok = data.refreshToken ?? data.data?.refreshToken ?? data.data?.refresh_token;
            const userData = data.user ?? data.data?.user ?? {};

            localStorage.setItem("access_token", accessToken);
            localStorage.setItem("refresh_token", refreshTok);
            localStorage.setItem("userinfo", JSON.stringify(userData));

            setToken(accessToken);
            setRefreshToken(refreshTok);
            setUser(userData);
            setIsAuthenticated(true);

            return data;
        } catch (err) {
            const status = err?.response?.status;
            const detail = err?.response?.data?.message;
            if (status === 401) {
                setError("Incorrect username or password");
            } else if (detail) {
                setError(detail);
            } else {
                setError("Network error — unable to reach server");
            }
            return null;
        } finally {
            setLoading(false);
        }
    }, []);

    const refreshAccessToken = useCallback(() => {
        return new Promise(async (resolve, reject) => {
            if (isRefreshing.current) {
                refreshQueue.current.push({ resolve, reject });
                return;
            }
            isRefreshing.current = true;
            try {
                const rt = refreshToken || localStorage.getItem("refresh_token");
                if (!rt) {
                    processQueue("No refresh token", null);
                    logout();
                    return reject("No refresh token");
                }

                const { data } = await axios.post(`${AUTH_BASE_URL}/auth/refresh`, { refresh_token: rt });
                const newToken = data.accessToken ?? data.data?.accessToken ?? data.data?.access_token;

                localStorage.setItem("access_token", newToken);
                setToken(newToken);
                processQueue(null, newToken);
                return resolve(newToken);
            } catch (err) {
                processQueue(err, null);
                logout();
                return reject(err);
            } finally {
                isRefreshing.current = false;
            }
        });
    }, [refreshToken, logout]);

    const getAuthToken = useCallback(async () => {
        const t = localStorage.getItem("access_token");
        try {
            await axios.get(`${AUTH_BASE_URL}/auth/me`, {
                headers: { Authorization: `Bearer ${t}` },
            });
            return t;
        } catch {
            return await refreshAccessToken();
        }
    }, [refreshAccessToken]);

    const fetchingUserInfo = () => {
        const info = localStorage.getItem("userinfo");
        setUser(info ? JSON.parse(info) : null);
        return info;
    };

    useEffect(() => {
        setRefreshHandler(refreshAccessToken);
    }, [refreshAccessToken]);

    useEffect(() => {
        (async () => {
            const t = localStorage.getItem("access_token");
            if (!t || t === "undefined") return;
            try {
                await axios.get(`${AUTH_BASE_URL}/auth/me`, {
                    headers: { Authorization: `Bearer ${t}` },
                });
                setIsAuthenticated(true);
            } catch {
                try {
                    await refreshAccessToken();
                } catch {
                    logout();
                }
            }
        })();
    }, []);

    return {
        user,
        token,
        refreshToken,
        login,
        logout,
        loading,
        error,
        setError,
        isAuthenticated,
        getAuthToken,
        fetchingUserInfo,
    };
}
