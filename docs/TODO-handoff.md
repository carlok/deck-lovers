# Security remediation handoff (Dependabot / OSV)

Context: PR `cursor/dependabot-security-fixes-74a6` bumps transitive npm and Python dependencies flagged by Dependabot/OSV. The integration token cannot read `repos/.../dependabot/alerts`; use the verification commands below instead.

## Verification checklist

Run from repository root (`deck-lovers/`).

### 1. OSV scan (expected: no rows)

```bash
osv-scanner -r .
```

**Expected:** banner ends with `No issues found` (or zero vulnerabilities in the summary table).

### 2. npm audit (expected: may still warn on deepmerge version string)

```bash
cd converter && npm ci && npm audit
cd ../server && npm ci && npm audit
```

**Expected:** Jest tests install cleanly. `npm audit` may still list `deepmerge@4.3.1` because the advisory range has no npm release; the lockfile pulls a **patched git commit** via `package.json` `overrides`. OSV is the source of truth for “code fixed.”

### 3. Python tests + coverage floors

```bash
python3 -m pip install --upgrade pip
pip install -r converter/requirements-test.txt
cd converter && pytest tests/ -q --cov=md2html --cov=palette --cov=emoji_img --cov-fail-under=88

pip install -r server/requirements-test.txt
cd ../server && pytest tests/ -q --cov=server --cov-fail-under=89
```

**Expected:** converter ≥88% total coverage, server ≥89%, all tests passed.

### 4. Shell helper tests

```bash
./tests/deploy_test.sh
```

**Expected:** `passed=35 failed=0`.

### 5. Jest (converter + server)

```bash
cd converter && npm test -- --ci
cd ../server && npm test -- --ci
```

**Expected:** 100% coverage on `*.pure.js`, all suites green.

### 6. CI parity

GitHub Actions workflow `.github/workflows/ci.yml` runs the same Python, shell, and Jest matrix. **Expected:** all jobs green on the PR branch.

### 7. Python transitive floors (spot check)

```bash
pip install -r server/requirements.txt -r server/requirements-test.txt -r converter/requirements-test.txt
python3 -c "import h11, certifi, idna; print(h11.__version__, certifi.__version__, idna.__version__)"
```

**Expected:** `h11>=0.16.0`, `certifi>=2026.10.18`, `idna>=3.15`.

## Prioritized TODO (if something fails)

| Priority | Task | Acceptance criteria |
|----------|------|---------------------|
| P0 | Restore green CI on the security PR | All `ci.yml` jobs pass |
| P1 | Keep `osv-scanner -r .` clean | Zero known vulns in repo manifests/lockfiles |
| P2 | Replace deepmerge git override when TehShrike ships ≥4.3.2 on npm | Remove git URL from `overrides`; use registry version; `osv-scanner` still clean |
| P3 | Re-check Dependabot UI after merge | Open alerts closed at https://github.com/carlok/deck-lovers/security/dependabot |

## Starter prompt for a follow-up agent

```
You are continuing security work on carlok/deck-lovers after the dependabot bulk-fix PR.

1. Checkout main (or the open security PR branch) and run every command in docs/TODO-handoff.md.
2. If osv-scanner or CI reports a new advisory, fix with minimal version bumps (prefer patch/minor) in requirements*.txt or npm overrides, then regenerate lockfiles.
3. When npm publishes deepmerge >4.3.1, drop the git override in converter/package.json and server/package.json and npm install in both dirs.
4. Open a single focused PR with test output in the description; do not claim fixes without osv-scanner + CI evidence.
```