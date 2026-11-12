// pull-baseline.mjs
//
// Re-pulls the expected counts for the 23 validation buildings straight from
// NYC Open Data and rewrites validation-buildings.json.
//
// It asks its own questions and does not use building-profile.js, so the two
// can check each other: if they disagree, one of them is counting wrong. Keep
// the methods below in step with the "Validation buildings" tab of the brief.
//
// Run it from the repository folder (needs Node 18 or later), about monthly:
//   node validation/pull-baseline.mjs
// Then run validate.mjs, review the changes with git diff, update the table in
// the brief, and commit.

import { readFileSync, writeFileSync } from 'node:fs';

const FILE = new URL('./validation-buildings.json', import.meta.url);
const SOCRATA = 'https://data.cityofnewyork.us/resource/';
const GEOSEARCH = 'https://geosearch.planninglabs.nyc/v2/search';
const headers = process.env.SOCRATA_APP_TOKEN ? { 'X-App-Token': process.env.SOCRATA_APP_TOKEN } : {};

// NYC Open Data sometimes answers 503 when it is busy, so each question is
// tried up to five times, waiting longer each time, before the run stops.
async function socrata(datasetId, params) {
  const url = new URL(SOCRATA + datasetId + '.json');
  for (const [key, value] of Object.entries(params)) url.searchParams.set(key, value);
  for (let attempt = 1; ; attempt += 1) {
    try {
      const response = await fetch(url, { headers });
      if (response.ok) return response.json();
      if (response.status < 500 || attempt === 5) throw new Error(`${datasetId} answered ${response.status}`);
    } catch (err) {
      if (attempt === 5 || /answered 4\d\d/.test(err.message)) throw err;
    }
    await new Promise((resolve) => setTimeout(resolve, 5000 * 2 ** (attempt - 1)));
  }
}

const count = async (datasetId, where, select = 'count(*) AS n') =>
  Number((await socrata(datasetId, { $select: select, $where: where }))[0]?.n ?? 0);

async function pull(entry) {
  const { bbl } = entry;
  const borough = bbl.slice(0, 1);
  const block = bbl.slice(1, 6);
  const lot = bbl.slice(6, 10);

  // The BIN the site will get for this address.
  const geoResponse = await fetch(`${GEOSEARCH}?size=1&text=${encodeURIComponent(entry.address)}`);
  if (!geoResponse.ok) throw new Error(`GeoSearch answered ${geoResponse.status}`);
  const geo = await geoResponse.json();
  const bin = geo.features?.[0]?.properties?.addendum?.pad?.bin || null;

  // PLUTO units and year built (0 means unknown in PLUTO).
  const [pluto] = await socrata('64uk-42ks', { $select: 'unitsres, yearbuilt', $where: `bbl=${bbl}` });

  // HPD open violations by class, matched on the dataset's own bbl column.
  const openByClass = Object.fromEntries(
    (await socrata('wvxf-dwi5', {
      $select: 'class, count(*) AS n',
      $where: `bbl='${bbl}' AND violationstatus='Open'`,
      $group: 'class',
    })).map((row) => [row.class, Number(row.n)]),
  );

  // Distinct complaints received in the last 365 days.
  const since = new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
  const complaints = await count('ygpa-z7cr', `bbl=${bbl} AND received_date >= '${since}T00:00:00'`,
    'count(distinct complaint_id) AS n');

  // HPD litigation cases, and cases with a harassment finding.
  const litigation = await count('59kj-x8nc', `bbl='${bbl}'`);
  const harassment = await count('59kj-x8nc',
    `bbl='${bbl}' AND findingofharassment in ('After Trial','After Inquest')`);

  // Executed residential evictions with this BBL (rows with no BBL are not counted).
  const evictions = await count('6z8x-wfk4', `bbl='${bbl}' AND residential_commercial_ind='Residential'`);

  // Active ECB summonses on the whole lot: every usable BIN on the lot from
  // Building Footprints, plus the address's own BIN, plus anything filed under
  // the lot itself. Placeholder BINs (ending 000000) are never used.
  const footprints = await socrata('5zhs-2jue', { $select: 'bin', $where: `mappluto_bbl='${bbl}' OR base_bbl='${bbl}'` });
  const bins = [...new Set([bin, ...footprints.map((row) => row.bin)])]
    .filter((b) => /^\d{7}$/.test(b ?? '') && !b.endsWith('000000'));
  const onLot = `(boro='${borough}' AND block='${block}' AND lot='${lot}')`;
  const where = bins.length ? `(bin in (${bins.map((b) => `'${b}'`).join(',')}) OR ${onLot})` : onLot;
  const ecb = await count('6bgk-3dad', `${where} AND ecb_violation_status='ACTIVE'`);

  return {
    ...entry,
    bin,
    unitsRes: Math.trunc(Number(pluto?.unitsres ?? 0)),
    yearBuilt: Math.trunc(Number(pluto?.yearbuilt ?? 0)),
    expected: {
      hpdOpenA: openByClass.A ?? 0,
      hpdOpenB: openByClass.B ?? 0,
      hpdOpenC: openByClass.C ?? 0,
      complaintsLast12Months: complaints,
      litigationCases: litigation,
      harassmentFindings: harassment,
      residentialEvictions: evictions,
      ecbActive: ecb,
    },
  };
}

const baseline = JSON.parse(readFileSync(FILE, 'utf8'));
const buildings = [];
for (const entry of baseline.buildings) {
  const updated = await pull(entry);
  buildings.push(updated);
  console.log(`${updated.address}: ${JSON.stringify(updated.expected)}`);
}

baseline.pulledOn = new Date().toISOString().slice(0, 10);
baseline.buildings = buildings;
writeFileSync(FILE, JSON.stringify(baseline, null, 2) + '\n');
console.log(`\nWrote ${buildings.length} buildings, pulled on ${baseline.pulledOn}.`);
