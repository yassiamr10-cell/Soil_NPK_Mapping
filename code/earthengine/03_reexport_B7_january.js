// =====================================================================
//  Re-export B7 (Red-Edge 3) for the January-2025 composite
//  Uses the IDENTICAL AOI, cloud mask, filter and compositing logic as
//  the original monthly export, so B7_2025_01 is treated exactly like
//  every other band already in covariates_clipped/.
//
//  WHY THIS RE-RUN IS NEEDED
//  The B7_2025_01.tif currently on disk is (a) in raw DN (max 7207
//  instead of ~0.72) and (b) masked differently from its siblings
//  (9,806,148 valid pixels vs 9,343,965 for every other band, and a
//  minimum of exactly 0). It was evidently exported without maskS2.
//
//  VERIFICATION BUILT IN
//  This script also re-exports B8A_2025_01, a band you already have and
//  trust. If the new B8A matches the existing file pixel-for-pixel, the
//  new B7 was produced by the same pipeline and can be trusted too.
// =====================================================================

// --- 1. AOI (identical to the original export) ------------------------
var aoi = ee.Geometry.Polygon([
  [
    [-7.152655325374058, 32.14382853284281],
    [-6.309454641780308, 32.14382853284281],
    [-6.309454641780308, 32.61932132661444],
    [-7.152655325374058, 32.61932132661444],
    [-7.152655325374058, 32.14382853284281]
  ]
]);
Map.addLayer(aoi, {color: 'red'}, 'AOI');
Map.centerObject(aoi, 10);

// --- 2. Cloud mask (identical to the original) ------------------------
// NOTE: the .divide(10000) here is the scaling step that was missing
// from the run which produced the current B7_2025_01.tif.
function maskS2(img) {
  var scl = img.select('SCL');
  var ok = scl.neq(3)      // cloud shadow
              .and(scl.neq(8))   // cloud medium probability
              .and(scl.neq(9))   // cloud high probability
              .and(scl.neq(10))  // thin cirrus
              .and(scl.neq(11)); // snow / ice
  return img.updateMask(ok).divide(10000)
            .copyProperties(img, img.propertyNames());
}

// --- 3. Monthly composite (identical to the original) -----------------
function getMonthlyComposite(year, month) {
  var start = ee.Date.fromYMD(year, month, 1);
  var end = start.advance(1, 'month');
  var col = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
      .filterBounds(aoi)
      .filterDate(start, end)
      .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 40))
      .map(maskS2);
  return col.median().clip(aoi);
}

var imgJan = getMonthlyComposite(2025, 1);

// --- 4. Sanity check in the Console BEFORE exporting ------------------
// Both should print reflectance-scale numbers (roughly 0.00 - 0.80).
// If B7 prints thousands, the scaling step did not apply.
print('Scene count (Jan 2025, cloud < 40%):',
      ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
        .filterBounds(aoi).filterDate('2025-01-01', '2025-02-01')
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 40)).size());

print('B7_2025_01 stats (expect ~0.00-0.80):',
      imgJan.select('B7').reduceRegion({
        reducer: ee.Reducer.minMax().combine(ee.Reducer.mean(), '', true),
        geometry: aoi, scale: 100, maxPixels: 1e13
      }));

print('B8A_2025_01 stats (control band, expect ~0.006-0.76):',
      imgJan.select('B8A').reduceRegion({
        reducer: ee.Reducer.minMax().combine(ee.Reducer.mean(), '', true),
        geometry: aoi, scale: 100, maxPixels: 1e13
      }));

Map.addLayer(imgJan.select('B7'), {min: 0, max: 0.4,
             palette: ['blue', 'white', 'green']}, 'B7_2025_01 (fixed)');

// --- 5. Export --------------------------------------------------------
// B7 = the band being fixed.
// B8A = control; compare against your existing B8A_2025_01.tif.
['B7', 'B8A'].forEach(function (band) {
  Export.image.toDrive({
    image: imgJan.select(band).toFloat(),
    description: band + '_2025_01_FIXED',
    folder: 'S2_Monthly_FIX',
    fileNamePrefix: band + '_2025_01_FIXED',
    region: aoi,
    scale: 10,
    crs: 'EPSG:4326',        // matches the existing covariates_clipped rasters
    maxPixels: 1e13
  });
});

// =====================================================================
//  AFTER THE EXPORT FINISHES
//  1. Download both GeoTIFFs from Google Drive -> folder S2_Monthly_FIX
//  2. Put them in:  D:\Doctorat\article1\covariates_clipped\
//     keeping the names B7_2025_01_FIXED.tif and B8A_2025_01_FIXED.tif
//  3. Run:  python fix_b7_extract_and_update.py
//     That script verifies the control band, extracts B7 at the 110
//     sample points, and updates Extracted_Predictors_BeniMoussa.xlsx.
// =====================================================================
