import assert from 'node:assert/strict'
import { readdirSync, readFileSync } from 'node:fs'
import { resolve, relative } from 'node:path'
import test from 'node:test'

const root = resolve(import.meta.dirname, '..')
function sourceFiles(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    if (['node_modules', 'dist', 'test-results', 'playwright-report', '.local'].includes(entry.name)) return []
    const path = resolve(directory, entry.name)
    return entry.isDirectory() ? sourceFiles(path) : [path]
  })
}

test('frontend source, tests and tool configurations use JavaScript', () => {
  const files = sourceFiles(root)
  assert.deepEqual(files.filter((file) => /\.(?:ts|tsx|tsbuildinfo)$/.test(file)).map((file) => relative(root, file)), [])
  const pkg = JSON.parse(readFileSync(resolve(root, 'package.json'), 'utf8'))
  for (const name of ['typescript', 'openapi-typescript', '@types/react', '@types/react-dom']) {
    assert.equal(pkg.devDependencies[name], undefined, `${name} must not be required`)
  }
  assert.equal(pkg.scripts.build, 'vite build')
  assert.equal(pkg.scripts.typecheck, undefined)
  assert.match(readFileSync(resolve(root, 'index.html'), 'utf8'), /src\/main\.jsx/)
  for (const file of files.filter((file) => /\.(?:js|jsx|mjs|json|html)$/.test(file) && !file.endsWith('javascript-migration.test.mjs'))) {
    if (file.endsWith('package-lock.json')) continue
    assert.doesNotMatch(readFileSync(file, 'utf8'), /(?:from\s*['"][^'"\n]*|src=['"][^'"\n]*)\.tsx?(?:['"?])/, relative(root, file))
  }
})
