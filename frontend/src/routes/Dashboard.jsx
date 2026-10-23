import { RequireEstate } from '../components/RequireEstate';
import { useAuth } from '../context/AuthContext';
import { AdminDashboard, DashboardBody } from './Dashboard.admin';
import { ResidentDashboard } from './Dashboard.resident';

export { AdminDashboard, ResidentDashboard, DashboardBody };

export function Dashboard() {
  return (
    <RequireEstate>
      <DashboardRouter />
    </RequireEstate>
  );
}

function DashboardRouter() {
  const { user } = useAuth();
  if (user?.role === 'hoa_admin') return <AdminDashboard />;
  if (user?.role === 'service_provider') return <Navigate to="/provider/work" replace />;
  return <ResidentDashboard />;
}
import { Navigate } from 'react-router-dom';
