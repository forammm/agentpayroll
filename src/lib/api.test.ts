import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, listTimesheets, uploadPayslip } from './api'

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

describe('central API client', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('returns parsed JSON on a successful request', async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse([{ id: '1' }]))

    const result = await listTimesheets('user-1')

    expect(result).toEqual([{ id: '1' }])
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/timesheets?user_id=user-1'), expect.any(Object))
  })

  it('throws ApiError with the backend-provided detail message on a non-2xx response', async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse({ detail: 'Timesheet not found.' }, 404))

    await expect(listTimesheets('user-1')).rejects.toMatchObject(
      new ApiError('Timesheet not found.', 404),
    )
  })

  it('joins FastAPI/Pydantic validation error arrays into a readable message', async () => {
    vi.mocked(fetch).mockResolvedValue(
      jsonResponse({ detail: [{ loc: ['body', 'user_id'], msg: 'field required', type: 'missing' }] }, 422),
    )

    await expect(listTimesheets('user-1')).rejects.toThrow('field required')
  })

  it('falls back to a generic message when the error body is not valid JSON', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response('<html>502</html>', { status: 502 }))

    await expect(listTimesheets('user-1')).rejects.toThrow('Request failed (502).')
  })

  it('converts a network failure into a friendly ApiError', async () => {
    vi.mocked(fetch).mockRejectedValue(new TypeError('Failed to fetch'))

    await expect(listTimesheets('user-1')).rejects.toThrow('Could not reach the server')
  })

  it('uploads a payslip as multipart form data without a JSON content-type header', async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse({ id: 'p1', status: 'EXTRACTED' }))
    const file = new File([new Uint8Array([1, 2, 3])], 'payslip.pdf', { type: 'application/pdf' })

    await uploadPayslip(file, 'user-1')

    const [, init] = vi.mocked(fetch).mock.calls[0]
    expect(init?.body).toBeInstanceOf(FormData)
    expect((init?.headers as Record<string, string> | undefined)?.['Content-Type']).toBeUndefined()
  })
})
