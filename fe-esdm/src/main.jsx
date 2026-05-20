import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App.jsx';
import {QueryClient, QueryClientProvider} from "@tanstack/react-query";
import {AuthProvider} from "@/contexts/AuthContext.jsx";
const queryClient = new QueryClient();
ReactDOM.createRoot(document.getElementById('root')).render(
    <BrowserRouter>
        <QueryClientProvider client={queryClient}>
            <AuthProvider>
            <App />
            </AuthProvider>
        </QueryClientProvider>
    </BrowserRouter>
);
