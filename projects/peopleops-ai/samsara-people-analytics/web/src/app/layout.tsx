import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = { title: "Samsara People Analytics — Demo", description: "A fully synthetic, independently verified employee survey analytics demonstration." };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
