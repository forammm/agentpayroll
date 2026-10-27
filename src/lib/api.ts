// Central API client for the whole app. Every backend call goes through
// `request`/`jsonRequest` below - no component should hardcode a fetch URL.
//
// There is no authentication yet (documented as a production-readiness gap in
// backend/README.md), so every call uses a fixed demo user id matching the
// "Alex Parker" placeholder shown in the sidebar - see
// backend/scripts/seed_demo_user.py. `authHeaders()` below is the one place
// an auth token would be attached once real auth exists.

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'
export const DEMO_USER_ID = import.meta.env.VITE_DEMO_USER_ID ?? 'a1e5f0c2-3b7d-4a6e-9c1f-7d2b3a4c5e6f'

const DEFAULT_TIMEOUT_MS = 15_000
const UPLOAD_TIMEOUT_MS = 45_000 // extraction (and OCR, when available) can take longer than a plain JSON call

export class ApiError extends Error {
  constructor(message: string, public status?: number) {
    super(message)
  }
}

function authHeaders(): Record<string, string> {
  try {
    const token = localStorage.getItem('payguide_auth_token')
    return token ? { Authorization: `Bearer ${token}` } : {}
  } catch {
    return {} // localStorage can throw in some private-browsing contexts
  }
}

async function parseErrorDetail(response: Response): Promise<string> {
  try {
    const body = await response.json()
    if (typeof body?.detail === 'string') return body.detail
    if (Array.isArray(body?.detail)) {
      // FastAPI/Pydantic validation error shape: [{loc, msg, type}, ...]
      return body.detail.map((item: { loc?: unknown[]; msg?: string }) => item.msg ?? JSON.stringify(item)).join(' ')
    }
  } catch {
    // body wasn't JSON - fall through to the generic message
  }
  return `Request failed (${response.status}).`
}

async function request<T>(path: string, init: RequestInit = {}, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<T> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)

  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      signal: controller.signal,
      headers: { ...authHeaders(), ...(init.headers ?? {}) },
    })
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new ApiError('The request timed out. Check that the backend is running and try again.')
    }
    throw new ApiError('Could not reach the server. Check that the backend is running and try again.')
  } finally {
    clearTimeout(timer)
  }

  if (!response.ok) throw new ApiError(await parseErrorDetail(response), response.status)
  if (response.status === 204) return undefined as T
  return response.json()
}

function jsonRequest<T>(path: string, init: RequestInit = {}, timeoutMs?: number): Promise<T> {
  return request<T>(path, { ...init, headers: { 'Content-Type': 'application/json', ...(init.headers ?? {}) } }, timeoutMs)
}

const qs = (params: Record<string, string | undefined>) =>
  '?' + new URLSearchParams(Object.entries(params).filter((e): e is [string, string] => e[1] !== undefined)).toString()

// ---------------------------------------------------------------------------
// Formatting - shared so money/dates render identically across every page.
// ---------------------------------------------------------------------------

export const formatMoney = (value: string | number | null | undefined): string =>
  value == null ? '—' : new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD' }).format(Number(value))

export const formatDate = (value: string | null | undefined): string =>
  value == null ? '—' : new Date(`${value}T00:00:00`).toLocaleDateString('en-AU', { day: 'numeric', month: 'short', year: 'numeric' })

export const formatDateTime = (value: string | null | undefined): string =>
  value == null ? '—' : new Date(value).toLocaleString('en-AU', { dateStyle: 'medium', timeStyle: 'short' })

export const formatPeriod = (start: string | null | undefined, end: string | null | undefined): string =>
  start && end ? `${formatDate(start)} – ${formatDate(end)}` : '—'

// ---------------------------------------------------------------------------
// Timesheets
// ---------------------------------------------------------------------------

export interface Timesheet {
  id: string
  user_id: string
  work_date: string
  start_time: string
  end_time: string
  break_minutes: number
  shift_type: string
  hours_worked: string
  created_at: string
}

export interface TimesheetInput {
  user_id: string
  work_date: string
  start_time: string
  end_time: string
  break_minutes: number
  shift_type: string
}

export const listTimesheets = (userId: string = DEMO_USER_ID) => jsonRequest<Timesheet[]>(`/timesheets${qs({ user_id: userId })}`)
export const createTimesheet = (input: TimesheetInput) => jsonRequest<Timesheet>('/timesheets', { method: 'POST', body: JSON.stringify(input) })
export const updateTimesheet = (id: string, input: TimesheetInput) => jsonRequest<Timesheet>(`/timesheets/${id}`, { method: 'PUT', body: JSON.stringify(input) })
export const deleteTimesheet = (id: string, userId: string = DEMO_USER_ID) => request<void>(`/timesheets/${id}${qs({ user_id: userId })}`, { method: 'DELETE' })

// ---------------------------------------------------------------------------
// Payroll rules
// ---------------------------------------------------------------------------

export interface PayrollRule {
  id: string
  user_id: string
  normal_rate: string
  overtime_rate: string
  saturday_rate: string
  sunday_rate: string
  public_holiday_rate: string
  overnight_rate: string
  early_morning_rate: string
  evening_rate: string
  created_at: string
  updated_at: string
}

export type PayrollRuleInput = Omit<PayrollRule, 'id' | 'created_at' | 'updated_at'>

export async function getPayrollRule(userId: string = DEMO_USER_ID): Promise<PayrollRule | null> {
  try {
    return await jsonRequest<PayrollRule>(`/payroll-rules/${userId}`)
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null
    throw err
  }
}

// The backend keeps payroll rules as a small version history - POST always
// records a new "current" rule set and GET always returns the latest, so
// saving an edit is the same call as creating the first one.
export const savePayrollRule = (input: PayrollRuleInput) => jsonRequest<PayrollRule>('/payroll-rules', { method: 'POST', body: JSON.stringify(input) })

// ---------------------------------------------------------------------------
// Payslips
// ---------------------------------------------------------------------------

export type PayslipStatus = 'UPLOADED' | 'PROCESSING' | 'EXTRACTED' | 'NEEDS_REVIEW' | 'FAILED'

export interface ExtractedEarningLine {
  label: string
  amount: string
}

export interface PayslipResult {
  id: string
  user_id: string
  file_name: string
  status: PayslipStatus
  used_ocr: boolean
  created_at: string
  employer_name: string | null
  period_start: string | null
  period_end: string | null
  pay_date: string | null
  gross_pay: string | null
  net_pay: string | null
  tax_deducted: string | null
  superannuation: string | null
  deductions: string | null
  ordinary_hours: string | null
  overtime_hours: string | null
  weekend_or_holiday_hours: string | null
  hourly_rate: string | null
  earnings_breakdown: ExtractedEarningLine[] | null
  extraction_warnings: string[] | null
  extraction_errors: string[] | null
}

export function uploadPayslip(file: File, userId: string = DEMO_USER_ID): Promise<PayslipResult> {
  const formData = new FormData()
  formData.append('file', file)
  return request<PayslipResult>(`/payslips/upload${qs({ user_id: userId })}`, { method: 'POST', body: formData }, UPLOAD_TIMEOUT_MS)
}

export const getPayslip = (payslipId: string) => jsonRequest<PayslipResult>(`/payslips/${payslipId}`)

// ---------------------------------------------------------------------------
// Verification
// ---------------------------------------------------------------------------

export type VerificationStatus = 'MATCH' | 'UNDERPAID' | 'OVERPAID' | 'NEEDS_REVIEW'

export interface VerificationResult {
  id: string
  payslip_id: string
  user_id: string
  status: VerificationStatus
  created_at: string
  pay_period_start: string | null
  pay_period_end: string | null
  expected_gross_pay: string | null
  actual_gross_pay: string | null
  expected_net_pay: string | null
  actual_net_pay: string | null
  gross_difference: string | null
  net_difference: string | null
  tolerance: string | null
  estimated_tax: string | null
  estimated_super: string | null
  deductions: string | null
  calculation_breakdown: Record<string, unknown> | null
  explanation_summary: string | null
  explanation_evidence: string[] | null
  explanation_uncertainties: string[] | null
  explanation_next_steps: string[] | null
  warnings: string[] | null
  errors: string[] | null
}

export const runVerification = (payslipId: string, userId: string = DEMO_USER_ID) =>
  jsonRequest<VerificationResult>('/verification/run', { method: 'POST', body: JSON.stringify({ user_id: userId, payslip_id: payslipId }) }, UPLOAD_TIMEOUT_MS)

export async function getVerification(payslipId: string, userId: string = DEMO_USER_ID): Promise<VerificationResult | null> {
  try {
    return await jsonRequest<VerificationResult>(`/verification/${payslipId}${qs({ user_id: userId })}`)
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null
    throw err
  }
}

export const listVerificationHistory = (userId: string = DEMO_USER_ID) => jsonRequest<VerificationResult[]>(`/verification${qs({ user_id: userId })}`)

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

export interface DashboardSummary {
  user_id: string
  latest_verification: VerificationResult | null
  hours_logged_current_period: string | null
  history: VerificationResult[]
}

export const getDashboard = (userId: string = DEMO_USER_ID) => jsonRequest<DashboardSummary>(`/dashboard/${userId}`)
