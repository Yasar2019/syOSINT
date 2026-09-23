import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "syOSINT — Syria Open-Source Situation Monitor",
  description:
    "A public-source, human-verified demonstration dashboard with transparent confidence and corrections.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
