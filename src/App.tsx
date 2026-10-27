import { useCallback, useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { NavLink, Route, Routes, useLocation, useSearchParams } from 'react-router-dom'
import { AlertTriangle, BarChart3, CalendarDays, CheckCircle2, ChevronRight, CircleDollarSign, Clock3, FileCheck2, FileUp, HelpCircle, Loader2, Menu, Pencil, Plus, ReceiptText, Search, Settings, ShieldCheck, Sparkles, Trash2, X } from 'lucide-react'
import {
  ApiError, DEMO_USER_ID, formatDate, formatDateTime, formatMoney, formatPeriod,
  createTimesheet, deleteTimesheet, listTimesheets, updateTimesheet,
  getPayrollRule, savePayrollRule,
  uploadPayslip,
  getDashboard, getVerification, runVerification,
  type DashboardSummary, type PayrollRuleInput, type PayslipResult, type PayslipStatus,
  type Timesheet, type TimesheetInput, type VerificationResult, type VerificationStatus,
} from './lib/api'

const MAX_UPLOAD_MB = 10
const PAYSLIP_STATUS_STYLES: Record<PayslipStatus, string> = { EXTRACTED: 'bg-emerald-50 text-emerald-700', NEEDS_REVIEW: 'bg-amber-50 text-amber-700', FAILED: 'bg-red-50 text-red-700', UPLOADED: 'bg-slate-100 text-slate-600', PROCESSING: 'bg-slate-100 text-slate-600' }
const PAYSLIP_STATUS_LABELS: Record<PayslipStatus, string> = { EXTRACTED: 'Extracted', NEEDS_REVIEW: 'Needs review', FAILED: 'Failed', UPLOADED: 'Uploaded', PROCESSING: 'Processing' }
const VERIFICATION_STATUS_STYLES: Record<VerificationStatus, string> = { MATCH: 'bg-emerald-50 text-emerald-700', UNDERPAID: 'bg-red-50 text-red-700', OVERPAID: 'bg-blue-50 text-blue-700', NEEDS_REVIEW: 'bg-amber-50 text-amber-700' }
const VERIFICATION_STATUS_LABELS: Record<VerificationStatus, string> = { MATCH: 'Match', UNDERPAID: 'Underpaid', OVERPAID: 'Overpaid', NEEDS_REVIEW: 'Needs review' }
const errorMessage = (e: unknown, fallback: string) => e instanceof ApiError ? e.message : fallback

function SummaryRow({ label, value }: { label: string, value: string }) { return <div className="flex justify-between border-b border-slate-100 py-2.5 text-sm last:border-0"><span className="text-slate-500">{label}</span><span className="font-semibold text-slate-900">{value}</span></div> }
function Spinner({ label }: { label: string }) { return <div className="card flex items-center justify-center gap-2 p-10 text-sm text-slate-500"><Loader2 size={18} className="animate-spin" />{label}</div> }
function ErrorCard({ message, onRetry }: { message: string, onRetry?: () => void }) { return <div className="card flex flex-col items-center gap-3 p-10 text-center"><AlertTriangle className="text-red-500" size={28} /><p className="text-sm text-slate-600">{message}</p>{onRetry && <button className="btn-secondary" onClick={onRetry}>Try again</button>}</div> }

const nav = [
  { to: '/', label: 'Dashboard', icon: BarChart3 }, { to: '/timesheets', label: 'Timesheets', icon: Clock3 },
  { to: '/rules', label: 'Payroll Rules', icon: ReceiptText }, { to: '/upload', label: 'Payslip Upload', icon: FileUp },
  { to: '/result', label: 'Verification Result', icon: FileCheck2 },
]
const titles: Record<string, [string, string]> = {
  '/': ['Dashboard', 'Your payroll verification overview'], '/timesheets': ['Timesheets', 'Record and manage your worked hours'],
  '/rules': ['Payroll Rules', 'Configure rates used to calculate expected pay'], '/upload': ['Payslip Upload', 'Upload a payslip to compare against your hours'],
  '/result': ['Verification Result', 'Detailed breakdown of a payroll verification'],
}

function Layout({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false); const location = useLocation(); const [title, sub] = titles[location.pathname] ?? titles['/']
  return <div className="min-h-screen lg:flex">
    {open && <button aria-label="Close menu" className="fixed inset-0 z-30 bg-slate-950/30 lg:hidden" onClick={() => setOpen(false)} />}
    <aside className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-[#10251f] text-white transition-transform lg:sticky lg:top-0 lg:h-screen ${open ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}`}>
      <div className="flex h-20 items-center justify-between px-6"><div className="flex items-center gap-3"><span className="grid h-9 w-9 place-items-center rounded-xl bg-brand-500"><CircleDollarSign size={21} /></span><span className="text-xl font-bold tracking-tight">Payguide</span></div><button className="lg:hidden" onClick={() => setOpen(false)}><X /></button></div>
      <div className="mx-4 border-t border-white/10" /><nav className="flex-1 space-y-1 p-4 pt-6">{nav.map(({ to, label, icon: Icon }) => <NavLink end={to === '/'} onClick={() => setOpen(false)} key={to} to={to} className={({ isActive }) => `flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium transition ${isActive ? 'bg-white text-[#133a2f] shadow-sm' : 'text-emerald-50/70 hover:bg-white/8 hover:text-white'}`}><Icon size={19} />{label}</NavLink>)}</nav>
      <div className="m-4 rounded-2xl bg-white/7 p-4"><div className="mb-2 flex items-center gap-2 text-sm font-semibold"><HelpCircle size={17} />Need help?</div><p className="text-xs leading-5 text-emerald-50/60">Learn how Payguide verifies your pay.</p></div>
      <div className="flex items-center gap-3 border-t border-white/10 p-5"><div className="grid h-9 w-9 place-items-center rounded-full bg-[#f1b87a] text-sm font-bold text-[#523010]">AP</div><div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold">Alex Parker</p><p className="truncate text-xs text-white/50">alex@example.com</p></div><Settings size={17} className="text-white/50" /></div>
    </aside>
    <main className="min-w-0 flex-1"><header className="flex min-h-20 items-center gap-4 border-b border-slate-200/70 bg-white px-4 sm:px-8"><button className="rounded-lg p-2 hover:bg-slate-100 lg:hidden" onClick={() => setOpen(true)}><Menu /></button><div className="flex-1"><h1 className="text-xl font-bold tracking-tight sm:text-2xl">{title}</h1><p className="mt-0.5 hidden text-sm text-slate-500 sm:block">{sub}</p></div><button className="rounded-xl border border-slate-200 p-2.5 text-slate-500"><Search size={18} /></button></header><div className="p-4 sm:p-8">{children}</div></main>
  </div>
}

function Stat({ label, value, icon: Icon, tone = 'green', hint }: { label: string, value: string, icon: any, tone?: string, hint: string }) { const c = tone === 'red' ? 'bg-red-50 text-red-600' : tone === 'amber' ? 'bg-amber-50 text-amber-600' : tone === 'blue' ? 'bg-blue-50 text-blue-600' : 'bg-brand-50 text-brand-600'; return <div className="card p-5"><div className="flex items-start justify-between"><div><p className="text-sm text-slate-500">{label}</p><p className="mt-2 text-2xl font-bold tracking-tight">{value}</p></div><span className={`rounded-xl p-2.5 ${c}`}><Icon size={20} /></span></div><p className="mt-4 text-xs text-slate-500">{hint}</p></div> }
function VerificationBadge({ value }: { value: VerificationStatus }) { return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-bold ${VERIFICATION_STATUS_STYLES[value]}`}>{VERIFICATION_STATUS_LABELS[value]}</span> }

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

function Dashboard() {
  const [state, setState] = useState<{ phase: 'loading' | 'ready' | 'error', data?: DashboardSummary, error?: string }>({ phase: 'loading' })

  function fetchDashboard() {
    getDashboard().then(data => setState({ phase: 'ready', data })).catch(e => setState({ phase: 'error', error: errorMessage(e, 'Could not load your dashboard.') }))
  }
  useEffect(fetchDashboard, [])
  function load() { setState({ phase: 'loading' }); fetchDashboard() } // retry handler (event-driven, not effect-driven)

  return <div className="space-y-6">
    <section className="rounded-2xl bg-[#163d32] p-6 text-white sm:flex sm:items-center sm:justify-between sm:p-8"><div><p className="mb-2 text-sm font-medium text-emerald-200">Welcome back, Alex</p><h2 className="max-w-xl text-2xl font-bold sm:text-3xl">Know exactly what you should be paid.</h2><p className="mt-2 text-sm text-white/65">Add your hours, upload your payslip, and let Payguide check the numbers.</p></div><NavLink to="/upload" className="mt-5 inline-flex items-center gap-2 rounded-xl bg-white px-4 py-3 text-sm font-bold text-[#14382f] sm:mt-0">Verify a payslip <ChevronRight size={17} /></NavLink></section>

    {state.phase === 'loading' && <Spinner label="Loading your dashboard…" />}
    {state.phase === 'error' && <ErrorCard message={state.error!} onRetry={load} />}

    {state.phase === 'ready' && (() => {
      const { latest_verification: latest, hours_logged_current_period: hours, history } = state.data!
      const underpaid = latest?.status === 'UNDERPAID' ? latest.gross_difference : null
      const overpaid = latest?.status === 'OVERPAID' ? latest.gross_difference : null
      return <>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <Stat label="Expected pay" value={latest ? formatMoney(latest.expected_gross_pay) : '—'} icon={CircleDollarSign} hint={latest ? formatPeriod(latest.pay_period_start, latest.pay_period_end) : 'No verification yet'} />
          <Stat label="Actual pay" value={latest ? formatMoney(latest.actual_gross_pay) : '—'} icon={ReceiptText} hint="From uploaded payslip" />
          <Stat label="Potential underpayment" value={underpaid ? formatMoney(underpaid.replace('-', '')) : '—'} icon={BarChart3} tone={underpaid ? 'red' : 'green'} hint={underpaid ? 'Requires attention' : 'None detected'} />
          <Stat label="Potential overpayment" value={overpaid ? formatMoney(overpaid) : '—'} icon={BarChart3} tone={overpaid ? 'amber' : 'green'} hint={overpaid ? 'Worth double-checking' : 'None detected'} />
        </div>

        <div className="grid gap-6 xl:grid-cols-[1.6fr_1fr]">
          <div className="card p-6">
            <div className="mb-6 flex items-center justify-between"><div><h3 className="font-bold">Recent verifications</h3><p className="text-sm text-slate-500">Your latest payroll checks</p></div></div>
            {history.length === 0
              ? <p className="rounded-xl bg-slate-50 p-6 text-center text-sm text-slate-500">No verifications yet. Upload a payslip to get started.</p>
              : <div className="overflow-x-auto"><table className="w-full min-w-[580px] text-left text-sm"><thead className="border-b border-slate-100 text-xs uppercase text-slate-400"><tr>{['Pay period', 'Expected', 'Actual', 'Difference', 'Status', ''].map(x => <th className="pb-3 font-semibold" key={x}>{x}</th>)}</tr></thead><tbody>{history.map(v => <tr className="border-b border-slate-100 last:border-0" key={v.id}>
                <td className="py-4 font-semibold">{formatPeriod(v.pay_period_start, v.pay_period_end)}</td>
                <td>{formatMoney(v.expected_gross_pay)}</td>
                <td>{formatMoney(v.actual_gross_pay)}</td>
                <td>{v.gross_difference == null ? '—' : formatMoney(v.gross_difference)}</td>
                <td><VerificationBadge value={v.status} /></td>
                <td><NavLink className="text-sm font-semibold text-brand-600" to={`/result?payslipId=${v.payslip_id}`}>View</NavLink></td>
              </tr>)}</tbody></table></div>}
          </div>

          <div className="card p-6">
            <h3 className="font-bold">Quick actions</h3><p className="text-sm text-slate-500">Continue setting up your pay check</p>
            <div className="mt-5 space-y-3">{[[CalendarDays, 'Add worked hours', '/timesheets'], [ReceiptText, 'Update pay rates', '/rules'], [FileUp, 'Upload a payslip', '/upload']].map(([Icon, label, to]: any) => <NavLink className="flex items-center gap-3 rounded-xl border border-slate-100 p-3 hover:bg-slate-50" to={to} key={label}><span className="rounded-lg bg-brand-50 p-2 text-brand-600"><Icon size={18} /></span><span className="flex-1 text-sm font-semibold">{label}</span><ChevronRight size={17} className="text-slate-400" /></NavLink>)}</div>
            {latest && <div className="mt-5 border-t border-slate-100 pt-5">
              <div className="flex items-center justify-between"><h4 className="text-sm font-bold">Latest result</h4><VerificationBadge value={latest.status} /></div>
              <p className="mt-2 text-xs leading-5 text-slate-500">{latest.explanation_summary ?? 'No explanation available.'}</p>
              <dl className="mt-4 space-y-2 text-xs"><div className="flex justify-between"><dt className="text-slate-500">Tax withheld</dt><dd className="font-semibold">{formatMoney(latest.estimated_tax)}</dd></div><div className="flex justify-between"><dt className="text-slate-500">Deductions</dt><dd className="font-semibold">{formatMoney(latest.deductions)}</dd></div><div className="flex justify-between"><dt className="text-slate-500">Hours logged</dt><dd className="font-semibold">{hours == null ? '—' : `${hours} hrs`}</dd></div></dl>
              <NavLink to={`/result?payslipId=${latest.payslip_id}`} className="btn-secondary mt-4 w-full">View full result</NavLink>
            </div>}
          </div>
        </div>
      </>
    })()}
  </div>
}

// ---------------------------------------------------------------------------
// Timesheets
// ---------------------------------------------------------------------------

const SHIFT_TYPES = [['normal', 'Normal'], ['saturday', 'Saturday'], ['sunday', 'Sunday'], ['public_holiday', 'Public holiday'], ['overnight', 'Overnight'], ['early_morning', 'Early morning'], ['evening', 'Evening']]
const todayIso = () => new Date().toISOString().slice(0, 10)
const emptyTimesheetForm = () => ({ work_date: todayIso(), start_time: '09:00', end_time: '17:00', break_minutes: '30', shift_type: 'normal' })

function Timesheets() {
  const [list, setList] = useState<Timesheet[] | null>(null)
  const [listError, setListError] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState(emptyTimesheetForm())
  const [formError, setFormError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [justSaved, setJustSaved] = useState(false)

  function refresh() {
    listTimesheets().then(setList).catch(e => setListError(errorMessage(e, 'Could not load your timesheets.')))
  }
  useEffect(refresh, [])
  useEffect(() => {
    if (!justSaved) return
    const timer = setTimeout(() => setJustSaved(false), 4000)
    return () => clearTimeout(timer)
  }, [justSaved])

  function startEdit(t: Timesheet) {
    setEditingId(t.id)
    setForm({ work_date: t.work_date, start_time: t.start_time.slice(0, 5), end_time: t.end_time.slice(0, 5), break_minutes: String(t.break_minutes), shift_type: t.shift_type })
    setFormError(null)
  }
  function cancelEdit() { setEditingId(null); setForm(emptyTimesheetForm()); setFormError(null) }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (form.start_time === form.end_time) { setFormError('Start time and end time must differ.'); return }
    const breakMinutes = Number(form.break_minutes)
    if (!Number.isFinite(breakMinutes) || breakMinutes < 0) { setFormError('Break minutes must be zero or more.'); return }

    const input: TimesheetInput = { user_id: DEMO_USER_ID, work_date: form.work_date, start_time: `${form.start_time}:00`, end_time: `${form.end_time}:00`, break_minutes: breakMinutes, shift_type: form.shift_type }
    setSaving(true); setFormError(null)
    try {
      if (editingId) await updateTimesheet(editingId, input)
      else await createTimesheet(input)
      cancelEdit(); refresh(); setJustSaved(true)
    } catch (e) { setFormError(errorMessage(e, 'Could not save this shift.')) }
    finally { setSaving(false) }
  }

  async function onDelete(id: string) {
    try { await deleteTimesheet(id); refresh(); if (editingId === id) cancelEdit() }
    catch (e) { setListError(errorMessage(e, 'Could not delete this shift.')) }
  }

  return <div className="grid gap-6 xl:grid-cols-[1fr_1.2fr]">
    <form className="card p-6" onSubmit={onSubmit}>
      <div className="mb-6 flex items-center gap-3"><span className="rounded-xl bg-brand-50 p-2.5 text-brand-600"><Plus /></span><div><h2 className="font-bold">{editingId ? 'Edit shift' : 'Add a shift'}</h2><p className="text-sm text-slate-500">Enter your worked hours</p></div></div>
      <div className="grid gap-5 sm:grid-cols-2">
        <div className="sm:col-span-2"><label><span className="label">Date</span><input className="input" type="date" value={form.work_date} onChange={e => setForm({ ...form, work_date: e.target.value })} required /></label></div>
        <label><span className="label">Start time</span><input className="input" type="time" value={form.start_time} onChange={e => setForm({ ...form, start_time: e.target.value })} required /></label>
        <label><span className="label">End time</span><input className="input" type="time" value={form.end_time} onChange={e => setForm({ ...form, end_time: e.target.value })} required /></label>
        <label><span className="label">Break (minutes)</span><input className="input" type="number" min="0" value={form.break_minutes} onChange={e => setForm({ ...form, break_minutes: e.target.value })} required /></label>
        <label><span className="label">Shift type</span><select className="input" value={form.shift_type} onChange={e => setForm({ ...form, shift_type: e.target.value })}>{SHIFT_TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
      </div>
      {formError && <p className="mt-4 flex items-center gap-2 rounded-xl bg-red-50 p-3 text-sm text-red-700"><AlertTriangle size={16} className="shrink-0" />{formError}</p>}
      <div className="mt-6 flex gap-3">
        <button className="btn-primary flex-1" type="submit" disabled={saving}>{saving ? <Loader2 size={17} className="animate-spin" /> : <Plus size={17} />}{editingId ? 'Save changes' : 'Add shift'}</button>
        {editingId && <button type="button" className="btn-secondary" onClick={cancelEdit}>Cancel</button>}
      </div>
      {!editingId && justSaved && <p className="mt-3 flex items-center gap-2 text-xs font-semibold text-emerald-600"><CheckCircle2 size={14} />Shift saved</p>}
    </form>

    <div className="card p-6">
      <div className="mb-5"><h2 className="font-bold">Your shifts</h2><p className="text-sm text-slate-500">{list ? `${list.length} shift${list.length === 1 ? '' : 's'} on record` : 'Loading…'}</p></div>
      {listError && <ErrorCard message={listError} onRetry={refresh} />}
      {!listError && list === null && <Spinner label="Loading timesheets…" />}
      {!listError && list?.length === 0 && <p className="rounded-xl bg-slate-50 p-6 text-center text-sm text-slate-500">No shifts recorded yet.</p>}
      {!listError && list && list.length > 0 && <div className="space-y-3">{list.map(t => <div className="grid grid-cols-[1fr_auto] items-center gap-2 rounded-xl border border-slate-100 p-4 sm:grid-cols-[1fr_1fr_auto_auto]" key={t.id}>
        <div><p className="text-sm font-semibold">{formatDate(t.work_date)}</p><p className="text-xs text-slate-500 sm:hidden">{t.start_time.slice(0, 5)} – {t.end_time.slice(0, 5)}</p></div>
        <p className="hidden text-sm text-slate-500 sm:block">{t.start_time.slice(0, 5)} – {t.end_time.slice(0, 5)}</p>
        <div className="text-right"><p className="text-sm font-bold">{t.hours_worked} hrs</p><p className="text-xs text-brand-600">{SHIFT_TYPES.find(([v]) => v === t.shift_type)?.[1] ?? t.shift_type}</p></div>
        <div className="flex gap-1 justify-self-end"><button aria-label="Edit shift" className="rounded-lg p-2 text-slate-400 hover:bg-slate-50 hover:text-brand-600" onClick={() => startEdit(t)}><Pencil size={16} /></button><button aria-label="Delete shift" className="rounded-lg p-2 text-slate-400 hover:bg-red-50 hover:text-red-600" onClick={() => onDelete(t.id)}><Trash2 size={16} /></button></div>
      </div>)}</div>}
    </div>
  </div>
}

// ---------------------------------------------------------------------------
// Payroll Rules
// ---------------------------------------------------------------------------

const RATE_FIELDS = [['normal_rate', 'Normal hourly rate'], ['overtime_rate', 'Overtime rate'], ['saturday_rate', 'Saturday rate'], ['sunday_rate', 'Sunday rate'], ['public_holiday_rate', 'Public holiday rate'], ['overnight_rate', 'Overnight rate'], ['early_morning_rate', 'Early morning rate'], ['evening_rate', 'Evening rate']] as const
type RateKey = typeof RATE_FIELDS[number][0]

function Rules() {
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [values, setValues] = useState<Record<RateKey, string>>(Object.fromEntries(RATE_FIELDS.map(([k]) => [k, ''])) as Record<RateKey, string>)
  const [hasExistingRule, setHasExistingRule] = useState(false)
  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle')
  const [saveError, setSaveError] = useState<string | null>(null)

  useEffect(() => {
    getPayrollRule().then(rule => {
      if (rule) { setHasExistingRule(true); setValues(Object.fromEntries(RATE_FIELDS.map(([k]) => [k, rule[k]])) as Record<RateKey, string>) }
    }).catch(e => setLoadError(errorMessage(e, 'Could not load your payroll rules.'))).finally(() => setLoading(false))
  }, [])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    for (const [key, label] of RATE_FIELDS) {
      const n = Number(values[key])
      if (values[key].trim() === '' || !Number.isFinite(n) || n < 0) { setSaveState('error'); setSaveError(`${label} must be a non-negative number.`); return }
    }
    setSaveState('saving'); setSaveError(null)
    try {
      const input: PayrollRuleInput = { user_id: DEMO_USER_ID, ...values } as PayrollRuleInput
      await savePayrollRule(input)
      setHasExistingRule(true); setSaveState('saved')
    } catch (e) { setSaveState('error'); setSaveError(errorMessage(e, 'Could not save your rates.')) }
  }

  return <div className="mx-auto max-w-4xl">
    <div className="mb-6 rounded-2xl border border-blue-100 bg-blue-50 p-4 text-sm text-blue-800"><div className="flex gap-3"><ShieldCheck className="shrink-0" size={20} /><p><b>Rates are private.</b> These are the rates <em>you</em> configure for calculating your expected pay - Payguide does not look up or apply award rates on your behalf.</p></div></div>
    {loading && <Spinner label="Loading your payroll rules…" />}
    {loadError && <ErrorCard message={loadError} />}
    {!loading && !loadError && <form className="card p-6 sm:p-8" onSubmit={onSubmit}>
      <div className="mb-7"><h2 className="text-lg font-bold">Your pay rates</h2><p className="text-sm text-slate-500">Enter gross hourly rates before tax and deductions.{hasExistingRule ? ' Saving creates a new current version - your rates stay fully under your control.' : ''}</p></div>
      <div className="grid gap-5 sm:grid-cols-2">{RATE_FIELDS.map(([key, label]) => <label key={key}><span className="label">{label}</span><div className="flex rounded-xl border border-slate-200 focus-within:border-brand-500 focus-within:ring-3 focus-within:ring-brand-100"><span className="border-r border-slate-200 px-3.5 py-2.5 text-sm text-slate-500">AUD $</span><input className="min-w-0 flex-1 rounded-r-xl px-3.5 py-2.5 text-sm outline-none" type="number" step=".01" min="0" value={values[key]} onChange={e => setValues({ ...values, [key]: e.target.value })} required /><span className="px-3.5 py-2.5 text-sm text-slate-400">/hr</span></div></label>)}</div>
      {saveError && <p className="mt-5 flex items-center gap-2 rounded-xl bg-red-50 p-3 text-sm text-red-700"><AlertTriangle size={16} className="shrink-0" />{saveError}</p>}
      <div className="mt-8 flex items-center justify-end gap-3">{saveState === 'saved' && <span className="flex items-center gap-1 text-xs font-semibold text-emerald-600"><CheckCircle2 size={14} />Rates saved</span>}<button className="btn-primary min-w-36" type="submit" disabled={saveState === 'saving'}>{saveState === 'saving' ? <Loader2 size={17} className="animate-spin" /> : 'Save rates'}</button></div>
    </form>}
  </div>
}

// ---------------------------------------------------------------------------
// Payslip Upload
// ---------------------------------------------------------------------------

function Upload() {
  const [file, setFile] = useState<File | null>(null)
  const [phase, setPhase] = useState<'idle' | 'uploading' | 'done' | 'error'>('idle')
  const [result, setResult] = useState<PayslipResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  function onPick(picked: File | null) {
    setResult(null); setError(null); setPhase('idle')
    if (!picked) { setFile(null); return }
    if (picked.type !== 'application/pdf' && !picked.name.toLowerCase().endsWith('.pdf')) { setFile(null); setError('Please choose a PDF file.'); return }
    if (picked.size > MAX_UPLOAD_MB * 1024 * 1024) { setFile(null); setError(`This file is larger than the ${MAX_UPLOAD_MB} MB limit.`); return }
    setFile(picked)
  }

  async function onVerify() {
    if (!file || phase === 'uploading') return
    setPhase('uploading'); setError(null)
    try { setResult(await uploadPayslip(file)); setPhase('done') }
    catch (e) { setError(errorMessage(e, 'Something went wrong while uploading your payslip.')); setPhase('error') }
  }

  return <div className="mx-auto max-w-3xl space-y-6">
    <div className="card p-6 sm:p-10">
      <div className="text-center"><span className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-brand-50 text-brand-600"><FileUp size={27} /></span><h2 className="mt-4 text-xl font-bold">Upload your payslip</h2><p className="mx-auto mt-2 max-w-md text-sm text-slate-500">Choose a PDF payslip. We’ll compare it with your hours and configured pay rates.</p></div>
      <label className="mt-8 flex min-h-56 cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-200 bg-slate-50/60 p-6 text-center transition hover:border-brand-400 hover:bg-brand-50/40">
        <input className="hidden" type="file" accept="application/pdf" onChange={e => onPick(e.target.files?.[0] ?? null)} />
        {file ? <><FileCheck2 size={34} className="text-brand-600" /><p className="mt-3 font-semibold">{file.name}</p><p className="mt-1 text-xs text-slate-500">{(file.size / 1024).toFixed(1)} KB · Ready to verify</p></> : <><FileUp size={32} className="text-slate-400" /><p className="mt-3 text-sm font-semibold">Drop your PDF here, or <span className="text-brand-600">browse</span></p><p className="mt-1 text-xs text-slate-400">PDF only · Maximum {MAX_UPLOAD_MB} MB</p></>}
      </label>
      {error && <p className="mt-4 flex items-center gap-2 rounded-xl bg-red-50 p-3 text-sm text-red-700"><AlertTriangle size={16} className="shrink-0" />{error}</p>}
      <button type="button" disabled={!file || phase === 'uploading'} onClick={onVerify} className={`btn-primary mt-6 w-full ${(!file || phase === 'uploading') ? 'pointer-events-none opacity-50' : ''}`}>
        {phase === 'uploading' ? <><Loader2 size={17} className="animate-spin" />Extracting…</> : <><Sparkles size={17} />{phase === 'error' ? 'Retry upload' : 'Verify payslip'}</>}
      </button>
    </div>
    <div className="flex items-center justify-center gap-2 text-xs text-slate-500"><ShieldCheck size={15} />Your payslip is encrypted and processed securely</div>

    {result && <div className="card p-6 sm:p-8">
      <div className="flex items-center justify-between"><h3 className="font-bold">Extraction summary</h3><span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-bold ${PAYSLIP_STATUS_STYLES[result.status]}`}>{PAYSLIP_STATUS_LABELS[result.status]}</span></div>
      {result.status === 'FAILED'
        ? <p className="mt-4 text-sm text-slate-600">We couldn’t read this payslip. {(result.extraction_errors ?? [])[0] ?? 'Please try a different file.'}</p>
        : <div className="mt-5 divide-y divide-slate-100">
          <SummaryRow label="Employer" value={result.employer_name ?? '—'} />
          <SummaryRow label="Pay period" value={formatPeriod(result.period_start, result.period_end)} />
          <SummaryRow label="Pay date" value={formatDate(result.pay_date)} />
          <SummaryRow label="Gross pay" value={formatMoney(result.gross_pay)} />
          <SummaryRow label="Tax withheld" value={formatMoney(result.tax_deducted)} />
          <SummaryRow label="Superannuation" value={formatMoney(result.superannuation)} />
          <SummaryRow label="Deductions" value={formatMoney(result.deductions)} />
          <SummaryRow label="Net pay" value={formatMoney(result.net_pay)} />
        </div>}
      {!!result.extraction_warnings?.length && <div className="mt-5 rounded-xl bg-amber-50 p-4 text-sm text-amber-800"><p className="font-bold">Needs review</p><ul className="mt-1 list-disc space-y-1 pl-5 text-xs leading-5">{result.extraction_warnings.map(w => <li key={w}>{w}</li>)}</ul></div>}
      {!!result.extraction_errors?.length && <div className="mt-3 rounded-xl bg-red-50 p-4 text-sm text-red-800"><p className="font-bold">Issues found</p><ul className="mt-1 list-disc space-y-1 pl-5 text-xs leading-5">{result.extraction_errors.map(e => <li key={e}>{e}</li>)}</ul></div>}
      {/* Always offer a way forward, even when extraction failed outright - the
          verification workflow handles missing/invalid data safely on its own
          (it reports NEEDS_REVIEW with a specific reason rather than guessing),
          so there is no reason to strand the user here with no next step. */}
      <NavLink to={`/result?payslipId=${result.id}`} className="btn-primary mt-6 w-full"><ChevronRight size={17} />{result.status === 'FAILED' ? 'Continue anyway' : 'Continue to verification'}</NavLink>
    </div>}
  </div>
}

// ---------------------------------------------------------------------------
// Verification Result
// ---------------------------------------------------------------------------

function Result() {
  const [params] = useSearchParams()
  const payslipId = params.get('payslipId')
  // Remount ResultView whenever the target payslip changes, so its initial
  // state is always correct for the new id without needing a synchronous
  // setState inside an effect to "reset" stale state from the previous one.
  return <ResultView key={payslipId ?? 'none'} payslipId={payslipId} />
}

function ResultView({ payslipId }: { payslipId: string | null }) {
  // 'loading' = checking whether this payslip was already verified; 'running' =
  // actively calling POST /verification/run (checks the timesheet and payroll
  // rules, runs the calculator, compares, classifies, and generates the
  // explanation - all inside one synchronous backend call, so this is shown as
  // one honest combined status rather than invented fake sub-steps).
  type ResultState = { phase: 'empty' | 'loading' | 'running' | 'ready' | 'error', result?: VerificationResult, error?: string }
  const [state, setState] = useState<ResultState>({ phase: payslipId ? 'loading' : 'empty' })
  // Prevents a duplicate verification run from React StrictMode's dev-only
  // double-invoke of effects (harmless either way - the backend upserts by
  // payslip id - but there's no reason to pay for two runs instead of one).
  const autoRunStarted = useRef(false)

  const triggerVerification = useCallback(async () => {
    if (!payslipId) return
    setState({ phase: 'running' })
    try { setState({ phase: 'ready', result: await runVerification(payslipId) }) }
    catch (e) { setState({ phase: 'error', error: errorMessage(e, 'Verification could not be completed.') }) }
  }, [payslipId])

  useEffect(() => {
    if (!payslipId) return
    let cancelled = false
    getVerification(payslipId).then(r => {
      if (cancelled) return
      if (r) { setState({ phase: 'ready', result: r }); return }
      // No saved result yet for this payslip - run verification now rather than
      // making the user find and click a second button after they already
      // chose "Continue to verification" on the upload page. The backend's own
      // deterministic routing (never this page) decides MATCH/UNDERPAID/
      // OVERPAID/NEEDS_REVIEW, so auto-running here cannot fabricate a result -
      // missing or inconsistent data still correctly comes back as NEEDS_REVIEW.
      if (!autoRunStarted.current) { autoRunStarted.current = true; triggerVerification() }
    }).catch(e => { if (!cancelled) setState({ phase: 'error', error: errorMessage(e, 'Could not load this verification.') }) })
    return () => { cancelled = true }
  }, [payslipId, triggerVerification])

  if (state.phase === 'empty') return <div className="card flex flex-col items-center gap-3 p-10 text-center"><FileCheck2 className="text-slate-300" size={32} /><p className="text-sm text-slate-500">Choose a payslip to verify from the <NavLink className="font-semibold text-brand-600" to="/upload">Upload page</NavLink>, or open one from your <NavLink className="font-semibold text-brand-600" to="/">dashboard history</NavLink>.</p></div>
  if (state.phase === 'loading') return <Spinner label="Loading verification…" />
  if (state.phase === 'error') return <ErrorCard message={state.error!} onRetry={triggerVerification} />
  if (state.phase === 'running') return <div className="card flex flex-col items-center gap-4 p-10 text-center">
    <Loader2 className="animate-spin text-brand-600" size={32} />
    <div><p className="font-semibold">Checking your timesheet and payroll rules, and calculating expected pay…</p><p className="mt-1 text-sm text-slate-500">This usually takes a few seconds.</p></div>
  </div>

  const r = state.result!
  const breakdown = r.calculation_breakdown ?? {}
  const breakdownRows: [string, string][] = [
    ['Ordinary hours', String(breakdown.ordinary_hours ?? '—')], ['Overtime hours', String(breakdown.overtime_hours ?? '—')],
    ['Weekend hours', String(breakdown.weekend_hours ?? '—')], ['Public holiday hours', String(breakdown.public_holiday_hours ?? '—')],
    ['Hourly rate', breakdown.hourly_rate ? formatMoney(String(breakdown.hourly_rate)) : '—'],
  ]
  const toneByStatus = { MATCH: 'border-emerald-100 bg-emerald-50 text-emerald-600', UNDERPAID: 'border-red-100 bg-red-50 text-red-600', OVERPAID: 'border-blue-100 bg-blue-50 text-blue-600', NEEDS_REVIEW: 'border-amber-100 bg-amber-50 text-amber-600' } as const
  const headline = { MATCH: 'Your payslip matches what was expected.', UNDERPAID: 'We found a possible pay discrepancy.', OVERPAID: 'Your payslip shows more than expected.', NEEDS_REVIEW: 'This payslip needs manual review.' }[r.status]

  return <div className="space-y-6">
    <div className={`rounded-2xl border p-5 sm:flex sm:items-center sm:justify-between ${toneByStatus[r.status]}`}>
      <div className="flex items-start gap-4"><span className="rounded-xl bg-white/60 p-2.5"><FileCheck2 /></span><div><VerificationBadge value={r.status} /><h2 className="mt-2 text-lg font-bold text-slate-900">{headline}</h2><p className="mt-1 text-sm text-slate-600">{r.status === 'NEEDS_REVIEW' ? 'A finding here is not proof of a payroll violation - review the details below.' : `Verified ${formatDateTime(r.created_at)}.`}</p></div></div>
    </div>

    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <Stat label="Expected gross pay" value={formatMoney(r.expected_gross_pay)} icon={CircleDollarSign} hint={formatPeriod(r.pay_period_start, r.pay_period_end)} />
      <Stat label="Actual gross pay" value={formatMoney(r.actual_gross_pay)} icon={ReceiptText} hint="Extracted from payslip" />
      <Stat label="Expected net pay" value={formatMoney(r.expected_net_pay)} icon={CircleDollarSign} hint="Gross minus estimated tax" />
      <Stat label="Actual net pay" value={formatMoney(r.actual_net_pay)} icon={ReceiptText} hint="Extracted from payslip" />
    </div>

    <div className="grid gap-6 xl:grid-cols-[1.5fr_1fr]">
      <div className="card p-6">
        <h3 className="font-bold">Calculation breakdown</h3><p className="mb-5 text-sm text-slate-500">From your timesheets and payroll rules for this period</p>
        <div className="overflow-x-auto"><table className="w-full min-w-[420px] text-sm"><tbody>{breakdownRows.map(([l, v]) => <tr className="border-b border-slate-100 last:border-0" key={l}><td className="py-3 font-medium">{l}</td><td className="py-3 text-right">{v}</td></tr>)}</tbody></table></div>
        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          <div className="rounded-xl bg-slate-50 p-4"><p className="text-xs text-slate-500">Gross pay difference</p><p className={`mt-1 text-lg font-bold ${r.gross_difference && Number(r.gross_difference) < 0 ? 'text-red-600' : 'text-slate-900'}`}>{r.gross_difference == null ? '—' : formatMoney(r.gross_difference)}</p></div>
          <div className="rounded-xl bg-slate-50 p-4"><p className="text-xs text-slate-500">Net pay difference</p><p className={`mt-1 text-lg font-bold ${r.net_difference && Number(r.net_difference) < 0 ? 'text-red-600' : 'text-slate-900'}`}>{r.net_difference == null ? '—' : formatMoney(r.net_difference)}</p></div>
        </div>
        {r.explanation_summary && <div className="mt-6 rounded-xl border border-slate-100 p-4"><p className="flex items-center gap-2 text-sm font-bold"><Sparkles size={15} className="text-brand-600" />AI explanation</p><p className="mt-2 text-sm leading-6 text-slate-600">{r.explanation_summary}</p>{!!r.explanation_evidence?.length && <ul className="mt-3 list-disc space-y-1 pl-5 text-xs leading-5 text-slate-500">{r.explanation_evidence.map(e => <li key={e}>{e}</li>)}</ul>}{!!r.explanation_next_steps?.length && <div className="mt-3 text-xs text-slate-500"><p className="font-semibold text-slate-600">What to check next</p><ul className="mt-1 list-disc space-y-1 pl-5">{r.explanation_next_steps.map(s => <li key={s}>{s}</li>)}</ul></div>}</div>}
      </div>

      <div className="card p-6">
        <h3 className="font-bold">Payslip summary</h3>
        <div className="mt-5 space-y-4 text-sm">
          <div className="flex justify-between text-slate-600"><span>Tax withheld</span><span className="font-semibold text-slate-900">{formatMoney(r.estimated_tax)}</span></div>
          <div className="flex justify-between text-slate-600"><span>Deductions</span><span className="font-semibold text-slate-900">{formatMoney(r.deductions)}</span></div>
          <div className="flex justify-between border-t pt-4 text-base font-bold"><span>Tolerance applied</span><span>{r.tolerance == null ? '—' : formatMoney(r.tolerance)}</span></div>
        </div>
        {(!!r.warnings?.length || !!r.errors?.length) && <div className="mt-6 rounded-xl bg-amber-50 p-4 text-sm text-amber-800"><p className="font-bold">Warnings</p><ul className="mt-1 list-disc space-y-1 pl-5 text-xs leading-5">{[...(r.errors ?? []), ...(r.warnings ?? [])].map(w => <li key={w}>{w}</li>)}</ul></div>}
        {!!r.explanation_uncertainties?.length && <div className="mt-3 rounded-xl bg-slate-50 p-4 text-sm text-slate-600"><p className="font-bold text-slate-700">Uncertainties</p><ul className="mt-1 list-disc space-y-1 pl-5 text-xs leading-5">{r.explanation_uncertainties.map(u => <li key={u}>{u}</li>)}</ul></div>}
        <p className="mt-5 text-xs text-slate-400">Verification ID {r.id.slice(0, 8)} · {formatDateTime(r.created_at)}</p>
      </div>
    </div>
  </div>
}

export default function App() { return <Layout><Routes><Route path="/" element={<Dashboard />} /><Route path="/timesheets" element={<Timesheets />} /><Route path="/rules" element={<Rules />} /><Route path="/upload" element={<Upload />} /><Route path="/result" element={<Result />} /></Routes></Layout> }
