/**
 * This is the entry point for the frontend application.
 * It sets up the router, providers, layouts, and pages for the app.
 */

import { Route, Routes } from "react-router";

import { ThemeProvider } from "@/components/theme-provider";
import { RootLayout } from "@/layouts/root-layout";
import { ChatPage } from "@/pages/chat-page";

function App() {
  return (
    <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
      <Routes>
        <Route element={<RootLayout />}>
          <Route index element={<ChatPage />} />
        </Route>
      </Routes>
    </ThemeProvider>
  );
}

export default App;
