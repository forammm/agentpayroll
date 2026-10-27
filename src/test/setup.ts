import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// React Testing Library's automatic afterEach(cleanup) only registers itself
// when Vitest's `globals` option is on. This project keeps `globals` off (test
// files import describe/it/expect explicitly instead), so cleanup must be
// wired up here - without it, DOM nodes and component state from one test
// leak into the next test in the same file.
afterEach(() => {
  cleanup()
})
