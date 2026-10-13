import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { BadgeCheck, XCircle, Loader2, Search } from "lucide-react";
import { api } from "../lib/api";
import AuthCard from "../components/AuthCard";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";

export default function VerifyCertificate() {
  const { code } = useParams();
  const nav = useNavigate();
  const [input, setInput] = useState(code || "");
  const [res, setRes] = useState(code ? undefined : null);

  useEffect(() => {
    if (!code) return;
    setRes(undefined);
    api.get(`/certificates/${encodeURIComponent(code)}`).then((r) => setRes(r.data)).catch(() => setRes(false));
  }, [code]);

  return (
    <AuthCard title="Verify a certificate" subtitle="Enter the certificate ID printed on the certificate." testid="verify-certificate-page">
      <form onSubmit={(e) => { e.preventDefault(); if (input.trim()) nav(`/verify/${input.trim().toUpperCase()}`); }} className="flex gap-2">
        <Input value={input} onChange={(e) => setInput(e.target.value)} placeholder="EF-XXXX-XXXX-XXXX" className="bg-[#0b1120] border-gray-800 text-white mono-font uppercase" data-testid="verify-input" />
        <Button type="submit" className="bg-blue-600 hover:bg-blue-700" data-testid="verify-submit"><Search className="w-4 h-4" /></Button>
      </form>
      {res === undefined && <div className="mt-6 text-sm text-gray-400 flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" />Checking…</div>}
      {res === false && (
        <div className="mt-6 rounded-md border border-rose-500/40 bg-rose-500/10 p-4 text-sm text-rose-200 flex gap-3" data-testid="verify-invalid">
          <XCircle className="w-5 h-5 shrink-0" />No certificate found with ID <b className="mono-font">{code}</b>.
        </div>
      )}
      {res && (
        <div className="mt-6 rounded-md border border-emerald-500/40 bg-emerald-500/10 p-4 text-sm space-y-2" data-testid="verify-valid">
          <div className="flex items-center gap-2 text-emerald-300 font-semibold"><BadgeCheck className="w-5 h-5" />Valid certificate</div>
          <div className="text-gray-300">Awarded to <b className="text-white" data-testid="verify-name">{res.name}</b></div>
          <div className="text-gray-300">for completing <b className="text-white" data-testid="verify-course">{res.course_title}</b></div>
          <div className="text-xs text-gray-400 mono-font">ID {res.id} · Issued {new Date(res.issued_at).toLocaleDateString()}</div>
        </div>
      )}
    </AuthCard>
  );
}
