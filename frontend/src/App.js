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
import ExamAttempt from "./pages/exam/ExamPage";
import Leaderboards from "./pages/Leaderboards";
import Leaderboard from "./pages/Leaderboard";
import TestResult from "./pages/TestResult";
import StudentDashboard from "./pages/StudentDashboard";
import CourseCatalog from "./pages/CourseCatalog";
import CourseDetail from "./pages/CourseDetail";
import StudyMaterials from "./pages/StudyMaterials";
import AuthCallback from "./pages/AuthCallback";
import AdminLayout from "./components/admin/AdminLayout";
import Overview from "./pages/admin/Overview";
import Questions from "./pages/admin/Questions";
import Series from "./pages/admin/Series";
import Tests from "./pages/admin/Tests";
import Courses from "./pages/admin/Courses";
import Materials from "./pages/admin/Materials";
import Categories from "./pages/admin/Categories";
import Users from "./pages/admin/Users";
import Orders from "./pages/admin/Orders";
import Settings from "./pages/admin/Settings";

const ADMIN_ROLES = ["admin", "super_admin"];
const STAFF_ROLES = [...ADMIN_ROLES, "teacher"];

function Protected({ children, roles }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="min-h-screen flex items-center justify-center text-gray-400">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to={STAFF_ROLES.includes(user.role) ? "/admin" : "/dashboard"} replace />;
  return children;
}

const adminOnly = (el) => <Protected roles={ADMIN_ROLES}>{el}</Protected>;

function AppRouter() {
  const location = useLocation();
  if (location.hash?.includes("session_id=")) return <AuthCallback />;
  return (
    <>
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
        <Route path="/leaderboard" element={<Leaderboards />} />
        <Route path="/leaderboard/:testId" element={<Leaderboard />} />
        <Route path="/dashboard" element={<Protected><StudentDashboard /></Protected>} />
        <Route path="/exam/:attemptId" element={<Protected><ExamAttempt /></Protected>} />
        <Route path="/result/:attemptId" element={<Protected><TestResult /></Protected>} />
        <Route path="/admin" element={<Protected roles={STAFF_ROLES}><AdminLayout /></Protected>}>
          <Route index element={<Overview />} />
          <Route path="questions" element={<Questions />} />
          <Route path="series" element={<Series />} />
          <Route path="tests" element={<Tests />} />
          <Route path="courses" element={<Courses />} />
          <Route path="materials" element={<Materials />} />
          <Route path="categories" element={adminOnly(<Categories />)} />
          <Route path="users" element={adminOnly(<Users />)} />
          <Route path="orders" element={adminOnly(<Orders />)} />
          <Route path="settings" element={adminOnly(<Settings />)} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
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
        <AppRouter />
        <Toaster richColors position="top-right" theme="dark" />
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
