import React, { useEffect, lazy, Suspense } from "react";
import "./App.css";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "./lib/auth";
import { Toaster } from "./components/ui/sonner";
import { SiteProvider } from "./lib/site";
import Footer from "./components/Footer";
import Navbar from "./components/Navbar";
import AnnouncementBar from "./components/AnnouncementBar";
import Home from "./pages/Home";
import AuthCallback from "./pages/AuthCallback";
const LegalPage = lazy(() => import("./pages/LegalPage"));
const SiteSettings = lazy(() => import("./pages/admin/SiteSettings"));
const HomeSettings = lazy(() => import("./pages/admin/HomeSettings"));
const LegalPages = lazy(() => import("./pages/admin/LegalPages"));
const AnnouncementSettings = lazy(() => import("./pages/admin/AnnouncementSettings"));
const Login = lazy(() => import("./pages/Login"));
const Register = lazy(() => import("./pages/Register"));
const TestSeriesCatalog = lazy(() => import("./pages/TestSeriesCatalog"));
const TestSeriesDetail = lazy(() => import("./pages/TestSeriesDetail"));
const ExamAttempt = lazy(() => import("./pages/exam/ExamPage"));
const Leaderboards = lazy(() => import("./pages/Leaderboards"));
const Leaderboard = lazy(() => import("./pages/Leaderboard"));
const TestResult = lazy(() => import("./pages/TestResult"));
const StudentDashboard = lazy(() => import("./pages/StudentDashboard"));
const CourseCatalog = lazy(() => import("./pages/CourseCatalog"));
const CourseDetail = lazy(() => import("./pages/CourseDetail"));
const StudyMaterials = lazy(() => import("./pages/StudyMaterials"));
const AdminLayout = lazy(() => import("./components/admin/AdminLayout"));
const Overview = lazy(() => import("./pages/admin/Overview"));
const Questions = lazy(() => import("./pages/admin/Questions"));
const Series = lazy(() => import("./pages/admin/Series"));
const Tests = lazy(() => import("./pages/admin/Tests"));
const Courses = lazy(() => import("./pages/admin/Courses"));
const Materials = lazy(() => import("./pages/admin/Materials"));
const Categories = lazy(() => import("./pages/admin/Categories"));
const Subjects = lazy(() => import("./pages/admin/Subjects"));
const Users = lazy(() => import("./pages/admin/Users"));
const Orders = lazy(() => import("./pages/admin/Orders"));
const Settings = lazy(() => import("./pages/admin/Settings"));
const Coupons = lazy(() => import("./pages/admin/Coupons"));

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

const PageLoader = () => (
  <div className="min-h-[60vh] flex items-center justify-center" data-testid="page-loader">
    <div className="w-8 h-8 rounded-full border-2 border-gray-700 border-t-cyan-400 animate-spin" />
  </div>
);

function AppRouter() {
  const location = useLocation();
  if (location.hash?.includes("session_id=")) return <AuthCallback />;
  return (
    <>
      {location.pathname === "/" && <AnnouncementBar />}
      <Navbar />
      <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/test-series" element={<TestSeriesCatalog />} />
        <Route path="/test-series/:id" element={<TestSeriesDetail />} />
        <Route path="/courses" element={<CourseCatalog />} />
        <Route path="/courses/:id" element={<Protected><CourseDetail /></Protected>} />
        <Route path="/study-materials" element={<StudyMaterials />} />
        <Route path="/page/:slug" element={<LegalPage />} />
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
          <Route path="subjects" element={<Subjects />} />
          <Route path="users" element={adminOnly(<Users />)} />
          <Route path="orders" element={adminOnly(<Orders />)} />
          <Route path="coupons" element={adminOnly(<Coupons />)} />
          <Route path="settings" element={adminOnly(<Settings />)} />
          <Route path="site" element={adminOnly(<SiteSettings />)} />
          <Route path="home" element={adminOnly(<HomeSettings />)} />
          <Route path="pages" element={adminOnly(<LegalPages />)} />
          <Route path="announcement" element={adminOnly(<AnnouncementSettings />)} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      </Suspense>
      <Footer />
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
      <SiteProvider>
      <BrowserRouter>
        <RazorpayLoader />
        <AppRouter />
        <Toaster richColors position="top-right" theme="dark" />
      </BrowserRouter>
      </SiteProvider>
    </AuthProvider>
  );
}

export default App;
