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

// Settings shared by every request. Leave them alone while testing; the site
// sets its own once, with configure().
//   appToken:  a Socrata app token, which raises the rate limit. Optional.
//   timeoutMs: how long to wait for one answer before giving up on that
//              dataset. NYC Open Data is sometimes very slow, and without a
//              limit one slow answer holds up the whole profile.
const settings = { appToken: '', timeoutMs: 20000 };

/** Change the shared settings, e.g. configure({ appToken: '…' }). */
export function configure(options = {}) {
  Object.assign(settings, options);
}

/**
 * Ask NYC Open Data a question and get the answer back as a list of objects.
 * `params` are SoQL query parameters, e.g. { $where: "bbl='2026100012'" }.
 * Stops waiting after settings.timeoutMs; that dataset then reports an error
 * and the others still come back.
 */
async function socrata(datasetId, params) {
  const url = new URL(SOCRATA + datasetId + '.json');
  for (const [key, value] of Object.entries(params)) url.searchParams.set(key, value);
  const headers = settings.appToken ? { 'X-App-Token': settings.appToken } : {};
  let response;
  try {
    response = await fetch(url, { headers, signal: AbortSignal.timeout(settings.timeoutMs) });
  } catch (err) {
    if (err.name === 'TimeoutError') {
      throw new Error(`${datasetId} did not answer within ${settings.timeoutMs / 1000} seconds`);
    }
    throw err;
  }
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

/**
 * HPD housing maintenance code violations (wvxf-dwi5): totals, open counts,
 * open counts by class, open rent-impairing count, and the latest inspection.
 *
 * The building is matched on the dataset's own `bbl` column, as text. Do not
 * match on the separate boroid, block, and lot columns: for 765 Lincoln Avenue
 * that returns no rows, even though the `bbl` column shows 5,082 open
 * violations. About 10,600 violation rows in the whole table have no `bbl`
 * value, and this function cannot count those.
 *
 * Class A is the least serious, B is serious, C is the most serious. Class I
 * is an informational order. rentimpairing is 'Y' or 'N'.
 */
async function hpdViolations(building) {
  if (!/^\d{10}$/.test(building.bbl)) {
    throw new Error('bbl is not 10 digits, so violations cannot be looked up');
  }

  // Socrata does the counting. One row comes back for each combination of
  // status, class, and rent-impairing flag, so only a few rows return.
  const rows = await socrata('wvxf-dwi5', {
    $select: 'violationstatus, class, rentimpairing, count(*) AS violations, max(inspectiondate) AS latest',
    $where: `bbl='${building.bbl}'`,
    $group: 'violationstatus, class, rentimpairing',
  });

  let total = 0;
  let open = 0;
  let openRentImpairing = 0;
  const openByClass = {};
  let latestInspectionDate = null;

  for (const row of rows) {
    const count = Number(row.violations);
    total += count;
    if (row.latest && (!latestInspectionDate || row.latest > latestInspectionDate)) {
      latestInspectionDate = row.latest;
    }
    if (row.violationstatus === 'Open') {
      open += count;
      openByClass[row.class] = (openByClass[row.class] ?? 0) + count;
      if (row.rentimpairing === 'Y') openRentImpairing += count;
    }
  }

  return {
    source: 'wvxf-dwi5',
    total,
    open,
    closed: total - open,
    openByClass,
    openRentImpairing,
    latestInspectionDate: latestInspectionDate ? latestInspectionDate.slice(0, 10) : null,
  };
}

/**
 * HPD housing maintenance code complaints (ygpa-z7cr): the number of separate
 * complaints, how many are still open, the number received in each year, and
 * the date of the latest complaint.
 *
 * Each row in this table is one problem inside a complaint, and one complaint
 * can hold several problems. So this function counts the distinct complaint
 * identifiers, not rows. A complaint has one status and one received date, so
 * the counts can be added across groups.
 *
 * The building is matched on the dataset's `bbl` column. About 37,400 of the
 * 16.4 million rows in the whole table have no `bbl`, and this function cannot
 * count those. Apartment numbers and the anonymous-complaint flag are never
 * returned.
 */
async function hpdComplaints(building) {
  if (!/^\d{10}$/.test(building.bbl)) {
    throw new Error('bbl is not 10 digits, so complaints cannot be looked up');
  }

  // Two questions, asked at the same time. Socrata does the counting.
  const [groups, latest] = await Promise.all([
    socrata('ygpa-z7cr', {
      $select: 'date_extract_y(received_date) AS year, complaint_status, count(distinct complaint_id) AS complaints',
      $where: `bbl=${building.bbl}`,
      $group: 'year, complaint_status',
      $order: 'year',
    }),
    socrata('ygpa-z7cr', {
      $select: 'max(received_date) AS latest',
      $where: `bbl=${building.bbl}`,
    }),
  ]);

  let total = 0;
  let open = 0;
  const byYear = {};
  for (const row of groups) {
    const count = Number(row.complaints);
    total += count;
    byYear[row.year] = (byYear[row.year] ?? 0) + count;
    if (row.complaint_status === 'OPEN') open += count;
  }

  const latestDate = latest[0]?.latest ?? null;
  return {
    source: 'ygpa-z7cr',
    totalComplaints: total,
    openComplaints: open,
    complaintsByYear: byYear,
    latestComplaintDate: latestDate ? latestDate.slice(0, 10) : null,
  };
}

/**
 * HPD housing litigation (59kj-x8nc): Housing Court cases that the city's
 * Housing Litigation Division filed against owners of this building.
 *
 * Returns the number of cases, the number still pending, the number of cases
 * by case type, the number of cases with a finding of harassment, and the date
 * the latest case was opened.
 *
 * A case is pending when its status is PENDING or APPLICATION PENDING. Almost
 * all other cases are CLOSED. A few old cases (2006 and earlier) have other
 * status text, and they count as not pending.
 *
 * A finding of harassment is counted when the finding column says After
 * Inquest or After Trial. The value No Harassment does not count.
 *
 * The building is matched on the dataset's `bbl` column. 318 rows in the whole
 * table have no `bbl`, and this function cannot count those. The respondent
 * name, the penalty, and the case identifiers are never returned. Case type
 * labels are the source's own, including its spelling "Harrassment".
 */
async function hpdLitigation(building) {
  if (!/^\d{10}$/.test(building.bbl)) {
    throw new Error('bbl is not 10 digits, so litigation cannot be looked up');
  }

  // Socrata does the counting. One row comes back for each combination of
  // case type, status, and harassment finding.
  const rows = await socrata('59kj-x8nc', {
    $select: 'casetype, casestatus, findingofharassment, count(*) AS cases, max(caseopendate) AS latest',
    $where: `bbl='${building.bbl}'`,
    $group: 'casetype, casestatus, findingofharassment',
  });

  let total = 0;
  let pending = 0;
  let harassmentFindings = 0;
  const byType = {};
  let latestOpenDate = null;

  for (const row of rows) {
    const count = Number(row.cases);
    total += count;
    byType[row.casetype] = (byType[row.casetype] ?? 0) + count;
    if (row.casestatus === 'PENDING' || row.casestatus === 'APPLICATION PENDING') pending += count;
    if (row.findingofharassment === 'After Inquest' || row.findingofharassment === 'After Trial') {
      harassmentFindings += count;
    }
    if (row.latest && (!latestOpenDate || row.latest > latestOpenDate)) latestOpenDate = row.latest;
  }

  return {
    source: '59kj-x8nc',
    totalCases: total,
    pendingCases: pending,
    casesByType: byType,
    harassmentFindings,
    latestCaseOpenDate: latestOpenDate ? latestOpenDate.slice(0, 10) : null,
  };
}

// TODO: add the other datasets from the brief, one function each, e.g.
//   async function hpdViolations(building) { ... }
//   async function dobViolations(building) { ... }
// then list them in DATASETS below.

const DATASETS = {
  evictions,
  hpdViolations,
  hpdComplaints,
  hpdLitigation,
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
