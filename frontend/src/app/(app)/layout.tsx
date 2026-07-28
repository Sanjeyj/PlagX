"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Shield, LayoutDashboard, FileUp, Files } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import type { User } from "@/lib/types";

const GUEST_USER: User = {
  id: "guest",
  email: "guest@plagx.internal",
  full_name: "Guest Scanner",
};

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  // IMPORTANT: Start as null so SSR and initial CSR both render the same thing.
  // Only populate from localStorage after client-side mount to prevent hydration mismatch.
  const [user, setUser] = useState<User | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    let stored: User | null = null;
    try {
      const raw = localStorage.getItem("user");
      if (raw) stored = JSON.parse(raw);
    } catch {}
    if (!stored) {
      stored = GUEST_USER;
      localStorage.setItem("user", JSON.stringify(GUEST_USER));
    }
    setUser(stored);
    setMounted(true);
  }, []);

  const navItems = [
    { href: "/upload", label: "Scan Document", icon: FileUp },
    { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
    { href: "/documents", label: "My Documents", icon: Files },
  ];

  const pageTitle =
    pathname === "/dashboard"
      ? "Overview"
      : pathname.split("/").filter(Boolean).pop()?.replace(/-/g, " ") || "Scanner";

  return (
    <div className="min-h-screen bg-muted/20 flex flex-col md:flex-row">
      {/* Sidebar */}
      <aside className="w-full md:w-64 border-r bg-card flex-shrink-0 md:min-h-screen">
        <div className="h-16 flex items-center px-6 border-b">
          <Link href="/" className="flex items-center gap-2 font-bold text-xl">
            <Shield className="h-6 w-6 text-primary" />
            <span>
              Plag<span className="text-primary">X</span>
            </span>
          </Link>
        </div>
        <nav className="p-4 space-y-1">
          {navItems.map((item) => {
            const isActive =
              pathname === item.href ||
              (pathname.startsWith("/report") && item.href === "/documents");
            return (
              <Link key={item.href} href={item.href}>
                <span
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
                    isActive
                      ? "bg-primary text-primary-foreground font-medium shadow-sm"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  }`}
                >
                  <item.icon className="h-4 w-4" />
                  {item.label}
                </span>
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* Main area */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 border-b bg-background/95 backdrop-blur-sm flex items-center justify-between px-6 sticky top-0 z-10">
          <h1 className="font-semibold text-lg capitalize">{pageTitle}</h1>

          {/* Only render avatar after client mount to avoid hydration mismatch */}
          {mounted && user && (
            <div className="relative group cursor-pointer">
              <Avatar className="h-9 w-9">
                <AvatarFallback className="bg-primary/10 text-primary font-semibold">
                  {user.full_name.charAt(0).toUpperCase()}
                </AvatarFallback>
              </Avatar>
              {/* Hover tooltip */}
              <div className="absolute right-0 top-11 w-48 bg-popover border rounded-lg shadow-lg p-3 text-sm opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-20">
                <p className="font-medium truncate">{user.full_name}</p>
                <p className="text-xs text-muted-foreground truncate">{user.email}</p>
              </div>
            </div>
          )}
        </header>

        <main className="flex-1 p-6 overflow-auto">{children}</main>
      </div>
    </div>
  );
}
