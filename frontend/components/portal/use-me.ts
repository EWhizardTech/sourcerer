"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getMe, logout } from "@/lib/portal-api";

/** Auth state from the portal session cookie. data === null -> signed out. */
export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: getMe,
    staleTime: 60_000,
    retry: false,
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return async () => {
    await logout();
    queryClient.setQueryData(["me"], null);
    queryClient.clear();
  };
}
