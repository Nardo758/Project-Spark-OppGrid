/**
 * Launch surface flags. Unset or any value other than 1/true/yes/on is off.
 * Backend reads the same names with or without the VITE_ prefix.
 */
function envFlag(value: string | undefined): boolean {
  if (!value) return false
  return ['1', 'true', 'yes', 'on'].includes(value.trim().toLowerCase())
}

export const launchFlags = {
  services: envFlag(import.meta.env.VITE_LAUNCH_SERVICES),
  apiPortal: envFlag(import.meta.env.VITE_LAUNCH_API_PORTAL),
  reportCatalog: envFlag(import.meta.env.VITE_LAUNCH_REPORT_CATALOG),
  workhub: envFlag(import.meta.env.VITE_LAUNCH_WORKHUB),
} as const

export type LaunchFlagName = keyof typeof launchFlags
