import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './contexts/AuthContext';
import LoginPage from './pages/LoginPage';
import TeacherDashboard from './pages/TeacherDashboard';
import AdminDashboard from './pages/AdminDashboard';
import AdminSummary from './pages/AdminSummary';
import AdminStatus from './pages/AdminStatus';
import AdminPlans from './pages/AdminPlans';
import AdminDiscrepancies from './pages/AdminDiscrepancies';
import AdminUsers from './pages/AdminUsers';
import AdminExport from './pages/AdminExport';
import Layout from './components/Layout';

export default function App() {
  const { user } = useAuth();

  if (!user) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="*" element={<Navigate to="/login" />} />
      </Routes>
    );
  }

  if (user.role === 'teacher') {
    return (
      <Layout>
        <Routes>
          <Route path="/" element={<TeacherDashboard />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </Layout>
    );
  }

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<AdminDashboard />} />
        <Route path="/summary" element={<AdminSummary />} />
        <Route path="/status" element={<AdminStatus />} />
        <Route path="/plans" element={<AdminPlans />} />
        <Route path="/discrepancies" element={<AdminDiscrepancies />} />
        <Route path="/users" element={<AdminUsers />} />
        <Route path="/export" element={<AdminExport />} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </Layout>
  );
}
