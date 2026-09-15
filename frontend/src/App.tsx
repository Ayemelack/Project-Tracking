import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './auth/AuthContext';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import AdminRoute from './components/AdminRoute';
import LoginPage from './pages/LoginPage';
import ResetPasswordPage from './pages/ResetPasswordPage';
import LandingPage from './pages/LandingPage';
import UsersPage from './pages/UsersPage';
import Dashboard from './pages/Dashboard';
import UploadPage from './pages/UploadPage';
import EstimateRegister from './pages/EstimateRegister';
import EstimateDetail from './pages/EstimateDetail';
import FundingRegister from './pages/FundingRegister';
import FundReceiptForm from './pages/FundReceiptForm';
import FundReceiptDetail from './pages/FundReceiptDetail';
import ExpenseRegister from './pages/ExpenseRegister';
import ExpenseForm from './pages/ExpenseForm';
import ExpenseDetailPage from './pages/ExpenseDetail';
import ResourceRegister from './pages/ResourceRegister';
import ResourceForm from './pages/ResourceForm';
import ResourceDetailPage from './pages/ResourceDetail';
import SchedulePage from './pages/SchedulePage';
import ActivityForm from './pages/ActivityForm';
import ActivityDetailPage from './pages/ActivityDetailPage';
import MilestoneForm from './pages/MilestoneForm';
import AskAssistant from './pages/AskAssistant';

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/estimates" element={<EstimateRegister />} />
            <Route path="/estimates/:id" element={<EstimateDetail />} />
            <Route path="/funding" element={<FundingRegister />} />
            <Route path="/funding/new" element={<FundReceiptForm />} />
            <Route path="/funding/:id" element={<FundReceiptDetail />} />
            <Route path="/expenses" element={<ExpenseRegister />} />
            <Route path="/expenses/new" element={<ExpenseForm />} />
            <Route path="/expenses/:id" element={<ExpenseDetailPage />} />
            <Route path="/resources" element={<ResourceRegister />} />
            <Route path="/resources/new" element={<ResourceForm />} />
            <Route path="/resources/:id" element={<ResourceDetailPage />} />
            <Route path="/schedule" element={<SchedulePage />} />
            <Route path="/schedule/new" element={<ActivityForm />} />
            <Route path="/schedule/milestones/new" element={<MilestoneForm />} />
            <Route path="/schedule/:id" element={<ActivityDetailPage />} />
            <Route path="/assistant" element={<AskAssistant />} />
            <Route path="/users" element={<AdminRoute><UsersPage /></AdminRoute>} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}