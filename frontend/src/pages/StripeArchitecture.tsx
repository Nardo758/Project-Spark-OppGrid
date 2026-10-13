import { Link } from 'react-router-dom'
import { ArrowDown, CreditCard, Users, FileText, Zap, Database, Webhook, CheckCircle, ArrowLeft } from 'lucide-react'

export default function StripeArchitecture() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Clickable Logo Header */}
        <div className="flex items-center justify-between mb-8">
          <Link to="/welcome" className="flex items-center gap-3 group">
            <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center group-hover:bg-emerald-400 transition-colors">
              <span className="text-slate-900 font-bold text-lg">OG</span>
            </div>
            <div className="flex flex-col">
              <span className="font-semibold text-xl text-white leading-tight group-hover:text-emerald-400 transition-colors">OppGrid</span>
              <span className="text-[10px] text-slate-400 leading-tight">The Opportunity Intelligence Platform</span>
            </div>
          </Link>
          <Link to="/welcome" className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors">
            <ArrowLeft className="w-4 h-4" />
            <span className="text-sm">Back to Home</span>
          </Link>
        </div>

        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-white mb-4">OppGrid Stripe Payment Architecture</h1>
          <p className="text-slate-400 text-lg">Three Revenue Streams: Subscriptions, Pay-Per-Report, Expert Services</p>
        </div>

        {/* Revenue Streams Summary */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          <div className="bg-gradient-to-br from-emerald-500/20 to-emerald-600/10 border border-emerald-500/30 rounded-xl p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 bg-emerald-500/20 rounded-lg flex items-center justify-center">
                <CreditCard className="w-6 h-6 text-emerald-400" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white">Subscriptions</h3>
                <p className="text-emerald-400 text-sm">Recurring Revenue</p>
              </div>
            </div>
            <div className="space-y-2 text-sm text-slate-300">
              <div className="flex justify-between"><span>OppGrid Monthly</span><span className="text-emerald-400">$39/mo</span></div>
            </div>
          </div>

          <div className="bg-gradient-to-br from-blue-500/20 to-blue-600/10 border border-blue-500/30 rounded-xl p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 bg-blue-500/20 rounded-lg flex items-center justify-center">
                <FileText className="w-6 h-6 text-blue-400" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white">Pay-Per-Report</h3>
                <p className="text-blue-400 text-sm">One-Time Purchases</p>
              </div>
            </div>
            <div className="space-y-2 text-sm text-slate-300">
              <div className="flex justify-between"><span>Deep Clone</span><span className="text-blue-400">$49</span></div>
            </div>
          </div>

          <div className="bg-gradient-to-br from-purple-500/20 to-purple-600/10 border border-purple-500/30 rounded-xl p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 bg-purple-500/20 rounded-lg flex items-center justify-center">
                <Users className="w-6 h-6 text-purple-400" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white">Expert Services</h3>
                <p className="text-purple-400 text-sm">Stripe Connect</p>
              </div>
            </div>
            <div className="space-y-2 text-sm text-slate-300">
              <div className="flex justify-between"><span>Platform Fee</span><span className="text-purple-400">15%</span></div>
              <div className="flex justify-between"><span>Expert Payout</span><span className="text-purple-400">85%</span></div>
              <div className="flex justify-between"><span>Auto Transfer</span><span className="text-purple-400">Yes</span></div>
            </div>
          </div>
        </div>

        {/* Architecture Diagram */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-8 mb-8">
          <h2 className="text-2xl font-bold text-white mb-8 text-center">System Architecture</h2>
          
          {/* Frontend Layer */}
          <div className="mb-8">
            <div className="text-center mb-4">
              <span className="bg-cyan-500/20 text-cyan-400 px-4 py-2 rounded-full text-sm font-medium">Frontend (React)</span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-slate-700/50 border border-slate-600 rounded-lg p-4 text-center">
                <p className="text-white font-medium text-sm">Pricing.tsx</p>
                <p className="text-slate-400 text-xs mt-1">Plan Selection</p>
              </div>
              <div className="bg-slate-700/50 border border-slate-600 rounded-lg p-4 text-center">
                <p className="text-white font-medium text-sm">OpportunityDetail.tsx</p>
                <p className="text-slate-400 text-xs mt-1">Pay-Per-Unlock</p>
              </div>
              <div className="bg-slate-700/50 border border-slate-600 rounded-lg p-4 text-center">
                <p className="text-white font-medium text-sm">IdeaEngine.tsx</p>
                <p className="text-slate-400 text-xs mt-1">Validation</p>
              </div>
              <div className="bg-slate-700/50 border border-slate-600 rounded-lg p-4 text-center">
                <p className="text-white font-medium text-sm">ExpertMarketplace.tsx</p>
                <p className="text-slate-400 text-xs mt-1">Expert Booking</p>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4 max-w-2xl mx-auto">
              <div className="bg-cyan-900/30 border border-cyan-700/50 rounded-lg p-4 text-center">
                <p className="text-cyan-400 font-medium text-sm">PayPerUnlockModal.tsx</p>
                <p className="text-slate-400 text-xs mt-1">Stripe Elements</p>
              </div>
              <div className="bg-cyan-900/30 border border-cyan-700/50 rounded-lg p-4 text-center">
                <p className="text-cyan-400 font-medium text-sm">ReportPurchaseModal.tsx</p>
                <p className="text-slate-400 text-xs mt-1">Payment Form</p>
              </div>
            </div>
          </div>

          {/* Arrow */}
          <div className="flex justify-center mb-8">
            <ArrowDown className="w-8 h-8 text-slate-500" />
          </div>

          {/* Backend Layer */}
          <div className="mb-8">
            <div className="text-center mb-4">
              <span className="bg-amber-500/20 text-amber-400 px-4 py-2 rounded-full text-sm font-medium">Backend API (FastAPI)</span>
            </div>
            
            {/* Routers */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-slate-700/50 border border-amber-600/30 rounded-lg p-4 text-center">
                <p className="text-amber-400 font-medium text-sm">subscriptions.py</p>
                <div className="text-slate-400 text-xs mt-2 space-y-1">
                  <p>/checkout</p>
                  <p>/portal</p>
                  <p>/cancel</p>
                </div>
              </div>
              <div className="bg-slate-700/50 border border-amber-600/30 rounded-lg p-4 text-center">
                <p className="text-amber-400 font-medium text-sm">payments.py</p>
                <div className="text-slate-400 text-xs mt-2 space-y-1">
                  <p>/micro</p>
                  <p>/project</p>
                  <p>/confirm</p>
                </div>
              </div>
              <div className="bg-slate-700/50 border border-amber-600/30 rounded-lg p-4 text-center">
                <p className="text-amber-400 font-medium text-sm">report_pricing.py</p>
                <div className="text-slate-400 text-xs mt-2 space-y-1">
                  <p>/pay-per-unlock</p>
                  <p>/deep-dive</p>
                  <p>/fast-pass</p>
                </div>
              </div>
              <div className="bg-slate-700/50 border border-amber-600/30 rounded-lg p-4 text-center">
                <p className="text-amber-400 font-medium text-sm">idea_validations.py</p>
                <div className="text-slate-400 text-xs mt-2 space-y-1">
                  <p>/validate</p>
                  <p>payment + AI</p>
                </div>
              </div>
            </div>

            {/* Core Service */}
            <div className="bg-gradient-to-r from-amber-900/30 to-orange-900/30 border border-amber-600/50 rounded-xl p-6 max-w-4xl mx-auto">
              <div className="flex items-center justify-center gap-2 mb-4">
                <Zap className="w-5 h-5 text-amber-400" />
                <p className="text-amber-400 font-bold">stripe_service.py (Core Service)</p>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <p className="text-white font-medium mb-2 text-sm">Subscription Management</p>
                  <ul className="text-slate-400 text-xs space-y-1">
                    <li>• create_checkout_session()</li>
                    <li>• create_portal_session()</li>
                    <li>• cancel_subscription()</li>
                    <li>• reactivate_subscription()</li>
                  </ul>
                </div>
                <div>
                  <p className="text-white font-medium mb-2 text-sm">One-Time Payments</p>
                  <ul className="text-slate-400 text-xs space-y-1">
                    <li>• create_micro_payment_intent()</li>
                    <li>• create_project_payment_intent()</li>
                    <li>• create_report_payment_intent()</li>
                    <li>• create_deep_dive_payment_intent()</li>
                    <li>• create_fast_pass_payment_intent()</li>
                    <li>• create_validation_payment_intent()</li>
                  </ul>
                </div>
                <div>
                  <p className="text-white font-medium mb-2 text-sm">Stripe Connect (Experts)</p>
                  <ul className="text-slate-400 text-xs space-y-1">
                    <li>• create_connect_account()</li>
                    <li>• create_connect_account_link()</li>
                    <li>• create_payment_intent_with_transfer()</li>
                    <li>• create_transfer_to_expert()</li>
                    <li>• calculate_platform_split()</li>
                  </ul>
                </div>
                <div>
                  <p className="text-white font-medium mb-2 text-sm">Pricing Constants</p>
                  <ul className="text-slate-400 text-xs space-y-1">
                    <li>• DEEP_DIVE: $49</li>
                    <li>• DEEP_CLONE: $49</li>
                    <li>• Expert Split: 85/15</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

          {/* Arrow */}
          <div className="flex justify-center mb-8">
            <div className="flex items-center gap-4">
              <ArrowDown className="w-8 h-8 text-slate-500" />
              <ArrowDown className="w-8 h-8 text-slate-500" />
            </div>
          </div>

          {/* Bottom Layer - Webhooks and Database */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Webhooks */}
            <div>
              <div className="text-center mb-4">
                <span className="bg-red-500/20 text-red-400 px-4 py-2 rounded-full text-sm font-medium">
                  <Webhook className="w-4 h-4 inline mr-2" />
                  Stripe Webhooks
                </span>
              </div>
              <div className="bg-slate-700/50 border border-red-600/30 rounded-xl p-6">
                <p className="text-red-400 font-medium text-sm mb-4 text-center">stripe_webhook.py → /api/v1/stripe-webhook</p>
                <div className="space-y-2 text-xs">
                  <p className="text-green-400 font-medium mb-1">Success Events</p>
                  <div className="flex items-center gap-2 text-slate-300">
                    <CheckCircle className="w-3 h-3 text-green-400" />
                    <span>checkout.session.completed → Link subscription</span>
                  </div>
                  <div className="flex items-center gap-2 text-slate-300">
                    <CheckCircle className="w-3 h-3 text-green-400" />
                    <span>payment_intent.succeeded → Fulfill purchase</span>
                  </div>
                  <div className="flex items-center gap-2 text-slate-300">
                    <CheckCircle className="w-3 h-3 text-green-400" />
                    <span>invoice.paid → Record payment</span>
                  </div>
                  <div className="flex items-center gap-2 text-slate-300">
                    <CheckCircle className="w-3 h-3 text-green-400" />
                    <span>customer.subscription.updated → Sync tier</span>
                  </div>
                  <div className="flex items-center gap-2 text-slate-300">
                    <CheckCircle className="w-3 h-3 text-green-400" />
                    <span>customer.subscription.deleted → Cancel</span>
                  </div>
                  <p className="text-red-400 font-medium mt-3 mb-1">Failure Events</p>
                  <div className="flex items-center gap-2 text-slate-300">
                    <CheckCircle className="w-3 h-3 text-red-400" />
                    <span>payment_intent.payment_failed → Mark failed</span>
                  </div>
                  <div className="flex items-center gap-2 text-slate-300">
                    <CheckCircle className="w-3 h-3 text-red-400" />
                    <span>invoice.payment_failed → Handle retry</span>
                  </div>
                </div>
                <div className="mt-4 p-3 bg-slate-800/50 rounded-lg">
                  <p className="text-slate-400 text-xs text-center">Idempotency: stripe_webhook_events table</p>
                </div>
              </div>
            </div>

            {/* Database */}
            <div>
              <div className="text-center mb-4">
                <span className="bg-green-500/20 text-green-400 px-4 py-2 rounded-full text-sm font-medium">
                  <Database className="w-4 h-4 inline mr-2" />
                  PostgreSQL Database
                </span>
              </div>
              <div className="bg-slate-700/50 border border-green-600/30 rounded-xl p-6">
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-slate-800/50 rounded-lg p-3 text-center">
                    <p className="text-green-400 text-xs font-medium">subscriptions</p>
                    <p className="text-slate-500 text-xs mt-1">tier, status, stripe_*_id</p>
                  </div>
                  <div className="bg-slate-800/50 rounded-lg p-3 text-center">
                    <p className="text-green-400 text-xs font-medium">transactions</p>
                    <p className="text-slate-500 text-xs mt-1">type, status, amount</p>
                  </div>
                  <div className="bg-slate-800/50 rounded-lg p-3 text-center">
                    <p className="text-green-400 text-xs font-medium">unlocked_opportunities</p>
                    <p className="text-slate-500 text-xs mt-1">user_id, method, expires</p>
                  </div>
                  <div className="bg-slate-800/50 rounded-lg p-3 text-center">
                    <p className="text-green-400 text-xs font-medium">stripe_webhook_events</p>
                    <p className="text-slate-500 text-xs mt-1">idempotency tracking</p>
                  </div>
                  <div className="bg-slate-800/50 rounded-lg p-3 text-center">
                    <p className="text-green-400 text-xs font-medium">engagements</p>
                    <p className="text-slate-500 text-xs mt-1">expert payments</p>
                  </div>
                  <div className="bg-slate-800/50 rounded-lg p-3 text-center">
                    <p className="text-green-400 text-xs font-medium">purchased_reports</p>
                    <p className="text-slate-500 text-xs mt-1">report purchases</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Integration Status */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <h3 className="text-xl font-bold text-white mb-6 text-center">Integration Status</h3>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {[
              { name: 'Checkout Flows', file: 'subscriptions.py', status: 'Connected' },
              { name: 'One-Time Unlocks', file: 'report_pricing.py', status: 'Connected' },
              { name: 'Idea Validation', file: 'idea_validations.py', status: 'Connected' },
              { name: 'Expert Payouts', file: 'expert_collaboration.py', status: 'Connected' },
              { name: 'Webhook Processing', file: 'stripe_webhook.py', status: 'Connected' },
            ].map((item) => (
              <div key={item.name} className="bg-slate-700/30 border border-green-500/30 rounded-lg p-4 text-center">
                <CheckCircle className="w-6 h-6 text-green-400 mx-auto mb-2" />
                <p className="text-white font-medium text-sm">{item.name}</p>
                <p className="text-slate-400 text-xs mt-1">{item.file}</p>
                <span className="inline-block mt-2 px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded-full">{item.status}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="text-center mt-8 text-slate-500 text-sm">
          OppGrid Payment Architecture Diagram • Last Updated: {new Date().toLocaleDateString()}
        </div>
      </div>
    </div>
  )
}
