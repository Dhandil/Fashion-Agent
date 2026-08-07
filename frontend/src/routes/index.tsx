import { Routes, Route } from "react-router-dom";
import AppLayout from "@/components/layout/AppLayout";
import ChatPage from "@/pages/chat/ChatPage";
import WardrobePage from "@/pages/wardrobe/WardrobePage";
import OutfitsPage from "@/pages/outfits/OutfitsPage";
import ProfilePage from "@/pages/profile/ProfilePage";
import SettingsPage from "@/pages/settings/SettingsPage";

export default function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<ChatPage />} />
        <Route path="wardrobe" element={<WardrobePage />} />
        <Route path="outfits" element={<OutfitsPage />} />
        <Route path="profile" element={<ProfilePage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
