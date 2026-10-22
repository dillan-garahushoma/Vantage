import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { AppShell } from './components/AppShell';
import { LoadingState } from './components/ui';
import { AuthProvider, useAuth } from './context/AuthContext';
import { EstateProvider } from './context/EstateContext';
import { AdminResidency } from './routes/AdminResidency';
import { AdminSetup } from './routes/AdminSetup';
import { Announcements } from './routes/Announcements';
import { Complaints } from './routes/Complaints';
import { Contact } from './routes/Contact';
import { Dashboard } from './routes/Dashboard';
import { EstateHealth } from './routes/EstateHealth';
import { Incidents } from './routes/Incidents';
import { Intelligence } from './routes/Intelligence';
import { Join } from './routes/Join';
import { Landing } from './routes/Landing';
import { Login } from './routes/Login';
import { Members } from './routes/Members';
import { Methodology } from './routes/Methodology';
import { Notifications } from './routes/Notifications';
import { NotFound } from './routes/NotFound';
import { Properties } from './routes/Properties';
import { PasswordRecovery } from './routes/PasswordRecovery';
import { ProviderWaiting } from './routes/ProviderWaiting';
import { ProviderWork } from './routes/ProviderWork';
import { Providers } from './routes/Providers';
import { Register } from './routes/Register';
import { RequestAccess } from './routes/RequestAccess';
import { Settings } from './routes/Settings';
import { Welcome } from './routes/Welcome';
import { WelcomeSuccess } from './routes/WelcomeSuccess';
import { WorkOrders } from './routes/WorkOrders';

function Protected({ children }) {
    const { user, checking } = useAuth();
    const location = useLocation();
    if (checking) {
        return (<div className="mx-auto max-w-[1200px] px-6 py-20">
        <LoadingState label="Checking your session"/>
      </div>);
    }
    if (!user)
        return <Navigate to="/login" replace state={{ from: location.pathname }}/>;
    return <>{children}</>;
}

export function App() {
    return (<AuthProvider>
      <EstateProvider>
        <Routes>
          <Route path="/" element={<Landing />}/>
          <Route path="/login" element={<Login />}/>
          <Route path="/password-recovery" element={<PasswordRecovery />}/>
          <Route path="/register" element={<Register />}/>
          <Route path="/contact" element={<Contact />}/>
          <Route path="/methodology" element={<Methodology />}/>

          {/* Onboarding routes: each one decides for itself whether the state
            still applies (a resident who already has an estate is sent to
            the dashboard, an administrator to their setup screen). */}
          <Route path="/welcome" element={<Protected>
                <Welcome />
              </Protected>}/>
          <Route path="/join" element={<Protected>
                <Join />
              </Protected>}/>
          {/* The approval-based resident path. A join code remains available
            beside it for an estate office that prefers to hand one out. */}
          <Route path="/request-access" element={<Protected>
                <RequestAccess />
              </Protected>}/>
          <Route path="/welcome-success" element={<Protected>
                <WelcomeSuccess />
              </Protected>}/>
          <Route path="/provider/waiting" element={<Protected>
                <ProviderWaiting />
              </Protected>}/>

          <Route path="/app" element={<Protected>
                <AppShell />
              </Protected>}>
            <Route index element={<Dashboard />}/>
            <Route path="health" element={<EstateHealth />}/>
            <Route path="complaints" element={<Complaints />}/>
            <Route path="work-orders" element={<WorkOrders />}/>
            <Route path="announcements" element={<Announcements />}/>
            <Route path="incidents" element={<Incidents />}/>
            <Route path="properties" element={<Properties />}/>
            <Route path="providers" element={<Providers />}/>
            <Route path="notifications" element={<Notifications />}/>
          </Route>

          {/* VALORA Intelligence is a workspace of its own rather than a tab of
            the dashboard: it carries the briefing, the findings and the panel,
            and it is scoped to the estate selected in the shell. */}
          <Route path="/intelligence" element={<Protected>
                <AppShell />
              </Protected>}>
            <Route index element={<Intelligence />}/>
          </Route>

          {/* The administrator and provider views share the app shell, so the
            navigation and estate scope stay identical wherever you land. */}
          <Route path="/admin" element={<Protected>
                <AppShell />
              </Protected>}>
            <Route path="setup" element={<AdminSetup />}/>
            <Route path="residency" element={<AdminResidency />}/>
            <Route path="members" element={<Members />}/>
            <Route path="settings" element={<Settings />}/>
          </Route>

          <Route path="/provider" element={<Protected>
                <AppShell />
              </Protected>}>
            <Route path="work" element={<ProviderWork />}/>
          </Route>

          {/* Earlier Group8 bookmarks lead into the current Vantage workspace. */}
          <Route path="/dashboard" element={<Navigate to="/app" replace/>}/>
          <Route path="/properties" element={<Navigate to="/app/properties" replace/>}/>
          <Route path="/property" element={<Navigate to="/app/properties" replace/>}/>
          <Route path="/property-management" element={<Navigate to="/app/properties" replace/>}/>
          <Route path="/registration-requests" element={<Navigate to="/admin/residency" replace/>}/>
          <Route path="/user-management" element={<Navigate to="/admin/members" replace/>}/>
          <Route path="/resident-directory" element={<Navigate to="/admin/members" replace/>}/>
          <Route path="/resident-complaints" element={<Navigate to="/app/complaints" replace/>}/>
          <Route path="/complaints" element={<Navigate to="/app/complaints" replace/>}/>
          <Route path="/maintenance" element={<Navigate to="/app/complaints" replace/>}/>
          <Route path="/announcements" element={<Navigate to="/app/announcements" replace/>}/>
          <Route path="/community-announcements" element={<Navigate to="/app/announcements" replace/>}/>
          <Route path="/community-analytics" element={<Navigate to="/app/health" replace/>}/>
          <Route path="/providers" element={<Navigate to="/app/providers" replace/>}/>
          <Route path="/head-admin" element={<Navigate to="/admin/setup" replace/>}/>
          <Route path="/landing-page-settings" element={<Navigate to="/admin/setup" replace/>}/>
          <Route path="*" element={<NotFound />}/>
        </Routes>
      </EstateProvider>
    </AuthProvider>);
}
