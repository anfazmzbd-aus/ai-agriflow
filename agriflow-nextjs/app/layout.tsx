import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = { title: { default:"AgriFlow AI | Smarter decisions, stronger harvests", template:"%s | AgriFlow AI" }, description:"A Sri Lanka-focused, climate-smart agricultural AI agent platform. Explore its vision, workflow, and interactive demo dashboard.", robots:{ index:true, follow:true } };
export default function RootLayout({children}:{children:React.ReactNode}) { return <html lang="en"><body>{children}</body></html>; }
