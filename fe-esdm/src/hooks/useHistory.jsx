import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { axiosInstance } from "@/api/client.jsx";

export const useHistory = (userId) => {
    const queryClient = useQueryClient();

    const { data: histories = [], isLoading } = useQuery({
        queryKey: ["histories", userId],
        enabled: !!userId,
        queryFn: async () => {
            const res = await axiosInstance.get(`/chat/sessions?user_id=${userId}`);
            return res.data.map((h) => ({ ...h, history_id: h.session_id }));
        },
    });

    const deleteHistoryMutation = useMutation({
        mutationFn: async (historyId) => {
            await axiosInstance.delete(`/chat/sessions/${historyId}`);
            return historyId;
        },
        onSuccess: () => {
            queryClient.invalidateQueries(["histories", userId]); // 🔥 auto refresh
        },
    });

    const deleteAllHistoryMutation = useMutation({
        mutationFn: async () => {
            await axiosInstance.delete(`/chat/users/${userId}/history`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries(["histories", userId]); // 🔥 clear UI
        },
    });

    const deleteHistoryById = (id) => deleteHistoryMutation.mutate(id);
    const deleteAllUserHistory = () => deleteAllHistoryMutation.mutate();

    const refetchHistories = () => {
        queryClient.invalidateQueries(["histories", userId]);
    };

    return {
        histories,
        isLoading,
        refetchHistories,
        deleteHistoryById,
        deleteAllUserHistory,
    };
};
