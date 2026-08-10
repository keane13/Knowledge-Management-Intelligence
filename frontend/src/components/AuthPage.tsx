"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Eye, EyeOff, Mail, Lock, User, Sparkles, ArrowRight, AlertCircle } from "lucide-react";

export default function AuthPage({ login, register }: { login: (email: string, password: string) => Promise<{ success: boolean; error?: string; }> | { success: boolean; error?: string; }; register: (name: string, email: string, password: string) => Promise<{ success: boolean; error?: string; }> | { success: boolean; error?: string; }; }) {
    const [mode, setMode] = useState<"login" | "register">("login");
    const [name, setName] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [showPassword, setShowPassword] = useState(false);
    const [error, setError] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);

    const switchMode = (newMode: "login" | "register") => {
        setMode(newMode);
        setError("");
        setName("");
        setEmail("");
        setPassword("");
        setConfirmPassword("");
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setIsSubmitting(true);

        await new Promise((r) => setTimeout(r, 400)); // subtle UX delay

        if (mode === "register") {
            if (!name.trim()) { setError("Please enter your name."); setIsSubmitting(false); return; }
            if (password !== confirmPassword) { setError("Passwords do not match."); setIsSubmitting(false); return; }
            const result = await register(name.trim(), email.trim(), password);
            if (!result.success) { setError(result.error || "Registration failed."); setIsSubmitting(false); return; }
        } else {
            const result = await login(email.trim(), password);
            if (!result.success) { setError(result.error || "Login failed."); setIsSubmitting(false); return; }
        }
        setIsSubmitting(false);
    };

    return (
        <div className="min-h-screen w-full flex bg-[#050508] relative">
            {/* Left Column - Branding & Abstract Background */}
            <div className="hidden lg:flex w-1/2 relative overflow-hidden flex-col items-center justify-center p-12 bg-[#050508]">
                {/* Animated gradient background */}
                <div className="absolute inset-0 overflow-hidden">
                    <div className="aurora-blob top-[-10%] left-[-20%] w-[80%] h-[80%] bg-sky-900/30" />
                    <div className="aurora-blob bottom-[-20%] right-[-20%] w-[80%] h-[80%] bg-blue-900/25" />
                    <div className="aurora-blob top-[30%] left-[30%] w-[60%] h-[60%] bg-cyan-900/15" />
                </div>

                {/* Grid overlay */}
                <div
                    className="absolute inset-0 opacity-[0.04]"
                    style={{
                        backgroundImage:
                            "linear-gradient(rgba(255,255,255,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.5) 1px, transparent 1px)",
                        backgroundSize: "40px 40px",
                    }}
                />

                {/* Left Side Content */}
                <motion.div 
                    initial={{ opacity: 0, x: -24 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
                    className="relative z-10 text-center flex flex-col items-center max-w-lg"
                >
                    <div className="inline-flex items-center justify-center w-20 h-20 rounded-3xl bg-gradient-to-br from-sky-600 to-blue-600 shadow-[0_0_60px_rgba(139,92,246,0.5)] mb-8">
                        <Sparkles className="w-10 h-10 text-white" />
                    </div>
                    <h1 className="text-4xl lg:text-5xl font-bold text-white tracking-tight mb-4 leading-tight">
                        Knowlytics Intelligence
                    </h1>
                    <p className="text-lg lg:text-xl text-gray-400 font-medium">
                        (Knowledge Management Intelligence)
                    </p>
                    <p className="text-gray-500 mt-6 max-w-sm">
                        Unlock the power of your documents with intelligent search, retrieval, and analysis.
                    </p>
                </motion.div>
            </div>

            {/* Right Column - Auth Form */}
            <div className="w-full lg:w-1/2 flex items-center justify-center relative bg-[#0a0a0f] lg:bg-[#07070a] px-4 py-12">
                {/* Subtle background for mobile if left side is hidden */}
                <div className="absolute inset-0 lg:hidden overflow-hidden">
                    <div className="aurora-blob top-0 left-0 w-full h-full bg-sky-900/10" />
                </div>

                <motion.div
                    initial={{ opacity: 0, y: 24, scale: 0.97 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
                    className="relative z-10 w-full max-w-md mx-auto"
                >
                    {/* Mobile Logo (hidden on large screens) */}
                    <div className="lg:hidden text-center mb-10">
                        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-sky-600 to-blue-600 shadow-[0_0_40px_rgba(139,92,246,0.4)] mb-4 mx-auto">
                            <Sparkles className="w-7 h-7 text-white" />
                        </div>
                        <h1 className="text-2xl font-bold text-white tracking-tight">Knowlytics Intelligence</h1>
                        <p className="text-sm text-gray-500 mt-1">Knowledge Management Intelligence</p>
                    </div>

                    <div className="mb-8 text-center lg:text-left">
                        <h2 className="text-2xl font-semibold text-white">
                            {mode === "login" ? "Welcome back" : "Create an account"}
                        </h2>
                        <p className="text-gray-400 mt-2 text-sm">
                            {mode === "login" ? "Enter your credentials to access your workspace." : "Sign up to start organizing your knowledge."}
                        </p>
                    </div>

                    {/* Glass Card */}
                    <div className="auth-card rounded-2xl p-6 lg:p-8 border border-white/[0.08] shadow-2xl bg-[#0c0c11]">
                        
                        {/* Tab switcher */}
                        <div className="flex bg-white/5 rounded-xl p-1 mb-8">
                            {(["login", "register"] as const).map((tab) => (
                                <button
                                    key={tab}
                                    onClick={() => switchMode(tab)}
                                    className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all duration-200 capitalize ${mode === tab
                                        ? "bg-white/10 text-white shadow-sm"
                                        : "text-gray-500 hover:text-gray-300"
                                        }`}
                                >
                                    {tab === "login" ? "Sign In" : "Create Account"}
                                </button>
                            ))}
                        </div>

                        {/* Form */}
                        <form onSubmit={handleSubmit} className="space-y-4">
                            <AnimatePresence mode="wait">
                                {mode === "register" && (
                                    <motion.div
                                        key="name-field"
                                        initial={{ opacity: 0, height: 0 }}
                                        animate={{ opacity: 1, height: "auto" }}
                                        exit={{ opacity: 0, height: 0 }}
                                        transition={{ duration: 0.2 }}
                                    >
                                        <div className="auth-input-wrap">
                                            <User className="auth-input-icon" />
                                            <input
                                                type="text"
                                                value={name}
                                                onChange={(e) => setName(e.target.value)}
                                                placeholder="Full name"
                                                className="auth-input"
                                                autoComplete="name"
                                                required={mode === "register"}
                                            />
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>

                            <div className="auth-input-wrap">
                                <Mail className="auth-input-icon" />
                                <input
                                    type="email"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    placeholder="Email address"
                                    className="auth-input"
                                    autoComplete="email"
                                    required
                                />
                            </div>

                            <div className="auth-input-wrap">
                                <Lock className="auth-input-icon" />
                                <input
                                    type={showPassword ? "text" : "password"}
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    placeholder="Password"
                                    className="auth-input pr-10"
                                    autoComplete={mode === "login" ? "current-password" : "new-password"}
                                    required
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 transition-colors"
                                >
                                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                </button>
                            </div>

                            <AnimatePresence mode="wait">
                                {mode === "register" && (
                                    <motion.div
                                        key="confirm-field"
                                        initial={{ opacity: 0, height: 0 }}
                                        animate={{ opacity: 1, height: "auto" }}
                                        exit={{ opacity: 0, height: 0 }}
                                        transition={{ duration: 0.2 }}
                                    >
                                        <div className="auth-input-wrap">
                                            <Lock className="auth-input-icon" />
                                            <input
                                                type={showPassword ? "text" : "password"}
                                                value={confirmPassword}
                                                onChange={(e) => setConfirmPassword(e.target.value)}
                                                placeholder="Confirm password"
                                                className="auth-input"
                                                autoComplete="new-password"
                                                required={mode === "register"}
                                            />
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>

                            {/* Error */}
                            <AnimatePresence>
                                {error && (
                                    <motion.div
                                        initial={{ opacity: 0, y: -4 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        exit={{ opacity: 0, y: -4 }}
                                        className="flex items-center gap-2 text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2 text-sm"
                                    >
                                        <AlertCircle className="w-4 h-4 shrink-0" />
                                        {error}
                                    </motion.div>
                                )}
                            </AnimatePresence>

                            {/* Submit */}
                            <button
                                type="submit"
                                disabled={isSubmitting}
                                className="auth-submit-btn w-full flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-semibold text-white transition-all duration-200 disabled:opacity-60 mt-2"
                            >
                                {isSubmitting ? (
                                    <span className="flex gap-1">
                                        <span className="w-1.5 h-1.5 bg-white/80 rounded-full animate-bounce [animation-delay:0ms]" />
                                        <span className="w-1.5 h-1.5 bg-white/80 rounded-full animate-bounce [animation-delay:150ms]" />
                                        <span className="w-1.5 h-1.5 bg-white/80 rounded-full animate-bounce [animation-delay:300ms]" />
                                    </span>
                                ) : (
                                    <>
                                        {mode === "login" ? "Sign In" : "Create Account"}
                                        <ArrowRight className="w-4 h-4" />
                                    </>
                                )}
                            </button>
                        </form>

                        {/* Switch */}
                        <p className="text-center text-xs text-gray-500 mt-6">
                            {mode === "login" ? "Don't have an account? " : "Already have an account? "}
                            <button
                                onClick={() => switchMode(mode === "login" ? "register" : "login")}
                                className="text-sky-400 hover:text-sky-300 font-medium transition-colors"
                            >
                                {mode === "login" ? "Create one" : "Sign in"}
                            </button>
                        </p>
                    </div>

                    <p className="text-center text-[10px] text-gray-600 mt-6 lg:mt-8">
                        Demo mode · Credentials stored locally in your browser
                    </p>
                </motion.div>
            </div>
        </div>
    );
}
