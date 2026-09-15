import { Navigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import Nav from '../components/landing/Nav';
import Hero from '../components/landing/Hero';
import Value from '../components/landing/Value';
import Capabilities from '../components/landing/Capabilities';
import Showcase from '../components/landing/Showcase';
import CtaBand from '../components/landing/CtaBand';
import Footer from '../components/landing/Footer';
import './landing.css';

export default function LandingPage() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="flex items-center gap-3 text-slate-500">
          <span className="w-5 h-5 border-2 border-slate-300 border-t-blue-800 rounded-full animate-spin" />
          <span className="text-sm font-medium">Loading…</span>
        </div>
      </div>
    );
  }

  if (user) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 antialiased">
      <Nav />
      <main>
        <Hero />
        <Value />
        <Capabilities />
        <Showcase />
        <CtaBand />
      </main>
      <Footer />
    </div>
  );
}