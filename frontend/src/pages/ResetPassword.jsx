import React, { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Loader2, Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";
import { api } from "../lib/api";
import { errMsg } from "../components/admin/kit";
import AuthCard from "../components/AuthCard";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";

export default function ResetPassword() {
  const token = useSearchParams()[0].get("token") || "";
  const nav = useNavigate();
  const [valid, setValid] = useState(null);
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!token) return setValid(false);
    api.get(`/auth/reset-password/${encodeURIComponent(token)}`).then((r) => setValid(r.data.valid)).catch(() => setValid(false));
  }, [token]);

  const submit = async (e) => {
    e.preventDefault();
    if (pw.length < 10) return toast.error("Password must be at least 10 characters");
    if (new TextEncoder().encode(pw).length > 72) return toast.error("Password must be 72 UTF-8 bytes or fewer");
    if (pw !== pw2) return toast.error("Passwords don't match");
    setLoading(true);
    try {
      await api.post("/auth/reset-password", { token, password: pw });
      toast.success("Password updated — sign in with your new password");
      nav("/login");
    } catch (err) { toast.error(errMsg(err)); setValid(false); }
    finally { setLoading(false); }
  };

  if (valid === null) return <AuthCard title="Reset password" testid="reset-password-page"><div className="text-sm text-gray-400 flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" />Checking link…</div></AuthCard>;
  if (!valid) {
    return (
      <AuthCard title="Link expired" subtitle="This reset link is invalid, already used or older than 1 hour." testid="reset-password-invalid">
        <Link to="/forgot-password"><Button className="w-full bg-blue-600 hover:bg-blue-700" data-testid="request-new-link">Request a new link</Button></Link>
      </AuthCard>
    );
  }
  const type = show ? "text" : "password";
  return (
    <AuthCard title="Set a new password" subtitle="Choose at least 10 characters (72 UTF-8 bytes maximum)." testid="reset-password-page">
      <form onSubmit={submit} className="space-y-4">
        <div>
          <Label className="text-gray-300">New password</Label>
          <div className="relative mt-1">
            <Input type={type} required minLength={10} maxLength={72} value={pw} onChange={(e) => setPw(e.target.value)} className="bg-[#0b1120] border-gray-800 text-white pr-10" data-testid="reset-password-new" autoComplete="new-password" />
            <button type="button" onClick={() => setShow(!show)} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white" aria-label="Show password">
              {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
        </div>
        <div>
          <Label className="text-gray-300">Confirm password</Label>
          <Input type={type} required minLength={10} maxLength={72} value={pw2} onChange={(e) => setPw2(e.target.value)} className="mt-1 bg-[#0b1120] border-gray-800 text-white" data-testid="reset-password-confirm" autoComplete="new-password" />
        </div>
        <Button type="submit" disabled={loading} className="w-full bg-blue-600 hover:bg-blue-700" data-testid="reset-password-submit">
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Update password"}
        </Button>
      </form>
    </AuthCard>
  );
}
