import type { Metadata } from 'next';
import './globals.css';
import Sidebar from '@/components/Sidebar';

export const metadata: Metadata = {
  title: 'SmartWaste — City Waste Management',
  description: 'AI-powered smart city waste management and truck routing dashboard',
};

import { Toaster } from 'react-hot-toast';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-gray-50" style={{ fontFamily: "'Inter', system-ui, sans-serif" }}>
        <Sidebar />
        <div className="ml-60 min-h-screen flex flex-col">
          {children}
        </div>
        <Toaster position="bottom-right" />
      </body>
    </html>
  );
}
