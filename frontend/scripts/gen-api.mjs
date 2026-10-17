#!/usr/bin/env node
/**
 * Generates `src/api/generated/` from the backend's published contract.
 *
 * Nothing in that directory is hand-edited: `npm run gen:api` rewrites it and
 * `npm run check:api` fails when the committed output has drifted.
 *
 * Two outputs, because they solve different problems:
 *
 *  * `schema.d.ts` — the whole contract as types, courtesy of `openapi-typescript`.
 *  * `enums.ts`    — the fixed vocabularies as RUNTIME arrays. The generator can
 *    emit `enum` declarations, but it writes a `.d.ts`, which has no runtime
 *    presence, so a dropdown could not read the values from it. Rather than retype
 *    them, this script reads the same `enum` arrays the contract publishes.
 *
 * Usage: node scripts/gen-api.mjs [--out-dir <dir>]
 */
import { execFileSync } from 'node:child_process'
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const frontendRoot = resolve(here, '..')
const repoRoot = resolve(frontendRoot, '..')
const openapiPath = process.env.VALORA_OPENAPI ?? join(repoRoot, 'docs', 'openapi.json')

const outDirFlag = process.argv.indexOf('--out-dir')
const outDir =
  outDirFlag === -1
    ? join(frontendRoot, 'src', 'api', 'generated')
    : resolve(frontendRoot, process.argv[outDirFlag + 1])

/** Where each runtime vocabulary lives in the contract. Values are never typed here. */
const VOCABULARIES = [
  { exportName: 'complaintCategories', typeName: 'ComplaintCategory', schema: 'ComplaintCreate', field: 'category' },
  { exportName: 'complaintPriorities', typeName: 'ComplaintPriority', schema: 'ComplaintCreate', field: 'priority' },
  { exportName: 'triageCategories', typeName: 'TriageCategory', schema: 'TriageDecisionRequest', field: 'category' },
  { exportName: 'triagePriorities', typeName: 'TriagePriority', schema: 'TriageDecisionRequest', field: 'priority' },
  { exportName: 'triageTrades', typeName: 'TriageTrade', schema: 'TriageDecisionRequest', field: 'trade' },
  { exportName: 'triageDecisions', typeName: 'TriageDecision', schema: 'TriageDecisionRequest', field: 'decision' },
]

/** A value a dropdown can show and the API accepts: plain `snake_case`, nothing exotic. */
const VALUE_PATTERN = /^[a-z][a-z0-9_]*$/

function enumValues(document, { schema, field }) {
  const node = document?.components?.schemas?.[schema]?.properties?.[field]
  if (!node) {
    throw new Error(`${schema}.${field} is missing from ${openapiPath} — was the contract regenerated?`)
  }
  // A nullable field publishes its values inside `anyOf: [{ enum: [...] }, { type: 'null' }]`.
  const values = node.enum ?? node.anyOf?.find((branch) => branch.enum)?.enum
  if (!Array.isArray(values) || values.length === 0) {
    throw new Error(`${schema}.${field} publishes no enum values in ${openapiPath}.`)
  }
  for (const value of values) {
    if (typeof value !== 'string' || !VALUE_PATTERN.test(value)) {
      throw new Error(`${schema}.${field} publishes an unusable value: ${JSON.stringify(value)}`)
    }
  }
  if (new Set(values).size !== values.length) {
    throw new Error(`${schema}.${field} publishes duplicate values.`)
  }
  return values
}

function renderEnums(document) {
  const lines = [
    '/**',
    ' * GENERATED FILE — DO NOT EDIT.',
    ' *',
    ' * Source: docs/openapi.json (the backend is the single source of truth).',
    ' * Regenerate: npm run gen:api   ·   Verify: npm run check:api',
    ' */',
    '',
  ]
  for (const vocabulary of VOCABULARIES) {
    const values = enumValues(document, vocabulary)
    const literal = `[${values.map((value) => `'${value}'`).join(', ')}] as const`
    lines.push(`export const ${vocabulary.exportName} = ${literal}`)
    lines.push(`export type ${vocabulary.typeName} = (typeof ${vocabulary.exportName})[number]`)
    lines.push('')
  }
  return `${lines.join('\n').trimEnd()}\n`
}

function generateTypes(target) {
  const packageJsonPath = join(frontendRoot, 'node_modules', 'openapi-typescript', 'package.json')
  if (!existsSync(packageJsonPath)) {
    throw new Error('openapi-typescript is not installed. Run `npm install` first.')
  }
  const packageJson = JSON.parse(readFileSync(packageJsonPath, 'utf8'))
  const bin = typeof packageJson.bin === 'string' ? packageJson.bin : packageJson.bin?.['openapi-typescript']
  if (!bin) throw new Error('openapi-typescript exposes no CLI entry point.')

  execFileSync(
    process.execPath,
    [join(dirname(packageJsonPath), bin), openapiPath, '--output', target],
    { stdio: 'inherit' },
  )
}

const document = JSON.parse(readFileSync(openapiPath, 'utf8'))
mkdirSync(outDir, { recursive: true })

generateTypes(join(outDir, 'schema.d.ts'))
writeFileSync(join(outDir, 'enums.ts'), renderEnums(document), 'utf8')

process.stdout.write(`Generated ${outDir} from ${openapiPath}\n`)
