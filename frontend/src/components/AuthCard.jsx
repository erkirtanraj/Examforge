import React from "react";
import BrandLogo from "./BrandLogo";

export default function AuthCard({ title, subtitle, children, testid }) {
  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-md card-elev p-6 sm:p-8 fade-in" data-testid={testid}>
        <div className="flex items-center gap-2 mb-6"><BrandLogo /></div>
        <h1 className="heading-font text-2xl font-bold text-white mb-1">{title}</h1>
        {subtitle && <p className="text-sm text-gray-400 mb-6">{subtitle}</p>}
        {children}
      </div>
    </div>
  );
}
