/**
 * This is the root layout component for the frontend application.
 * It sets up the chat provider, sidebar provider, and the main layout structure.
 */

import { Outlet } from "react-router";

// custom components
import { ChatProvider } from "@/components/chat/chat-provider";
import { AppSidebar } from "@/components/app-sidebar";
import { ModeToggle } from "@/components/mode-toggle";

// shadcn components
import { StatusPill } from "@/components/ui/status-pill";
import { Separator } from "@/components/ui/separator";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";

export function RootLayout() {
  return (
    <ChatProvider>
      <SidebarProvider>
        <AppSidebar />
        <SidebarInset>
          <header className="flex h-14 shrink-0 items-center gap-2 border-b px-4">
            <SidebarTrigger />
            <Separator orientation="vertical" className="h-5" />
            <div className="flex-1" />
            <StatusPill />
            <Separator orientation="vertical" className="h-5" />
            <ModeToggle />
          </header>
          <div className="flex min-h-0 flex-1 flex-col">
            <Outlet />
          </div>
        </SidebarInset>
      </SidebarProvider>
    </ChatProvider>
  );
}
