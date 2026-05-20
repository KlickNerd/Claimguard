import { cookies } from "next/headers";
import { AppSidebar } from "@/components/app/app-sidebar";
import { AuthProvider } from "@/lib/auth-context";
import { createServerClientFromCookies } from "@/lib/supabase-server";

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Pre-fetch the session on the server so the first client render
  // already knows who the user is - avoids the "logged-out flicker"
  // while the client awaits its own getSession() call. The middleware
  // has already redirected anonymous users to /login by the time we
  // get here, so the session should never be null in practice.
  const cookieStore = await cookies();
  const supabase = createServerClientFromCookies(cookieStore);
  const {
    data: { session },
  } = await supabase.auth.getSession();

  return (
    <AuthProvider initialSession={session}>
      <div className="flex min-h-screen bg-background">
        <AppSidebar />
        <div className="flex min-w-0 flex-1 flex-col">{children}</div>
      </div>
    </AuthProvider>
  );
}
