import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'
import { AppShell } from './components/AppShell'
import { LoadingState } from './components/ui'
import { AuthProvider, useAuth } from './context/AuthContext'
import { EstateProvider } from './context/EstateContext'
import { AdminResidency } from './routes/AdminResidency'
import { AdminSetup } from './routes/AdminSetup'
import { Announcements } from './routes/Announcements'
import { Assets } from './routes/Assets'
import { Community } from './routes/Community'
import { Complaints } from './routes/Complaints'
import { Dashboard } from './routes/Dashboard'
import { EstateHealth } from './routes/EstateHealth'
import { Financial } from './routes/Financial'
import { Incidents } from './routes/Incidents'
import { Intelligence } from './routes/Intelligence'
import { Join } from './routes/Join'
import { Landing } from './routes/Landing'
import { Login } from './routes/Login'
import { Members } from './routes/Members'
import { NotFound } from './routes/NotFound'
import { Properties } from './routes/Properties'
import { ProviderPortal } from './routes/ProviderPortal'
import { ProviderWaiting } from './routes/ProviderWaiting'
import { ProviderWork } from './routes/ProviderWork'
import { Providers } from './routes/Providers'
import { PublicEstateDetail } from './routes/PublicEstateDetail'
import { PublicEstates } from './routes/PublicEstates'
import { Register } from './routes/Register'
import { RequestAccess } from './routes/RequestAccess'
import { Settings } from './routes/Settings'
import { Welcome } from './routes/Welcome'
import { WorkOrders } from './routes/WorkOrders'

function Protected({ children }: { children: ReactNode }) {
  const { user, checking } = useAuth()
  const location = useLocation()

  if (checking) {
    return (
      <div className="mx-auto max-w-[1200px] px-6 py-20">
        <LoadingState label="Checking your session" />
      </div>
    )
  }

  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />

  return <>{children}</>
}

export function App() {
  return (
    <AuthProvider>
      <EstateProvider>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/estates" element={<PublicEstates />} />
          <Route path="/estates/:id" element={<PublicEstateDetail />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* Onboarding routes: each one decides for itself whether the state
              still applies (a resident who already has an estate is sent to
              the dashboard, an administrator to their setup screen). */}
          <Route
            path="/welcome"
            element={
              <Protected>
                <Welcome />
              </Protected>
            }
          />
          <Route
            path="/join"
            element={
              <Protected>
                <Join />
              </Protected>
            }
          />
          {/* The approval-based resident path. A join code remains available
              beside it for an estate office that prefers to hand one out. */}
          <Route
            path="/request-access"
            element={
              <Protected>
                <RequestAccess />
              </Protected>
            }
          />
          <Route
            path="/provider/waiting"
            element={
              <Protected>
                <ProviderWaiting />
              </Protected>
            }
          />

          <Route
            path="/app"
            element={
              <Protected>
                <AppShell />
              </Protected>
            }
          >
            <Route index element={<Dashboard />} />
            <Route path="health" element={<EstateHealth />} />
            <Route path="assets" element={<Assets />} />
            <Route path="complaints" element={<Complaints />} />
            <Route path="work-orders" element={<WorkOrders />} />
            <Route path="announcements" element={<Announcements />} />
            <Route path="incidents" element={<Incidents />} />
            <Route path="financial" element={<Financial />} />
            <Route path="community" element={<Community />} />
            <Route path="properties" element={<Properties />} />
            <Route path="providers" element={<Providers />} />
          </Route>

          {/* VALORA Intelligence is a workspace of its own rather than a tab of
              the dashboard: it carries the briefing, the findings and the panel,
              and it is scoped to the estate selected in the shell. */}
          <Route
            path="/intelligence"
            element={
              <Protected>
                <AppShell />
              </Protected>
            }
          >
            <Route index element={<Intelligence />} />
          </Route>

          {/* The administrator and provider views share the app shell, so the
              navigation and estate scope stay identical wherever you land. */}
          <Route
            path="/admin"
            element={
              <Protected>
                <AppShell />
              </Protected>
            }
          >
            <Route path="setup" element={<AdminSetup />} />
            <Route path="residency" element={<AdminResidency />} />
            <Route path="members" element={<Members />} />
            <Route path="settings" element={<Settings />} />
          </Route>

          <Route
            path="/provider"
            element={
              <Protected>
                <AppShell />
              </Protected>
            }
          >
            <Route path="work" element={<ProviderWork />} />
            <Route path="portal" element={<ProviderPortal />} />
          </Route>

          <Route path="*" element={<NotFound />} />
        </Routes>
      </EstateProvider>
    </AuthProvider>
  )
}
