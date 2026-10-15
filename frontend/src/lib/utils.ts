import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

// Backend base URL — baked in at build time via NEXT_PUBLIC_API_URL (see frontend/Dockerfile).
export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
