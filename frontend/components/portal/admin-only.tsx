"use client";

import { Loader2, type LucideIcon } from "lucide-react";
import ComingSoon from "@/components/portal/coming-soon";
import { useMe } from "@/components/portal/use-me";

/** Beta gate: admins get the real feature, participants see Coming Soon. */
export default function AdminOnly({
  icon,
  title,
  description,
  children,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  const { data: me, isLoading } = useMe();

  if (isLoading)
    return (
      <div className="grid min-h-[70vh] place-items-center text-muted">
        <Loader2 className="size-6 animate-spin" />
      </div>
    );

  if (!me?.is_admin)
    return <ComingSoon icon={icon} title={title} description={description} />;

  return <>{children}</>;
}
