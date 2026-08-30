// =====================================================================
//  gee_02_export_covariates_CORRECTED.js
//
//  Exports the Sentinel-2 covariates used in the revised analysis.
//
//  WHY THIS SCRIPT EXISTS
//  The originally submitted export (kept as gee_00_original_as_submitted.js
//  for transparency) computed four indices that did not match their stated
//  definitions:
//
//    SI    was  (B11-B8)/(B11+B8)      = the exact negative of NDMI
//               declared as B11 x B12
//    VSSI  was  (B11-B3)/(B11+B3)      = the exact negative of NDSI
//               declared as 2*B3 - 5*(B4+B8)
//    NDSI  was  (B3-B11)/(B3+B11)      = the standard MNDWI formula
//               and was not defined in Table 2 at all
//    MNDWI was  (B3-B12)/(B3+B12)      = used B12 in place of B11
//
//  Two of the 42 exported layers were therefore sign-flipped duplicates of
//  two others and carried no independent information.
//
//  WHAT CHANGED HERE
//  1. SI, VSSI and MNDWI now compute what they claim.
//  2. The redundant NDSI layer is removed. 10 bands + 10 indices per month.
//  3. Only the 10 REFLECTANCE BANDS are exported. The indices are computed
//     downstream in 01_build_predictors_and_blocks.py and
//     03_predict_10m_maps.py from these bands, with the formulas verified
//     against the deposited values to within 3e-8. Exporting the indices
//     as rasters is therefore unnecessary and halves the export volume.
//     Set EXPORT_INDICES = true below if you want them anyway.
//  4. An explicit crs is set, so the output grid is reproducible.
//
//  Everything else - AOI, cloud filter, SCL mask, scaling, median
//  compositing, 10 m scale - is unchanged from the original.
//
//  Amrouss et al., Beni Moussa irrigated district, Tadla Plain, Morocco.
// =====================================================================

var EXPORT_INDICES = false;   // bands alone are sufficient for the pipeline

// --- 1. AOI -----------------------------------------------------------
var aoi = ee.Geometry.Polygon([[
  [-7.152655325374058, 32.14382853284281],
  [-6.309454641780308, 32.14382853284281],
  [-6.309454641780308, 32.61932132661444],
  [-7.152655325374058, 32.61932132661444],
  [-7.152655325374058, 32.14382853284281]
]]);
Map.centerObject(aoi, 9);

// --- 2. Cloud mask (unchanged) ----------------------------------------
function maskS2(img) {
  var scl = img.select('SCL');
  var ok = scl.neq(3)       // cloud shadow
              .and(scl.neq(8))    // cloud, medium probability
              .and(scl.neq(9))    // cloud, high probability
              .and(scl.neq(10))   // thin cirrus
              .and(scl.neq(11));  // snow / ice
  return img.updateMask(ok).divide(10000)
            .copyProperties(img, img.propertyNames());
}

// --- 3. Monthly median composite (unchanged) --------------------------
function getMonthlyComposite(year, month) {
  var start = ee.Date.fromYMD(year, month, 1);
  return ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
      .filterBounds(aoi)
      .filterDate(start, start.advance(1, 'month'))
      .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 40))
      .map(maskS2)
      .median()
      .clip(aoi);
}

var imgNov = getMonthlyComposite(2024, 11);
var imgJan = getMonthlyComposite(2025, 1);

// --- 4. CORRECTED indices ---------------------------------------------
//     Each formula matches Table 2 of the manuscript exactly.
function addIndices(img) {
  var B2  = img.select('B2'),  B3  = img.select('B3'),  B4  = img.select('B4'),
      B5  = img.select('B5'),  B8  = img.select('B8'),  B8A = img.select('B8A'),
      B11 = img.select('B11'), B12 = img.select('B12');

  var NDVI  = img.expression('(N - R)/(N + R)', {N: B8, R: B4}).rename('NDVI');
  var SAVI  = img.expression('1.5*(N - R)/(N + R + 0.5)', {N: B8, R: B4}).rename('SAVI');
  var EVI   = img.expression('2.5*(N - R)/(N + 6*R - 7.5*B + 1)',
                             {N: B8, R: B4, B: B2}).rename('EVI');
  var GNDVI = img.expression('(N - G)/(N + G)', {N: B8, G: B3}).rename('GNDVI');
  // NDRE uses B8A: B8A and B5 share the same 20 m native support.
  var NDRE  = img.expression('(Nn - RE1)/(Nn + RE1)', {Nn: B8A, RE1: B5}).rename('NDRE');
  var NDMI  = img.expression('(N - SW1)/(N + SW1)', {N: B8, SW1: B11}).rename('NDMI');

  // CORRECTED: MNDWI uses SWIR-1 (B11), per Xu (2006).
  var MNDWI = img.expression('(G - SW1)/(G + SW1)', {G: B3, SW1: B11}).rename('MNDWI');

  var BSI   = img.expression('((SW1 + R) - (N + B)) / ((SW1 + R) + (N + B))',
                             {SW1: B11, R: B4, N: B8, B: B2}).rename('BSI');

  // CORRECTED: SI is the product of the two SWIR bands, per Khan et al. (2005).
  var SI    = img.expression('SW1 * SW2', {SW1: B11, SW2: B12}).rename('SI');

  // CORRECTED: VSSI per Dehni and Lounis (2012).
  var VSSI  = img.expression('2*G - 5*(R + N)', {G: B3, R: B4, N: B8}).rename('VSSI');

  // NDSI is deliberately NOT computed: the layer of that name in the original
  // export duplicated MNDWI and was absent from Table 2.
  return img.addBands([NDVI, SAVI, EVI, GNDVI, NDRE, NDMI, MNDWI, BSI, SI, VSSI]);
}

imgNov = addIndices(imgNov);
imgJan = addIndices(imgJan);

// --- 5. Sanity checks before exporting --------------------------------
var BANDS = ['B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B8A', 'B11', 'B12'];
var INDICES = ['NDVI', 'SAVI', 'EVI', 'GNDVI', 'NDRE', 'NDMI', 'MNDWI',
               'BSI', 'SI', 'VSSI'];

print('bands per composite  ', BANDS.length);
print('indices per composite', INDICES.length);
print('total predictors     ', (BANDS.length + INDICES.length) * 2);

// Reflectance should sit in roughly 0.01-0.60. If it prints thousands, the
// divide(10000) did not apply.
print('Nov band range (expect ~0.01-0.60)',
      imgNov.select(BANDS).reduceRegion({
        reducer: ee.Reducer.min().combine(ee.Reducer.max(), '', true),
        geometry: aoi, scale: 100, maxPixels: 1e13, bestEffort: true}));

// The three corrected indices should now differ from the layers they used to
// duplicate. Each correlation below should be far from -1.
var chk = imgNov.select(['SI', 'NDMI', 'VSSI', 'MNDWI']);
print('SI vs NDMI correlation (was exactly -1 before the fix)',
      chk.select(['SI', 'NDMI']).reduceRegion({
        reducer: ee.Reducer.pearsonsCorrelation(),
        geometry: aoi, scale: 100, maxPixels: 1e13, bestEffort: true}));
print('VSSI vs MNDWI correlation',
      chk.select(['VSSI', 'MNDWI']).reduceRegion({
        reducer: ee.Reducer.pearsonsCorrelation(),
        geometry: aoi, scale: 100, maxPixels: 1e13, bestEffort: true}));

Map.addLayer(imgNov.select(['B4', 'B3', 'B2']), {min: 0.02, max: 0.25},
             'Nov 2024 true colour');
Map.addLayer(imgJan.select(['B4', 'B3', 'B2']), {min: 0.02, max: 0.25},
             'Jan 2025 true colour', false);

// --- 6. Export --------------------------------------------------------
var toExport = EXPORT_INDICES ? BANDS.concat(INDICES) : BANDS;

[[imgNov, '2024_11'], [imgJan, '2025_01']].forEach(function (pair) {
  var img = pair[0], tag = pair[1];
  toExport.forEach(function (band) {
    Export.image.toDrive({
      image: img.select(band).toFloat(),
      description: band + '_' + tag,
      folder: 'S2_Monthly_CORRECTED',
      fileNamePrefix: band + '_' + tag,
      region: aoi,
      scale: 10,
      crs: 'EPSG:4326',          // explicit, so the grid is reproducible
      maxPixels: 1e13
    });
  });
});

print('export tasks queued', toExport.length * 2);

// =====================================================================
//  AFTER THE EXPORT FINISHES
//  1. Download the GeoTIFFs from Drive -> S2_Monthly_CORRECTED
//  2. Place them in covariates_clipped/
//  3. Run, in order:
//       python 01_build_predictors_and_blocks.py
//       python 02_nested_cv_and_baselines.py
//       python 03_predict_10m_maps.py
//     Steps 01 and 03 recompute the ten indices from these bands using the
//     same corrected formulas, so the analysis does not depend on the index
//     rasters being exported.
// =====================================================================
