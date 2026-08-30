// =====================================================================
//  gee_00_original_as_submitted.js
//
//  ARCHIVED FOR TRANSPARENCY - DO NOT RUN THIS TO REPRODUCE THE ANALYSIS.
//
//  This is the covariate export script used for the previously submitted
//  version of the manuscript, kept verbatim so that the errors reported
//  under referee comment M5 can be independently confirmed. Use
//  gee_02_export_covariates_CORRECTED.js instead.
//
//  FOUR INDEX DEFINITIONS BELOW DO NOT MATCH THEIR STATED FORMULAS:
//
//    SI    computes (B11-B8)/(B11+B8), the exact negative of NDMI,
//          although Table 2 declared B11 x B12.
//    VSSI  computes (B11-B3)/(B11+B3), the exact negative of the layer
//          named NDSI, although Table 2 declared 2*B3 - 5*(B4+B8).
//    NDSI  computes (B3-B11)/(B3+B11), which is the standard MNDWI, and
//          was not defined in Table 2 at all.
//    MNDWI computes (B3-B12)/(B3+B12), using SWIR-2 in place of SWIR-1.
//
//  Consequences, verified at all 110 sampling points on both dates:
//    SI + NDMI  = 0 to machine precision
//    VSSI + NDSI = 0 to machine precision
//  Two of the 42 exported layers therefore carried no information beyond
//  another column of the same matrix.
//
//  The AOI definition was not preserved with the original file; the
//  polygon used is the one in gee_02_export_covariates_CORRECTED.js,
//  recovered from the accompanying B7 re-export script.
// =====================================================================

// --- 2. Cloud mask ------------------------------------------------------- //
function maskS2(img) {
  var scl = img.select('SCL');
  var ok = scl.neq(3).and(scl.neq(8)).and(scl.neq(9))
              .and(scl.neq(10)).and(scl.neq(11)); // remove clouds & shadows
  return img.updateMask(ok).divide(10000)
            .copyProperties(img, img.propertyNames());
}

// --- 3. Sentinel-2 collection loader ------------------------------------ //
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

// --- 4. Monthly composites ---------------------------------------------- //
var imgNov = getMonthlyComposite(2024, 11);
var imgJan = getMonthlyComposite(2025, 1);

// --- 5. Function to add all indices ------------------------------------ //
function addIndices(img) {
  var B2=img.select('B2'),B3=img.select('B3'),B4=img.select('B4'),
      B5=img.select('B5'),B6=img.select('B6'),B7=img.select('B7'),
      B8=img.select('B8'),B8A=img.select('B8A'),
      B11=img.select('B11'),B12=img.select('B12');

  var NDVI  = img.expression('(N - R)/(N + R)', {N:B8,R:B4}).rename('NDVI');
  var EVI   = img.expression('2.5*(N - R)/(N + 6*R - 7.5*B + 1)', {N:B8,R:B4,B:B2}).rename('EVI');
  var NDRE  = img.expression('(Nn - RE1)/(Nn + RE1)', {Nn:B8A,RE1:B5}).rename('NDRE');
  var GNDVI = img.expression('(N - G)/(N + G)', {N:B8,G:B3}).rename('GNDVI');
  var SAVI  = img.expression('1.5*(N - R)/(N + R + 0.5)', {N:B8,R:B4}).rename('SAVI');
  var NDMI  = img.expression('(N - SW)/(N + SW)', {N:B8,SW:B11}).rename('NDMI');
  var BSI   = img.expression('((SW + R) - (N + B)) / ((SW + R) + (N + B))',
                 {SW:B11,R:B4,N:B8,B:B2}).rename('BSI');
  var SI    = img.expression('(SW - N)/(SW + N)', {SW:B11,N:B8}).rename('SI');       // WRONG
  var NDSI  = img.expression('(G - SW)/(G + SW)', {G:B3,SW:B11}).rename('NDSI');     // = MNDWI
  var VSSI  = img.expression('(SW - G)/(SW + G)', {SW:B11,G:B3}).rename('VSSI');     // = -NDSI
  var MNDWI = img.expression('(G - SW2)/(G + SW2)', {G:B3,SW2:B12}).rename('MNDWI'); // uses B12

  return img.addBands([
    NDVI,EVI,NDRE,GNDVI,SAVI,NDMI,BSI,SI,NDSI,VSSI,MNDWI
  ]);
}

// --- 6. Add indices to both months ------------------------------------ //
imgNov = addIndices(imgNov);
imgJan = addIndices(imgJan);

// --- 7. List all layers to export ------------------------------------- //
var allBands = [
  'B2','B3','B4','B5','B6','B7','B8','B8A','B11','B12',
  'NDVI','EVI','NDRE','GNDVI','SAVI','NDMI','BSI','SI','NDSI','VSSI','MNDWI'
];

// --- 8. Visualization -------------------------------------------------- //
Map.centerObject(aoi, 10);
allBands.forEach(function(band){
  Map.addLayer(imgNov.select(band), {min:0,max:0.4,palette:['blue','white','green']}, band + '_2024_11');
  Map.addLayer(imgJan.select(band), {min:0,max:0.4,palette:['blue','white','green']}, band + '_2025_01');
});

// --- 9. Export each band/index separately ----------------------------- //
allBands.forEach(function(band){
  Export.image.toDrive({
    image: imgNov.select(band),
    description: band + '_2024_11',
    folder: 'S2_Monthly',
    fileNamePrefix: band + '_2024_11',
    region: aoi,
    scale: 10,
    maxPixels: 1e13
  });
  Export.image.toDrive({
    image: imgJan.select(band),
    description: band + '_2025_01',
    folder: 'S2_Monthly',
    fileNamePrefix: band + '_2025_01',
    region: aoi,
    scale: 10,
    maxPixels: 1e13
  });
});
