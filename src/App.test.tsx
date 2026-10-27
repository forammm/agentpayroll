import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { ApiError } from './lib/api'

vi.mock('./lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./lib/api')>()
  return {
    ...actual,
    uploadPayslip: vi.fn(),
    getDashboard: vi.fn(),
    listTimesheets: vi.fn(),
    createTimesheet: vi.fn(),
    updateTimesheet: vi.fn(),
    deleteTimesheet: vi.fn(),
    getPayrollRule: vi.fn(),
    savePayrollRule: vi.fn(),
    getVerification: vi.fn(),
    runVerification: vi.fn(),
  }
})

import { createTimesheet, deleteTimesheet, getDashboard, getVerification, listTimesheets, runVerification, uploadPayslip } from './lib/api'

function renderAt(path: string) {
  return render(<MemoryRouter initialEntries={[path]}><App /></MemoryRouter>)
}

describe('Upload page', () => {
  beforeEach(() => vi.clearAllMocks())

  it('rejects a non-PDF file before ever calling the API', async () => {
    // A renamed file or a drag-and-drop can still hand the input a non-PDF file
    // despite its accept="application/pdf" hint (that attribute only filters
    // the native OS picker dialog) - use fireEvent here because userEvent.upload
    // deliberately emulates that OS-picker filtering and would refuse to select
    // a non-matching file at all, never exercising this validation path.
    renderAt('/upload')
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const textFile = new File(['not a pdf'], 'notes.txt', { type: 'text/plain' })

    fireEvent.change(input, { target: { files: [textFile] } })

    expect(await screen.findByText('Please choose a PDF file.')).toBeInTheDocument()
    expect(uploadPayslip).not.toHaveBeenCalled()
  })

  it('uploads a valid PDF and displays the extraction summary', async () => {
    vi.mocked(uploadPayslip).mockResolvedValue({
      id: 'payslip-1', user_id: 'u1', file_name: 'payslip.pdf', status: 'EXTRACTED', used_ocr: false,
      created_at: '2026-06-01T00:00:00Z', employer_name: 'Acme Pty Ltd', period_start: '2026-06-01', period_end: '2026-06-14',
      pay_date: null, gross_pay: '1842.50', net_pay: '1452.00', tax_deducted: '348.00', superannuation: null, deductions: '42.50',
      ordinary_hours: null, overtime_hours: null, weekend_or_holiday_hours: null, hourly_rate: null, earnings_breakdown: null,
      extraction_warnings: null, extraction_errors: null,
    })
    renderAt('/upload')
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const pdfFile = new File(['%PDF-1.7 fake'], 'payslip.pdf', { type: 'application/pdf' })
    await userEvent.upload(input, pdfFile)

    await userEvent.click(screen.getByRole('button', { name: /verify payslip/i }))

    expect(await screen.findByText('Acme Pty Ltd')).toBeInTheDocument()
    expect(screen.getByText('Extraction summary')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /continue to verification/i })).toHaveAttribute('href', '/result?payslipId=payslip-1')
  })

  it('shows a retry option when the upload fails', async () => {
    vi.mocked(uploadPayslip).mockRejectedValue(new ApiError('The uploaded file is not a valid PDF.', 400))
    renderAt('/upload')
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    await userEvent.upload(input, new File(['%PDF-1.7'], 'payslip.pdf', { type: 'application/pdf' }))

    await userEvent.click(screen.getByRole('button', { name: /verify payslip/i }))

    expect(await screen.findByText('The uploaded file is not a valid PDF.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /retry upload/i })).toBeInTheDocument()
  })

  // Regression test: a payslip that fails extraction entirely (e.g. a scanned
  // PDF with no OCR available) used to hide the only way to move forward,
  // leaving the user stuck with no next step. The verification workflow
  // handles this safely on its own (NEEDS_REVIEW with a specific reason), so
  // there is no reason to block navigation here.
  it('still offers a way forward when extraction fails outright, instead of a dead end', async () => {
    vi.mocked(uploadPayslip).mockResolvedValue({
      id: 'payslip-failed', user_id: 'u1', file_name: 'scanned.pdf', status: 'FAILED', used_ocr: false,
      created_at: '2026-06-01T00:00:00Z', employer_name: null, period_start: null, period_end: null,
      pay_date: null, gross_pay: null, net_pay: null, tax_deducted: null, superannuation: null, deductions: null,
      ordinary_hours: null, overtime_hours: null, weekend_or_holiday_hours: null, hourly_rate: null, earnings_breakdown: null,
      extraction_warnings: ['This appears to be a scanned or image-based PDF and OCR is not available in this environment.'],
      extraction_errors: ['No readable text could be extracted from this PDF.'],
    })
    renderAt('/upload')
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    await userEvent.upload(input, new File(['%PDF-1.7'], 'scanned.pdf', { type: 'application/pdf' }))

    await userEvent.click(screen.getByRole('button', { name: /verify payslip/i }))

    expect(await screen.findByText('No readable text could be extracted from this PDF.')).toBeInTheDocument()
    const link = screen.getByRole('link', { name: /continue anyway/i })
    expect(link).toHaveAttribute('href', '/result?payslipId=payslip-failed')
  })
})

describe('Dashboard', () => {
  beforeEach(() => vi.clearAllMocks())
  afterEach(() => vi.clearAllMocks())

  it('shows an empty state rather than fabricated numbers when there is no verification yet', async () => {
    vi.mocked(getDashboard).mockResolvedValue({ user_id: 'u1', latest_verification: null, hours_logged_current_period: null, history: [] })

    renderAt('/')

    expect(await screen.findByText(/no verifications yet/i)).toBeInTheDocument()
    expect(screen.queryByText('$1,842.50')).not.toBeInTheDocument()
  })

  it('shows an error state with a working retry on API failure', async () => {
    vi.mocked(getDashboard).mockRejectedValueOnce(new ApiError('Could not reach the server.'))
    vi.mocked(getDashboard).mockResolvedValueOnce({ user_id: 'u1', latest_verification: null, hours_logged_current_period: null, history: [] })

    renderAt('/')

    expect(await screen.findByText('Could not reach the server.')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /try again/i }))

    expect(await screen.findByText(/no verifications yet/i)).toBeInTheDocument()
    expect(getDashboard).toHaveBeenCalledTimes(2)
  })

  it('renders real verification data when it is available', async () => {
    vi.mocked(getDashboard).mockResolvedValue({
      user_id: 'u1',
      latest_verification: {
        id: 'v1', payslip_id: 'p1', user_id: 'u1', status: 'UNDERPAID', created_at: '2026-06-15T00:00:00Z',
        pay_period_start: '2026-06-01', pay_period_end: '2026-06-14', expected_gross_pay: '1842.50', actual_gross_pay: '1745.20',
        expected_net_pay: null, actual_net_pay: null, gross_difference: '-97.30', net_difference: null, tolerance: '1.00',
        estimated_tax: '348.00', estimated_super: null, deductions: '42.50', calculation_breakdown: null,
        explanation_summary: 'Your payslip shows less pay than expected.', explanation_evidence: null, explanation_uncertainties: null,
        explanation_next_steps: null, warnings: null, errors: null,
      },
      hours_logged_current_period: '76.50',
      history: [],
    })

    renderAt('/')

    expect(await screen.findByText('$1,842.50')).toBeInTheDocument()
    expect(screen.getByText('$1,745.20')).toBeInTheDocument()
    expect(screen.getByText('Your payslip shows less pay than expected.')).toBeInTheDocument()
  })
})

describe('Timesheets', () => {
  beforeEach(() => vi.clearAllMocks())

  it('lists existing timesheets and supports deleting one', async () => {
    vi.mocked(listTimesheets).mockResolvedValue([
      { id: 't1', user_id: 'u1', work_date: '2026-06-01', start_time: '09:00:00', end_time: '17:00:00', break_minutes: 30, shift_type: 'normal', hours_worked: '7.50', created_at: '2026-06-01T00:00:00Z' },
    ])
    vi.mocked(deleteTimesheet).mockResolvedValue(undefined)

    renderAt('/timesheets')

    expect(await screen.findByText('7.50 hrs')).toBeInTheDocument()

    vi.mocked(listTimesheets).mockResolvedValue([])
    await userEvent.click(screen.getByRole('button', { name: /delete shift/i }))

    await waitFor(() => expect(deleteTimesheet).toHaveBeenCalledWith('t1'))
  })

  it('creates a new timesheet from the form and refreshes the list', async () => {
    vi.mocked(listTimesheets).mockResolvedValue([])
    vi.mocked(createTimesheet).mockResolvedValue({
      id: 't2', user_id: 'u1', work_date: '2026-06-02', start_time: '09:00:00', end_time: '17:00:00', break_minutes: 30, shift_type: 'normal', hours_worked: '7.50', created_at: '2026-06-02T00:00:00Z',
    })

    renderAt('/timesheets')
    await screen.findByText(/no shifts recorded yet/i)

    await userEvent.click(screen.getByRole('button', { name: /add shift/i }))

    await waitFor(() => expect(createTimesheet).toHaveBeenCalled())
  })

  it('shows a validation error instead of submitting when start and end time are equal', async () => {
    vi.mocked(listTimesheets).mockResolvedValue([])
    renderAt('/timesheets')
    await screen.findByText(/no shifts recorded yet/i)

    const [startInput, endInput] = screen.getAllByLabelText(/time/i) as HTMLInputElement[]
    await userEvent.clear(endInput)
    await userEvent.type(endInput, startInput.value)

    await userEvent.click(screen.getByRole('button', { name: /add shift/i }))

    expect(await screen.findByText('Start time and end time must differ.')).toBeInTheDocument()
    expect(createTimesheet).not.toHaveBeenCalled()
  })
})

const sampleVerification = {
  id: 'v1', payslip_id: 'p1', user_id: 'u1', status: 'MATCH' as const, created_at: '2026-10-24T00:00:00Z',
  pay_period_start: '2026-10-19', pay_period_end: '2026-10-19', expected_gross_pay: '243.75', actual_gross_pay: '243.75',
  expected_net_pay: '195.00', actual_net_pay: '195.00', gross_difference: '0.00', net_difference: '0.00', tolerance: '1.00',
  estimated_tax: '48.75', estimated_super: '28.03', deductions: null, calculation_breakdown: null,
  explanation_summary: 'Your payslip matches the pay calculated from your timesheets and payroll rules.',
  explanation_evidence: null, explanation_uncertainties: null, explanation_next_steps: null, warnings: null, errors: null,
}

describe('Verification Result page', () => {
  beforeEach(() => vi.clearAllMocks())

  // Regression test: uploading a payslip and clicking "Continue to verification"
  // used to land on a page that required a *second* manual "Run verification"
  // click before any result appeared, which read as a broken/incomplete
  // workflow. Verification must now run automatically the moment the page
  // finds no saved result yet for the given payslip.
  it('automatically runs verification when a payslip has not been verified yet, with no button click required', async () => {
    vi.mocked(getVerification).mockResolvedValue(null)
    vi.mocked(runVerification).mockResolvedValue(sampleVerification)

    renderAt('/result?payslipId=p1')

    await waitFor(() => expect(runVerification).toHaveBeenCalledWith('p1'))
    expect(await screen.findByText('Match')).toBeInTheDocument()
    expect(screen.getByText(sampleVerification.explanation_summary)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /run verification/i })).not.toBeInTheDocument()
  })

  it('displays an already-saved result directly without re-running verification', async () => {
    vi.mocked(getVerification).mockResolvedValue({ ...sampleVerification, status: 'UNDERPAID' })

    renderAt('/result?payslipId=p1')

    expect(await screen.findByText('Underpaid')).toBeInTheDocument()
    expect(runVerification).not.toHaveBeenCalled()
  })

  it('shows a prompt instead of an error when no payslip has been selected', async () => {
    renderAt('/result')

    expect(await screen.findByText(/choose a payslip to verify/i)).toBeInTheDocument()
    expect(getVerification).not.toHaveBeenCalled()
  })

  it('surfaces a retry option if the automatic verification run fails, and retry tries again', async () => {
    vi.mocked(getVerification).mockResolvedValue(null)
    vi.mocked(runVerification).mockRejectedValueOnce(new ApiError('Verification could not be completed.'))
    vi.mocked(runVerification).mockResolvedValueOnce(sampleVerification)

    renderAt('/result?payslipId=p1')

    expect(await screen.findByText('Verification could not be completed.')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /try again/i }))

    expect(await screen.findByText('Match')).toBeInTheDocument()
    expect(runVerification).toHaveBeenCalledTimes(2)
  })
})
