import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { GraduationCap, Loader2 } from "lucide-react";
import { toast } from "sonner";
import GoogleButton, { OrDivider } from "../components/GoogleButton";

export default function Register() {
  const { register } = useAuth();
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "student" });
  const [loading, setLoading] = useState(false);
  const nav = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await register(form);
      toast.success("Account created");
      nav("/dashboard");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-md card-elev p-8 fade-in">
        <div className="flex items-center gap-2 mb-6">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-600 to-cyan-500 flex items-center justify-center">
            <GraduationCap className="w-5 h-5 text-white" />
          </div>
          <span className="heading-font text-xl font-bold text-white">ExamForge</span>
        </div>
        <h1 className="heading-font text-2xl font-bold text-white mb-1">Create your account</h1>
        <p className="text-sm text-gray-400 mb-6">Free forever for basic test series.</p>
        <GoogleButton label="Sign up with Google" />
        <OrDivider />
        <form onSubmit={submit} className="space-y-4">
          <div>
            <Label className="text-gray-300">Full name</Label>
            <Input data-testid="register-name" required value={form.name}
                   onChange={(e) => setForm({ ...form, name: e.target.value })}
                   className="mt-1 bg-[#0b1120] border-gray-800 text-white" />
          </div>
          <div>
            <Label className="text-gray-300">Email</Label>
            <Input data-testid="register-email" type="email" required value={form.email}
                   onChange={(e) => setForm({ ...form, email: e.target.value })}
                   className="mt-1 bg-[#0b1120] border-gray-800 text-white" />
          </div>
          <div>
            <Label className="text-gray-300">Password</Label>
            <p className="text-xs text-gray-500 mt-1">Use at least 10 characters (72 UTF-8 bytes maximum).</p>
            <Input data-testid="register-password" type="password" required minLength={10} maxLength={72} value={form.password}
                   onChange={(e) => setForm({ ...form, password: e.target.value })}
                   className="mt-1 bg-[#0b1120] border-gray-800 text-white" />
          </div>
          <Button type="submit" data-testid="register-submit" disabled={loading} className="w-full bg-blue-600 hover:bg-blue-700">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Create account"}
          </Button>
        </form>
        <div className="mt-5 text-sm text-gray-400 text-center">
          Already have an account? <Link to="/login" className="text-blue-400 hover:text-blue-300">Sign in</Link>
        </div>
      </div>
    </div>
  );
}
