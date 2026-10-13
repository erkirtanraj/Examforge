import React, { useEffect } from "react";
import "./App.css";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "./lib/auth";
import { Toaster } from "./components/ui/sonner";
import Navbar from "./components/Navbar";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Register from "./pages/Register";
import TestSeriesCatalog from "./pages/TestSeriesCatalog";
import TestSeriesDetail from "./pages/TestSeriesDetail";
import ExamAttempt from "./pages/ExamAttempt";
import TestResult from "./pages/TestResult";
import StudentDashboard from "./pages/StudentDashboard";
import CourseCatalog from "./pages/CourseCatalog";
import CourseDetail from "./pages/CourseDetail";
import StudyMaterials from "./pages/StudyMaterials";
import AdminDashboard from "./pages/AdminDashboard";

function Protected({ children, admin = false }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="min-h-screen flex items-center justify-center text-gray-400">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (admin && user.role !== "admin" && user.role !== "super_admin")
    return <Navigate to="/dashboard" replace />;
  return children;
}

function RazorpayLoader() {
  useEffect(() => {
    if (document.getElementById("razorpay-sdk")) return;
    const s = document.createElement("script");
    s.id = "razorpay-sdk";
    s.src = "https://checkout.razorpay.com/v1/checkout.js";
    s.async = true;
    document.body.appendChild(s);
  }, []);
  return null;
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <RazorpayLoader />
        <Navbar />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/test-series" element={<TestSeriesCatalog />} />
          <Route path="/test-series/:id" element={<TestSeriesDetail />} />
          <Route path="/courses" element={<CourseCatalog />} />
          <Route path="/courses/:id" element={<Protected><CourseDetail /></Protected>} />
          <Route path="/study-materials" element={<StudyMaterials />} />
          <Route path="/dashboard" element={<Protected><StudentDashboard /></Protected>} />
          <Route path="/exam/:attemptId" element={<Protected><ExamAttempt /></Protected>} />
          <Route path="/result/:attemptId" element={<Protected><TestResult /></Protected>} />
          <Route path="/admin" element={<Protected admin><AdminDashboard /></Protected>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <Toaster richColors position="top-right" theme="dark" />
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
