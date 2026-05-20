// src/hooks/useApiKeys.jsx
import {useState, useCallback, useEffect} from 'react';
import { axiosInstance } from "../api/client.jsx";
import {USER_ID} from "@/utils/constants.jsx";
import {useAuth} from "@/hooks/useAuth.jsx";


export const useApiKeys = () => {
    const [apiKeys, setApiKeys] = useState([]);
    const [apiKey, setApiKey] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const {user} = useAuth();

    const fetchApiKeys = useCallback(async () => {
        setLoading(true);
        try {
            const res = await axiosInstance.get(`/api-keys/user/${user?.id || JSON.parse(user)?.id}`);
            setApiKeys(res.data);
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to fetch API keys');
        } finally {
            setLoading(false);
        }
    }, []);

    const generateApiKey = useCallback(async (name, validityPeriod) => {
        setLoading(true);
        try {
            const formData = new FormData();
            formData.append('user_id', user?.id || JSON.parse(user)?.id);
            formData.append('name', name);
            formData.append('validity_duration_days', validityPeriod);
            const res = await axiosInstance.post(`/api-keys/generate`, formData);
            setApiKey(res.data.api_key);
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to generate API key');
        } finally {
            setLoading(false);
        }
    }, []);

    const revokeApiKey = useCallback(async (key) => {
        setLoading(true);
        try {
            await axiosInstance.post(`/api-keys/revoke/${key}`);
            setApiKeys((prev) => prev.filter((k) => k.api_key !== key));
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to revoke API key');
        } finally {
            setLoading(false);
        }
    }, []);
    const removeApiKey = useCallback(async (key) => {
        setLoading(true);
        try {
            await axiosInstance.delete(`/api-keys/remove/${key}`);
            setApiKeys((prev) => prev.filter((k) => k.api_key !== key));
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to delete API key');
        } finally {
            setLoading(false);
        }
    }, []);

    return {
        apiKeys,
        apiKey,
        loading,
        error,
        fetchApiKeys,
        generateApiKey,
        revokeApiKey,
        removeApiKey
    };
};
