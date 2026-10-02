/**
 * This is a custom React hook for checking the health status of the backend API in the frontend application.
 */

import { useEffect, useState } from "react";

import { getHealth } from "@/api/health";

export type HealthStatus = "checking" | "ok" | "error";

const POLL_INTERVAL_MS = 20_000;

export function useHealth() {
  const [status, setStatus] = useState<HealthStatus>("checking");

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();

    const check = async () => {
      try {
        await getHealth(controller.signal);
        if (!cancelled) setStatus("ok");
      } catch {
        if (!cancelled) setStatus("error");
      }
    };

    check();
    const interval = setInterval(check, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      controller.abort();
      clearInterval(interval);
    };
  }, []);

  return { status };
}
