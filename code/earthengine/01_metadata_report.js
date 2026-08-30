// =====================================================================
//  gee_01_metadata_report.js
//
//  Prints and exports every piece of Sentinel-2 provenance the referee
//  asks for under comment M5: asset identifiers, sensing dates, MGRS
//  tiles, cloud percentages, compositing rules, SCL classes excluded,
//  reflectance scaling and resampling.
//
//  Run this in the Earth Engine Code Editor. It changes nothing; it only
//  reports. The CSV it writes to Drive becomes Supplementary Table S8.
//
//  Amrouss et al., Beni Moussa irrigated district, Tadla Plain, Morocco.
// =====================================================================

// --- 1. AOI, identical to the covariate export ------------------------
var aoi = ee.Geometry.Polygon([[
  [-7.152655325374058, 32.14382853284281],
  [-6.309454641780308, 32.14382853284281],
  [-6.309454641780308, 32.61932132661444],
  [-7.152655325374058, 32.61932132661444],
  [-7.152655325374058, 32.14382853284281]
]]);
Map.centerObject(aoi, 9);
Map.addLayer(aoi, {color: 'red'}, 'AOI', false);

var CLOUD_MAX = 40;                    // CLOUDY_PIXEL_PERCENTAGE threshold
var SCL_DROP  = [3, 8, 9, 10, 11];     // shadow, cloud med, cloud high, cirrus, snow
var COLL      = 'COPERNICUS/S2_SR_HARMONIZED';

print('=== AREA OF INTEREST ===');
print('bounds', aoi.bounds());
print('area (ha)', aoi.area(1).divide(1e4));

// --- 2. Cloud mask (identical to the export) --------------------------
function maskS2(img) {
  var scl = img.select('SCL');
  var ok = scl.neq(3).and(scl.neq(8)).and(scl.neq(9))
              .and(scl.neq(10)).and(scl.neq(11));
  return img.updateMask(ok).divide(10000)
            .copyProperties(img, img.propertyNames());
}

// --- 3. Scene inventory for one month ---------------------------------
function monthCollection(year, month) {
  var start = ee.Date.fromYMD(year, month, 1);
  return ee.ImageCollection(COLL)
      .filterBounds(aoi)
      .filterDate(start, start.advance(1, 'month'));
}

function report(year, month, tag) {
  var raw  = monthCollection(year, month);
  var kept = raw.filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', CLOUD_MAX));

  print('=====================================================');
  print(tag + ' composite');
  print('  scenes intersecting AOI      ', raw.size());
  print('  scenes with cloud < ' + CLOUD_MAX + '%     ', kept.size());
  print('  distinct MGRS tiles          ',
        kept.aggregate_array('MGRS_TILE').distinct().sort());
  print('  distinct relative orbits     ',
        kept.aggregate_array('SENSING_ORBIT_NUMBER').distinct().sort());
  print('  platforms                    ',
        kept.aggregate_array('SPACECRAFT_NAME').distinct().sort());
  print('  processing baselines         ',
        kept.aggregate_array('PROCESSING_BASELINE').distinct().sort());
  print('  cloud cover min / max / mean ',
        kept.aggregate_min('CLOUDY_PIXEL_PERCENTAGE'),
        kept.aggregate_max('CLOUDY_PIXEL_PERCENTAGE'),
        kept.aggregate_mean('CLOUDY_PIXEL_PERCENTAGE'));
  print('  BOA_ADD_OFFSET_B2 (expect -1000)',
        ee.Image(kept.first()).get('BOA_ADD_OFFSET_B2'));

  // one row per contributing scene, ready for the supplementary table
  var rows = kept.map(function (img) {
    return ee.Feature(null, {
      composite:  tag,
      asset_id:   ee.String(COLL).cat('/').cat(img.get('system:index')),
      product_id: img.get('PRODUCT_ID'),
      granule_id: img.get('GRANULE_ID'),
      sensing_utc: ee.Date(img.get('system:time_start'))
                     .format('YYYY-MM-dd HH:mm:ss'),
      mgrs_tile:  img.get('MGRS_TILE'),
      cloud_pct:  img.get('CLOUDY_PIXEL_PERCENTAGE'),
      cloud_land_pct: img.get('CLOUDY_PIXEL_OVER_LAND_PERCENTAGE'),
      shadow_pct: img.get('CLOUD_SHADOW_PERCENTAGE'),
      nodata_pct: img.get('NODATA_PIXEL_PERCENTAGE'),
      platform:   img.get('SPACECRAFT_NAME'),
      baseline:   img.get('PROCESSING_BASELINE'),
      orbit:      img.get('SENSING_ORBIT_NUMBER'),
      sun_zenith: img.get('MEAN_SOLAR_ZENITH_ANGLE'),
      sun_azimuth: img.get('MEAN_SOLAR_AZIMUTH_ANGLE'),
      boa_offset_B2: img.get('BOA_ADD_OFFSET_B2')
    });
  });
  print('  scene table (open the table icon to expand)', rows.limit(60));

  Export.table.toDrive({
    collection: ee.FeatureCollection(rows),
    description: 'S2_scene_inventory_' + tag,
    folder: 'S2_metadata',
    fileNamePrefix: 'S2_scene_inventory_' + tag,
    fileFormat: 'CSV',
    selectors: ['composite', 'asset_id', 'product_id', 'granule_id', 'sensing_utc',
                'mgrs_tile', 'cloud_pct', 'cloud_land_pct', 'shadow_pct',
                'nodata_pct', 'platform', 'baseline', 'orbit',
                'sun_zenith', 'sun_azimuth', 'boa_offset_B2']
  });

  return kept.map(maskS2);
}

var novCol = report(2024, 11, '2024_11');
var janCol = report(2025,  1, '2025_01');

// --- 4. Composite depth: how many clear observations per pixel --------
function depth(col, tag) {
  var n = col.select('B8').count().rename('n_obs').clip(aoi);
  print(tag + ' clear observations per pixel',
        n.reduceRegion({
          reducer: ee.Reducer.min()
                     .combine(ee.Reducer.max(), '', true)
                     .combine(ee.Reducer.mean(), '', true),
          geometry: aoi, scale: 100, maxPixels: 1e13, bestEffort: true
        }));
  Map.addLayer(n, {min: 0, max: 12, palette: ['red', 'yellow', 'green']},
               tag + ' composite depth', false);
}
depth(novCol, '2024_11');
depth(janCol, '2025_01');

// --- 5. Reflectance range after masking and scaling -------------------
//     Confirms the divide(10000) was applied on the correct scale.
var BANDS = ['B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B8A', 'B11', 'B12'];
function bandStats(col, tag) {
  var med = col.median().select(BANDS).clip(aoi);
  print(tag + ' band reflectance after mask + scale (expect ~0.01-0.60)',
        med.reduceRegion({
          reducer: ee.Reducer.min().combine(ee.Reducer.max(), '', true),
          geometry: aoi, scale: 100, maxPixels: 1e13, bestEffort: true
        }));
}
bandStats(novCol, '2024_11');
bandStats(janCol, '2025_01');

// --- 6. Fixed provenance statement ------------------------------------
print('=== PROVENANCE, FOR SECTION 3.2.1 ===');
print(ee.Dictionary({
  collection:            COLL,
  scene_cloud_filter:    'CLOUDY_PIXEL_PERCENTAGE < ' + CLOUD_MAX,
  scl_classes_masked:    SCL_DROP,
  scl_class_meanings:    '3 cloud shadow, 8 cloud medium, 9 cloud high, ' +
                         '10 thin cirrus, 11 snow/ice',
  reflectance_scaling:   'divide by 10000 after masking',
  boa_add_offset:        '-1000, applied by the harmonized collection',
  compositing:           'per-pixel median over each calendar month',
  mosaicking:            'the median composite also mosaics across MGRS tiles',
  export_scale_m:        10,
  export_crs:            'EPSG:4326',
  resampling_20m_to_10m: 'bilinear, on export to the 10 m grid'
}));

// =====================================================================
//  After running: Tasks tab -> run both S2_scene_inventory_* exports.
//  The two CSVs land in Drive/S2_metadata and together form
//  Supplementary Table S8.
// =====================================================================
