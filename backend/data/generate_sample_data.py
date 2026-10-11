"""
Generate 300 SYNTHETIC labelled complaints -> data/sample_complaints.csv

    python data/generate_sample_data.py            (from the backend/ folder)

The data is made from templates in English, Tamil, Malayalam and mixed
language (Tanglish / Manglish / code-mixed script). It is only for
building and testing the system. Replace or extend it with real
complaints from the Google Form pilot (data/real_complaints.csv).

The random seed is fixed, so every run produces the same file.
"""
import csv
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
from ai.campus import PLACES  # noqa: E402  (plain Python module, no Django needed)

SEED = 42
TOTAL = 300
# All dates are relative to this moment. load_sample_data shifts them so ANCHOR becomes "now".
ANCHOR = datetime(2026, 10, 10, 18, 0)
DAYS_BACK = 56  # 8 weeks of history

# category: (how many complaints, places where it happens with weights)
CATEGORY_PLAN = {
    "HOSTEL": (55, {"B Block Hostel": 5, "A Block Hostel": 2, "C Block Hostel": 2, "Girls Hostel": 2}),
    "IT": (50, {"A Block Hostel": 3, "B Block Hostel": 3, "Library": 2, "CSE Lab": 2, "Girls Hostel": 1}),
    "MESS": (45, {"Main Mess": 1}),
    "MAINTENANCE": (40, {"A Block Hostel": 2, "B Block Hostel": 2, "C Block Hostel": 3, "Library": 1, "Physics Lab": 1, "Girls Hostel": 1}),
    "SANITATION": (35, {"Main Mess": 2, "C Block Hostel": 2, "A Block Hostel": 1, "Library": 1, "Sports Ground": 1}),
    "LAB": (30, {"CSE Lab": 3, "Physics Lab": 2}),
    "TRANSPORT": (25, {"Bus Bay": 3, "Main Gate": 1}),
    "SECURITY": (20, {"Main Gate": 2, "Girls Hostel": 2, "Sports Ground": 1, "A Block Hostel": 1}),
}

LANGUAGE_WEIGHTS = {"en": 0.45, "ta": 0.2, "ml": 0.2, "mixed": 0.15}

# Typical days to resolve, per department, and multipliers per urgency.
BASE_DAYS = {"HOSTEL": 3.0, "IT": 1.5, "MESS": 1.0, "MAINTENANCE": 2.0, "SANITATION": 1.5,
             "LAB": 5.0, "TRANSPORT": 4.0, "SECURITY": 1.0}
URGENCY_FACTOR = {"critical": 0.4, "high": 0.7, "medium": 1.0, "low": 1.6}
URGENCIES = ["low", "medium", "high", "critical"]

# (title, description, base urgency). Slots: {place} {room} {n} {route}
TEMPLATES = {
    "HOSTEL": {
        "en": [
            ("Fan not working in room", "The ceiling fan in my room at {place} has not been working for {n} days. It is very hot at night.", "medium"),
            ("No water supply in hostel", "There is no water supply in the bathrooms of {place} since morning. We cannot bathe before class.", "high"),
            ("Broken cot and cupboard", "My cot is broken and the cupboard door does not close in {place}, room {room}.", "low"),
            ("Room door lock broken", "The door lock of room {room} in {place} is broken, we cannot lock the room.", "high"),
        ],
        "ta": [
            ("அறையில் மின்விசிறி வேலை செய்யவில்லை", "{place} அறை {room}-ல் மின்விசிறி {n} நாட்களாக வேலை செய்யவில்லை. இரவில் தூங்க முடியவில்லை.", "medium"),
            ("விடுதியில் தண்ணீர் இல்லை", "{place} குளியலறையில் காலை முதல் தண்ணீர் வரவில்லை.", "high"),
            ("கட்டில் உடைந்துள்ளது", "{place} அறை {room}-ல் கட்டில் உடைந்துள்ளது, தயவுசெய்து மாற்றவும்.", "low"),
        ],
        "ml": [
            ("മുറിയിലെ ഫാൻ പ്രവർത്തിക്കുന്നില്ല", "{place} മുറി {room}-ലെ ഫാൻ {n} ദിവസമായി പ്രവർത്തിക്കുന്നില്ല. രാത്രി ഉറങ്ങാൻ പറ്റുന്നില്ല.", "medium"),
            ("ഹോസ്റ്റലിൽ വെള്ളമില്ല", "{place} ബാത്ത്റൂമിൽ രാവിലെ മുതൽ വെള്ളം വരുന്നില്ല.", "high"),
            ("കട്ടിൽ പൊട്ടിയിരിക്കുന്നു", "{place} മുറി {room}-ലെ കട്ടിൽ പൊട്ടിയിരിക്കുന്നു, ദയവായി മാറ്റി തരണം.", "low"),
        ],
        "mixed": [
            ("Room fan work aagala", "{place} room {room} la fan {n} days ah work aagala, romba heat ah iruku.", "medium"),
            ("Hostel il vellam illa", "{place} bathroom il morning muthal water varunilla, please check cheyyu.", "high"),
            ("Hostel room lock problem", "{place} room {room} லாக் broken ஆகிவிட்டது, room lock பண்ண முடியல.", "high"),
        ],
    },
    "MESS": {
        "en": [
            ("Food quality is poor", "The food served at {place} today was stale and the rice was undercooked.", "medium"),
            ("Insect found in food", "We found an insect in the sambar at {place} during lunch. This is a hygiene issue.", "high"),
            ("Mess timing issue", "Breakfast at {place} closes before 8 am, students with early lab cannot eat.", "low"),
            ("Food poisoning after dinner", "Several students got stomach pain and vomiting after dinner at {place} yesterday.", "critical"),
        ],
        "ta": [
            ("சாப்பாடு தரம் மோசம்", "{place}-ல் இன்று கொடுத்த சாப்பாடு பழையதாக இருந்தது, சாதம் சரியாக வேகவில்லை.", "medium"),
            ("உணவில் பூச்சி", "மதிய உணவில் சாம்பாரில் பூச்சி இருந்தது. {place} சுத்தம் இல்லை.", "high"),
            ("காலை உணவு நேரம்", "{place} காலை உணவு 8 மணிக்கு முன்பே மூடிவிடுகிறார்கள்.", "low"),
        ],
        "ml": [
            ("ഭക്ഷണത്തിന്റെ ഗുണനിലവാരം മോശം", "{place}-ൽ ഇന്ന് നൽകിയ ഭക്ഷണം പഴകിയതായിരുന്നു, ചോറ് ശരിയായി വെന്തിട്ടില്ല.", "medium"),
            ("ഭക്ഷണത്തിൽ പ്രാണി", "ഉച്ചഭക്ഷണത്തിലെ സാമ്പാറിൽ പ്രാണിയെ കണ്ടു. {place} വൃത്തിയില്ല.", "high"),
            ("അത്താഴത്തിന് ശേഷം വയറുവേദന", "ഇന്നലെ {place}-ലെ അത്താഴത്തിന് ശേഷം പല വിദ്യാർത്ഥികൾക്കും വയറുവേദനയും ഛർദ്ദിയും ഉണ്ടായി.", "critical"),
        ],
        "mixed": [
            ("Mess food romba mosam", "{place} la innaiku food stale ah irundhuchu, rice sariya vegala.", "medium"),
            ("Mess il food cold aanu", "{place} il dinner always cold aanu, chappathi kazhikkan pattunnilla.", "low"),
            ("சாப்பாட்டில் insect", "Lunch sambar-ல insect இருந்தது, {place} hygiene சரியில்ல.", "high"),
        ],
    },
    "IT": {
        "en": [
            ("Wi-Fi not working", "Wi-Fi is not working in {place} for {n} days. We cannot attend online classes.", "high"),
            ("Very slow internet", "Internet speed in {place} is very slow in the evening, pages do not load.", "medium"),
            ("Cannot log in to portal", "I cannot log in to the student portal, it says invalid password even after reset.", "medium"),
            ("LAN port not working", "The LAN port in room {room} at {place} is not working.", "low"),
        ],
        "ta": [
            ("வைஃபை வேலை செய்யவில்லை", "{place}-ல் {n} நாட்களாக வைஃபை வேலை செய்யவில்லை. ஆன்லைன் வகுப்பில் சேர முடியவில்லை.", "high"),
            ("இணையம் மிகவும் மெதுவாக உள்ளது", "மாலை நேரத்தில் {place}-ல் இணைய வேகம் மிகவும் குறைவாக உள்ளது.", "medium"),
            ("போர்ட்டலில் உள்நுழைய முடியவில்லை", "மாணவர் போர்ட்டலில் உள்நுழைய முடியவில்லை, கடவுச்சொல் தவறு என்று வருகிறது.", "medium"),
        ],
        "ml": [
            ("വൈഫൈ പ്രവർത്തിക്കുന്നില്ല", "{place}-ൽ {n} ദിവസമായി വൈഫൈ പ്രവർത്തിക്കുന്നില്ല. ഓൺലൈൻ ക്ലാസിൽ കയറാൻ പറ്റുന്നില്ല.", "high"),
            ("ഇന്റർനെറ്റ് വളരെ സ്ലോ ആണ്", "വൈകുന്നേരം {place}-ൽ ഇന്റർനെറ്റ് വേഗത വളരെ കുറവാണ്.", "medium"),
            ("പോർട്ടലിൽ ലോഗിൻ ചെയ്യാൻ കഴിയുന്നില്ല", "സ്റ്റുഡന്റ് പോർട്ടലിൽ ലോഗിൻ ചെയ്യാൻ കഴിയുന്നില്ല, പാസ്‌വേഡ് തെറ്റാണെന്ന് കാണിക്കുന്നു.", "medium"),
        ],
        "mixed": [
            ("Wifi work aagala", "{place} la {n} days ah wifi work aagala, assignment submit panna mudiyala.", "high"),
            ("Wifi kittunnilla", "{place} il wifi kittunnilla, assignment submit cheyyan pattunnilla.", "high"),
            ("Internet ரொம்ப slow", "{place}-ல evening time internet ரொம்ப slow ஆக இருக்கு.", "medium"),
        ],
    },
    "LAB": {
        "en": [
            ("Lab computers not working", "Half of the computers in {place} do not boot. We share systems during practicals.", "medium"),
            ("Projector not working", "The projector in {place} is not working for {n} days, lectures are affected.", "medium"),
            ("Lab equipment broken", "The equipment in {place} is broken and we could not finish the experiment.", "medium"),
            ("Gas smell in lab", "There is a strong gas smell in {place}, students feel dizzy.", "critical"),
        ],
        "ta": [
            ("ஆய்வக கணினிகள் வேலை செய்யவில்லை", "{place}-ல் பாதி கணினிகள் ஆன் ஆகவில்லை. செய்முறை வகுப்பில் சிரமம்.", "medium"),
            ("புரொஜெக்டர் வேலை செய்யவில்லை", "{place}-ல் புரொஜெக்டர் {n} நாட்களாக வேலை செய்யவில்லை.", "medium"),
            ("ஆய்வக உபகரணம் உடைந்துள்ளது", "{place}-ல் உபகரணங்கள் உடைந்துள்ளதால் சோதனையை முடிக்க முடியவில்லை.", "medium"),
        ],
        "ml": [
            ("ലാബിലെ കമ്പ്യൂട്ടറുകൾ പ്രവർത്തിക്കുന്നില്ല", "{place}-ലെ പകുതി കമ്പ്യൂട്ടറുകളും ഓണാകുന്നില്ല. പ്രാക്ടിക്കൽ ക്ലാസിൽ ബുദ്ധിമുട്ടാണ്.", "medium"),
            ("പ്രൊജക്ടർ പ്രവർത്തിക്കുന്നില്ല", "{place}-ലെ പ്രൊജക്ടർ {n} ദിവസമായി പ്രവർത്തിക്കുന്നില്ല.", "medium"),
            ("ലാബിൽ ഗ്യാസിന്റെ മണം", "{place}-ൽ ശക്തമായ ഗ്യാസിന്റെ മണം, വിദ്യാർത്ഥികൾക്ക് തലകറക്കം.", "critical"),
        ],
        "mixed": [
            ("Lab system boot aagala", "{place} la half systems boot aagala, practicals la share panrom.", "medium"),
            ("Lab il projector work cheyyunnilla", "{place} il projector {n} divasamayi work cheyyunnilla.", "medium"),
            ("Lab equipment உடைஞ்சிருக்கு", "{place}-ல equipment உடைஞ்சிருக்கு, experiment finish பண்ண முடியல.", "medium"),
        ],
    },
    "TRANSPORT": {
        "en": [
            ("College bus always late", "The college bus on route {route} reaches {place} 30 minutes late every day.", "medium"),
            ("Bus breakdown", "Bus number {route} broke down on the way, students missed the exam.", "high"),
            ("Rash driving", "The driver of bus {route} drives very rashly, it is not safe.", "high"),
            ("Bus overcrowded", "Bus {route} is overcrowded, students stand on the footboard near {place}.", "medium"),
        ],
        "ta": [
            ("கல்லூரி பேருந்து தாமதம்", "வழித்தடம் {route} பேருந்து தினமும் 30 நிமிடம் தாமதமாக {place} வருகிறது.", "medium"),
            ("பேருந்து பழுது", "{route} எண் பேருந்து வழியில் பழுதடைந்தது, தேர்வுக்கு தாமதமானது.", "high"),
            ("ஓட்டுநர் வேகமாக ஓட்டுகிறார்", "{route} பேருந்து ஓட்டுநர் மிகவும் வேகமாக ஓட்டுகிறார், பாதுகாப்பு இல்லை.", "high"),
        ],
        "ml": [
            ("കോളേജ് ബസ് എപ്പോഴും വൈകുന്നു", "റൂട്ട് {route} ബസ് ദിവസവും 30 മിനിറ്റ് വൈകിയാണ് {place}-ൽ എത്തുന്നത്.", "medium"),
            ("ബസ് വഴിയിൽ കേടായി", "{route} നമ്പർ ബസ് വഴിയിൽ കേടായി, പരീക്ഷയ്ക്ക് വൈകി.", "high"),
            ("ബസിൽ വലിയ തിരക്ക്", "{route} ബസിൽ വലിയ തിരക്കാണ്, കുട്ടികൾ ഫുട്ബോർഡിൽ നിൽക്കുന്നു.", "medium"),
        ],
        "mixed": [
            ("Bus daily late ah varudhu", "Route {route} bus daily 30 mins late ah {place} ku varudhu.", "medium"),
            ("Bus driver rash aayi odikkunnu", "Bus {route} driver valare rash aayi odikkunnu, safe alla.", "high"),
            ("Bus breakdown ஆகிடுச்சு", "{route} bus வழியில breakdown ஆகிடுச்சு, exam-க்கு late ஆச்சு.", "high"),
        ],
    },
    "MAINTENANCE": {
        "en": [
            ("Power cut", "There is no electricity in {place} for {n} hours. Fans and lights are off.", "high"),
            ("Tap leaking", "The tap in the washroom near {place} is leaking continuously and water is wasted.", "low"),
            ("Electric shock from switch", "I got an electric shock from the switch board in {place}. Wires are exposed.", "critical"),
            ("Tube light not working", "Tube lights in the corridor of {place} are not working, it is dark at night.", "medium"),
        ],
        "ta": [
            ("மின்சாரம் இல்லை", "{place}-ல் {n} மணி நேரமாக மின்சாரம் இல்லை.", "high"),
            ("குழாய் கசிவு", "{place} அருகே கழிவறையில் குழாய் தொடர்ந்து கசிகிறது.", "low"),
            ("சுவிட்சில் மின்சார அதிர்ச்சி", "{place} சுவிட்ச் போர்டில் மின்சார அதிர்ச்சி அடித்தது. கம்பிகள் வெளியே தெரிகின்றன.", "critical"),
        ],
        "ml": [
            ("കറന്റ് ഇല്ല", "{place}-ൽ {n} മണിക്കൂറായി കറന്റ് ഇല്ല.", "high"),
            ("ടാപ്പ് ലീക്ക് ആകുന്നു", "{place}-ന് അടുത്തുള്ള വാഷ്റൂമിലെ ടാപ്പ് തുടർച്ചയായി ലീക്ക് ആകുന്നു.", "low"),
            ("സ്വിച്ചിൽ നിന്ന് ഷോക്ക്", "{place}-ലെ സ്വിച്ച് ബോർഡിൽ നിന്ന് ഷോക്ക് അടിച്ചു. വയറുകൾ പുറത്താണ്.", "critical"),
        ],
        "mixed": [
            ("Current illa", "{place} la {n} hours ah current illa, fan light ellam off.", "high"),
            ("Tap leak aavunnu", "{place} washroom il tap continuous aayi leak aavunnu.", "low"),
            ("Tube light வேலை செய்யல", "{place} corridor-ல tube light வேலை செய்யல, night இருட்டா இருக்கு.", "medium"),
        ],
    },
    "SANITATION": {
        "en": [
            ("Washroom not cleaned", "The washrooms in {place} have not been cleaned for {n} days and smell very bad.", "medium"),
            ("Garbage not collected", "Garbage bins near {place} are overflowing, nobody collected them.", "medium"),
            ("Mosquito problem", "There are too many mosquitoes in {place}, please arrange fogging.", "medium"),
            ("Rats in the building", "Rats are seen every night in {place}.", "high"),
        ],
        "ta": [
            ("கழிவறை சுத்தம் செய்யப்படவில்லை", "{place} கழிவறைகள் {n} நாட்களாக சுத்தம் செய்யப்படவில்லை, துர்நாற்றம் வீசுகிறது.", "medium"),
            ("குப்பை அள்ளப்படவில்லை", "{place} அருகே குப்பைத் தொட்டிகள் நிரம்பி வழிகின்றன.", "medium"),
            ("கொசு தொல்லை", "{place}-ல் கொசு தொல்லை அதிகம், புகை மருந்து அடிக்கவும்.", "medium"),
        ],
        "ml": [
            ("വാഷ്റൂം വൃത്തിയാക്കിയിട്ടില്ല", "{place}-ലെ വാഷ്റൂമുകൾ {n} ദിവസമായി വൃത്തിയാക്കിയിട്ടില്ല, ദുർഗന്ധമാണ്.", "medium"),
            ("മാലിന്യം നീക്കം ചെയ്തിട്ടില്ല", "{place}-ന് അടുത്തുള്ള മാലിന്യ ബിന്നുകൾ നിറഞ്ഞു കവിയുന്നു.", "medium"),
            ("കൊതുക് ശല്യം", "{place}-ൽ കൊതുക് ശല്യം കൂടുതലാണ്, ഫോഗിംഗ് ചെയ്യണം.", "medium"),
        ],
        "mixed": [
            ("Washroom clean pannala", "{place} washroom {n} days ah clean pannala, romba smell.", "medium"),
            ("Garbage edukkunnilla", "{place} near garbage bin full aayi, aarum edukkunnilla.", "medium"),
            ("கொசு romba அதிகம்", "{place}-ல mosquito romba அதிகம், fogging பண்ணுங்க.", "medium"),
        ],
    },
    "SECURITY": {
        "en": [
            ("Phone stolen", "My phone was stolen from {place} yesterday evening. Please check the CCTV.", "high"),
            ("Outsiders entering campus", "Outsiders are entering through {place} at night without any check.", "high"),
            ("Dark path near hostel", "The path near {place} is completely dark at night, girls feel unsafe.", "high"),
            ("Ragging incident", "Some seniors are ragging first years near {place}. Please take action.", "critical"),
        ],
        "ta": [
            ("கைபேசி திருடப்பட்டது", "நேற்று மாலை {place}-ல் என் கைபேசி திருடப்பட்டது. CCTV பார்க்கவும்.", "high"),
            ("வெளியாட்கள் நுழைகிறார்கள்", "இரவில் {place} வழியாக வெளியாட்கள் சோதனை இல்லாமல் நுழைகிறார்கள்.", "high"),
            ("ராகிங் சம்பவம்", "{place} அருகே சில மூத்த மாணவர்கள் முதலாம் ஆண்டு மாணவர்களை ராகிங் செய்கிறார்கள்.", "critical"),
        ],
        "ml": [
            ("ഫോൺ മോഷണം പോയി", "ഇന്നലെ വൈകുന്നേരം {place}-ൽ നിന്ന് എന്റെ ഫോൺ മോഷണം പോയി. സിസിടിവി പരിശോധിക്കണം.", "high"),
            ("പുറത്തുനിന്നുള്ളവർ ക്യാമ്പസിൽ കയറുന്നു", "രാത്രി {place} വഴി പുറത്തുനിന്നുള്ളവർ പരിശോധനയില്ലാതെ കയറുന്നു.", "high"),
            ("റാഗിംഗ്", "{place}-ന് സമീപം ചില സീനിയേഴ്സ് ഒന്നാം വർഷ വിദ്യാർത്ഥികളെ റാഗ് ചെയ്യുന്നു.", "critical"),
        ],
        "mixed": [
            ("Phone thirudu poiduchu", "Nethu evening {place} la en phone thirudu poiduchu, CCTV check pannunga.", "high"),
            ("Night il outsiders kerunnu", "Night {place} vazhi outsiders oru checking um illathe kerunnu.", "high"),
            ("Path இருட்டா இருக்கு", "{place} பக்கத்துல path night-ல ரொம்ப இருட்டா இருக்கு, safe இல்ல.", "high"),
        ],
    },
}

COLUMNS = ["id", "title", "description", "category", "urgency", "language", "location", "block",
           "created_at", "resolution_days", "synthetic"]


def weighted_choice(rng, weights):
    return rng.choices(list(weights), weights=list(weights.values()), k=1)[0]


def random_time(rng):
    """A time in the last 8 weeks, mostly during waking hours (7:00-23:00)."""
    day = rng.randint(0, DAYS_BACK - 1)
    hour = rng.choices(range(24), weights=[1, 1, 1, 1, 1, 1, 2] + [6] * 16 + [3], k=1)[0]
    moment = (ANCHOR - timedelta(days=day)).replace(hour=hour, minute=rng.randint(0, 59))
    if moment > ANCHOR:  # never create complaints in the future
        moment -= timedelta(days=1)
    return moment


def bump_urgency(rng, urgency):
    """15% of the time, move urgency one level up or down (real people disagree)."""
    if rng.random() < 0.15:
        i = URGENCIES.index(urgency) + rng.choice([-1, 1])
        return URGENCIES[max(0, min(i, 3))]
    return urgency


def resolution_days(rng, category, urgency, created_at):
    days = BASE_DAYS[category] * URGENCY_FACTOR[urgency]
    if created_at.weekday() >= 5:
        days *= 1.3  # weekends are slower
    days *= rng.lognormvariate(0, 0.3)  # random noise
    return round(max(0.1, days), 1)


def make_row(rng, category, created_at=None, place=None, language=None, template=None):
    places = CATEGORY_PLAN[category][1]
    place = place or weighted_choice(rng, places)
    language = language or weighted_choice(rng, LANGUAGE_WEIGHTS)
    title, description, urgency = template or rng.choice(TEMPLATES[category][language])
    slots = {"place": place, "room": rng.randint(101, 420), "n": rng.randint(2, 6), "route": rng.randint(1, 12)}
    created_at = created_at or random_time(rng)
    urgency = bump_urgency(rng, urgency)
    return {
        "title": title.format(**slots),
        "description": description.format(**slots),
        "category": category,
        "urgency": urgency,
        "language": language,
        "location": place,
        "block": PLACES[place][0],
        "created_at": created_at.isoformat(timespec="minutes"),
        "resolution_days": resolution_days(rng, category, urgency, created_at),
        "synthetic": "yes",
    }


def generate(total=TOTAL, seed=SEED):
    rng = random.Random(seed)
    rows = []

    # 1. A Wi-Fi outage spike: 14 IT complaints within one hour, 3 days ago (for spike detection).
    spike_start = (ANCHOR - timedelta(days=3)).replace(hour=21, minute=0)
    for i in range(14):
        place = rng.choice(["A Block Hostel", "B Block Hostel"])
        language = rng.choice(["en", "en", "ta", "ml", "mixed"])
        template = TEMPLATES["IT"][language][0]  # "Wi-Fi not working" in each language
        rows.append(make_row(rng, "IT", spike_start + timedelta(minutes=rng.randint(0, 55)), place, language, template))

    # 2. Normal complaints spread over 8 weeks, following CATEGORY_PLAN.
    for category, (count, _) in CATEGORY_PLAN.items():
        already = sum(r["category"] == category for r in rows)
        rows.extend(make_row(rng, category) for _ in range(count - already))

    rows.sort(key=lambda r: r["created_at"])
    for i, row in enumerate(rows[:total], start=1):
        row["id"] = i
    return rows[:total]


def main():
    out = Path(__file__).resolve().parent / "sample_complaints.csv"
    rows = generate()
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} synthetic complaints to {out}")


if __name__ == "__main__":
    main()
