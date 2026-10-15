// building-profile.js
//
// This is the file you edit. test.html calls getBuildingProfile() with the
// building the user picked, and prints whatever object you return.
//
// It runs in the browser, the same way Tenant Triage will run it. That is why
// it is JavaScript and not Python: the site has no server, so there is nowhere
// for Python to run.
//
// What you receive (`building`) is the address match from GeoSearch, already
// resolved. Example:
//
//   {
//     bbl: '2026100012',          // always present, 10 digits
//     bin: '2004223',             // can be null, or a placeholder like '2000000'
//     label: '530 EAST 169 STREET, Bronx, NY, USA',
//     displayLabel: '530 East 169 Street, Bronx, NY, USA',
//     borough: 'Bronx',
//     houseNumber: '530',
//     street: 'EAST 169 STREET',
//     postalCode: '10456',        // can be null
//     latitude: 40.8326,
//     longitude: -73.9046
//   }
//
// What you return: one object, one section per dataset. Counts and other
// derived values only. Never return raw rows, apartment numbers, court index
// numbers, or a person's name. See "Privacy rules" in the project brief.
//
// Below is one dataset done end to end (DOI evictions) as a pattern to copy.

const SOCRATA = 'https://data.cityofnewyork.us/resource/';

// Optional. A Socrata app token raises the rate limit. Leave it empty while
// testing; the site will pass its own.
const APP_TOKEN = '';

/**
 * Ask NYC Open Data a question and get the answer back as a list of objects.
 * `params` are SoQL query parameters, e.g. { $where: "bbl='2026100012'" }.
 */
async function socrata(datasetId, params) {
  const url = new URL(SOCRATA + datasetId + '.json');
  for (const [key, value] of Object.entries(params)) url.searchParams.set(key, value);
  const headers = APP_TOKEN ? { 'X-App-Token': APP_TOKEN } : {};
  const response = await fetch(url, { headers });
  if (!response.ok) throw new Error(`${datasetId} answered ${response.status}`);
  return response.json();
}

// ---------------------------------------------------------------------------
// One function per dataset. Each takes the building and returns a small object.
// ---------------------------------------------------------------------------

/** DOI marshal evictions (6z8x-wfk4): residential evictions per year. */
async function evictions(building) {
  // Socrata does the counting for us, so only a few numbers come back
  // instead of every eviction record.
  const rows = await socrata('6z8x-wfk4', {
    $select: 'date_extract_y(executed_date) AS year, count(*) AS evictions',
    $where: `bbl='${building.bbl}' AND residential_commercial_ind='Residential'`,
    $group: 'year',
    $order: 'year',
  });
  const byYear = Object.fromEntries(rows.map((row) => [row.year, Number(row.evictions)]));
  const total = Object.values(byYear).reduce((sum, n) => sum + n, 0);
  return { source: '6z8x-wfk4', residentialTotal: total, residentialByYear: byYear };
}

// TODO: add the other datasets from the brief, one function each, e.g.
//   async function hpdViolations(building) { ... }
//   async function dobViolations(building) { ... }
// then list them in DATASETS below.

const DATASETS = {
  evictions,
};

// ---------------------------------------------------------------------------

/**
 * The one function the site calls. Runs every dataset at the same time.
 * If one dataset fails, the others still come back, and the failure is noted.
 */
export async function getBuildingProfile(building) {
  const names = Object.keys(DATASETS);
  const results = await Promise.allSettled(names.map((name) => DATASETS[name](building)));

  const datasets = {};
  names.forEach((name, i) => {
    const result = results[i];
    datasets[name] = result.status === 'fulfilled'
      ? result.value
      : { error: String(result.reason?.message ?? result.reason) };
  });

  return {
    bbl: building.bbl,
    bin: building.bin,
    zip: building.postalCode,
    fetchedAt: new Date().toISOString(),
    datasets,
  };
}
