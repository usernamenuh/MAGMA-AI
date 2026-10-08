import {useCallback, useState} from "react";
import {axiosInstance} from "@/api/client.jsx";

export default function useChatHistory() {
    const [history, setHistory] = useState([]);

    const addMessage = (user_input, output = null) => {
        setHistory((prev) => [...prev, { user_input, output }]);
    };

    const updateLast = (dataOrError, isError = false) => {
        setHistory((prev) => {
            if (!prev.length) return prev;

            const updated = [...prev];
            const lastIndex = updated.length - 1;
            const lastItem = updated[lastIndex];

            if (isError) {
                updated[lastIndex] = {
                    ...lastItem,
                    output: dataOrError,
                    api_call: null,
                    references: null,
                    response: typeof dataOrError === 'string' ? dataOrError : 'An error occurred',
                    isError: true,
                    errorMessage: typeof dataOrError === 'string' ? dataOrError : JSON.stringify(dataOrError)
                };
            } else {
                updated[lastIndex] = {
                    ...lastItem,
                    output: dataOrError?.output || lastItem.output,
                    answer: dataOrError?.answer || dataOrError?.output || lastItem.output,
                    api_call: dataOrError?.api_call || lastItem.api_call,
                    references: dataOrError?.references || lastItem.references,
                    response: dataOrError?.response || dataOrError?.message || lastItem.response,
                    follow_ups: dataOrError?.follow_ups || dataOrError?.suggested_follow_ups || [],
                    suggested_follow_ups: dataOrError?.suggested_follow_ups || [],
                    isError: false,
                    errorMessage: null
                };
            }
            return updated;
        });
    };
    const fetchSessionHistory = useCallback(async (sessionId, userId) => {
        if (!sessionId || !userId) return;
        try {
            const res = await axiosInstance.get(
                `/chat/session/${sessionId}?user_id=${userId}&skip=0&limit=200`
            );

            const messages = res.data;
            const mapped = [];
            let tempUserInput = null;

            for (const msg of messages) {
                if (msg.role === "user") {
                    // store user input temporarily
                    tempUserInput = msg.message;
                } else if (msg.role === "assistant") {
                    // pair with last user input
                    let fuList = [];
                    if (msg.response && typeof msg.response === "object") {
                        fuList = msg.response.follow_ups || [];
                    }
                    mapped.push({
                        type: msg.type,
                        lang: msg.lang,
                        references: msg.references,
                        user_input: tempUserInput,
                        output: msg.message,
                        answer: msg.message,
                        created_at: msg.created_at,
                        api_call: msg.api_call || null,
                        response: msg.response || null,
                        geoLocation: msg.geo_location || null,
                        follow_ups: fuList,
                    });
                    
                    tempUserInput = null; // reset
                }
            }

            setHistory(mapped);
        } catch (err) {
            console.error("Failed to fetch session history", err);
        }
    }, []);

    return { history, addMessage, updateLast, fetchSessionHistory };
}
