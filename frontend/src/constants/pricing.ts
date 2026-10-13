export type Tier = 'free' | 'monthly' | 'starter' | 'growth' | 'pro' | 'team' | 'business' | 'enterprise'

export type PlanSlug = 'starter' | 'builder' | 'scaler' | 'team' | 'business' | 'enterprise'

export type PlanTrack = 'individual' | 'business'

export const TIER_LEVELS: Record<Tier, number> = {
  free: 0,
  monthly: 0,
  starter: 1,
  growth: 2,
  pro: 3,
  team: 4,
  business: 5,
  enterprise: 6,
}

export const PLAN_TO_TIER: Record<PlanSlug, Tier> = {
  starter: 'starter',
  builder: 'pro',
  scaler: 'business',
  team: 'team',
  business: 'business',
  enterprise: 'enterprise',
}

export const TIER_TO_TRACK: Record<Tier, PlanTrack> = {
  free: 'individual',
  monthly: 'individual',
  starter: 'individual',
  growth: 'individual',
  pro: 'individual',
  team: 'business',
  business: 'business',
  enterprise: 'business',
}

export interface TierConfig {
  name: string
  price: number
  priceLabel: string
  slots: number
  seats: number
  reportDiscount: number
  extraSlotPrice: number
  whiteLabel: boolean
  apiAccess: boolean
  commercialUse: boolean
  freeReportsPerMonth: number
  priceCents?: number
}

export const TIER_CONFIG: Record<Tier, TierConfig> = {
  free: {
    name: 'Free',
    price: 0,
    priceLabel: 'Free',
    slots: 0,
    seats: 1,
    reportDiscount: 0,
    extraSlotPrice: 0,
    whiteLabel: false,
    apiAccess: false,
    commercialUse: false,
    freeReportsPerMonth: 0,
  },
  monthly: {
    name: 'OppGrid Monthly',
    price: 39,
    priceLabel: '$39/mo',
    priceCents: 3900,
    slots: 0,
    seats: 1,
    reportDiscount: 0,
    extraSlotPrice: 0,
    whiteLabel: false,
    apiAccess: false,
    commercialUse: false,
    freeReportsPerMonth: 2,
  },
  starter: {
    name: 'Starter',
    price: 20,
    priceLabel: '$20/mo',
    slots: 1,
    seats: 1,
    reportDiscount: 0,
    extraSlotPrice: 50,
    whiteLabel: false,
    apiAccess: false,
    commercialUse: false,
    freeReportsPerMonth: 1,
  },
  growth: {
    name: 'Growth',
    price: 50,
    priceLabel: '$50/mo',
    slots: 3,
    seats: 1,
    reportDiscount: 10,
    extraSlotPrice: 35,
    whiteLabel: false,
    apiAccess: false,
    commercialUse: false,
    freeReportsPerMonth: 3,
  },
  pro: {
    name: 'Pro',
    price: 99,
    priceLabel: '$99/mo',
    slots: 5,
    seats: 1,
    reportDiscount: 15,
    extraSlotPrice: 25,
    whiteLabel: false,
    apiAccess: false,
    commercialUse: true,
    freeReportsPerMonth: 5,
  },
  team: {
    name: 'Team',
    price: 250,
    priceLabel: '$250/mo',
    slots: 5,
    seats: 3,
    reportDiscount: 0,
    extraSlotPrice: 30,
    whiteLabel: true,
    apiAccess: false,
    commercialUse: true,
    freeReportsPerMonth: 10,
  },
  business: {
    name: 'Business',
    price: 750,
    priceLabel: '$750/mo',
    slots: 15,
    seats: 10,
    reportDiscount: 20,
    extraSlotPrice: 25,
    whiteLabel: true,
    apiAccess: true,
    commercialUse: true,
    freeReportsPerMonth: 20,
  },
  enterprise: {
    name: 'Enterprise',
    price: 2500,
    priceLabel: '$2,500+/mo',
    slots: 30,
    seats: -1,
    reportDiscount: 50,
    extraSlotPrice: 20,
    whiteLabel: true,
    apiAccess: true,
    commercialUse: true,
    freeReportsPerMonth: -1,
  },
}

export const PLAN_DISPLAY: Record<PlanSlug, { name: string; price: string; color: string; tier: Tier }> = {
  starter: { name: 'Starter', price: '$20/mo', color: 'gray', tier: 'starter' },
  builder: { name: 'Pro', price: '$99/mo', color: 'purple', tier: 'pro' },
  scaler: { name: 'Business', price: '$750/mo', color: 'emerald', tier: 'business' },
  team: { name: 'Team', price: '$250/mo', color: 'blue', tier: 'team' },
  business: { name: 'Business', price: '$750/mo', color: 'emerald', tier: 'business' },
  enterprise: { name: 'Enterprise', price: '$2,500+/mo', color: 'amber', tier: 'enterprise' },
}

export function getTierLevel(tier: Tier | string | undefined): number {
  return TIER_LEVELS[(tier || 'free') as Tier] ?? 0
}

export function hasTierAccess(userTier: Tier | string | undefined, requiredTier: Tier): boolean {
  return getTierLevel(userTier) >= TIER_LEVELS[requiredTier]
}

export function isBusinessTrack(tier: Tier | string | undefined): boolean {
  return TIER_TO_TRACK[(tier || 'free') as Tier] === 'business'
}

export const LAUNCH_OFFERS = {
  deepClone: { name: 'Deep Clone', priceCents: 4900, priceLabel: '$49' },
  monthly: { name: 'OppGrid Monthly', priceCents: 3900, priceLabel: '$39/mo' },
} as const

export const MONTHLY_LOCKED_FEATURES = [
  'expert_marketplace',
  'workhub',
  'datasets',
  'alerts',
] as const

export function getTierConfig(tier: Tier | string | undefined): TierConfig {
  return TIER_CONFIG[(tier || 'free') as Tier] ?? TIER_CONFIG.free
}
