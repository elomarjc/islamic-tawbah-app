/**
 * frontend/js/static_engine.js
 * Client-Side Islamic Analysis Engine & LocalStorage Persistence for GitHub Pages.
 * Ensures 100% standalone functionality when hosted statically on GitHub Pages
 * without a running Python backend.
 */

const LS_CONFESSIONS_KEY = 'tawbah_static_confessions_v1';
const LS_ACTIONS_KEY = 'tawbah_static_actions_v1';
const LS_JOURNAL_KEY = 'tawbah_static_journal_v1';

let cachedKnowledge = null;

async function loadKnowledgeDatasets() {
  if (cachedKnowledge) return cachedKnowledge;
  try {
    const [quran, hadith, duas, fiqh_rules] = await Promise.all([
      fetch('./knowledge/quran.json').then((r) => r.json()),
      fetch('./knowledge/hadith.json').then((r) => r.json()),
      fetch('./knowledge/duas.json').then((r) => r.json()),
      fetch('./knowledge/fiqh_rules.json').then((r) => r.json()),
    ]);
    cachedKnowledge = { quran, hadith, duas, fiqh_rules };
  } catch {
    cachedKnowledge = { quran: [], hadith: [], duas: [], fiqh_rules: [] };
  }
  return cachedKnowledge;
}

function readJsonStorage(key, fallback = []) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function writeJsonStorage(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {}
}

function splitIntoIncidents(rawText) {
  const cleaned = String(rawText || '').trim();
  if (!cleaned) return [];

  // Check for temporal / discourse markers ("Senere", "Dernæst", "Derudover", "Desuden", "Og så")
  const splitRegex = /\.\s+(?=(?:Senere|Dernæst|Derudover|Desuden|Efterfølgende|Samtidig|Og så)\b)/i;
  const parts = cleaned
    .split(splitRegex)
    .map((s) => s.trim())
    .filter((s) => s.length > 5);

  return parts.length > 1 ? parts : [cleaned];
}

function classifySingleIncident(text, idx) {
  const t = text.toLowerCase();
  const id = `inc_${idx + 1}`;

  // 1. Disrespect / insulting mother or parents
  if (/\b(mor|moder|moderen|forældre)\b/.test(t) && /\b(respektløs|grin|råbte|sur|sårende|fornærm|skældte|hævede stemmen|vægt)\b/.test(t)) {
    return {
      scenario: 'mother',
      incident_id: id,
      incident_title: 'Respektløs tale og krænkelse af moderen (Uquq al-Walidayn)',
      sin_classification: 'both',
      description: text,
      affected_parties: ['Moderen'],
      allah_rights: [
        'Overtrædelse af Allahs befaling i Koranen (17:23) om at vise forældre den højeste godhed og aldrig tale hårdt til dem.',
      ],
      people_rights: [
        'Krænkelse af moderens ære, værdighed og følelsesmæssige ret til respekt og omsorg (Birr al-Walidayn).',
      ],
      apology_guidance:
        'Du skal henvende dig direkte og ydmygt til din mor, anerkende din fejl uden undskyldninger og bede om hendes tilgivelse. Vis hende ekstra venlighed og tjen hende med tålmodighed.',
      restitution_guidance:
        'Ingen økonomisk gæld i selve den verbale krænkelse, men følelsesmæssig genopretning gennem god opførsel, gaver og oprigtig omsorg er påkrævet.',
      required_actions: [
        {
          id: `${id}_req_1`,
          category: 'wajib',
          title: 'Foretag oprigtig Tawbah til Allah',
          description: 'Stop den respektløse adfærd, føl dyb fortrydelse i hjertet (Nadam) og beslut aldrig at gentage det.',
          explanation: 'Ulydighed og respektløshed mod forældre er blandt de store synder (Kaba’ir) i Islam.',
          completed: false,
        },
        {
          id: `${id}_req_2`,
          category: 'wajib',
          title: 'Bed din mor om tilgivelse med ydmyghed',
          description: 'Gå til din mor, undskyld oprigtigt for dine ord og søg hendes tilfredshed (Rida al-Walidayn).',
          explanation: 'Moderens ret er en menneskelig ret (Huqooq al-Ibad), som kræver hendes tilgivelse.',
          completed: false,
        },
      ],
      recommended_actions: [
        {
          id: `${id}_rec_1`,
          category: 'mustahabb',
          title: 'Lav dua for dine forældre ("Rabbi irhamhuma...")',
          description: 'Bed Allah om at vise dine forældre barmhjertighed, ligesom de opfostrede dig da du var lille (Surah Al-Isra 17:24).',
          explanation: 'Styrker hjertets ydmyghed og genopbygger båndet til forældrene.',
          completed: false,
        },
      ],
      quran_keys: ['Al-Isra', 'Az-Zumar'],
      hadith_nums: ['5971', '2449'],
    };
  }

  // 2. Stealing from father or taking money
  if (/\b(far|fader|faderen)\b/.test(t) && /\b(stjal|stjålet|tog|penge|kroner|kr|pung)\b/.test(t)) {
    const amountMatch = text.match(/(\d+(?:[.,]\d+)?)\s*(?:kroner|kr)/i);
    const amountStr = amountMatch ? `${amountMatch[1]} kroner` : 'det stjålne beløb';
    return {
      scenario: 'father_theft',
      incident_id: id,
      incident_title: `Uretmæssig tilegnelse af penge fra faderen (${amountStr})`,
      sin_classification: 'both',
      description: text,
      affected_parties: ['Faderen'],
      allah_rights: [
        'Overtrædelse af Allahs forbud mod tyveri og uretmæssig tilegnelse af andres ejendom.',
      ],
      people_rights: [
        `Krænkelse af faderens ejendomsret (${amountStr}) samt brud på familiens tillid.`,
      ],
      apology_guidance:
        'Hvis du kan fortælle din far sandheden og bede om hans tilgivelse uden at det skaber alvorlig familiekonflikt (fitnah), bør du gøre det. Hvis direkte bekendelse vil skade familierelationen alvorligt, tillader lærde at pengene lægges tilbage diskret.',
      restitution_guidance:
        `Det er obligatorisk (Wajib) at tilbagelevere ${amountStr} fuldt ud til din far (Radd al-Mazalim) — enten direkte eller ved diskret at lægge pengene tilbage i hans pung eller overføre dem til ham. At sige "Astaghfirullah" alene sletter ikke en økonomisk gæld.`,
      required_actions: [
        {
          id: `${id}_req_1`,
          category: 'wajib',
          title: `Tilbagelever ${amountStr} til din far`,
          description: `Sørg for at din far får sine ${amountStr} tilbage (direkte eller diskret i hans pung/konto).`,
          explanation: 'Menneskers økonomiske rettigheder bortfalder ikke uden tilbagelevering eller eftergivelse.',
          completed: false,
        },
        {
          id: `${id}_req_2`,
          category: 'wajib',
          title: 'Angr oprigtigt over for Allah (Tawbah)',
          description: 'Fortryd handlingen dybt og beslut aldrig at tage noget uden tilladelse igen.',
          explanation: 'Tyveri fra forældre krænker både ejendomsretten og pligten til Birr al-Walidayn.',
          completed: false,
        },
      ],
      recommended_actions: [
        {
          id: `${id}_rec_1`,
          category: 'mustahabb',
          title: 'Giv en gave eller vis ekstra hjælpsomhed over for din far',
          description: 'Følg en dårlig handling op med en god gerning, som udvisker den.',
          explanation: 'Anbefalet i Sunnah for at styrke kærligheden til forældrene.',
          completed: false,
        },
      ],
      quran_keys: ['An-Nisa', 'Al-Isra'],
      hadith_nums: ['2449'],
    };
  }

  // 3. Backbiting (Ghibah)
  if (/\b(bagtal|bagtalte|ghibah|sladrede|snakkede grimt om)\b/.test(t)) {
    return {
      scenario: 'backbiting',
      incident_id: id,
      incident_title: 'Bagtalelse (Ghibah) af en bror/søster eller kollega',
      sin_classification: 'both',
      description: text,
      affected_parties: ['Den bagtalte person'],
      allah_rights: [
        'Overtrædelse af Allahs udtrykkelige forbud mod bagtalelse i Surah Al-Hujurat (49:12).',
      ],
      people_rights: [
        'Krænkelse af den omtalte persons ære og omdømme i vedkommendes fravær.',
      ],
      apology_guidance:
        'Lærdes nuancerede vejledning: Hvis personen allerede ved, at du har bagtalt vedkommende, skal du bede om personlig tilgivelse. Hvis personen IKKE ved det, og det at fortælle det vil skabe fjendskab, sårede følelser eller større splid (fitnah), skal du IKKE informere vedkommende om detaljerne — men i stedet tale godt om personen samme sted og lave oprigtig dua for vedkommende (Ibn Taymiyyah & Ibn al-Qayyim).',
      restitution_guidance:
        'Genopret personens ære i den forsamling, hvor bagtalelsen fandt sted, ved at fremhæve personens gode sider og bede Allah om at tilgive og velsigne vedkommende.',
      scholarly_disagreement:
        'Der er klassisk meningsforskel (Ikhtilaf) blandt Ahlus-Sunnah lærde om, hvorvidt man altid skal informere den bagtalte. Flertallet af verifikationslærde (herunder Ibn Taymiyyah og Ibn al-Qayyim) fastslår, at hvis oplysning forårsager større skade (fitnah), må man ikke oplyse det, men skal nøjes med dua, istighfar og ros af personen.',
      required_actions: [
        {
          id: `${id}_req_1`,
          category: 'wajib',
          title: 'Stop bagtalelsen og foretag oprigtig Tawbah til Allah',
          description: 'Angr i hjertet og vogt tungen mod fremtidig bagtalelse.',
          explanation: 'Koranen sammenligner bagtalelse med at spise sin døde brors kød (49:12).',
          completed: false,
        },
        {
          id: `${id}_req_2`,
          category: 'wajib',
          title: 'Lav oprigtig dua for personen og omtal vedkommende godt',
          description: 'Bed Allah om tilgivelse og velsignelse for den person, du omtalte, og ros vedkommende i samme kreds.',
          explanation: 'Genopretter personens ære uden at skabe ny splid (fitnah).',
          completed: false,
        },
      ],
      recommended_actions: [
        {
          id: `${id}_rec_1`,
          category: 'mustahabb',
          title: 'Forsvar andres ære, når nogen bagtaler i dit nærvær',
          description: 'Skift emne eller forsvar din bror/søster, når andre taler dårligt om dem.',
          explanation: 'Profeten ﷺ lovede beskyttelse mod Helvedes ild for den, der forsvarer sin brors ære.',
          completed: false,
        },
      ],
      quran_keys: ['Al-Hujurat', 'Az-Zumar'],
      hadith_nums: ['2589', '2449'],
    };
  }

  // 4. Missing Fajr or obligatory prayer
  if (/\b(fajr|bøn|bønnen|salah|sov over)\b/.test(t)) {
    return {
      scenario: 'prayer',
      incident_id: id,
      incident_title: 'Forsømmelse af obligatorisk bøn (Fajr / Salah)',
      sin_classification: 'huqooq_allah',
      description: text,
      affected_parties: [],
      allah_rights: [
        'Forsømmelse af den obligatoriske bøn på dens fastsatte tidspunkt (Surah An-Nisa 4:103 & Surah Maryam 19:59).',
      ],
      people_rights: [],
      apology_guidance:
        'Denne synd vedrører udelukkende Allahs rettigheder (Huqooq Allah). Du skal ikke bekende eller undskylde over for andre mennesker.',
      restitution_guidance:
        'Ifølge de fire sunni-lovskoler (Hanafi, Maliki, Shafi’i og Hanbali) er det obligatorisk straks at indhente den forsømte bøn (Qada) sammen med oprigtig Tawbah.',
      scholarly_disagreement:
        'De fire klassiske lovskoler fastslår, at en forsømt obligatorisk bøn skal bedes som Qada med det samme. En mindre gruppe lærde (bl.a. Ibn Taymiyyah) mente, at en bevidst udeladt bøn ikke kan indhentes som Qada, men kræver angrende Tawbah og mange frivillige Sunnah-bønner (Nawafil). At bede Qada med det samme samt øge frivillige bønner opfylder begge hensyn.',
      required_actions: [
        {
          id: `${id}_req_1`,
          category: 'wajib',
          title: 'Bed den forsømte bøn (Qada) med det samme',
          description: 'Udfør wudu og bed den manglende Fajr-bøn straks.',
          explanation: 'Profeten ﷺ sagde: "Den der glemmer en bøn eller sover fra den, dets soning er at bede den, når han husker den" (Sahih Muslim 684).',
          completed: false,
        },
        {
          id: `${id}_req_2`,
          category: 'wajib',
          title: 'Foretag oprigtig Tawbah og tag praktiske forholdsregler',
          description: 'Angr forsømmelsen, sæt flere alarmer og gå tidligt i seng med intention om at vågne til Fajr.',
          explanation: 'Fast beslutning (Al-Azm) indebærer at fjerne årsagerne til forsømmelsen.',
          completed: false,
        },
      ],
      recommended_actions: [
        {
          id: `${id}_rec_1`,
          category: 'mustahabb',
          title: 'Bed ekstra frivillige Sunnah-bønner (Rawatib)',
          description: 'Styrk dine daglige obligatoriske bønner med Sunnah-bønnerne før og efter.',
          explanation: 'Frivillige bønner udfylder mangler i de obligatoriske bønner på Dommedagen.',
          completed: false,
        },
      ],
      quran_keys: ['Maryam', 'Az-Zumar'],
      hadith_nums: ['684'],
    };
  }

  // 8. Private sin (Al-Sitr)
  if (/\b(privat synd|skjulte|alene om natten|mellem mig og allah|ingen andre kender)\b/.test(t)) {
    return {
      scenario: 'private_sin',
      incident_id: id,
      incident_title: 'Privat synd mellem tjeneren og Allah (Pligt til Al-Sitr)',
      sin_classification: 'huqooq_allah',
      description: text,
      affected_parties: [],
      allah_rights: ['Overtrædelse af Allahs grænser i det skjulte.'],
      people_rights: [],
      apology_guidance:
        'VIGTIGT (Al-Sitr): Da denne synd udelukkende er mellem dig og Allah og ikke har skadet andre mennesker, er det i Islam forbudt at afsløre eller bekende den over for andre mennesker (heller ikke ægtefælle, forældre eller venner). Bevar Allahs slør (Sitr) over dig selv og angre alene over for Allah.',
      restitution_guidance:
        'Ingen økonomisk eller menneskelig genopretning er påkrævet. Sagen renses udelukkende gennem oprigtig Tawbah til Allah og gode gerninger.',
      required_actions: [
        {
          id: `${id}_req_1`,
          category: 'wajib',
          title: 'Stop synden, fortryd i hjertet og beslut aldrig at vende tilbage',
          description: 'Henvend dig direkte til Allah i enerum uden mellemled.',
          explanation: 'Allah elsker den angrende tjener og tilgiver alle synder for den, der vender om.',
          completed: false,
        },
        {
          id: `${id}_req_2`,
          category: 'wajib',
          title: 'Bevar synden skjult (Al-Sitr) — fortæl den ikke til nogen',
          description: 'Afslør ikke det, som Allah har dækket over for dig.',
          explanation: 'Profeten ﷺ sagde: "Hele min Ummah vil blive tilgivet undtagen dem, der offentliggør deres synder (al-mujahirun)" (Bukhari 6069).',
          completed: false,
        },
      ],
      recommended_actions: [
        {
          id: `${id}_rec_1`,
          category: 'mustahabb',
          title: 'Udfør wudu og bed 2 rak’ah Tawbah-bøn (Salat al-Tawbah)',
          description: 'Bed to frivillige rak’ah og bed Allah om tilgivelse i sujud.',
          explanation: 'Autentisk praksis berettet fra Abu Bakr as-Siddiq (må Allah være tilfreds med ham).',
          completed: false,
        },
      ],
      quran_keys: ['Az-Zumar', 'Ali \'Imran'],
      hadith_nums: ['6069', '2758'],
    };
  }

  // 9. False accusation / Slander (Buhtan)
  if (/\b(falsk anklage|falsk rygte|buhtan|beskyldte|løgn om en bekendt)\b/.test(t)) {
    return {
      scenario: 'slander',
      incident_id: id,
      incident_title: 'Falsk anklage og bagvaskelse (Buhtan)',
      sin_classification: 'both',
      description: text,
      affected_parties: ['Den falsk anklagede person', 'Modtagerne af den falske oplysning'],
      allah_rights: [
        'Overtrædelse af Allahs strenge forbud mod falsk anklage og løgn (Surah An-Nur 24:19 & Al-Ahzab 33:58).',
      ],
      people_rights: [
        'Alvorlig krænkelse af en uskyldig persons ære og omdømme gennem usandheder.',
      ],
      apology_guidance:
        'Ved falsk anklage (Buhtan) er det obligatorisk at trække den falske påstand tilbage over for dem, der hørte eller læste den, så offerets navn og ære renses fuldstændigt, samt at bede offeret om tilgivelse.',
      restitution_guidance:
        'Korriger de falske oplysninger i præcis det forum (f.eks. gruppechat eller vennekreds), hvor løgnen blev spredt.',
      required_actions: [
        {
          id: `${id}_req_1`,
          category: 'wajib',
          title: 'Træk den falske anklage tilbage og rens personens navn',
          description: 'Informer dem, der hørte rygtet, om at oplysningen var usand, og at personen er uskyldig.',
          explanation: 'Tawbah for spredning af falske beskyldninger kræver offentlig korrektion af løgnen (Surah Al-Baqarah 2:160).',
          completed: false,
        },
        {
          id: `${id}_req_2`,
          category: 'wajib',
          title: 'Bed den forurettede person om tilgivelse og angre over for Allah',
          description: 'Søg personens eftergivelse for den skade, anklagen har forvoldt.',
          explanation: 'Buhtan er en af de alvorligste krænkelser af Huqooq al-Ibad.',
          completed: false,
        },
      ],
      recommended_actions: [
        {
          id: `${id}_rec_1`,
          category: 'mustahabb',
          title: 'Giv Sadaqah og lav dua for den forurettede',
          description: 'Bed Allah om at belønne og ophøje den person, hvis ære blev krænket.',
          explanation: 'Hjælper med at opveje uretten.',
          completed: false,
        },
      ],
      quran_keys: ['Al-Hujurat', 'Az-Zumar'],
      hadith_nums: ['2589', '2449'],
    };
  }

  // Default / General interpersonal or financial wrongdoing (spouse, neighbor, trust, restitution)
  return {
    scenario: 'general_both',
    incident_id: id,
    incident_title: 'Krænkelse af islamiske forpligtelser og medmenneskers rettigheder',
    sin_classification: 'both',
    description: text,
    affected_parties: ['Den forurettede part'],
    allah_rights: [
      'Overtrædelse af Allahs påbud om sandfærdighed, tillid (Amanah) og respekt for andres ejendom og rettigheder.',
    ],
    people_rights: [
      'Krænkelse af et andet menneskes tillid, ejendom eller ret til ærlig behandling.',
    ],
    apology_guidance:
      'Når et andet menneskes ret er krænket, skal uretten genoprettes. Hvis det drejer sig om løgn eller tillidsbrud i nære relationer (f.eks. ægtefælle), bør du rette op på sandheden og bede om tilgivelse på en klog og hensynsfuld måde.',
    restitution_guidance:
      'Hvis der er tale om penge, betroede midler (Amanah) eller skade på ejendom (f.eks. nabo eller kollega), er det obligatorisk at tilbagelevere beløbet eller erstatte skaden fuldt ud. Dette kan gøres direkte eller anonymt, hvis direkte konfrontation skaber alvorlig skade (fitnah).',
    required_actions: [
      {
        id: `${id}_req_1`,
        category: 'wajib',
        title: 'Foretag oprigtig Tawbah til Allah (Ophør, Anger, Fast beslutning)',
        description: 'Stop handlingen øjeblikkeligt, fortryd oprigtigt i hjertet og beslut ikke at vende tilbage til den.',
        explanation: 'De første tre grundbetingelser for enhver gyldig Tawbah.',
        completed: false,
      },
      {
        id: `${id}_req_2`,
        category: 'wajib',
        title: 'Genopret den krænkede parts ret (Tilbagelevering / Erstatning / Undskyldning)',
        description: 'Lever eventuelle penge/værdier tilbage (direkte eller anonymt), erstat skade eller bed om tilgivelse.',
        explanation: 'Den fjerde betingelse for Tawbah, når menneskers rettigheder (Huqooq al-Ibad) er involveret.',
        completed: false,
      },
    ],
    recommended_actions: [
      {
        id: `${id}_rec_1`,
        category: 'mustahabb',
        title: 'Reciter Sayyid al-Istighfar og giv frivillig velgørenhed (Sadaqah)',
        description: 'Søg Allahs tilgivelse morgen og aften og følg fejlen op med gode gerninger.',
        explanation: 'Gode gerninger bortvisker dårlige gerninger (Koranen 11:114).',
        completed: false,
      },
    ],
    quran_keys: ['An-Nisa', 'Az-Zumar'],
    hadith_nums: ['2449', '6094'],
  };
}

export const StaticEngine = {
  async analyzeConfession(rawText, rawInputType = 'text', transcript = null) {
    const kb = await loadKnowledgeDatasets();
    const segments = splitIntoIncidents(rawText);
    const incidents = segments.map((seg, i) => classifySingleIncident(seg, i));

    const classifications = new Set(incidents.map((x) => x.sin_classification));
    let overallClass = 'both';
    if (classifications.size === 1) {
      overallClass = [...classifications][0];
    }

    const affectedParties = [...new Set(incidents.flatMap((x) => x.affected_parties))];
    const allahRights = [...new Set(incidents.flatMap((x) => x.allah_rights))];
    const peopleRights = [...new Set(incidents.flatMap((x) => x.people_rights))];
    const requiredActions = incidents.flatMap((x) => x.required_actions);
    const recommendedActions = incidents.flatMap((x) => x.recommended_actions);

    const apologyGuidance = incidents
      .map((x) => x.apology_guidance)
      .filter(Boolean)
      .join(' ');
    const restitutionGuidance = incidents
      .map((x) => x.restitution_guidance)
      .filter(Boolean)
      .join(' ');
    const scholarlyDisagreement =
      incidents
        .map((x) => x.scholarly_disagreement)
        .filter(Boolean)
        .join(' ') ||
      'Ahlus-Sunnah wal-Jama’ah lærde er enige om de 4 grundbetingelser for Tawbah. Ved tilbagelevering af penge og undskyldning for bagtalelse tages der hensyn til, om direkte konfrontation vil udløse større skade (fitnah), hvorfor anonym tilbagelevering eller dua for offeret i visse tilfælde er tilladt.';

    // Match verified Quran references from curated JSON
    const wantedSurahs = new Set(incidents.flatMap((x) => x.quran_keys || ['Az-Zumar']));
    const quranRefs = (kb.quran || [])
      .filter((q) => wantedSurahs.has(q.surah) || q.surah === 'Az-Zumar')
      .slice(0, 3)
      .map((q) => ({
        surah: q.surah,
        ayah: Number(q.ayah),
        arabic_text: q.arabic_text,
        danish_translation: q.danish_translation || q.translation_da,
        explanation: q.explanation || q.relevance,
      }));

    // Match verified Hadith references from curated JSON
    const wantedHadiths = new Set(incidents.flatMap((x) => x.hadith_nums || ['2449']));
    const hadithRefs = (kb.hadith || [])
      .filter((h) => wantedHadiths.has(String(h.hadith_number)))
      .slice(0, 3)
      .map((h) => ({
        collection: h.collection,
        hadith_number: String(h.hadith_number),
        authenticity_grading: h.authenticity_grading || h.grade || 'Sahih',
        arabic_text: h.arabic_text,
        danish_translation: h.danish_translation || h.translation_da,
        explanation: h.explanation || h.relevance,
      }));

    const recommendedDuas = (kb.duas || []).slice(0, 2).map((d) => ({
      title: d.title,
      arabic_text: d.arabic_text,
      transliteration: d.transliteration || '',
      danish_translation: d.danish_translation || d.translation_da,
      source: d.source,
      context: d.context || d.when_to_recite || '',
    }));

    const confessionId = `conf_${Date.now()}`;
    const nowIso = new Date().toISOString();

    const result = {
      confession_id: confessionId,
      created_at: nowIso,
      raw_input_type: rawInputType,
      transcript: transcript || undefined,
      offline_mode: true,
      demonstration_mode: rawInputType === 'voice' && !transcript,
      incident_summary:
        incidents.length > 1
          ? `Din bekendelse indeholder ${incidents.length} særskilte hændelser, som hver kræver sin egen islamiske håndtering.`
          : `Din bekendelse er blevet analyseret ud fra Koranen og autentisk Sunnah (${incidents[0].incident_title}).`,
      incidents,
      sin_classification: overallClass,
      allah_rights: allahRights,
      people_rights: peopleRights,
      affected_parties: affectedParties,
      severity_explanation:
        overallClass === 'huqooq_allah'
          ? 'Denne handling vedrører forholdet mellem dig og Allah (Huqooq Allah). Tilgivelse opnås gennem oprigtig anger (Nadam), øjeblikkeligt ophør (Iqla’), fast beslutning om ikke at vende tilbage (Azm) samt indhentning af eventuelle forsømte pligter (Qada). Bevar synden skjult (Al-Sitr).'
          : 'Denne handling berører både Allahs lov og et andet menneskes rettigheder (Huqooq al-Ibad). Ud over oprigtig Tawbah over for Allah kræver fuld tilgivelse, at den uret, der er begået mod den anden person, genoprettes gennem tilbagelevering af værdier, erstatning eller undskyldning.',
      required_actions: requiredActions,
      recommended_actions: recommendedActions,
      apology_guidance: apologyGuidance,
      restitution_guidance: restitutionGuidance,
      quran_references: quranRefs,
      hadith_references: hadithRefs,
      recommended_duas: recommendedDuas,
      scholarly_disagreement: scholarlyDisagreement,
      confidence_level: 'high',
      scholar_consultation_required: /\b(vold|trussel|misbrug|kriminel|underslæb)\b/i.test(rawText),
      final_reminder:
        'Husk at ingen synd er for stor til at Allah kan tilgive den, når du vender oprigtigt tilbage til Ham, og at ethvert skridt du tager for at gøre uret god igen over for andre mennesker, løfter din rang hos Allah. Mist aldrig håbet om Allahs uendelige barmhjertighed (Koranen 39:53).',
    };

    // Persist in localStorage
    const allConfs = readJsonStorage(LS_CONFESSIONS_KEY, []);
    allConfs.unshift({
      id: confessionId,
      raw_input_type: rawInputType,
      raw_text: rawText,
      summary: result.incident_summary,
      sin_classification: result.sin_classification,
      confidence_level: result.confidence_level,
      scholar_consultation_required: result.scholar_consultation_required,
      created_at: nowIso,
      status: 'completed',
      analysis_json: result,
    });
    writeJsonStorage(LS_CONFESSIONS_KEY, allConfs);

    const allActs = readJsonStorage(LS_ACTIONS_KEY, []);
    for (const act of [...requiredActions, ...recommendedActions]) {
      allActs.unshift({
        ...act,
        id: `${confessionId}_${act.id}`,
        short_id: act.id,
        confession_id: confessionId,
        created_at: nowIso,
      });
    }
    writeJsonStorage(LS_ACTIONS_KEY, allActs);

    return result;
  },

  getConfessions() {
    return readJsonStorage(LS_CONFESSIONS_KEY, []).map((c) => ({
      id: c.id,
      raw_input_type: c.raw_input_type,
      raw_text: c.raw_text,
      summary: c.summary,
      sin_classification: c.sin_classification,
      confidence_level: c.confidence_level,
      scholar_consultation_required: c.scholar_consultation_required,
      created_at: c.created_at,
      status: c.status,
    }));
  },

  getConfessionById(confessionId) {
    const found = readJsonStorage(LS_CONFESSIONS_KEY, []).find((c) => c.id === confessionId);
    if (!found) throw new Error('Bekendelse ikke fundet.');
    const actions = readJsonStorage(LS_ACTIONS_KEY, []).filter((a) => a.confession_id === confessionId);
    const map = {};
    actions.forEach((a) => {
      map[a.id] = Boolean(a.completed);
      if (a.short_id) map[a.short_id] = Boolean(a.completed);
    });
    const data = { ...found.analysis_json };
    for (const k of ['required_actions', 'recommended_actions']) {
      for (const act of data[k] || []) {
        if (act.id in map) act.completed = map[act.id];
      }
    }
    return data;
  },

  deleteConfession(confessionId) {
    const confs = readJsonStorage(LS_CONFESSIONS_KEY, []).filter((c) => c.id !== confessionId);
    const acts = readJsonStorage(LS_ACTIONS_KEY, []).filter((a) => a.confession_id !== confessionId);
    writeJsonStorage(LS_CONFESSIONS_KEY, confs);
    writeJsonStorage(LS_ACTIONS_KEY, acts);
    return { status: 'ok' };
  },

  getActions() {
    return readJsonStorage(LS_ACTIONS_KEY, []);
  },

  toggleAction(actionId, completed) {
    const acts = readJsonStorage(LS_ACTIONS_KEY, []);
    for (const a of acts) {
      if (a.id === actionId || a.short_id === actionId || String(a.id).endsWith(`_${actionId}`)) {
        a.completed = Boolean(completed);
      }
    }
    writeJsonStorage(LS_ACTIONS_KEY, acts);
    return { id: actionId, completed: Boolean(completed) };
  },

  getJournal() {
    return readJsonStorage(LS_JOURNAL_KEY, []);
  },

  createJournalEntry(title, reflection, tags = []) {
    const entries = readJsonStorage(LS_JOURNAL_KEY, []);
    const entry = {
      id: `entry_${Date.now()}`,
      title: title || 'Personlig refleksion',
      content: reflection,
      tags,
      created_at: new Date().toISOString(),
    };
    entries.unshift(entry);
    writeJsonStorage(LS_JOURNAL_KEY, entries);
    return entry;
  },

  deleteJournalEntry(entryId) {
    const entries = readJsonStorage(LS_JOURNAL_KEY, []).filter((e) => e.id !== entryId);
    writeJsonStorage(LS_JOURNAL_KEY, entries);
    return { status: 'ok' };
  },

  getDashboardSummary() {
    const confs = readJsonStorage(LS_CONFESSIONS_KEY, []);
    const acts = readJsonStorage(LS_ACTIONS_KEY, []);
    const journal = readJsonStorage(LS_JOURNAL_KEY, []);
    return {
      total_confessions: confs.length,
      completed_actions: acts.filter((a) => a.completed).length,
      pending_actions: acts.filter((a) => !a.completed).length,
      journal_entries: journal.length,
    };
  },

  async getKnowledgeBase(query = '', category = '') {
    const kb = await loadKnowledgeDatasets();
    const q = String(query || '').trim().toLowerCase();
    const cat = String(category || '').trim().toLowerCase();

    const matches = (item) => {
      const blob = JSON.stringify(item).toLowerCase();
      if (q && !blob.includes(q)) return false;
      if (cat && cat !== 'all' && !blob.includes(cat)) return false;
      return true;
    };

    return {
      quran: (kb.quran || []).filter(matches),
      hadith: (kb.hadith || []).filter(matches),
      duas: (kb.duas || []).filter(matches),
      fiqh_rules: (kb.fiqh_rules || []).filter(matches),
    };
  },

  wipeAccountData() {
    localStorage.removeItem(LS_CONFESSIONS_KEY);
    localStorage.removeItem(LS_ACTIONS_KEY);
    localStorage.removeItem(LS_JOURNAL_KEY);
    return { status: 'ok' };
  },
};
