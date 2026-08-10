"use client";

import { useAuth } from "@/lib/useAuth";
import AuthPage from "@/components/AuthPage";
import ChatInterface from "@/components/ChatInterface";

export default function Home() {
  const { user, isLoading, login, register, logout } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen w-full flex items-center justify-center bg-[#050508]">
        <div className="flex gap-1.5">
          <span className="w-2 h-2 bg-sky-500 rounded-full animate-bounce [animation-delay:0ms]" />
          <span className="w-2 h-2 bg-sky-500 rounded-full animate-bounce [animation-delay:150ms]" />
          <span className="w-2 h-2 bg-sky-500 rounded-full animate-bounce [animation-delay:300ms]" />
        </div>
      </div>
    );
  }

  if (!user) {
    return <AuthPage login={login} register={register} />;
  }

  return (
    <main className="flex min-h-screen flex-col p-0 overflow-hidden">
      <ChatInterface user={user} onLogout={logout} />
    </main>
  );
}

