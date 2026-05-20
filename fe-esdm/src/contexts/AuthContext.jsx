import React, {
    createContext,
    useContext,
    useState,
    useMemo,
    useEffect,
    useCallback
} from 'react';

const AuthContext = createContext(null);

const getInitialAuthStatus = () => {
    const token = localStorage.getItem('auth_token');
    return !!token;
};

export const AuthProvider = ({ children }) => {
    const [isAuthenticated, setIsAuthenticated] = useState(getInitialAuthStatus());
    const [user, setUser] = useState(null); // Optional: State to hold user info

    const login = useCallback((token, userData) => {
        localStorage.setItem('auth_token', token);
        setIsAuthenticated(true);
        setUser(userData);
    }, []);

    const logout = useCallback(() => {
        localStorage.removeItem('auth_token');

        setIsAuthenticated(false);
        setUser(null);
    }, []);

    // Optional: Effect to re-check status if storage changes (e.g., in other tabs)
    useEffect(() => {
        const handleStorageChange = () => {
            setIsAuthenticated(getInitialAuthStatus());
        };
        window.addEventListener('storage', handleStorageChange);
        return () => {
            window.removeEventListener('storage', handleStorageChange);
        };
    }, []);

    // Use useMemo to prevent unnecessary re-renders of consuming components
    const contextValue = useMemo(
        () => ({
            isAuthenticated,
            user,
            login,
            logout,
        }),
        [isAuthenticated, user, login, logout]
    );

    return (
        <AuthContext.Provider value={contextValue}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};