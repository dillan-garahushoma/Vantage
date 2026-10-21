import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { CreateWorkOrderDialog } from './valora/CreateWorkOrderDialog';
import { LogComplaintDrawer } from '../routes/Complaints';
import { MobileNav, MobileNavSheet } from './layout/MobileNav';
import { Sidebar } from './layout/Sidebar';
import { TopBar } from './layout/TopBar';
/**
 * The signed-in workspace.
 *
 * One shell for residents, administrators and providers: the rail filters itself
 * by role, the estate switcher scopes every screen, and the header offers the one
 * action that role may actually take. The two creation flows live here because
 * they are reachable from every screen — a work order for an administrator, a
 * complaint for a resident — and both post to the real API.
 */
export function AppShell() {
    const { user } = useAuth();
    const [navOpen, setNavOpen] = useState(false);
    const [creatingWorkOrder, setCreatingWorkOrder] = useState(false);
    const [loggingComplaint, setLoggingComplaint] = useState(false);
    if (!user)
        return null;
    return (<div className="min-h-screen bg-paper">
      <Sidebar />

      <div className="lg:pl-[272px]">
        <TopBar onOpenNav={() => setNavOpen(true)} onCreateWorkOrder={user.role === 'hoa_admin' ? () => setCreatingWorkOrder(true) : undefined} onLogComplaint={user.role === 'resident' ? () => setLoggingComplaint(true) : undefined}/>

        <main className="mx-auto max-w-[1440px] px-4 pt-5 pb-28 sm:px-6 lg:px-8 lg:pb-12">
          <Outlet />
        </main>
      </div>

      <MobileNav onOpenNav={() => setNavOpen(true)} onCreate={user.role === 'hoa_admin'
            ? () => setCreatingWorkOrder(true)
            : user.role === 'resident'
                ? () => setLoggingComplaint(true)
                : undefined} createLabel={user.role === 'resident' ? 'Log issue' : 'Work order'}/>
      <MobileNavSheet open={navOpen} onOpenChange={setNavOpen}/>

      <CreateWorkOrderDialog open={creatingWorkOrder} onOpenChange={setCreatingWorkOrder}/>
      {loggingComplaint ? (<LogComplaintDrawer onClose={() => setLoggingComplaint(false)} onDone={() => setLoggingComplaint(false)}/>) : null}
    </div>);
}
