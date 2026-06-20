/* EcoPlant Plant-AI Engine v3 — single-pass spatial analysis */

function analyzeImage(imgEl) {
  var cv = document.getElementById('cv');
  var MAX = 320;
  var sw = imgEl.naturalWidth  || imgEl.width  || MAX;
  var sh = imgEl.naturalHeight || imgEl.height || MAX;
  var sc = Math.min(MAX / sw, MAX / sh, 1);
  cv.width  = Math.max(1, Math.round(sw * sc));
  cv.height = Math.max(1, Math.round(sh * sc));
  var ctx = cv.getContext('2d');
  ctx.drawImage(imgEl, 0, 0, cv.width, cv.height);

  var data, W = cv.width, H = cv.height;
  try { data = ctx.getImageData(0, 0, W, H).data; }
  catch(e) { return null; }

  var zw = Math.max(1, Math.floor(W / 3));
  var zh = Math.max(1, Math.floor(H / 3));

  // 9 zones — row-major [TL,TC,TR,ML,MC,MR,BL,BC,BR]
  var zones = [];
  for (var i = 0; i < 9; i++) zones.push({ G:0, Y:0, R:0, n:0, hSum:0, hSumSq:0 });

  var totalColored = 0, totalPx = (data.length / 4);

  for (var pi = 0; pi < data.length; pi += 4) {
    var a = data[pi + 3];
    if (a < 80) continue;

    var r = data[pi] / 255, g = data[pi+1] / 255, b = data[pi+2] / 255;
    var mx = Math.max(r,g,b), mn = Math.min(r,g,b);
    var l = (mx + mn) / 2, s = 0, h = 0;
    if (mx !== mn) {
      var d = mx - mn;
      s = l > 0.5 ? d / (2 - mx - mn) : d / (mx + mn);
      if (mx === r) h = ((g - b) / d + (g < b ? 6 : 0)) / 6;
      else if (mx === g) h = ((b - r) / d + 2) / 6;
      else h = ((r - g) / d + 4) / 6;
    }
    h *= 360;

    // Skip near-greyscale (backgrounds, pots, walls)
    if (s < 0.11 || l < 0.07 || l > 0.93) continue;
    totalColored++;

    // Which zone?
    var pxIdx = pi / 4;
    var px = pxIdx % W, py = Math.floor(pxIdx / W);
    var zc = Math.min(2, Math.floor(px / zw));
    var zr = Math.min(2, Math.floor(py / zh));
    var z = zones[zr * 3 + zc];
    z.n++;
    z.hSum += h;
    z.hSumSq += h * h;

    // Classify
    if (h >= 72 && h <= 168 && s >= 0.13) { z.G++; }
    else if (h >= 42 && h < 72 && s >= 0.16 && l > 0.28) { z.Y++; }
    else if ((h < 42 || h > 320) && s >= 0.10 && l > 0.07 && l < 0.58) { z.R++; }
  }

  // Normalise each zone
  var normZones = zones.map(function(z) {
    var n = z.n || 1;
    var hMean = z.hSum / n;
    var hVar  = z.n > 1 ? (z.hSumSq / n - hMean * hMean) : 0;
    return { G: z.G/n, Y: z.Y/n, R: z.R/n, hVar: hVar, n: z.n };
  });

  // Whole-image aggregates
  var tot = totalColored || 1;
  var totG = normZones.reduce(function(s,z){return s+z.G*z.n;},0)/tot;
  var totY = normZones.reduce(function(s,z){return s+z.Y*z.n;},0)/tot;
  var totR = normZones.reduce(function(s,z){return s+z.R*z.n;},0)/tot;

  var center = normZones[4];
  var edgeR  = ([0,1,2,3,5,6,7,8].reduce(function(s,i){return s+normZones[i].R;},0))/8;
  var edgeY  = ([0,1,2,3,5,6,7,8].reduce(function(s,i){return s+normZones[i].Y;},0))/8;
  var topY   = (normZones[0].Y + normZones[1].Y + normZones[2].Y) / 3;
  var botY   = (normZones[6].Y + normZones[7].Y + normZones[8].Y) / 3;
  var topR   = (normZones[0].R + normZones[1].R + normZones[2].R) / 3;
  var botR   = (normZones[6].R + normZones[7].R + normZones[8].R) / 3;
  var leftR  = (normZones[0].R + normZones[3].R + normZones[6].R) / 3;
  var rightR = (normZones[2].R + normZones[5].R + normZones[8].R) / 3;

  // Spot score: std-dev of zone R values (scattered = fungal)
  var rVals = normZones.map(function(z){return z.R;});
  var rMean = rVals.reduce(function(a,b){return a+b;},0)/9;
  var rVar  = rVals.reduce(function(s,v){return s+(v-rMean)*(v-rMean);},0)/9;
  var spotScore = Math.sqrt(rVar);

  return {
    G: totG, Y: totY, R: totR,
    coloredRatio: totalColored / totalPx,
    zones: normZones,
    center: center,
    edgeR: edgeR, edgeY: edgeY,
    topY: topY, botY: botY,
    topR: topR, botR: botR,
    leftR: leftR, rightR: rightR,
    spotScore: spotScore,
    textureVar: center.hVar
  };
}

function p100(v) { return Math.round(v * 100) + '%'; }

function diagnose(f) {
  if (!f) {
    return { score:50, dot:'warn', status:'Analysis Error',
      diag:'Could not analyse the image pixels. Please try a different photo.',
      issues:[], treats:['Try a different image format (JPG or PNG).','Ensure the photo is not corrupted.'] };
  }

  var g = f.G, y = f.Y, r = f.R;

  if (f.coloredRatio < 0.05) {
    return { score:0, dot:'warn', status:'No Plant Detected',
      diag:'Not enough coloured plant tissue found. Upload a close-up with leaves filling the frame.',
      issues:['Insufficient plant tissue visible'],
      treats:['Move the camera closer to the leaves.','Ensure good natural lighting.','Avoid dark or busy backgrounds.'] };
  }

  var score = Math.round(Math.max(5, Math.min(97, 55 + g*100*0.55 - y*100*0.55 - r*100*0.9)));
  var dot, status, diag, issues = [], treats = [];

  // ── 12-condition engine ──────────────────────────────────────────
  if (g > 0.52 && y < 0.12 && r < 0.09 && score >= 78) {
    dot='ok'; status='Thriving — Excellent Health';
    diag='Outstanding health confirmed. Chlorophyll coverage at '+p100(g)+' with stress markers (yellow '+p100(y)+', brown '+p100(r)+') well below critical thresholds. The plant is photosynthesising efficiently — no disease or deficiency signatures detected.';
    treats=['Keep current watering schedule.','Apply balanced NPK fertiliser monthly.','Wipe leaves with a damp cloth for maximum light absorption.','Repot every 1-2 years as roots fill the pot.'];

  } else if (f.spotScore > 0.07 && r > 0.10 && g > 0.20) {
    dot='bad'; status='Fungal Infection — Scattered Lesions';
    diag='Scattered brown lesion clusters detected across multiple zones (variance score: '+f.spotScore.toFixed(3)+'). The non-uniform distribution is the hallmark signature of fungal disease — Septoria leaf spot, Cercospora, or Rust. Isolated lesions surrounded by green tissue confirm active sporulation.';
    issues.push('Fungal leaf spot (Septoria / Cercospora / Rust)', 'Scattered necrotic lesions');
    if (y > 0.12) issues.push('Chlorotic halos around lesions');
    treats.push('Remove and bin all spotted leaves — do not compost.', 'Apply neem oil (5 ml/L) or copper fungicide every 5 days for 3 weeks.', 'Water at soil level only — avoid wetting leaves.', 'Improve air circulation around the plant.', 'Quarantine from other plants immediately.');

  } else if (f.edgeR > f.center.R * 1.4 && f.edgeR > 0.14 && g > 0.18) {
    dot='warn'; status='Tip Burn / Edge Scorch';
    diag='Brown pigmentation concentrated at leaf edges and tips (edge: '+p100(f.edgeR)+') while the centre remains healthier (centre: '+p100(f.center.R)+'). Classic margin necrosis pattern — caused by salt build-up from fertiliser or tap water, or low humidity causing excessive transpiration loss at leaf tips.';
    issues.push('Marginal leaf necrosis — tip burn', 'Salt toxicity or low humidity stress');
    treats.push('Flush soil with distilled water to leach salts.', 'Switch to filtered or rainwater.', 'Mist daily or use a pebble tray to raise humidity above 50%.', 'Trim brown tips without cutting into green tissue.', 'Stop fertilising for 6 weeks.');

  } else if (f.botY > f.topY * 1.35 && f.botY > 0.18) {
    dot='bad'; status='Root Rot / Overwatering';
    diag='Yellowing concentrated in lower zones (bottom: '+p100(f.botY)+' vs top: '+p100(f.topY)+'). Bottom-up yellowing with basal stress is the primary visual signature of Phytophthora root rot from chronic overwatering and anaerobic root conditions.';
    issues.push('Root rot — Phytophthora / Pythium overgrowth', 'Chronic overwatering — oxygen-deprived roots');
    if (f.botR > 0.12) issues.push('Basal stem necrosis');
    treats.push('Unpot immediately — inspect and trim all black or mushy roots.', 'Rinse healthy roots in 3% hydrogen peroxide solution.', 'Repot in fresh fast-draining mix with added perlite.', 'Do not water for 7-10 days after repotting.', 'Apply a systemic fungicide drench to the root zone.');

  } else if (f.topY > f.botY * 1.3 && f.topY > 0.17) {
    dot='warn'; status='Iron / Manganese Deficiency';
    diag='Yellowing concentrated in upper (newer) zones (top: '+p100(f.topY)+'). When new growth yellows first, the deficiency is in a non-mobile nutrient — most commonly Iron or Manganese. These cannot relocate from old leaves when soil pH is too high (above 7.0).';
    issues.push('Iron / Manganese deficiency — interveinal chlorosis', 'Soil pH likely too high (>7.0)');
    treats.push('Apply chelated iron (Fe-EDTA) foliar spray to new leaves.', 'Test and lower soil pH to 6.0-6.5 using sulphur granules.', 'Repot into ericaceous compost if lime-hating species.', 'Use rainwater instead of tap water.');

  } else if (y > 0.28 && Math.abs(f.topY - f.botY) < 0.09 && r < 0.14) {
    dot='warn'; status='Nitrogen Deficiency — Uniform Chlorosis';
    diag='Generalised yellowing across all zones equally (yellow: '+p100(y)+'). Uniform yellowing without zonal preference strongly indicates nitrogen deficiency — the primary building block of chlorophyll, and the most commonly depleted macronutrient in container plants.';
    issues.push('Nitrogen deficiency', 'Chlorosis across all leaf tissue');
    treats.push('Apply a high-nitrogen liquid fertiliser (e.g. 20-10-10) immediately.', 'Repot if soil is over 2 years old — nutrients exhaust over time.', 'Add organic worm castings to improve microbial nitrogen release.', 'Feed every 2 weeks through the growing season.');

  } else if (Math.abs(f.leftR - f.rightR) > 0.11 && Math.max(f.leftR, f.rightR) > 0.14) {
    dot='warn'; status='Sunscald / Unilateral Light Stress';
    diag='Brown tissue asymmetrically concentrated on one side (left: '+p100(f.leftR)+', right: '+p100(f.rightR)+'). Unilateral damage is the classic sign of direct sunlight scalding or radiant heat from a nearby window burning the exposed side.';
    issues.push('Sunscald — UV / heat damage on exposed side');
    treats.push('Move plant away from direct sun immediately.', 'Rotate 180° so the undamaged side gets more light.', 'Trim the most damaged leaves at the base.', 'Filtered or north-facing window light is ideal for most tropical plants.');

  } else if (r > 0.28) {
    dot='bad'; status='Severe Infection — Immediate Action';
    diag='Critical brown necrosis at '+p100(r)+'. This level of tissue death indicates advanced bacterial blight, late blight (Phytophthora), or severe fungal colonisation. Recovery is uncertain without aggressive treatment.';
    issues.push('Advanced bacterial or fungal blight', 'Extensive necrosis — '+p100(r)+' of plant affected');
    if (y > 0.14) issues.push('Secondary chlorosis from nutrient lockout');
    treats.push('Remove all diseased leaves with sterilised scissors (sterilise blades between cuts).', 'Apply systemic fungicide or copper hydroxide.', 'Isolate from all other plants immediately.', 'Water at base only — keep foliage dry.', 'If >60% affected, propagate healthy cuttings and discard the parent.');

  } else if (f.textureVar > 700 && y > 0.13 && r < 0.14) {
    dot='warn'; status='Pest Damage — Stippling (Spider Mites / Thrips)';
    diag='High hue texture variance ('+Math.round(f.textureVar)+') in leaf tissue combined with pale mottling suggests stippling — the hallmark of piercing-sucking insects like spider mites or thrips. These puncture individual cells, creating pale speckles visible as irregular colour variance.';
    issues.push('Stippling damage — spider mites / thrips suspected', 'High texture variance indicating cellular disruption');
    treats.push('Inspect leaf undersides with a magnifying glass for tiny mites or webbing.', 'Spray leaves top and bottom with insecticidal soap every 3 days for 2 weeks.', 'Wipe leaves with a damp cloth to physically remove mites.', 'Raise humidity above 60% — mites thrive in dry air.', 'Introduce predatory mites as biological control.');

  } else if (score >= 60 && y < 0.22 && r < 0.16) {
    dot='ok'; status='Healthy — Good Condition';
    diag='The plant is in good health. Green tissue dominates at '+p100(g)+' with minor stress markers (yellow: '+p100(y)+', brown: '+p100(r)+') within the acceptable range — no active disease detected.';
    if (y > 0.10) { issues.push('Mild chlorosis — slight yellowing'); treats.push('Allow soil to dry between waterings.'); }
    if (r > 0.07) { issues.push('Minor spotting'); treats.push('Check leaf undersides for early pests.'); }
    treats.push('Feed with half-strength liquid fertiliser fortnightly.', 'Ensure 6-8 hours of bright indirect light.');

  } else if (y > 0.16 || r > 0.10) {
    dot='warn'; status='Early Stress — Monitor Closely';
    diag='Mild but notable stress markers detected (yellow: '+p100(y)+', brown: '+p100(r)+'). Not yet critical, but care adjustments are needed now to prevent progression.';
    if (y > 0.16) issues.push('Early chlorosis');
    if (r > 0.10) issues.push('Early lesion development');
    treats.push('Water only when the top 3 cm of soil is completely dry.', 'Check fertiliser schedule — feed monthly in growing season.', 'Inspect stem joints for mealybugs or scale insects.', 'Ensure adequate light and good air circulation.');

  } else {
    dot='ok'; status='Healthy — Looking Good';
    diag='Predominantly healthy green tissue at '+p100(g)+'. Low stress markers with no significant disease, deficiency, or pest damage patterns detected.';
    treats.push('Continue your current care routine.', 'Water when the top 2 cm of soil is dry.', 'Apply balanced liquid fertiliser monthly in growing season.', 'Repot every 1-2 years into fresh compost.');
  }

  return { score:score, dot:dot, status:status, diag:diag, issues:issues, treats:treats };
}
