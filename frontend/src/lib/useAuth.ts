"use client";

import { useState, useEffect, useCallback } from "react";

export interface AuthUser {
    name: string;
    email: string;
    token?: string;
}

const STORAGE_KEY = "rag_pro_user";

export function useAuth() {
    const [user, setUser] = useState<AuthUser | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        try {
            const stored = localStorage.getItem(STORAGE_KEY);
            if (stored) {
                const parsed = JSON.parse(stored);
                setUser({ name: parsed.name, email: parsed.email, token: parsed.token });
            }
        } catch {
            // ignore
        } finally {
            setIsLoading(false);
        }
    }, []);

    const login = useCallback(
        async (email: string, password: string): Promise<{ success: boolean; error?: string }> => {
            try {
                const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
                const res = await fetch(`${apiUrl}/login`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ username: email, password })
                });
                const data = await res.json();

                if (!res.ok) {
                    return { success: false, error: data.detail || "Login failed" };
                }

                const authUser: AuthUser = { name: data.username || email.split('@')[0], email, token: data.token };
                localStorage.setItem(STORAGE_KEY, JSON.stringify(authUser));
                setUser(authUser);
                return { success: true };
            } catch (err: any) {
                return { success: false, error: err.message || "Network error" };
            }
        },
        []
    );

    const register = useCallback(
        async (
            name: string,
            email: string,
            password: string
        ): Promise<{ success: boolean; error?: string }> => {
            if (password.length < 8) {
                return {
                    success: false,
                    error: "Password must be at least 8 characters.",
                };
            }
            try {
                const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
                const res = await fetch(`${apiUrl}/register`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ username: email, password })
                });
                const data = await res.json();

                if (!res.ok) {
                    return { success: false, error: data.detail || "Registration failed" };
                }

                const authUser: AuthUser = { name, email, token: data.token };
                localStorage.setItem(STORAGE_KEY, JSON.stringify(authUser));
                setUser(authUser);
                return { success: true };
            } catch (err: any) {
                return { success: false, error: err.message || "Network error" };
            }
        },
        []
    );

    const logout = useCallback(() => {
        localStorage.removeItem(STORAGE_KEY);
        setUser(null);
    }, []);

    return { user, isLoading, login, register, logout };
}
