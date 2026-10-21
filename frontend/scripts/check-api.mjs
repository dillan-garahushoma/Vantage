#!/usr/bin/env node
/**
 * Fails when `src/api/generated/` no longer matches `docs/openapi.json`.
 *
 * The generated files are regenerated into a scratch directory and compared byte
 * for byte, so a stale API vocabulary cannot be committed quietly.
 *
 * Usage: node scripts/check-api.mjs
 */
import { spawnSync } from 'node:child_process'
import { mkdtempSync, readFileSync, rmSync, existsSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const frontendRoot = resolve(here, '..')
const committedDir = join(frontendRoot, 'src', 'api', 'generated')
const GENERATED_FILES = ['enums.js']

const scratch = mkdtempSync(join(tmpdir(), 'valora-api-check-'))
let failed = false

try {
  const result = spawnSync(
    process.execPath,
    [join(here, 'gen-api.mjs'), '--out-dir', scratch],
    { stdio: 'inherit' },
  )
  if (result.status !== 0) {
    process.stderr.write('check:api — generation failed, so the committed output cannot be verified.\n')
    process.exit(result.status ?? 1)
  }

  for (const file of GENERATED_FILES) {
    const committed = join(committedDir, file)
    if (!existsSync(committed)) {
      process.stderr.write(`check:api — src/api/generated/${file} is missing. Run \`npm run gen:api\`.\n`)
      failed = true
      continue
    }
    const expected = readFileSync(join(scratch, file), 'utf8')
    const actual = readFileSync(committed, 'utf8')
    if (expected !== actual) {
      process.stderr.write(
        `check:api — src/api/generated/${file} is stale: it differs from the file generated from docs/openapi.json.\n` +
          'Run `npm run gen:api` and review the diff.\n',
      )
      failed = true
    }
  }

  if (!failed) process.stdout.write('check:api — the generated API files match docs/openapi.json.\n')
} finally {
  rmSync(scratch, { recursive: true, force: true })
}

process.exit(failed ? 1 : 0)
