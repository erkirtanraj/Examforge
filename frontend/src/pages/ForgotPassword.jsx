import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Loader2, MailCheck, ArrowLeft } from "lucide-react";
import { toast } from "sonner";
import { api } from "../lib/api";
import { errMsg } from "../components/admin/kit";
import AuthCard from "../components/AuthCard";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try { await api.post("/auth/forgot-password", { email }); setSent(true); }
    catch (err) { toast.error(errMsg(err)); }
    finally { setLoading(false); }
  };

  return (
    <AuthCard title="Forgot password?" subtitle={sent ? null : "Enter your account email and we'll send you a link to reset it."} testid="forgot-password-page">
      {sent ? (
        <div className="space-y-4" data-testid="forgot-password-sent">
          <div className="rounded-md border border-emerald-500/40 bg-emerald-500/10 p-4 text-sm text-emerald-200 flex gap-3">
            <MailCheck className="w-5 h-5 shrink-0" />
            <span>If an account exists for <b className="text-white">{email}</b>, a reset link is on its way. It expires in 1 hour — check your spam folder too.</span>
          </div>
          <button type="button" onClick={() => setSent(false)} className="text-sm text-blue-400 hover:text-blue-300" data-testid="forgot-password-retry">Use a different email</button>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-4">
          <div>
            <Label className="text-gray-300">Email</Label>
            <Input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com"
                   className="mt-1 bg-[#0b1120] border-gray-800 text-white" data-testid="forgot-password-email" />
          </div>
          <Button type="submit" disabled={loading} className="w-full bg-blue-600 hover:bg-blue-700" data-testid="forgot-password-submit">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Send reset link"}
          </Button>
        </form>
      )}
      <Link to="/login" className="mt-6 inline-flex items-center gap-1.5 text-sm text-gray-400 hover:text-white" data-testid="back-to-login">
        <ArrowLeft className="w-4 h-4" /> Back to sign in
      </Link>
    </AuthCard>
  );
}
