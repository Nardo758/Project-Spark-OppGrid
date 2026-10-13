import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { launchFlags, type LaunchFlagName } from '../config/launchFlags'
import { useAuthStore } from '../stores/authStore'

/** Buyer routes for a launch-hidden surface redirect to pricing while the flag is off. */
export function LaunchRoute({ flag, children }: { flag: LaunchFlagName; children: ReactNode }) {
  if (!launchFlags[flag]) {
    return <Navigate to="/pricing" replace />
  }
  return <>{children}</>
}

/** WorkHub stays available to admins when its launch flag is off. */
export function WorkHubRoute({ children }: { children: ReactNode }) {
  const isAdmin = useAuthStore((s) => Boolean(s.user?.is_admin))
  if (launchFlags.workhub || isAdmin) {
    return <>{children}</>
  }
  return <Navigate to="/pricing" replace />
}
