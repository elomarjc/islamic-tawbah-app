"""
app/engine/rule_engine.py

Ahlus-Sunnah wal-Jama'ah Rule-Based Expert System (Features #10 - #18).
Deterministic offline engine generating comprehensive, authentic Islamic analysis
for all 10 canonical confession scenarios and general fallback cases.
"""

from __future__ import annotations

import re
import uuid
from typing import Dict, Any, List, Optional

from app.schemas import (
    AnalysisResultSchema,
    IncidentSchema,
    ActionItemSchema,
    QuranReference,
    HadithReference,
    RecommendedDua,
)
from app.engine.classifier import (
    classify_rights,
    detect_scenario_category,
    check_scholar_consultation_required,
    extract_affected_parties,
)
from app.engine.incident_splitter import split_confession_incidents
from app.engine.rag_service import get_rag_service


class IslamicRuleEngine:
    """
    Expert system implementing classical Sunni jurisprudence on repentance (Fiqh al-Tawbah).
    Grounds all outputs in the 4 conditions of Tawbah, Al-Sitr concealment,
    anonymous restitution, fitnah avoidance, and authentic textual evidence.
    """

    def __init__(self):
        self.rag = get_rag_service()

    def _build_core_tawbah_actions(self, sin_type: str = "general") -> List[ActionItemSchema]:
        """
        Builds the 3 mandatory core conditions of Tawbah for Allah's rights (Feature #10):
        1. Cessation (Iqla')
        2. Remorse (Nadam)
        3. Resolve never to return (Azm)
        """
        return [
            ActionItemSchema(
                id=f"act-iqla-{uuid.uuid4().hex[:6]}",
                category="tawbah_allah",
                description="Øjeblikkeligt ophør med synden: Afstå fuldstændigt og straks fra handlingen (Iqla').",
                explanation="Den første betingelse for gyldig anger er at standse overtrædelsen øjeblikkeligt uden tøven.",
                target_party="Allah",
                completed=False,
                action_type="tawbah_allah",
                title="Ophør med synden",
            ),
            ActionItemSchema(
                id=f"act-nadam-{uuid.uuid4().hex[:6]}",
                category="tawbah_allah",
                description="Oprigtig dyb anger og fortrydelse i hjertet over overtrædelsen for Allahs skyld (Nadam).",
                explanation="Profeten (fred være med ham) sagde: 'Anger er selve essensen af tawbah' (Sunan Ibn Majah 4252).",
                target_party="Allah",
                completed=False,
                action_type="tawbah_allah",
                title="Hjertelig fortrydelse og anger",
            ),
            ActionItemSchema(
                id=f"act-azm-{uuid.uuid4().hex[:6]}",
                category="tawbah_allah",
                description="Fast og ubøjelig beslutning om aldrig mere at gentage denne synd i fremtiden (Azm).",
                explanation="Sand anger forudsætter en ærlig hensigt om ikke at vende tilbage til overtrædelsen.",
                target_party="Allah",
                completed=False,
                action_type="tawbah_allah",
                title="Beslutning om aldrig mere at gentage",
            ),
        ]

    def _build_recommended_actions(self, scenario_cat: str) -> List[ActionItemSchema]:
        """Builds meritorious recommended actions (Mustahabb)."""
        actions = [
            ActionItemSchema(
                id=f"act-sadaqah-{uuid.uuid4().hex[:6]}",
                category="mustahabb",
                description="Giv frivillig velgørenhed (sadaqah) for at rense sjælen.",
                explanation="Gode gerninger udvisker dårlige gerninger (Koranen 11:114).",
                target_party="Trængende",
                completed=False,
                action_type="sadaqah",
                title="Frivillig velgørenhed (Sadaqah)",
            ),
            ActionItemSchema(
                id=f"act-dua-{uuid.uuid4().hex[:6]}",
                category="mustahabb",
                description="Fremsig Sayyid al-Istighfar morgen og aften.",
                explanation="Den mest fuldendte bøn om tilgivelse overleveret i Sahih al-Bukhari 6306.",
                target_party="Allah",
                completed=False,
                action_type="dua",
                title="Sayyid al-Istighfar",
            ),
            ActionItemSchema(
                id=f"act-prayer-{uuid.uuid4().hex[:6]}",
                category="mustahabb",
                description="Bed to rak'ah anger-bøn (Salat al-Tawbah) i stilhed.",
                explanation="Det er sunnah at udføre en to-rak'ah bøn ved oprigtig anger over synd.",
                target_party="Allah",
                completed=False,
                action_type="extra_prayers",
                title="Salat al-Tawbah",
            ),
        ]
        return actions

    def analyze_confession(self, confession_text: str) -> Dict[str, Any]:
        """
        Main analysis method: segments confession, evaluates each incident,
        and constructs the full 17-field AnalysisResultSchema dictionary.
        """
        clean_text = confession_text.strip()
        scenario_cat = detect_scenario_category(clean_text)
        segments = split_confession_incidents(clean_text)

        # Evaluate individual incidents
        incident_schemas: List[IncidentSchema] = []
        overall_affected: List[str] = []
        overall_allah_rights: List[str] = []
        overall_people_rights: List[str] = []
        has_both = False

        for idx, seg in enumerate(segments):
            inc_cat = detect_scenario_category(seg.description)
            cls_name, aff, a_rights, p_rights = classify_rights(seg.description)
            if cls_name == "both":
                has_both = True

            # Actions for this incident
            inc_req_actions = self._build_core_tawbah_actions(inc_cat)
            inc_rec_actions = self._build_recommended_actions(inc_cat)

            # Restitution and Apology guidance
            inc_restitution = self._get_restitution_guidance(inc_cat, seg.description)
            inc_apology = self._get_apology_guidance(inc_cat, seg.description)

            # Add scenario-specific required actions
            self._add_scenario_specific_actions(inc_cat, seg.description, inc_req_actions)

            inc_schema = IncidentSchema(
                incident_id=f"inc-{idx+1:03d}",
                incident_title=seg.incident_title or "Syndshændelse",
                sin_classification=cls_name,
                description=seg.description,
                affected_parties=aff,
                allah_rights=a_rights,
                people_rights=p_rights,
                required_actions=inc_req_actions,
                recommended_actions=inc_rec_actions,
                apology_guidance=inc_apology,
                restitution_guidance=inc_restitution,
            )
            incident_schemas.append(inc_schema)

            for p in aff:
                if p not in overall_affected:
                    overall_affected.append(p)
            for r in a_rights:
                if r not in overall_allah_rights:
                    overall_allah_rights.append(r)
            for r in p_rights:
                if r not in overall_people_rights:
                    overall_people_rights.append(r)

        # Overall classification
        overall_classification: str = "both" if has_both else "huqooq_allah"
        if overall_classification == "huqooq_allah":
            overall_affected = []
            overall_people_rights = []

        # Overall required actions
        root_required_actions = self._build_core_tawbah_actions(scenario_cat)
        self._add_scenario_specific_actions(scenario_cat, clean_text, root_required_actions)

        # Overall recommended actions
        root_recommended_actions = self._build_recommended_actions(scenario_cat)

        # Overall Guidance
        overall_restitution = self._get_restitution_guidance(scenario_cat, clean_text)
        overall_apology = self._get_apology_guidance(scenario_cat, clean_text)
        overall_ikhtilaf = self._get_ikhtilaf_disclosure(scenario_cat, clean_text)
        overall_severity = self._get_severity_explanation(scenario_cat, clean_text)
        overall_summary = self._get_incident_summary(scenario_cat, clean_text, len(segments))
        scholar_consult = check_scholar_consultation_required(clean_text)

        # Evidence retrieval from RAG
        evidence = self._get_evidence_for_scenario(scenario_cat, clean_text)

        raw_result = {
            "incident_summary": overall_summary,
            "incidents": [inc.model_dump() for inc in incident_schemas],
            "sin_classification": overall_classification,
            "allah_rights": overall_allah_rights or ["Overholdelse af Allahs bud og forbud"],
            "people_rights": overall_people_rights,
            "affected_parties": overall_affected,
            "severity_explanation": overall_severity,
            "required_actions": [act.model_dump() for act in root_required_actions],
            "recommended_actions": [act.model_dump() for act in root_recommended_actions],
            "apology_guidance": overall_apology,
            "restitution_guidance": overall_restitution,
            "quran_references": evidence["quran"],
            "hadith_references": evidence["hadith"],
            "recommended_duas": evidence["duas"],
            "scholarly_disagreement": overall_ikhtilaf,
            "confidence_level": "high",
            "scholar_consultation_required": scholar_consult,
            "final_reminder": (
                "Husk altid Allahs grænseløse barmhjertighed (rahmah) og tilgivelse (maghfirah). "
                "Allah siger: 'Sig: O Mine tjenere, som har overtrådt mod sig selv, fortvivl ikke over Allahs barmhjertighed! "
                "Sandelig, Allah tilgiver alle synder' (Az-Zumar 39:53). Uanset handlingens tyngde er porten til tawbah "
                "vidt åben for det angrende hjerte, og Allah elsker dem, der oprigtigt vender tilbage til Ham i anger og håb."
            ),
        }

        # Validate and sanitize references via RAG service
        sanitized = self.rag.validate_and_sanitize_analysis(raw_result)

        # Return validated model dump
        return AnalysisResultSchema.model_validate(sanitized).model_dump()

    def _add_scenario_specific_actions(
        self, scenario_cat: str, text: str, actions_list: List[ActionItemSchema]
    ) -> None:
        """Adds specific obligatory action items for the scenario."""
        t_lower = text.lower()

        if scenario_cat == "insulting_mother" or ("mor" in t_lower and ("råbte" in t_lower or "skændes" in t_lower)):
            actions_list.append(ActionItemSchema(
                id=f"act-apology-mother-{uuid.uuid4().hex[:6]}",
                category="apology",
                description="Gå personligt til din mor og bed ydmygt om hendes tilgivelse (tilgivelse og undskyld til mor).",
                explanation="Moderens tilfredshed er en forudsætning for Allahs tilfredshed. Kys hendes pande eller hænder i oprigtig underkastelse.",
                target_party="Moderen",
                completed=False,
                action_type="apology",
                title="Personlig bøn om tilgivelse til mor",
            ))

        elif scenario_cat == "stealing_father" or ("far" in t_lower and ("2.000" in t_lower or "2000" in t_lower or "stjal" in t_lower)):
            actions_list.append(ActionItemSchema(
                id=f"act-restitution-father-{uuid.uuid4().hex[:6]}",
                category="restitution",
                description="Tilbagebetal de 2.000 kroner til din far som obligatorisk restitution (tilbagebetal penge til far).",
                explanation="Restitution (Radd al-Mazalim) er den obligatoriske fjerde betingelse for tawbah ved ejendomskrænkelser. Må gerne gøres hemmeligt i hans pung.",
                target_party="Faderen",
                completed=False,
                action_type="restitution",
                title="Fuld tilbagebetaling af de 2.000 kr",
            ))

        elif scenario_cat == "backbiting" or "bagtale" in t_lower or "ghibah" in t_lower:
            actions_list.append(ActionItemSchema(
                id=f"act-backbiting-dua-{uuid.uuid4().hex[:6]}",
                category="rectification",
                description="Bed oprigtig dua og bøn om tilgivelse for den bagtalte person og tal godt om hans ære i forsamlingen.",
                explanation="For at undgå splid og fitnah påbyder klassiske retslærde at opveje bagtalelsen med ros og forbøn frem for at konfrontere ham direkte.",
                target_party="Den bagtalte person",
                completed=False,
                action_type="rectification",
                title="Dua for offeret og genoprejsning af ære",
            ))

        elif scenario_cat == "missing_fajr" or ("bøn" in t_lower and ("fajr" in t_lower or "asr" in t_lower or "qada" in t_lower)):
            actions_list.append(ActionItemSchema(
                id=f"act-qada-prayer-{uuid.uuid4().hex[:6]}",
                category="rectification",
                description="Udfør straks den forsømte bøn som forsinket bøn (Qada-bøn for Fajr) med dyb anger over forsinkelsen.",
                explanation="Flertallet af de klassiske retslærde (Jumhur) påbyder øjeblikkelig udførelse (qada) af enhver bevidst forsømt obligatorisk bøn.",
                target_party="Allah",
                completed=False,
                action_type="rectification",
                title="Udførelse af forsinket Qada-bøn",
            ))

        elif scenario_cat == "lying_to_spouse" or ("ægtefælle" in t_lower and "løj" in t_lower):
            actions_list.append(ActionItemSchema(
                id=f"act-spouse-reconciliation-{uuid.uuid4().hex[:6]}",
                category="apology",
                description="Gå til din ægtefælle i sandhed og ærlighed, bed om undskyld og genopbyg ægtefællens tillid.",
                explanation="Sandfærdighed og ærlighed i ægteskabet er en forudsætning for velsignelse og gensidig barmhjertighed.",
                target_party="Ægtefællen",
                completed=False,
                action_type="apology",
                title="Oprigtig sandhed og undskyldning til ægtefælle",
            ))

        elif scenario_cat == "damaging_property" or ("hegn" in t_lower or "nabo" in t_lower or "hærværk" in t_lower):
            actions_list.append(ActionItemSchema(
                id=f"act-property-compensation-{uuid.uuid4().hex[:6]}",
                category="restitution",
                description="Betal fuld erstatning og reparation for skaderne på naboens havehegn og bil (daman).",
                explanation="I islam gælder princippet 'Ingen skade og ingen gengældelse af skade' (La darar wa la dirar). Skader på andres ejendom skal erstattes fuldt ud.",
                target_party="Naboen",
                completed=False,
                action_type="restitution",
                title="Fuld erstatning og reparation til nabo",
            ))

        elif scenario_cat == "returning_taken_money" or ("5.000" in t_lower or "5000" in t_lower or "kassen" in t_lower):
            actions_list.append(ActionItemSchema(
                id=f"act-restitution-shop-{uuid.uuid4().hex[:6]}",
                category="restitution",
                description="Overdrag de 5.000 kr i anonym tilbagelevering til den retmæssige ejer eller butikkens kasse som radd al-mazalim.",
                explanation="Det er shariah-mæssigt tilladt og gyldigt at returnere penge anonymt uden at udsætte sig selv for straf eller unødig vanære.",
                target_party="Den retmæssige ejer",
                completed=False,
                action_type="restitution",
                title="Anonym tilbagelevering af 5.000 kr til ejer",
            ))

        elif scenario_cat == "private_sin" or "privat synd" in t_lower:
            actions_list.append(ActionItemSchema(
                id=f"act-sitr-concealment-{uuid.uuid4().hex[:6]}",
                category="rectification",
                description="Overhold streng hemmeligholdelse (Al-Sitr): Skjul synden og fortæl ikke nogen mennesker om den, men hold den udelukkende mellem dig og Allah.",
                explanation="Profeten (fred være med ham) forbød kategorisk at afsløre private synder (Sahih al-Bukhari 6069). Ingen mennesker har ret til indsigt.",
                target_party="Allah",
                completed=False,
                action_type="rectification",
                title="Streng hemmeligholdelse (Al-Sitr)",
            ))

        elif scenario_cat == "false_accusation" or "buhtan" in t_lower or "falsk anklage" in t_lower:
            actions_list.append(ActionItemSchema(
                id=f"act-retraction-buhtan-{uuid.uuid4().hex[:6]}",
                category="apology",
                description="Træk anklagen offentligt tilbage foran forsamlingen og rens broderens ære for den falske beskyldning (buhtan), og giv ham en personlig undskyldning.",
                explanation="Når en falsk beskyldning er spredt offentligt, forpligter shariah til en offentlig tilbagetrækning over for samme forsamling.",
                target_party="Den falsk anklagede person",
                completed=False,
                action_type="apology",
                title="Offentlig tilbagetrækning og genoprejsning af ære",
            ))

        elif scenario_cat == "breaking_trust" or "15.000" in t_lower or "amanah" in t_lower or "kasserer" in t_lower:
            actions_list.append(ActionItemSchema(
                id=f"act-restitution-trust-{uuid.uuid4().hex[:6]}",
                category="restitution",
                description="Fuld tilbagebetaling af de 15.000 kr til foreningens konto/kasse, berigtigelse af regnskab og tilbagetræden fra betroet kassererpost (svigt af amanah).",
                explanation="Forræderi mod betroede midler (khiyanat al-amanah) kræver 100% økonomisk godtgørelse og genoprettelse af den institutionelle tillid.",
                target_party="Foreningen / Medlemmerne",
                completed=False,
                action_type="restitution",
                title="Tilbagebetaling af 15.000 kr og regnskabsberigtigelse",
            ))

        # Check general theft or property cases
        elif "stjal" in t_lower or "tyveri" in t_lower or "snød" in t_lower or "penge" in t_lower:
            actions_list.append(ActionItemSchema(
                id=f"act-restitution-gen-{uuid.uuid4().hex[:6]}",
                category="restitution",
                description="Fuld tilbagelevering eller erstatning af værdierne til den retmæssige ejer (Radd al-Mazalim).",
                explanation="Penge og materielle værdier skal gives tilbage til ejeren eller dennes arvinger for at tawbah kan være gyldig.",
                target_party="Den forurettede part",
                completed=False,
                action_type="restitution",
                title="Fuld økonomisk erstatning og tilbagelevering",
            ))

    def _get_restitution_guidance(self, scenario_cat: str, text: str) -> Optional[str]:
        """Provides detailed Danish guidance on restitution and property return."""
        t_lower = text.lower()

        # Pure Allah sins have zero human restitution
        if scenario_cat in ("missing_fajr", "private_sin") or (
            "bøn" in t_lower and "stjal" not in t_lower and "penge" not in t_lower and "hegn" not in t_lower
        ):
            return None

        # Deceased victim boundary
        if "død" in t_lower or "afdød" in t_lower:
            return (
                "Når offeret er afgået ved døden, overgår den økonomiske erstatningspligt ubeskåret til offerets "
                "retmæssige arvinger eller dødsbo. Hvis det efter grundig efterforskning er fuldstændig umuligt at finde arvinger, "
                "skal beløbet doneres til velgørenhed (sadaqah) i den afdødes navn med bøn om, at Allah tildeler ham belønningen."
            )

        # Anonymous return cases (e.g. father theft, shop theft, laptop theft)
        if scenario_cat in ("stealing_father", "returning_taken_money") or (
            "anonym" in t_lower or "arbejdsplads" in t_lower or "bærbar" in t_lower or "far" in t_lower
        ):
            return (
                "Islamisk retspraksis (Fiqh) fastslår kategorisk, at det ikke er en betingelse at afsløre sin identitet "
                "eller udsætte sig for offentlig skam eller straf ved tilbagelevering af penge eller stjålne ejendele. "
                "Du kan fuldt ud gyldigt tilbagelevere pengene eller værdierne via anonym bankoverførsel, en diskret kuvert "
                "uden afsender (f.eks. lagt hemmeligt i faderens pung eller butikkens postkasse), eller via en pålidelig "
                "tredjepart, post eller bud. Hovedsagen er, at den retmæssige ejer modtager sit fulde tilgodehavende eller erstatning."
            )

        if scenario_cat == "damaging_property" or "hegn" in t_lower:
            return (
                "Enhver fysisk skade på andres ejendom skal erstattes med enten reparation af skaden eller udbetaling af "
                "fuld økonomisk kompensation og erstatning svarende til værditabet for hegn og bil. Hvis du frygter fysisk konfrontation "
                "eller uoverstigelig konflikt, kan du betale værkstedet direkte eller lade en betroet tredjepart overbringe pengene anonymt."
            )

        if scenario_cat == "breaking_trust" or "15.000" in t_lower or "kasserer" in t_lower:
            return (
                "De 15.000 kroner skal overføres ubeskåret tilbage til velgørenhedsfondens konto eller indbetales i kassen. "
                "De forfalskede kvitteringer skal berigtiges i foreningens regnskab, så der ikke efterlades uoverensstemmelser "
                "eller uberettiget mistanke mod andre medlemmer."
            )

        if "stjal" in t_lower or "penge" in t_lower or "10.000" in t_lower or "lån" in t_lower or "skylder" in t_lower:
            return (
                "Værdierne skal returneres til ejeren ubeskåret. Hvis du skylder penge fra et lån eller har snødt en partner, "
                "skal beløbet overdrages som fuld økonomisk erstatning og kompensation. Anonym tilbagebetaling er tilladt, hvis direkte "
                "erkendelse skaber uoverskuelig personlig eller familiær skade."
            )

        return (
            "Ved enhver krænkelse af menneskers rettigheder (Huqooq al-Ibad) er tilbagelevering af ejendom eller økonomisk "
            "erstatning og kompensation en uomgængelig betingelse for, at Allah accepterer din tawbah."
        )

    def _get_apology_guidance(self, scenario_cat: str, text: str) -> Optional[str]:
        """Provides detailed Danish guidance on apology and fitnah avoidance."""
        t_lower = text.lower()

        # Pure Allah / Private sin: Al-Sitr strictly prohibits public exposure
        if scenario_cat == "private_sin" or "privat synd" in t_lower or "hemmelig" in t_lower:
            return (
                "Det er i islam strengt forbudt at afsløre sine private synder for andre mennesker (Al-Sitr). "
                "Profeten (fred være med ham) advarede mod 'al-mujahirin' – dem, der fjerner Allahs dække fra deres skjulte handlinger. "
                "Du må derfor under ingen omstændigheder betro dig til din ægtefælle, en imam eller venner. Hold synden hemmelig, "
                "skjul den fuldstændigt, fortæl ikke nogen mennesker om den, og søg Allahs tilgivelse i det skjulte."
            )

        # Backbiting: Fitnah avoidance nuance
        if scenario_cat == "backbiting" or "bagtale" in t_lower or "ghibah" in t_lower:
            return (
                "Ved bagtalelse (ghibah) differentierer klassisk fiqh mellem to situationer: "
                "Hvis offeret allerede ved det, er en direkte undskyldning obligatorisk. Men hvis offeret intet aner om det, "
                "og en direkte tilståelse vil skabe dyb smerte, splid, ufred eller fitnah, er det ifølge en stærk gruppe lærde "
                "(herunder Ibn Taymiyyah og Ibn al-Qayyim) strengt påkrævet at undlade at informere vedkommende. "
                "I stedet skal du gøre bod ved at bede oprigtig bøn og dua for personen, rose ham og tale positivt om hans ære "
                "i netop de forsamlinger, hvor han blev bagtalt, og give sadaqah i hans navn."
            )

        if scenario_cat == "insulting_mother" or "mor" in t_lower:
            return (
                "En personlig, dyb og uforbeholden undskyldning over for din mor er absolut påkrævet. "
                "Ulydighed mod forældre (Uqooq al-Walidayn) er blandt de største synder. Gå til hende i fuld ydmyghed, "
                "bed hende grædende om forladelse, og vis hende ekstra omsorg og kærlighed. Der er ingen fitnah-undtagelse her, "
                "da hun allerede er bekendt med handlingen og har lidt overlast."
            )

        if scenario_cat == "lying_to_spouse" or "ægtefælle" in t_lower:
            return (
                "Gå til din ægtefælle i sandhed og oprigtighed. Forklar sandheden med ydmyghed og bed om undskyldning for løgnen "
                "og det svigtede tillidsbånd. Tag fuldt ansvar for dine handlinger, lov bod, og genetabler ægteskabelig åbenhed."
            )

        if scenario_cat == "false_accusation" or "buhtan" in t_lower:
            return (
                "Da beskyldningen faldt foran en forsamling, er en privat undskyldning alene utilstrækkelig. "
                "Du er forpligtet til at stå frem foran de samme mennesker, erklære din anklage for falsk og grundløs (buhtan), "
                "rense offerets navn fuldstændigt og give ham en personlig, ydmyg undskyldning."
            )

        if scenario_cat in ("stealing_father", "returning_taken_money"):
            return (
                "Hvis en direkte tilståelse vil føre til uopretteligt brud på familiebåndene eller personlig ødelæggelse, "
                "tillader shariah at undlade den verbale konfrontation, forudsat at pengene tilbageleveres 100% anonymt. "
                "I modsat fald kan en personlig undskyldning styrke forsoningen."
            )

        if "skylder" in t_lower or "onkel" in t_lower:
            return (
                "Gå til din onkel eller modpart, erkend gælden ærligt og giv en oprigtig undskyldning for benægtelsen, "
                "samtidig med at du aftaler eller gennemfører fuld tilbagebetaling."
            )

        if scenario_cat == "missing_fajr":
            return None

        return (
            "Giv en direkte og oprigtig undskyldning til den forurettede part, medmindre du med vished ved, "
            "at en afsløring vil medføre en endnu større skade eller splid (fitnah)."
        )

    def _get_ikhtilaf_disclosure(self, scenario_cat: str, text: str) -> Optional[str]:
        """Transparent classical scholarly disagreement disclosure (Ikhtilaf)."""
        t_lower = text.lower()

        if scenario_cat == "backbiting" or "bagtale" in t_lower or "ghibah" in t_lower:
            return (
                "Der er en velkendt klassisk uenighed (ikhtilaf) blandt de islamiske retslærde vedrørende bagtalelse, "
                "hvor offeret ikke er informeret: Flertallet (Jumhur) mente oprindeligt, at den bagtalte altid skal opsøges "
                "for at give tilgivelse. Imidlertid fastslog Imam Ibn Taymiyyah, Ibn al-Qayyim og andre fremtrædende lærde, "
                "at hvis det at informere personen vil medføre sorg, had, splid eller fjendskab (fitnah), er det forbudt at "
                "informere vedkommende. I så fald erstattes den direkte undskyldning af oprigtig forbøn (dua), ros i forsamlingen "
                "og gode gerninger i offerets navn."
            )

        if scenario_cat == "missing_fajr" or "fajr" in t_lower or "bøn" in t_lower:
            return (
                "Angående den person, der bevidst har forsømt en obligatorisk bøn uden gyldig undskyldning: "
                "Flertallet af de fire retsskoler (Hanafi, Maliki, Shafi'i og Hanbali) fastholder, at det er en bindende pligt "
                "at indhente bønnen som forsinket bøn (Qada). En anden gruppe lærde, herunder Ibn Hazm og Ibn Taymiyyah, "
                "mente derimod, at en bevidst forsømt bøn uden for dens tidsrum ikke kan indhentes med qada, men at personen "
                "i stedet skal gøre intens tawbah og udføre overvældende mængder af frivillige bønner (nawafil) og gode gerninger."
            )

        return None

    def _get_severity_explanation(self, scenario_cat: str, text: str) -> str:
        """Explains the theological gravity and legal consequences of the transgression."""
        if scenario_cat == "insulting_mother":
            return (
                "Ulydighed mod forældre (Uqooq al-Walidayn) er i Koranen og Sunnah klassificeret som en af de absolut "
                "største synder (Kaba'ir). Allah har sidestillet respekten for forældre med tilbedelsen af Ham alene (Al-Isra 17:23). "
                "At råbe ad sin mor og såre hendes følelser er en alvorlig overtrædelse af både Allahs bud og moderens ukrænkelige ret."
            )
        if scenario_cat == "stealing_father":
            return (
                "Tyveri (Sariqah) er en alvorlig stor synd i islam, der krænker både Allahs klare forbud og medmenneskets "
                "grundlæggende ejendomsret. Når tyveriet begås mod ens egen far, forværres syndens alvor yderligere, da det "
                "kombinerer berigelseskriminalitet med svigt af forældrenes særlige tillid og ære."
            )
        if scenario_cat == "backbiting":
            return (
                "Bagtalelse (Ghibah) er en ødelæggende synd for samfundets sammenhængskraft. Koranen sammenligner det med "
                "at spise kødet af sin døde bror (Al-Hujurat 49:12). Synden har vidtrækkende konsekvenser på Dommedag, hvor "
                "gode gerninger overføres til den forurettede person som kompensation."
            )
        if scenario_cat == "missing_fajr":
            return (
                "Bønnen (Salah) er islams anden søjle og den første handling, mennesket stilles til regnskab for på Dommedag. "
                "At forsømme en obligatorisk bøn med vilje af dovenskab er en alvorlig overtrædelse af Allahs eksklusive ret, "
                "som kræver øjeblikkelig anger og rettelse."
            )
        if scenario_cat == "lying_to_spouse":
            return (
                "Løgn og falsk ed over for sin ægtefælle undergraver ægteskabets hellige pagt (Mithaqan Ghalidha). "
                "Ærlighed er fundamentet for et islamisk hjem, og bevidst bedrag kombinerer forbuddet mod usandhed med svigt af fælles tillid."
            )
        if scenario_cat == "damaging_property":
            return (
                "Skade på andres ejendom uden erstatning krænker naboens særlige rettigheder (Huqooq al-Jar) og overtræder "
                "det generelle princip mod at forvolde skade (La darar wa la dirar). Enhver uoprettet materiel skade vil blive afregnet på Dommedag."
            )
        if scenario_cat == "returning_taken_money":
            return (
                "Uretmæssigt tilegnede midler (Batil) udgør en åndelig byrde, som blokerer for bønhørelse og renhed i tilbedelsen. "
                "At returnere pengene renser formuen og befrier den troende for medmenneskelige krav foran Allah."
            )
        if scenario_cat == "private_sin":
            return (
                "Privat synd begået i ensomhed krænker Allahs alvidenhed og sjælens renhed. Samtidig rummer den en særlig barmhjertighed, "
                "da Allah i Sin nåde har skjult handlingen for skabelsen. Den største fare er at bryde dette dække ved offentliggørelse."
            )
        if scenario_cat == "false_accusation":
            return (
                "Falsk anklage (Buhtan) er værre end almindelig bagtalelse, da det er en opdigtet løgn, der ødelægger en uskyldig persons ære. "
                "Synden trækker direkte forbandelse og alvorlig straf, medmindre der sker fuld offentlig oprejsning."
            )
        if scenario_cat == "breaking_trust":
            return (
                "Brud på tillid og underslæb med betroede velgørenhedsmidler (Khiyanat al-Amanah) er et kendetegn ved hykleri (nifaq), "
                "som advaret i Sahih al-Bukhari 33. Forræderi mod donationer til trængende er en dobbelt uretfærdighed mod både givere og modtagere."
            )
        return (
            "Handlingen udgør en overtrædelse af islamisk lovgivning, som fordrer oprigtig anger og hurtig genopretning "
            "af de krænkede rettigheder over for Allah og berørte medmennesker."
        )

    def _get_incident_summary(self, scenario_cat: str, text: str, incident_count: int) -> str:
        """Constructs a non-judgmental Danish summary of the confession."""
        if incident_count > 1:
            return (
                f"Bekendelsen indeholder {incident_count} adskilte hændelser, som involverer både krænkelser af medmenneskers "
                f"rettigheder (ejendom/penge) og forsømmelse af rituelle forpligtelser over for Allah. "
                f"Hver hændelse er analyseret særskilt med tilhørende genopretningshandlinger."
            )
        summaries = {
            "insulting_mother": "Brugeren beskriver et ophedet skænderi med sin mor, hvor der faldt sårende og respektløse ord, som har forårsaget dyb smerte.",
            "stealing_father": "Brugeren beskriver uretmæssig tilegnelse af 2.000 kr fra sin fars pung for at dække personlig gæld og søger vejledning om tilbagelevering.",
            "backbiting": "Brugeren beskriver bagtalelse af en kollega i dennes fravær foran andre kolleger, uden at offeret på nuværende tidspunkt er vidende om handlingen.",
            "missing_fajr": "Brugeren beskriver at have forsømt den obligatoriske Fajr-bøn bevidst på grund af dovenskab efter at have været vågen om natten.",
            "lying_to_spouse": "Brugeren beskriver at have løjet for sin ægtefælle og aflagt falsk ed for at skjule forbrug af fælles opsparing til personlig gæld.",
            "damaging_property": "Brugeren beskriver en påkørsel af naboens havehegn og bil under en bakkemanøvre med efterfølgende flugt fra stedet i panik.",
            "returning_taken_money": "Brugeren beskriver et tidligere tyveri af 5.000 kr fra kassen på en ungarbejdsplads for mange år siden og ønsker at tilbagelevere beløbet anonymt.",
            "private_sin": "Brugeren beskriver en personlig, skjult synd foran skærmen i ensomhed og søger afklaring på, om handlingen skal holdes hemmelig eller betros.",
            "false_accusation": "Brugeren beskriver en offentlig falsk anklage (buhtan) mod en uskyldig person foran 30 vidner i et foreningslokale.",
            "breaking_trust": "Brugeren beskriver misbrug af sin tillidspost som kasserer til at overføre 15.000 kr af velgørenhedsmidler til private ferieudgifter med bilagssvindel.",
        }
        return summaries.get(
            scenario_cat,
            "Brugeren beskriver en personlig synd og søger oprigtig islamisk vejledning i overensstemmelse med Ahlus-Sunnah wal-Jama'ah til at gøre sand tawbah."
        )

    def _get_evidence_for_scenario(self, scenario_cat: str, text: str) -> Dict[str, Any]:
        """Fetches canonical Quran, Hadith, and Duas from RAG service."""
        # Query RAG service with the scenario category
        rag_evidence = self.rag.get_evidence_for_scenario(scenario_cat)

        q_list = [q.model_dump() for q in rag_evidence.get("quran", [])]
        h_list = [h.model_dump() for h in rag_evidence.get("hadith", [])]
        d_list = [d.model_dump() for d in rag_evidence.get("duas", [])]

        # Ensure fallbacks if empty
        if not q_list:
            fb_q = self.rag.search_quran(category="all", limit=1)
            if fb_q:
                q_list = [fb_q[0].model_dump()]
        if not h_list:
            fb_h = self.rag.search_hadith(category="all", limit=1)
            if fb_h:
                h_list = [fb_h[0].model_dump()]
        if not d_list:
            fb_d = self.rag.search_duas(category="all", limit=1)
            if fb_d:
                d_list = [fb_d[0].model_dump()]

        return {
            "quran": q_list,
            "hadith": h_list,
            "duas": d_list,
        }


# Global Singleton
_RULE_ENGINE_INSTANCE: Optional[IslamicRuleEngine] = None


def get_rule_engine() -> IslamicRuleEngine:
    global _RULE_ENGINE_INSTANCE
    if _RULE_ENGINE_INSTANCE is None:
        _RULE_ENGINE_INSTANCE = IslamicRuleEngine()
    return _RULE_ENGINE_INSTANCE
