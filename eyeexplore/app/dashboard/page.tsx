import { redirect } from "next/navigation";

// Keep old bookmarks working while sending visitors straight to the full-page
// Dash workspace. The landing site's navigation no longer links to this path.
export default function DashboardRedirect(): never {
  redirect("/dashboard-app/");
}
