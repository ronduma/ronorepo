/**
 * This is the sidebar component for the frontend application.
 * It provides navigation links and actions for the app.
 */

// react router
import { Link, useLocation } from "react-router";

// providers
import { useChatContext } from "@/components/chat/chat-provider";

// shadcn components
import { Button } from "@/components/ui/button";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";

// lucide icons
import { MessageSquare, SquarePen } from "lucide-react";

export function AppSidebar() {
  const { resetChat } = useChatContext();
  const location = useLocation();

  return (
    <Sidebar>
      <SidebarHeader>
        <div className="flex items-center justify-between px-2 py-1">
          <span className="font-mono text-sm font-medium tracking-tight">
            ronorepo
          </span>
        </div>
        <Button
          variant="outline"
          className="justify-start gap-2"
          onClick={resetChat}
        >
          <SquarePen className="size-4" />
          New chat
        </Button>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Workspace</SidebarGroupLabel>
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton
                isActive={location.pathname === "/"}
                className="data-active:bg-signal/10 data-active:text-signal"
                render={<Link to="/" />}
              >
                <MessageSquare className="size-4" />
                <span>Chat</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarGroup>
        <SidebarGroup>
          <SidebarGroupLabel>Chats</SidebarGroupLabel>
          <p className="px-2 py-1.5 text-xs text-muted-foreground">
            No conversations yet
          </p>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter />
    </Sidebar>
  );
}
