"use client";

import { useEffect, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import { getAdminToken } from "./api";

function subscribeToStorage(callback: () => void) {
  window.addEventListener("storage", callback);
  return () => window.removeEventListener("storage", callback);
}

/** SSR-safe read of the admin token: matches server (null) during hydration,
 * then picks up the real localStorage value once mounted on the client. */
export function useAdminToken(): string | null {
  return useSyncExternalStore(subscribeToStorage, getAdminToken, () => null);
}

/** Redirects to /admin/login if there's no admin token, and returns the
 * current token (null while redirecting) for pages under /admin/*. */
export function useRequireAdmin(): string | null {
  const router = useRouter();
  const token = useAdminToken();

  useEffect(() => {
    // Deliberately a direct, one-time read (not `token` above): during
    // hydration useSyncExternalStore briefly reports the SSR value (null)
    // before self-correcting to the real client value on the very next
    // paint, and this effect would otherwise fire on that transient null
    // and redirect an already-logged-in admin straight back to /login.
    if (!getAdminToken()) {
      router.push("/admin/login");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return token;
}
