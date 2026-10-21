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

/**
 * Decides whether one building number (BIN) can be used to look up Department
 * of Buildings data. A missing BIN, a BIN that is not 7 digits, or a
 * placeholder BIN that ends in 000000 would return other buildings' records,
 * so it is not used.
 * Returns null when the BIN is usable, or a short note saying why not.
 */
function binProblem(bin) {
  if (!bin) return 'The building number (BIN) is missing.';
  if (!/^\d{7}$/.test(bin)) return 'The building number (BIN) is not 7 digits.';
  if (/000000$/.test(bin)) return 'The building number (BIN) is a placeholder that ends in 000000.';
  return null;
}

/**
 * Lists the usable building numbers (BINs) of every building on the building's
 * tax lot (the Borough, Block, and Lot, called bbl here).
 *
 * NYC Building Footprints (5zhs-2jue) returns the BIN of every building on the
 * lot. The BIN that the address search returned (building.bin) is added to
 * that list. Every BIN that binProblem() rejects is removed, and each BIN is
 * listed once. The list can be empty.
 */
async function binsOnLot(building) {
  if (!/^\d{10}$/.test(building.bbl)) {
    throw new Error('bbl is not 10 digits, so the buildings on the lot cannot be listed');
  }

  const rows = await socrata('5zhs-2jue', {
    $select: 'bin',
    $where: `mappluto_bbl='${building.bbl}' OR base_bbl='${building.bbl}'`,
  });

  const candidateBins = [building.bin, ...rows.map((row) => row.bin)];
  const usableBins = candidateBins.filter((bin) => binProblem(bin) === null);
  return [...new Set(usableBins)];
}

/** The source writes dates as YYYYMMDD. This turns one into YYYY-MM-DD. */
function formatCompactDate(text) {
  return /^\d{8}$/.test(text ?? '') ? `${text.slice(0, 4)}-${text.slice(4, 6)}-${text.slice(6, 8)}` : null;
}

/**
 * Department of Buildings violations (3h2n-5cm9): the older civil penalties
 * that the Department of Buildings recorded. The newer civil penalties are in
 * a different dataset, DOB Safety Violations, which this function does not
 * read. Summonses judged by the Environmental Control Board are in the next
 * function.
 *
 * Returns the number of buildings on the lot, the number of violations, the
 * number still active, how many of the active ones are hazardous, and the
 * latest issue date.
 *
 * A violation is counted when its building number (BIN) is in the list of
 * BINs on the lot, or when the row itself is on the building's lot. This
 * dataset holds the borough as one digit, the block as 5 digits, and the lot
 * as 5 digits. A placeholder BIN is never used in the query. If the list of
 * BINs is empty, only the lot is used.
 *
 * A violation is active when its category ends with the word ACTIVE. One
 * category with the text "V%-DOB VIOLATION" (about 1,000 rows in the whole
 * table) does not say active or dismissed and is not counted as active.
 * Hazardous means the category starts with VH or VWH.
 */
async function dobViolations(building) {
  if (!/^\d{10}$/.test(building.bbl)) {
    throw new Error('bbl is not 10 digits, so violations cannot be looked up');
  }

  const bins = await binsOnLot(building);

  const borough = building.bbl.slice(0, 1);
  const block = building.bbl.slice(1, 6);
  const lot = '0' + building.bbl.slice(6, 10);
  const onLot = `(boro='${borough}' AND block='${block}' AND lot='${lot}')`;
  const binList = bins.map((bin) => `'${bin}'`).join(',');
  const where = bins.length > 0 ? `(bin in (${binList}) OR ${onLot})` : onLot;

  const rows = await socrata('3h2n-5cm9', {
    $select: 'violation_category, count(*) AS violations, max(issue_date) AS latest',
    $where: where,
    $group: 'violation_category',
  });

  let total = 0;
  let active = 0;
  let activeHazardous = 0;
  let latest = null;
  for (const row of rows) {
    const count = Number(row.violations);
    const category = row.violation_category ?? '';
    total += count;
    if (row.latest && (!latest || row.latest > latest)) latest = row.latest;
    if (category.endsWith('ACTIVE')) {
      active += count;
      if (category.startsWith('VH') || category.startsWith('VWH')) activeHazardous += count;
    }
  }

  return {
    source: '3h2n-5cm9',
    buildingsOnLot: bins.length,
    totalViolations: total,
    activeViolations: active,
    activeHazardousViolations: activeHazardous,
    latestIssueDate: formatCompactDate(latest),
  };
}

/**
 * Department of Buildings summonses judged by the Environmental Control Board
 * (6bgk-3dad): the number of buildings on the lot, the number of summonses,
 * the number still active, the active ones by severity, and the latest issue
 * date.
 *
 * A summons is counted when its building number (BIN) is in the list of BINs
 * on the lot, or when the row itself is on the building's lot. This dataset
 * holds the borough as one digit, the block as 5 digits, and the lot as 4
 * digits. A placeholder BIN is never used in the query. If the list of BINs is
 * empty, only the lot is used.
 *
 * A summons is active when its status is ACTIVE. The source also uses RESOLVE
 * and, for 3 rows in the whole table, Unknown. The respondent name, the
 * penalty, and the dollar amounts are never returned. The source does not
 * define the money columns, so no dollar figure is returned.
 */
async function ecbViolations(building) {
  if (!/^\d{10}$/.test(building.bbl)) {
    throw new Error('bbl is not 10 digits, so summonses cannot be looked up');
  }

  const bins = await binsOnLot(building);

  const borough = building.bbl.slice(0, 1);
  const block = building.bbl.slice(1, 6);
  const lot = building.bbl.slice(6, 10);
  const onLot = `(boro='${borough}' AND block='${block}' AND lot='${lot}')`;
  const binList = bins.map((bin) => `'${bin}'`).join(',');
  const where = bins.length > 0 ? `(bin in (${binList}) OR ${onLot})` : onLot;

  const rows = await socrata('6bgk-3dad', {
    $select: 'ecb_violation_status, severity, count(*) AS summonses, max(issue_date) AS latest',
    $where: where,
    $group: 'ecb_violation_status, severity',
  });

  let total = 0;
  let active = 0;
  const activeBySeverity = {};
  let latest = null;
  for (const row of rows) {
    const count = Number(row.summonses);
    total += count;
    if (row.latest && (!latest || row.latest > latest)) latest = row.latest;
    if (row.ecb_violation_status === 'ACTIVE') {
      active += count;
      const severity = row.severity ?? 'Not stated';
      activeBySeverity[severity] = (activeBySeverity[severity] ?? 0) + count;
    }
  }

  return {
    source: '6bgk-3dad',
    buildingsOnLot: bins.length,
    totalSummonses: total,
    activeSummonses: active,
    activeBySeverity,
    latestIssueDate: formatCompactDate(latest),
  };
}

const DATASETS = {
  evictions,
  hpdViolations,
  hpdComplaints,
  hpdLitigation,
  dobViolations,
  ecbViolations,
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