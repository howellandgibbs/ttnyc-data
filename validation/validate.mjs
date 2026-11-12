// validate.mjs
//
// Checks building-profile.js against the 23 validation buildings.
//
// For each building it does what the site does: finds the address with
// GeoSearch, then calls getBuildingProfile(). It compares the result with the
// expected counts in validation-buildings.json and prints one line per
// building. It exits with an error if any building fails, so it can run in
// automation later.
//
// Run it from the repository folder (needs Node 18 or later):
//   node validation/validate.mjs
//
// Counts change every day, so a failure can mean the data moved rather than
// that the code is wrong. If many buildings drift, refresh the expected counts
// with pull-baseline.mjs and compare again.

import { readFileSync } from 'node:fs';
import { getBuildingProfile, configure } from '../building-profile.js';

const baseline = JSON.parse(readFileSync(new URL('./validation-buildings.json', import.meta.url), 'utf8'));
const GEOSEARCH = 'https://geosearch.planninglabs.nyc/v2/search';

if (process.env.SOCRATA_APP_TOKEN) configure({ appToken: process.env.SOCRATA_APP_TOKEN });

/** Same matching as the site: the best GeoSearch match for the address. */
async function geocode(address) {
  const response = await fetch(`${GEOSEARCH}?size=1&text=${encodeURIComponent(address)}`);
  if (!response.ok) throw new Error(`GeoSearch answered ${response.status}`);
  const feature = (await response.json()).features?.[0];
  const props = feature?.properties ?? {};
  const pad = props.addendum?.pad ?? {};
  return { bbl: pad.bbl ?? null, bin: pad.bin || null, label: props.label, postalCode: props.postalcode ?? null };
}

/** The brief's tolerance: zero exactly, otherwise within 10% or 5, whichever is larger. */
function withinTolerance(actual, expected) {
  if (typeof actual !== 'number') return false;
  if (expected === 0) return actual === 0;
  return Math.abs(actual - expected) <= Math.max(5, expected * 0.1);
}

/** Pull the numbers the baseline records out of a building profile. */
function actualCounts(profile) {
  const d = profile.datasets;
  return {
    hpdOpenA: d.hpdViolations?.openByClass?.A ?? (d.hpdViolations?.error ? undefined : 0),
    hpdOpenB: d.hpdViolations?.openByClass?.B ?? (d.hpdViolations?.error ? undefined : 0),
    hpdOpenC: d.hpdViolations?.openByClass?.C ?? (d.hpdViolations?.error ? undefined : 0),
    complaintsLast12Months: d.hpdComplaints?.complaintsLast12Months,
    litigationCases: d.hpdLitigation?.totalCases,
    harassmentFindings: d.hpdLitigation?.harassmentFindings,
    residentialEvictions: d.evictions?.residentialTotal,
    ecbActive: d.ecbViolations?.activeSummonses,
  };
}

let failures = 0;
console.log(`Expected counts pulled on ${baseline.pulledOn}. Checking ${baseline.buildings.length} buildings.\n`);

for (const expected of baseline.buildings) {
  const problems = [];
  const started = performance.now();

  let building;
  try {
    building = await geocode(expected.address);
  } catch (err) {
    problems.push(`address search failed: ${err.message}`);
  }

  if (building) {
    if (building.bbl !== expected.bbl) problems.push(`BBL ${building.bbl}, expected ${expected.bbl}`);
    if (building.bin !== expected.bin) problems.push(`BIN ${building.bin}, expected ${expected.bin}`);

    // An error usually means NYC Open Data was busy (503) or slow, not that the
    // code is wrong, so a building with errors is looked up once more.
    let profile = await getBuildingProfile(building);
    if (Object.values(profile.datasets).some((dataset) => dataset.error)) {
      await new Promise((resolve) => setTimeout(resolve, 10000));
      profile = await getBuildingProfile(building);
    }
    for (const [name, dataset] of Object.entries(profile.datasets)) {
      if (dataset.error) problems.push(`${name} error: ${dataset.error}`);
    }
    const actual = actualCounts(profile);
    for (const [field, want] of Object.entries(expected.expected)) {
      if (!withinTolerance(actual[field], want)) problems.push(`${field} ${actual[field]}, expected ${want}`);
    }
  }

  const seconds = ((performance.now() - started) / 1000).toFixed(1).padStart(5);
  const status = problems.length ? 'FAIL' : 'pass';
  console.log(`${status} ${seconds}s  ${expected.address}${problems.length ? '\n       ' + problems.join('\n       ') : ''}`);
  if (problems.length) failures += 1;
}

console.log(`\n${baseline.buildings.length - failures} passed, ${failures} failed.`);
process.exitCode = failures ? 1 : 0;
