/**
 * Property 8: Focus-Visible Ring Consistency
 *
 * For any interactive element receiving keyboard focus (:focus-visible),
 * a 2px solid outline in Google Blue (#4285F4) offset by 2px must be displayed.
 *
 * Validates: Requirements 4.6
 */

import { readFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const CSS_FILE = resolve(__dirname, '../../src/index.css');

function runTests() {
  const css = readFileSync(CSS_FILE, 'utf8');
  const failures = [];

  // ── Property 8: Focus-Visible Ring Consistency ──────────────────────────────
  //
  // The global :focus-visible rule must exist and contain:
  //   outline: 2px solid var(--accent-blue)
  //   outline-offset: 2px

  // Extract the global :focus-visible block (not .btn:focus-visible)
  // Match a :focus-visible rule that is NOT preceded by a selector character
  const focusVisibleMatch = css.match(/(?<![.#\w]):focus-visible\s*\{([^}]*)\}/);

  if (!focusVisibleMatch) {
    failures.push('FAIL: Global :focus-visible rule not found in index.css');
  } else {
    const block = focusVisibleMatch[1];

    // Check outline value
    if (!/outline\s*:\s*2px\s+solid\s+var\(--accent-blue\)/.test(block)) {
      failures.push(
        `FAIL: :focus-visible outline is not "2px solid var(--accent-blue)". Found block: ${block.trim()}`
      );
    } else {
      console.log('  PASS: outline: 2px solid var(--accent-blue) ✓');
    }

    // Check outline-offset value
    if (!/outline-offset\s*:\s*2px/.test(block)) {
      failures.push(
        `FAIL: :focus-visible outline-offset is not "2px". Found block: ${block.trim()}`
      );
    } else {
      console.log('  PASS: outline-offset: 2px ✓');
    }
  }

  // Also verify .btn:focus-visible has the same values (belt-and-suspenders)
  const btnFocusVisibleMatch = css.match(/\.btn:focus-visible\s*\{([^}]*)\}/);
  if (btnFocusVisibleMatch) {
    const btnBlock = btnFocusVisibleMatch[1];
    if (
      /outline\s*:\s*2px\s+solid\s+var\(--accent-blue\)/.test(btnBlock) &&
      /outline-offset\s*:\s*2px/.test(btnBlock)
    ) {
      console.log('  PASS: .btn:focus-visible also has correct outline values ✓');
    }
  }

  return failures;
}

console.log('\nProperty 8: Focus-Visible Ring Consistency');
console.log('===========================================');

const failures = runTests();

if (failures.length === 0) {
  console.log('\nResult: PASS — :focus-visible rule exists with correct values\n');
  process.exit(0);
} else {
  console.error('\nResult: FAIL');
  failures.forEach(f => console.error(' ', f));
  console.error();
  process.exit(1);
}
