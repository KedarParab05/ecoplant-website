/* EcoPlant AI Chat Widget — chatbot-widget.js
   Self-contained plant AI. No API key. Runs entirely in the browser. */
(function(){
'use strict';

// ── Styles ───────────────────────────────────────────────────────────────────
var CSS=`
#ep-fab{position:fixed;bottom:24px;right:24px;z-index:9998;width:56px;height:56px;border-radius:50%;background:linear-gradient(135deg,#3a7d44,#1c2d1c);border:none;cursor:pointer;box-shadow:0 4px 20px rgba(58,125,68,.40);display:flex;align-items:center;justify-content:center;font-size:24px;transition:.25s;color:#fff}
#ep-fab:hover{transform:scale(1.08);box-shadow:0 6px 28px rgba(58,125,68,.55)}
#ep-chat{position:fixed;bottom:90px;right:24px;z-index:9999;width:360px;max-width:calc(100vw - 32px);background:#fff;border-radius:20px;box-shadow:0 16px 56px rgba(14,26,14,.18);display:none;flex-direction:column;overflow:hidden;font-family:'DM Sans',sans-serif;animation:ep-up .25s ease}
@keyframes ep-up{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}
#ep-head{background:linear-gradient(135deg,#1c2d1c,#3a7d44);padding:16px 18px;display:flex;align-items:center;gap:10px}
.ep-av{width:36px;height:36px;border-radius:50%;background:rgba(255,255,255,.15);display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0}
.ep-title{color:#fff;font-weight:600;font-size:14px}
.ep-sub{color:rgba(255,255,255,.65);font-size:11px}
#ep-close{margin-left:auto;background:none;border:none;color:rgba(255,255,255,.8);cursor:pointer;font-size:20px;line-height:1;padding:0}
#ep-msgs{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:10px;max-height:380px;min-height:200px;background:#faf7f2}
.ep-msg{max-width:82%;padding:10px 13px;border-radius:14px;font-size:13px;line-height:1.6;animation:ep-up .2s ease}
.ep-msg.ep-bot{background:#fff;color:#1c2d1c;border:1px solid #d8e8d8;align-self:flex-start;border-bottom-left-radius:4px}
.ep-msg.ep-usr{background:linear-gradient(135deg,#3a7d44,#2e6b38);color:#fff;align-self:flex-end;border-bottom-right-radius:4px}
.ep-typing{display:flex;gap:4px;align-items:center;padding:10px 14px}
.ep-dot{width:7px;height:7px;border-radius:50%;background:#8aaf8a;animation:ep-blink 1.2s infinite}
.ep-dot:nth-child(2){animation-delay:.2s}.ep-dot:nth-child(3){animation-delay:.4s}
@keyframes ep-blink{0%,80%,100%{opacity:.3}40%{opacity:1}}
.ep-chips{display:flex;flex-wrap:wrap;gap:6px;padding:0 16px 10px}
.ep-chip{background:#edf5ed;border:1px solid #b3cbb3;border-radius:999px;padding:5px 12px;font-size:11.5px;color:#2e4a2e;cursor:pointer;transition:.15s;font-family:'DM Sans',sans-serif}
.ep-chip:hover{background:#d8e8d8}
#ep-form{display:flex;padding:10px 12px;border-top:1px solid #e8e8e8;gap:8px;background:#fff}
#ep-inp{flex:1;border:1.5px solid #d8e8d8;border-radius:999px;padding:9px 14px;font-size:13px;font-family:'DM Sans',sans-serif;outline:none;color:#1c2d1c;background:#faf7f2;transition:.2s}
#ep-inp:focus{border-color:#3a7d44}
#ep-send{width:36px;height:36px;border-radius:50%;background:#3a7d44;border:none;cursor:pointer;color:#fff;font-size:16px;flex-shrink:0;transition:.2s;display:flex;align-items:center;justify-content:center}
#ep-send:hover{background:#2e6b38}
@media(max-width:400px){#ep-chat{width:calc(100vw - 16px);right:8px}}
`;

// ── Plant Knowledge Base ─────────────────────────────────────────────────────
var KB = {
  greeting: {
    keys:['hello','hi','hey','good morning','good afternoon','good evening','howdy','sup','what\'s up','whats up','greetings','namaste'],
    res:['Hello! \uD83C\uDF3F I\'m EcoPlant AI, your personal plant care expert. Ask me anything about plant health, watering, diseases, pests, or care tips!',
         'Hey there! \uD83C\uDF31 I\'m here to help with all your plant questions — from diagnosis to daily care. What can I help you with today?',
         'Hi! \uD83E\uDEA8 Welcome to EcoPlant AI. I can help you diagnose plant diseases, suggest care routines, identify pests, and much more. What\'s on your mind?']
  },
  watering: {
    keys:['water','watering','overwater','underwater','wet','dry','drought','moist','moisture','thirsty','soggy','damp','irrigat','drip','how often','when to water'],
    res:['Most houseplants prefer to dry out slightly between waterings. The best rule: stick your finger 2-3 cm into the soil — if it feels dry, water thoroughly until it drains from the bottom. \uD83D\uDCA7\n\n\u2022 Succulents & cacti: every 2-6 weeks\n\u2022 Tropical plants (monstera, pothos): every 7-10 days\n\u2022 Ferns: every 3-5 days\n\u2022 Snake plant: every 2-4 weeks\n\nAlways check the soil, not just the calendar!',
         'Overwatering is the #1 killer of houseplants! Signs of overwatering include yellow leaves, mushy stems, and soggy soil. Signs of underwatering include crispy brown tips, dry soil pulling away from pot edges, and wilting that doesn\'t recover after watering.\n\n\uD83D\uDCA7 Golden rule: "When in doubt, wait it out" — most plants prefer slightly dry over waterlogged roots.']
  },
  yellow: {
    keys:['yellow','yellowing','pale','chlorosis','pale green','light green','fading','color','colour','discolor'],
    res:['Yellow leaves can have several causes:\n\n\uD83D\uDFE1 \u2022 Overwatering \u2014 most common cause. Soggy roots can\'t absorb nutrients.\n\uD83D\uDFE1 \u2022 Nitrogen deficiency \u2014 especially in older lower leaves first\n\uD83D\uDFE1 \u2022 Iron/Magnesium deficiency \u2014 yellowing between green veins (interveinal chlorosis)\n\uD83D\uDFE1 \u2022 Too little light \u2014 leaves lose chlorophyll\n\uD83D\uDFE1 \u2022 Natural aging \u2014 old lower leaves yellow normally\n\nWhich leaves are yellowing \u2014 old bottom leaves, new top leaves, or all leaves equally?']
  },
  brown: {
    keys:['brown','browning','crispy','dry tips','brown tips','necrosis','dead','scorched','burn','burnt'],
    res:['Brown leaves indicate tissue death \u2014 here are the most common patterns:\n\n\uD83D\uDFE4 \u2022 Brown tips only \u2014 low humidity, salt build-up, or fluoride in tap water\n\uD83D\uDFE4 \u2022 Brown edges \u2014 underwatering or wind/draught stress\n\uD83D\uDFE4 \u2022 Brown spots with yellow rings \u2014 fungal disease (leaf spot)\n\uD83D\uDFE4 \u2022 Brown and mushy \u2014 root rot from overwatering\n\uD83D\uDFE4 \u2022 Uniform brown crispy \u2014 too much direct sun (sunscald)\n\nDescribe the brown areas and I\'ll give you a specific diagnosis!']
  },
  wilting: {
    keys:['wilt','wilting','droop','drooping','limp','flop','collapse','sad','weak','falling'],
    res:['Wilting means your plant is stressed. Here\'s how to diagnose it:\n\n\uD83C\uDF3F Check the soil first:\n\u2022 Soil bone dry \u2192 water immediately and deeply\n\u2022 Soil soggy wet \u2192 root rot (stop watering, check roots)\n\u2022 Soil seems fine \u2192 could be root rot, pests, or disease\n\nIf watering doesn\'t help within 2-4 hours, unpot the plant and check for dark, mushy roots \u2014 that\'s root rot. Trim mushy roots and repot in fresh dry mix.']
  },
  pests: {
    keys:['pest','bug','insect','mite','aphid','mealybug','scale','thrip','gnat','fly','spider','web','white','sticky','crawl','bite','holes'],
    res:['\uD83D\uDC1B Common Plant Pests & How to Fight Them:\n\n\uD83D\uDD78\uFE0F Spider Mites \u2014 tiny dots + webbing on undersides. Fix: neem oil spray, raise humidity.\n\uD83E\uDEB2 Mealybugs \u2014 white fluffy clusters. Fix: wipe with 70% alcohol, neem oil.\n\uD83E\uDEB0 Scale \u2014 brown bumps on stems. Fix: scrape off, treat with insecticidal soap.\n\uD83E\uDEB3 Fungus Gnats \u2014 tiny flies in soil. Fix: let soil dry, use sticky traps.\n\uD83D\uDC1C Aphids \u2014 soft green/black clusters on new growth. Fix: blast with water, insecticidal soap.\n\nFor all pests: isolate the plant immediately and treat every 5 days for 3 weeks.']
  },
  fungal: {
    keys:['fungus','mold','mould','rot','disease','blight','spot','rust','powdery','mildewy','mildew','infected','infection','leaf spot'],
    res:['\uD83C\uDF44 Fungal diseases are common in humid conditions:\n\n\u2022 Powdery Mildew \u2014 white powder on leaves. Fix: improve airflow, apply baking soda solution.\n\u2022 Leaf Spot (Septoria) \u2014 brown spots with yellow halos. Fix: remove affected leaves, copper fungicide.\n\u2022 Root Rot (Phytophthora) \u2014 wilting despite wet soil. Fix: repot, trim mushy roots, hydrogen peroxide drench.\n\u2022 Botrytis (Grey Mould) \u2014 fuzzy grey coating. Fix: remove affected parts, reduce humidity.\n\n\uD83D\uDCA1 Prevention: avoid wetting leaves, improve airflow, don\'t overwater.']
  },
  rootrot: {
    keys:['root rot','rotting root','root','mushy','black root','soggy root','smelly soil','rotten'],
    res:['Root rot is serious but often treatable if caught early!\n\n\uD83D\uDD34 Signs: wilting despite wet soil, yellow leaves, mushy dark stems, foul smell from soil.\n\n\u2705 Treatment steps:\n1. Unpot the plant immediately\n2. Rinse roots under running water\n3. Trim ALL black or mushy roots with sterilised scissors\n4. Soak healthy roots in 3% hydrogen peroxide for 5 minutes\n5. Repot in FRESH dry, well-draining mix\n6. Do not water for 7-10 days\n7. Apply systemic fungicide drench\n\nSuccess depends on how much healthy root remains.']
  },
  repot: {
    keys:['repot','repotting','pot','potting','soil','mix','transplant','roots coming out','rootbound','root bound','outgrow'],
    res:['\uD83E\uDEA8 When to repot:\n\u2022 Roots growing from drainage holes\n\u2022 Roots circling the pot surface\n\u2022 Plant wilts very quickly after watering\n\u2022 Soil dries out within 1-2 days\n\u2022 Plant looks too big for the pot\n\n\uD83C\uDF31 How to repot:\n1. Choose a pot 2-5 cm wider (no bigger!)\n2. Use appropriate soil mix for the plant type\n3. Water 1-2 days before repotting\n4. Gently loosen root ball, remove dead roots\n5. Repot and water lightly\n6. Keep in bright indirect light for 2 weeks\n\nBest time: spring or early summer when the plant is actively growing.']
  },
  fertilizer: {
    keys:['fertiliz','fertilis','feed','nutrient','npk','nitrogen','phosphorus','potassium','compost','manure','deficien','hungry','starv'],
    res:['\uD83C\uDF31 Plant Nutrition Guide:\n\n\uD83D\uDFE2 N (Nitrogen) \u2014 leafy green growth. Deficiency = pale/yellow leaves.\n\uD83D\uDFE1 P (Phosphorus) \u2014 roots, flowers, fruit. Deficiency = purple tints.\n\uD83D\uDD34 K (Potassium) \u2014 overall health, disease resistance. Deficiency = brown leaf edges.\n\nGeneral schedule:\n\u2022 Spring/Summer: feed every 2 weeks (growing season)\n\u2022 Autumn/Winter: feed monthly or not at all\n\u2022 Newly repotted plants: wait 6 weeks before feeding\n\u2022 Always water before fertilising \u2014 never feed a dry plant!\n\nUse balanced 20-20-20 for most houseplants.']
  },
  light: {
    keys:['light','sun','sunlight','dark','shade','bright','shadow','window','indoor','outdoor','direct','indirect','lumens','lux'],
    res:['\u2600\uFE0F Light requirements by plant type:\n\n\uD83C\uDF1F Bright indirect: Monstera, Pothos, Peace Lily, Ficus\n\uD83D\uDD06 Medium light: Snake Plant, ZZ Plant, Cast Iron Plant\n\uD83C\uDF1A Low light: Heart-leaf Philodendron, Dracaena, Chinese Evergreen\n\u2600\uFE0F Full sun: Cacti, Succulents, Croton, Bird of Paradise\n\n\uD83D\uDCA1 Signs of too little light: stretching/leaning towards windows, pale leaves, slow growth.\nSigns of too much light: bleached or scorched patches, crispy brown spots.']
  },
  humidity: {
    keys:['humid','humidity','dry air','mist','spray','pebble','tray','tropical','moisture'],
    res:['\uD83D\uDCA7 Humidity guide for houseplants:\n\nMost tropical houseplants prefer 50-70% relative humidity. Here\'s how to boost it:\n\n1. \uD83E\uDEA8 Pebble tray: place plant on tray of wet pebbles (water below pot level)\n2. \uD83E\uDE74 Group plants together \u2014 they create their own microclimate\n3. \uD83D\uDCA8 Small humidifier nearby (most effective)\n4. \uD83D\uDCA7 Mist leaves 2-3x daily (not ideal \u2014 can encourage fungal disease)\n5. \uD83D\uDECF\uFE0F Keep away from radiators and AC vents\n\nPlants that love high humidity: ferns, calathea, orchids, air plants.\nPlants that prefer dry: cacti, succulents, snake plant.']
  },
  monstera: {
    keys:['monstera','swiss cheese','deliciosa','fenestration'],
    res:['\uD83C\uDF3F Monstera Care Guide:\n\n\uD83D\uDCA7 Water: every 7-10 days, let top 2-3 cm dry out\n\u2600\uFE0F Light: bright indirect light (avoid direct sun on leaves)\n\uD83C\uDF21\uFE0F Temp: 18-27\u00b0C, no cold draughts\n\uD83D\uDCA7 Humidity: 60-80% (loves humidity!)\n\uD83E\uDE74 Soil: well-draining, chunky mix with perlite\n\uD83E\uDEA8 Repot: every 1-2 years in spring\n\uD83C\uDF31 Feed: monthly in spring/summer with balanced fertiliser\n\nLeaves not developing splits? \u2192 Not enough light. Give it a brighter spot or move closer to the window.']
  },
  pothos: {
    keys:['pothos','epipremnum','devil\'s ivy','money plant','golden pothos'],
    res:['\uD83C\uDF3F Pothos Care Guide:\n\n\uD83D\uDCA7 Water: every 7-14 days (very forgiving!)\n\u2600\uFE0F Light: low to bright indirect \u2014 tolerates almost any light\n\uD83C\uDF21\uFE0F Temp: 15-29\u00b0C\n\uD83E\uDE74 Soil: any well-draining potting mix\n\uD83C\uDF31 Feed: monthly in spring/summer\n\nCommon problems:\n\u2022 Leggy/small leaves \u2192 needs more light\n\u2022 Yellow leaves \u2192 overwatering\n\u2022 Brown tips \u2192 low humidity or fluoride in tap water\n\nOne of the easiest plants to care for \u2014 great for beginners!']
  },
  snakeplant: {
    keys:['snake plant','sansevieria','dracaena trifasciata','mother in law','sanseveria'],
    res:['\uD83C\uDF3F Snake Plant Care Guide:\n\n\uD83D\uDCA7 Water: every 2-6 weeks (highly drought tolerant!)\n\u2600\uFE0F Light: low to bright indirect \u2014 extremely adaptable\n\uD83C\uDF21\uFE0F Temp: 13-29\u00b0C\n\uD83E\uDE74 Soil: fast-draining cactus or succulent mix\n\uD83C\uDF31 Feed: 2-3 times per year only\n\nThe #1 rule: DO NOT OVERWATER. Root rot is the only thing that easily kills a snake plant.\n\uD83D\uDC4D Perfect beginner plant, tolerates neglect, purifies air, and thrives with minimal care.']
  },
  succulent: {
    keys:['succulent','cactus','cacti','aloe','echeveria','haworthia','jade','sedum'],
    res:['\uD83C\uDF35 Succulent & Cactus Care:\n\n\uD83D\uDCA7 Water: every 2-6 weeks (less in winter!)\n\u2600\uFE0F Light: 6+ hours of direct or very bright indirect sun\n\uD83E\uDE74 Soil: cactus/succulent mix with extra grit or perlite\n\uD83C\uDF21\uFE0F Temp: 10-35\u00b0C (avoid frost)\n\uD83C\uDF31 Feed: once per month in summer only\n\nMost common mistake: overwatering! Always let soil dry completely. Use the "soak and dry" method \u2014 water deeply, then wait until bone dry.\n\uD83C\uDF1E Etiolation (stretching) = not enough light. Move to sunniest spot available.']
  },
  propagate: {
    keys:['propagat','cutting','stem cutting','leaf cutting','division','offshoot','pup','baby plant','multiply','grow more'],
    res:['\uD83C\uDF31 Plant Propagation Methods:\n\n\u2702\uFE0F Stem cuttings (pothos, monstera, philodendron):\n1. Cut below a node (joint) with 1-2 leaves\n2. Remove lower leaves\n3. Root in water or moist soil for 4-8 weeks\n\n\uD83C\uDF43 Leaf cuttings (succulents, snake plant):\n1. Remove a healthy leaf cleanly\n2. Let callous over for 1-2 days\n3. Place on well-draining soil\n4. Mist lightly every few days\n\n\u2702\uFE0F Division (spider plant, peace lily, calathea):\n1. Unpot the plant\n2. Gently separate root clumps\n3. Repot each section individually\n\nBest time to propagate: spring and early summer!']
  },
  diagnosis: {
    keys:['diagnos','what\'s wrong','help my plant','sick plant','dying plant','plant dying','plant is dying','not growing','stunted','problem','issue','something wrong'],
    res:['I can help diagnose your plant! Please describe what you\'re seeing:\n\n\uD83D\uDCA1 Tell me about:\n1. What the leaves look like (color, spots, texture)\n2. Where the problem started (top, bottom, edges, center)\n3. How long it\'s been happening\n4. Your watering frequency\n5. Light conditions\n6. Any recent changes (repotting, moving, new soil)\n\nThe more detail you give, the better I can diagnose it! Or you can use our \uD83D\uDD2C Plant Doctor AI to upload a photo for instant visual analysis.']
  },
  thanks: {
    keys:['thank','thanks','thank you','cheers','appreciate','great','amazing','helpful','perfect','awesome'],
    res:['Happy to help! \uD83C\uDF3F Your plants are lucky to have such an attentive caregiver. Feel free to ask anything else!',
         'Glad I could help! \uD83D\uDC9A Don\'t hesitate to come back if you have more plant questions. Happy growing!',
         'You\'re welcome! \uD83C\uDF31 Remember, happy plants = happy home. Come back anytime!']
  },
  bye: {
    keys:['bye','goodbye','see you','cya','later','take care','farewell','quit','exit','close'],
    res:['Goodbye! \uD83C\uDF3F Take good care of your plants. Feel free to chat anytime!',
         'See you later! \uD83D\uDC9A Happy planting!']
  }
};

// ── Quick-reply chips ────────────────────────────────────────────────────────
var CHIPS_INIT = ['Why are my leaves yellow?','How often should I water?','My plant has brown tips','Identify pests','Monstera care tips'];
var CHIPS_AFTER = ['Tell me more','Repotting guide','Fertiliser tips','How to propagate?','Pest treatment'];

// ── Conversation context ────────────────────────────────────────────────────
var ctx = { lastIntent: null, msgCount: 0 };

// ── Intent detection ─────────────────────────────────────────────────────────
function detectIntent(msg) {
  var m = msg.toLowerCase();
  var best = null, bestScore = 0;
  for (var k in KB) {
    var score = KB[k].keys.filter(function(w){ return m.indexOf(w) !== -1; }).length;
    if (score > bestScore) { bestScore = score; best = k; }
  }
  return bestScore > 0 ? best : null;
}

function getResponse(intent) {
  if (!intent || !KB[intent]) {
    return "I'm not sure about that, but I'm learning! \uD83C\uDF31 Try asking about:\n\u2022 Watering schedules\n\u2022 Yellow or brown leaves\n\u2022 Pest identification\n\u2022 Specific plant care (monstera, pothos, snake plant)\n\u2022 Repotting or propagation\n\nOr use our Plant Doctor AI to upload a photo for visual diagnosis! \uD83D\uDD2C";
  }
  var r = KB[intent].res;
  return r[Math.floor(Math.random() * r.length)];
}

// ── DOM injection ────────────────────────────────────────────────────────────
function inject() {
  var s = document.createElement('style'); s.textContent = CSS; document.head.appendChild(s);

  // FAB button
  var fab = document.createElement('button');
  fab.id = 'ep-fab'; fab.title = 'Chat with Plant AI';
  fab.textContent = '\uD83C\uDF31';
  document.body.appendChild(fab);

  // Chat panel
  var panel = document.createElement('div'); panel.id = 'ep-chat';
  panel.innerHTML = '<div id="ep-head"><div class="ep-av">\uD83E\uDEA8</div><div><div class="ep-title">EcoPlant AI</div><div class="ep-sub">Plant expert \u2022 Always online</div></div><button id="ep-close">&times;</button></div>'
    + '<div id="ep-msgs"></div>'
    + '<div class="ep-chips" id="ep-chips"></div>'
    + '<form id="ep-form"><input id="ep-inp" type="text" placeholder="Ask about your plant..." autocomplete="off"><button type="submit" id="ep-send">&#x27A4;</button></form>';
  document.body.appendChild(panel);

  // Events
  fab.addEventListener('click', toggleChat);
  document.getElementById('ep-close').addEventListener('click', function(){ panel.style.display='none'; });
  document.getElementById('ep-form').addEventListener('submit', function(e){ e.preventDefault(); sendMsg(); });
  document.getElementById('ep-inp').addEventListener('keydown', function(e){ if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendMsg();} });

  // Welcome message
  setTimeout(function(){
    addMsg('bot', 'Hi! \uD83C\uDF31 I\'m EcoPlant AI \u2014 your on-device plant expert. Ask me anything about plant care, diseases, pests, or watering!');
    renderChips(CHIPS_INIT);
  }, 300);

  // Show chat hint after 5 seconds if user hasn't opened it
  setTimeout(function(){
    if(panel.style.display !== 'flex') {
      fab.style.animation = 'ep-up .3s ease';
      fab.title = 'Ask me about your plants!';
    }
  }, 5000);
}

// ── Chat logic ────────────────────────────────────────────────────────────────
var chatOpen = false;
function toggleChat() {
  var panel = document.getElementById('ep-chat');
  chatOpen = !chatOpen;
  panel.style.display = chatOpen ? 'flex' : 'none';
  if (chatOpen) { document.getElementById('ep-inp').focus(); scrollToBottom(); }
}

function addMsg(role, text) {
  var msgs = document.getElementById('ep-msgs');
  var div = document.createElement('div');
  div.className = 'ep-msg ep-' + role;
  // Render newlines
  div.innerHTML = text.replace(/\n/g,'<br>');
  msgs.appendChild(div);
  scrollToBottom();
  return div;
}

function showTyping() {
  var msgs = document.getElementById('ep-msgs');
  var div = document.createElement('div');
  div.className = 'ep-msg ep-bot ep-typing';
  div.innerHTML = '<div class="ep-dot"></div><div class="ep-dot"></div><div class="ep-dot"></div>';
  msgs.appendChild(div);
  scrollToBottom();
  return div;
}

function renderChips(chips) {
  var c = document.getElementById('ep-chips');
  c.innerHTML = '';
  chips.forEach(function(ch){
    var btn = document.createElement('button');
    btn.className = 'ep-chip'; btn.textContent = ch;
    btn.addEventListener('click', function(){ processInput(ch); });
    c.appendChild(btn);
  });
}

function scrollToBottom() {
  var m = document.getElementById('ep-msgs');
  setTimeout(function(){ m.scrollTop = m.scrollHeight; }, 50);
}

function sendMsg() {
  var inp = document.getElementById('ep-inp');
  var text = inp.value.trim();
  if (!text) return;
  inp.value = '';
  processInput(text);
}

function processInput(text) {
  document.getElementById('ep-chips').innerHTML = '';
  addMsg('usr', text);
  var typing = showTyping();
  ctx.msgCount++;

  setTimeout(function(){
    typing.remove();
    var intent = detectIntent(text);
    ctx.lastIntent = intent;
    var response = getResponse(intent);

    // Add Plant Doctor link for diagnosis questions
    if(intent === 'diagnosis' || intent === 'fungal' || intent === 'pests' || intent === 'rootrot') {
      response += '\n\n\uD83D\uDD17 <a href="doctor.html" style="color:#3a7d44;font-weight:600">Open Plant Doctor AI \u2192</a>';
    }

    var msgEl = addMsg('bot', response);
    renderChips(ctx.msgCount % 3 === 0 ? CHIPS_INIT : CHIPS_AFTER);
  }, 800 + Math.random() * 500);
}

// ── Boot ─────────────────────────────────────────────────────────────────────
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', inject);
} else {
  inject();
}

})();
