import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { GraduationCap, Loader2 } from "lucide-react";
import { toast } from "sonner";
import GoogleButton, { OrDivider } from "../components/GoogleButton";

export default function Login() {
  const { login } = useAuth();
  const [form, setForm] = useState({ email: "", password: "" });
  const [loading, setLoading] = useState(false);
  const nav = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const u = await login(form.email, form.password);
      toast.success(`Welcome back, ${u.name}`);
      nav(["admin", "super_admin", "teacher"].includes(u.role) ? "/admin" : "/dashboard");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-md card-elev p-8 fade-in">
        <div className="flex items-center gap-2 mb-6">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-600 to-cyan-500 flex items-center justify-center">
            <GraduationCap className="w-5 h-5 text-white" />
          </div>
          <span className="heading-font text-xl font-bold text-white">ExamForge</span>
        </div>
        <h1 className="heading-font text-2xl font-bold text-white mb-1">Welcome back</h1>
        <p className="text-sm text-gray-400 mb-6">Sign in to continue your prep.</p>
        <GoogleButton />
        <OrDivider />
        <form onSubmit={submit} className="space-y-4">
          <div>
            <Label className="text-gray-300">Email</Label>
            <Input data-testid="login-email" type="email" required value={form.email}
                   onChange={(e) => setForm({ ...form, email: e.target.value })}
                   className="mt-1 bg-[#0b1120] border-gray-800 text-white" placeholder="you@example.com" />
          </div>
          <div>
            <Label className="text-gray-300">Password</Label>
            <Input data-testid="login-password" type="password" required value={form.password}
                   onChange={(e) => setForm({ ...form, password: e.target.value })}
                   className="mt-1 bg-[#0b1120] border-gray-800 text-white" placeholder="••••••••" />
          </div>
          <Button type="submit" data-testid="login-submit" disabled={loading} className="w-full bg-blue-600 hover:bg-blue-700">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Sign in"}
          </Button>
        </form>
        <div className="mt-5 text-sm text-gray-400 text-center">
          New here? <Link to="/register" className="text-blue-400 hover:text-blue-300">Create account</Link>
        </div>
        <div className="mt-6 rounded-md border border-gray-800 bg-[#0b1120] p-3 text-xs text-gray-400">
          <div className="font-semibold text-gray-300 mb-1">Demo credentials</div>
          <div>Admin: admin@lms.com / admin123</div>
          <div>Student: student@lms.com / student123</div>
        </div>
      </div>
    </div>
  );
}
