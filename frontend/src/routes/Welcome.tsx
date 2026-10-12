import { Navigate } from 'react-router-dom'
import { Keyline } from '../components/Brand'
import { PublicShell } from '../components/PublicShell'
import { Button, Card, ErrorState, LoadingState } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { useEstate } from '../context/EstateContext'
import { homeRouteFor } from '../lib/roleRouting'

/**
 * A single landing point after sign-in or registration.
 *
 * The destination is not the person's global role — it is what the *server*
 * says they are a member of: an estate administrator goes to the setup
 * checklist, a resident with no estate yet is sent to redeem a code, and a
 * provider with no estate waits to be added. Nobody is dropped on a dashboard
 * they cannot read.
 */
export function Welcome() {
  const { user } = useAuth()
  const { estates, loading, error, reload } = useEstate()

  if (!user) return <Navigate to="/login" replace />

  if (loading) {
    return (
      <PublicShell>
        <div className="mx-auto max-w-xl px-5 py-16">
          <Card className="p-6">
            <h1 className="text-[18px] font-semibold">Setting up your account</h1>
            <Keyline className="mt-3" />
            <LoadingState label="Resolving the estates you can act in" />
          </Card>
        </div>
      </PublicShell>
    )
  }

  if (error) {
    return (
      <PublicShell>
        <div className="mx-auto max-w-xl px-5 py-16">
          <ErrorState
            title="Could not resolve your estates"
            message={error.message}
            requestId={error.requestId}
            action={
              <Button variant="secondary" onClick={reload}>
                Try again
              </Button>
            }
          />
        </div>
      </PublicShell>
    )
  }

  return <Navigate to={homeRouteFor(user, estates)} replace />
}
