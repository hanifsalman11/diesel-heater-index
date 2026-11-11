import os
import json
import re
import time
import math
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone

# ==========================================
# ENVIRONMENT CONFIGURATION
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "https://hanifsalman11.github.io/diesel-heater-index").rstrip("/")
INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7").strip()
CUSTOM_HEATER = os.environ.get("CUSTOM_HEATER", "").strip()
PAGES_PER_RUN = int(os.environ.get("PAGES_PER_RUN", "3"))

DOCS_DIR = "docs"
DATA_DIR = "data"
PUBLISHED_FILE = os.path.join(DATA_DIR, "published_heaters.json")
MONETIZATION_FILE = os.path.join(DATA_DIR, "monetization.json")

_CACHED_MODELS = None

# Format: (Heater / Vehicle Scenario, True Output kW, Space Volume Cu Ft, Max Fuel Burn L/hr, Min Fuel Burn L/hr, Max Pump Hz, Duct Dia mm)
SEED_HEATERS = [
    ("VEVOR 2kW 12V Diesel Air Heater (Campervan & Truck Cab)", 2.0, 260, 0.28, 0.12, 3.2, 60),
    ("VEVOR 5kW 12V All-in-One Diesel Air Heater (Garage & RV)", 4.8, 550, 0.48, 0.18, 4.5, 75),
    ("VEVOR 8kW 12V/24V Toolbox Diesel Heater (True 5kW Output)", 5.0, 600, 0.52, 0.20, 4.8, 75),
    ("Webasto Air Top 2000 STC (2.0 kW) 12V Diesel/Gas Van Heater", 2.0, 280, 0.24, 0.12, 3.1, 60),
    ("Webasto Air Top Evo 40 (4.0 kW) & Evo 55 (5.5 kW) Expedition", 4.0, 520, 0.45, 0.18, 4.3, 75),
    ("Espar / Eberspächer Airtronic S2 D2L (2.2 kW) Brushless 12V", 2.2, 300, 0.28, 0.10, 3.3, 60),
    ("Espar / Eberspächer Airtronic M2 D4L (4.0 kW) Large Van/Boat", 4.0, 540, 0.51, 0.16, 4.4, 75),
    ("Lavaner Pro 2kW Alpine (True 2.0 kW) High-Altitude Camper", 2.0, 270, 0.26, 0.11, 3.2, 60),
    ("Lavaner Pro 5kW Alpine (True 4.8 kW) 12V Diesel Heater", 4.8, 560, 0.48, 0.17, 4.5, 75),
    ("Hcalory 5kW–8kW Bluetooth All-in-One Portable Diesel Heater", 4.8, 520, 0.48, 0.18, 4.5, 75),
    ("Planar / Autoterm Air 2D (2.0 kW) & 4D (4.0 kW) Marine/Van", 2.0, 280, 0.24, 0.10, 3.1, 60),
    ("Maxpeedingrods 5kW 12V Bluetooth Diesel Heater Setup", 4.7, 500, 0.46, 0.18, 4.4, 75),
    ("LF Bros 5kW 12V/110V Dual-Power Portable Diesel Heater", 4.8, 520, 0.48, 0.18, 4.5, 75),
    ("Mercedes Sprinter 144 WB Campervan (2kW vs 5kW) Sizing", 2.0, 290, 0.26, 0.11, 3.2, 60),
    ("Mercedes Sprinter 170 & 170 EXT Campervan Winter Heater", 4.0, 440, 0.42, 0.16, 4.2, 75),
    ("Ford Transit 148 High-Roof Campervan Diesel Heater Sizing", 2.2, 330, 0.28, 0.12, 3.3, 60),
    ("Ram ProMaster 136 & 159 WB Campervan Diesel Heater Sizing", 2.2, 320, 0.27, 0.11, 3.2, 60),
    ("Overland Roof-Top Tent (RTT) & Truck Bed Camper 2kW Setup", 2.0, 140, 0.22, 0.10, 3.0, 60),
    ("Insulated Ice Fishing Shanty & Hub Shelter (8x8 / 8x16) Heater", 4.5, 420, 0.45, 0.17, 4.4, 75),
    ("2-Car Garage Workshop (480 Sq Ft) Single vs Dual 5kW/8kW", 5.0, 750, 0.52, 0.22, 4.8, 75),
    ("30-to-40 Ft Sailboat & Trawler Cabin Marine Diesel Heater", 4.0, 520, 0.44, 0.16, 4.2, 75),
    ("Semi-Truck Sleeper Cab 2kW 12V Overnight Idling Replacement", 2.0, 210, 0.24, 0.10, 3.1, 60),
    ("20-to-28 Ft Travel Trailer & Fifth-Wheel RV Diesel Conversion", 4.8, 580, 0.48, 0.18, 4.5, 75),
    ("School Bus Conversion (Skoolie 30-to-40 Ft) Dual Diesel Heater", 5.0, 850, 0.55, 0.22, 4.8, 75),
    ("Shipping Container Cabin (20 Ft & 40 Ft) Off-Grid Diesel Heater", 4.8, 650, 0.48, 0.18, 4.5, 75),
    ("2kW vs 5kW vs Fake 8kW Chinese Diesel Heater Truth & Sizing", 2.0, 280, 0.26, 0.11, 3.2, 60),
    ("High-Altitude (5,000–11,000 Ft) Fuel Pump Hz & Fan RPM Tuning", 2.0, 280, 0.22, 0.09, 2.4, 60),
    ("Diesel Heater E-01 / E-02 Undervoltage 12V Wire Gauge Fix", 4.8, 500, 0.48, 0.18, 4.5, 75),
    ("Jackery / EcoFlow 12V Cigarette Port 10A Trip vs 15A Glow Plug", 2.0, 260, 0.26, 0.11, 3.2, 60),
    ("Kerosene vs #1 Winter Diesel vs #2 Diesel Fuel Burn & Soot", 4.8, 520, 0.46, 0.17, 4.4, 75)
]


def load_json(filepath, default):
    """Self-healing JSON loader: otomatis pulih jika file korup atau kosong."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, type(default)) else default
        except Exception as e:
            print(f"[SELF-HEAL] Recovering {filepath} due to read notice: {e}")
    return default


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    return re.sub(r"[\s-]+", "-", text).strip("-")


def safe_float(val, default=2.0):
    try:
        cleaned = re.sub(r"[^0-9.]", "", str(val))
        return float(cleaned) if cleaned else float(default)
    except Exception:
        return float(default)


def build_amazon_url(search_keywords, mon_cfg):
    domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")
    encoded_q = urllib.parse.quote_plus(search_keywords)
    return f"https://{domain}/s?k={encoded_q}&tag={tag}"


def get_active_gemini_model(api_key):
    """
    LAPIS 1: Mesin Pemindai Versi Model Free Tier Otomatis berbasis Regex tanpa angka versi manual.
    Otomatis mendeteksi model Gemini Flash STABIL generasi tertinggi lintas tahun.
    """
    global _CACHED_MODELS
    if _CACHED_MODELS is not None:
        return _CACHED_MODELS

    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        req = urllib.request.Request(list_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            scored_models = []

            for m in data.get("models", []):
                name = m.get("name", "").replace("models/", "")
                methods = m.get("supportedGenerationMethods", [])

                if "generateContent" not in methods or "flash" not in name.lower():
                    continue

                if any(bad in name.lower() for bad in [
                    "preview", "exp", "thinking", "image", "tts", "audio", "vision", "8b"
                ]):
                    continue

                ver_match = re.search(r"gemini-(\d+(?:\.\d+)?)-flash", name.lower())
                if ver_match:
                    ver_num = float(ver_match.group(1))
                    if name.lower() == f"gemini-{ver_match.group(1)}-flash":
                        tier_score = 2
                    elif name.lower() == f"gemini-{ver_match.group(1)}-flash-lite":
                        tier_score = 1
                    else:
                        tier_score = 0
                    scored_models.append((ver_num, tier_score, name))
                elif name.lower() == "gemini-flash-latest":
                    scored_models.append((0.1, 0, name))

            if scored_models:
                scored_models.sort(key=lambda x: (x[0], x[1]), reverse=True)
                _CACHED_MODELS = [item[2] for item in scored_models[:2]]
                print(f"[GEMINI] Future-proof active models locked: {_CACHED_MODELS}")
                return _CACHED_MODELS
    except Exception as e:
        print(f"[WARN] Dynamic model discovery notice: {e}")

    _CACHED_MODELS = ["gemini-flash-latest"]
    return _CACHED_MODELS


def discover_google_heater_queries(published_slugs):
    """
    LAPIS 4: 3-Tier Infinite Keyword Supply:
    Tier A: Seed List -> Tier B: Google Suggest US -> Tier C: Combinatorial Space × Climate × Altitude Permutator.
    """
    discovered = []
    seeds = [
        "diesel heater fuel consumption ",
        "2kw vs 5kw diesel heater ",
        "vevor diesel heater ",
        "diesel heater battery calculator "
    ]
    for seed in seeds:
        try:
            url = f"http://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=us&q={urllib.parse.quote(seed)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for suggestion in data[1]:
                    cleaned = suggestion.lower()
                    for pref in seeds:
                        if "calculator" in pref:
                            cleaned = cleaned.replace(pref, "")
                    cleaned = re.sub(
                        r"\b(calculator|size|sizing|chart|manual|review|reddit|for)\b",
                        "",
                        cleaned
                    ).strip()
                    if 5 <= len(cleaned) <= 42:
                        kw_v = 2.0 if "2kw" in cleaned else 4.8
                        vol_v = 280 if kw_v <= 2.2 else 540
                        max_l = 0.26 if kw_v <= 2.2 else 0.48
                        min_l = 0.11 if kw_v <= 2.2 else 0.18
                        hz_v = 3.2 if kw_v <= 2.2 else 4.5
                        d_mm = 60 if kw_v <= 2.2 else 75
                        discovered.append((cleaned.title(), kw_v, vol_v, max_l, min_l, hz_v, d_mm))
        except Exception as e:
            print(f"[WARN] Google Suggest notice: {e}")

    # Tier C Fallback: Combinatorial Permutator (Anti-Habis Lintas Tahun)
    spaces = [
        ("Small Truck Camper & RTT (150 Cu Ft)", 2.0, 150, 0.24, 0.10, 3.1, 60),
        ("144 WB Campervan (280 Cu Ft)", 2.0, 280, 0.26, 0.11, 3.2, 60),
        ("170 EXT High-Roof Van (420 Cu Ft)", 4.0, 420, 0.42, 0.16, 4.2, 75),
        ("Canvas Wall Tent & Ice Shanty (480 Cu Ft)", 4.8, 480, 0.48, 0.18, 4.5, 75),
        ("26-Ft Travel Trailer RV (600 Cu Ft)", 4.8, 600, 0.48, 0.18, 4.5, 75),
        ("Off-Grid Tiny Cabin & Shop (750 Cu Ft)", 5.0, 750, 0.52, 0.20, 4.8, 75)
    ]
    climates = [
        ("Mild Winter (+25°F Outdoor)"),
        ("Freezing Winter (0°F Outdoor)"),
        ("Sub-Zero Arctic (-20°F Outdoor)"),
        ("High-Altitude Mountain (8,000 Ft)")
    ]
    for sp_desc, kw_o, vol_c, mx_l, mn_l, mx_hz, dct_m in spaces:
        for cl_desc in climates:
            combo_title = f"{sp_desc} in {cl_desc}"
            test_slug = slugify(f"{combo_title}-kw-fuel-wire-calculator")
            if test_slug not in published_slugs:
                discovered.append((combo_title, kw_o, vol_c, mx_l, mn_l, mx_hz, dct_m))
                if len(discovered) >= 25:
                    return discovered
    return discovered


def build_deterministic_heater_data(htr_tuple):
    """
    LAPIS 3: Mesin Fisika Pemanas Diesel (BTU/kW, Altitude Pump Hz, 12V Glow-Plug Wire AWG & Runtime) (100% Bebas Gagal).
    """
    model_name, true_kw, space_cuft, max_l_hr, min_l_hr, max_hz, duct_mm = htr_tuple

    # 1. Konversi Output Termal (1 kW = 3,412 BTU/hr):
    max_btu_hr = int(round(true_kw * 3412.0, -1))
    min_btu_hr = int(round(max_btu_hr * 0.32, -1))

    # 2. Konsumsi Solar Rata-Rata Semalam (10 Jam Tidur pada Modulasi Menengah 45%):
    avg_l_per_hr = round((min_l_hr * 0.60) + (max_l_hr * 0.40), 2)
    ten_hr_night_liters = round(avg_l_per_hr * 10.0, 2)
    ten_hr_night_gallons = round(ten_hr_night_liters / 3.7854, 2)
    runtime_10l_tank_hrs = round(10.0 / max(0.08, avg_l_per_hr), 1)

    # 3. Konsumsi Baterai 12V DC Semalam (10 Jam):
    # Glow Plug Ignition + Shutdown Cycle = 13.5 Amps (162W) selama 6 menit total = 1.35 Ah
    # Running Blower + Fuel Pump @ Medium = ~1.8 Amps (22W) x 10 jam = 18.0 Ah -> Total ~19.5 Ah per 10-hour night!
    glow_plug_surge_amps = 13.5
    running_avg_amps_12v = 1.8 if true_kw <= 2.5 else 2.4
    ten_hr_battery_ah = round(1.4 + (running_avg_amps_12v * 10.0), 1)
    nights_on_100ah_lifepo4 = round(90.0 / ten_hr_battery_ah, 1)

    # 4. Aturan Kabel 12V Anti-Error E-01/E-02 (<0.4V drop pada beban 13.5A Glow-Plug):
    # Untuk jarak 10 kaki (20 ft round-trip), gunakan 10 AWG; untuk 15-25 kaki, gunakan 8 AWG!
    wire_awg_10ft = "10 AWG Marine Tinned Copper (15A–20A Blade Fuse)"
    # 5. Koreksi Frekuensi Pompa Solar di Ketinggian 8,000 Kaki (-24% Oksigen -> Kurangi Max Hz sebesar 22%):
    altitude_8000ft_max_hz = round(max_hz * 0.78, 1)

    return {
        "heater_name": model_name,
        "duct_spec": f"{duct_mm}mm ({round(duct_mm/25.4, 1)}\") Hot-Air Duct",
        "seo_title": f"{model_name} kW/BTU, Fuel Burn, 12V Wire & Altitude Hz Calculator (2026)",
        "meta_description": f"Calculate exact diesel heater output ({true_kw} kW / {max_btu_hr:,} BTU/hr), 10-hour fuel burn ({ten_hr_night_liters}L / {ten_hr_night_gallons} gal), 12V battery draw ({ten_hr_battery_ah} Ah/night), E-01 {wire_awg_10ft.split()[0]} AWG wire, and 8,000-ft altitude Hz ({altitude_8000ft_max_hz} Hz) for {model_name}.",
        "specs": {
            "true_thermal_kw": true_kw,
            "max_btu_hr": max_btu_hr,
            "min_btu_hr": min_btu_hr,
            "recommended_volume_cuft": space_cuft,
            "fuel_burn_min_l_hr": min_l_hr,
            "fuel_burn_max_l_hr": max_l_hr,
            "fuel_burn_avg_l_hr": avg_l_per_hr,
            "ten_hour_night_liters": ten_hr_night_liters,
            "ten_hour_night_gallons": ten_hr_night_gallons,
            "ten_liter_tank_runtime_hrs": runtime_10l_tank_hrs,
            "glow_plug_startup_amps": glow_plug_surge_amps,
            "running_avg_amps_12v": running_avg_amps_12v,
            "ten_hour_battery_ah": ten_hr_battery_ah,
            "nights_on_100ah_lifepo4": nights_on_100ah_lifepo4,
            "sea_level_max_pump_hz": max_hz,
            "altitude_8000ft_max_hz": altitude_8000ft_max_hz,
            "recommended_12v_wire_awg": wire_awg_10ft,
            "duct_diameter_mm": duct_mm
        },
        "thermal_verdict": f"Delivering {true_kw} kW ({min_btu_hr:,} to {max_btu_hr:,} BTU/hr across a {duct_mm}mm duct), {model_name} is ideally matched to spaces around {space_cuft:,} cu. ft. so the burner runs at a clean, hot medium-high modulation without carbon-sooting the glow-plug screen. Over a 10-hour winter night, it burns ~{ten_hr_night_liters} Liters ({ten_hr_night_gallons} US gallons, lasting {runtime_10l_tank_hrs} hours on a standard 10L tank) and consumes {ten_hr_battery_ah} Ah from a 12V battery ({nights_on_100ah_lifepo4} nights on a 12V 100Ah LiFePO4 pack). To eliminate E-01/E-02 startup undervoltage cutouts during the {glow_plug_surge_amps}A (162W) glow-plug cycle, wire directly to the battery busbar with {wire_awg_10ft}. Above 8,000 ft elevation, derate max fuel pump frequency from {max_hz} Hz down to {altitude_8000ft_max_hz} Hz.",
        "hardware_bundle": [
            {
                "badge": f"{true_kw:g} kW ({max_btu_hr:,} BTU) Heater",
                "title": f"{model_name} w/ Plateau Altitude LCD Controller & Remote",
                "price_range": "$119 - $989",
                "amazon_query": f"12V {int(round(true_kw))}kW Diesel Air Heater Plateau Controller Campervan",
                "htr_note": f"Automatic barometric/manual Hz control burns {avg_l_per_hr} L/hr cleanly from sea level up to 12,000 feet."
            },
            {
                "badge": f"12V 100Ah LiFePO4 ({nights_on_100ah_lifepo4} Nights)",
                "title": "12V 100Ah Low-Temp Cut-Off Deep-Cycle LiFePO4 Battery + 10 AWG Marine Tinned Copper Wire Kit",
                "price_range": "$189 - $349",
                "amazon_query": "12V 100Ah LiFePO4 Battery Low Temp Cut Off 10 AWG Marine Wire",
                "htr_note": f"Holds rock-steady 13.2V during the {glow_plug_surge_amps}A glow-plug startup surge—stopping E-01 undervoltage errors permanently."
            },
            {
                "badge": "Stainless Turret & Heat Wrap",
                "title": "316 Stainless Steel Floor Turret Mounting Plate (40mm–75mm Depth) + Titanium Exhaust Wrap & Muffler",
                "price_range": "$44 - $119",
                "amazon_query": "Diesel Heater Stainless Steel Turret Plate Titanium Exhaust Wrap Muffler",
                "htr_note": "Seals the hot exhaust flange safely through thick insulated campervan floors without charring subfloor plywood."
            },
            {
                "badge": f"Quiet Pump & {duct_mm}mm Duct Kit",
                "title": f"Ultra-Quiet Low-Pulse Dosing Fuel Pump + Aluminum Diesel Filter & {duct_mm}mm Y-Splitter Duct Kit",
                "price_range": "$48 - $129",
                "amazon_query": f"Diesel Heater Quiet Fuel Pump {duct_mm}mm Ducting Y Splitter Filter",
                "htr_note": "Isolates the annoying 'tick-tick-tick' solenoid pump noise and splits warm airflow evenly to bed and floor zones."
            }
        ],
        "builder_checklist": [
            f"Never Oversize a 5kW/8kW Heater into a Small Campervan (<320 cu. ft.)! Note that '8kW' Chinese diesel heaters use the exact same 140mm aluminum heat exchanger casting as a 5kW heater and output ~4.8–5.0 kW max. If you put a 5kW/8kW heater in a small van, it will bake you out and idle at 1.2 Hz Low all night—causing cold combustion that clogs the burner mesh with black carbon soot in 40 hours.",
            f"Fix Error E-01 / E-02 (Undervoltage) & Cigarette-Lighter Trips: the silicon nitride glow plug draws 11A to 15A (~165W) for 3 minutes during startup AND shutdown. Factory 16 AWG wires or 10A portable power station cigarette ports drop below 10.5V and trip out. Wire {wire_awg_10ft} directly to your 12V battery or use a 12V-to-12V 20A DC converter.",
            "Mount the Dosing Fuel Pump at a 15° to 35° Upward Angle (outlet pointing up) using a soft rubber isolation mount and stiff 2mm ID nylon fuel line (not soft blue/green silicone tube, which balloons with each pulse and starves the burner).",
            f"Tune Air-Fuel Ratio for High Altitude (>5,000 ft) & Never Cut 12V Power Abruptly: at 8,000 ft, air has 24% less oxygen, so lower max pump frequency from {max_hz} Hz to ~{altitude_8000ft_max_hz} Hz. Always shut down via the LCD power button and wait 5 minutes for the fan cooldown cycle so residual heat doesn't melt the plastic ECU board."
        ],
        "faqs": [
            {
                "q": f"Should I buy a 2kW or 5kW/8kW diesel heater for {model_name}?",
                "a": f"For spaces up to 320 cu. ft. (Sprinter 144, Transit 148, truck campers, roof-top tents), a 2kW heater (6,824 BTU/hr, 60mm duct) is far superior because it runs at medium-high output where combustion stays above 550°C and burns off carbon soot. Use a 5kW ('8kW' marketed, 16,300+ BTU/hr, 75mm duct) only for spaces over 400 cu. ft., uninsulated ice shanties, or garages."
            },
            {
                "q": f"How much diesel fuel and 12V battery Ah does {model_name} use per night?",
                "a": f"Burning {min_l_hr} L/hr on Low and {max_l_hr} L/hr on High (~{avg_l_per_hr} L/hr average), a 10-hour winter night uses {ten_hr_night_liters} Liters ({ten_hr_night_gallons} gallons), giving ~{runtime_10l_tank_hrs} hours on a 10-Liter tank. Electrically, it uses ~{ten_hr_battery_ah} Ah per 10-hour night (including the {glow_plug_surge_amps}A glow-plug start/stop cycles and {running_avg_amps_12v}A fan run)."
            },
            {
                "q": f"What wire gauge do I need to stop E-01 undervoltage errors on a 12V diesel heater?",
                "a": f"During the 3-minute glow-plug ignition and shutdown burn-off, current spikes to {glow_plug_surge_amps} Amps. To keep voltage at the heater's internal ECU above the 10.8V low-voltage cutoff, cut off the thin factory harness and run {wire_awg_10ft} for runs up to 12 feet (or 8 AWG for 15–25 feet)."
            }
        ]
    }


def generate_heater_data(htr_tuple):
    """
    LAPIS 2: Memanggil model Gemini stabil dengan proteksi Cooldown HTTP 429 & Fallback Otomatis.
    """
    if not GEMINI_API_KEY:
        return build_deterministic_heater_data(htr_tuple)

    model_name, true_kw, space_cuft, max_l_hr, min_l_hr, max_hz, duct_mm = htr_tuple
    det_fallback = build_deterministic_heater_data(htr_tuple)
    sp = det_fallback["specs"]

    prompt = f"""
You are a Certified Master RV/Campervan Upfitter & Hydronic/Air Diesel Heating Engineer (Webasto / Espar / Autoterm Specialist). Create an accurate 2026 12V/24V diesel air heater kW/BTU sizing, fuel consumption (L/hr & Gal/night), 12V battery Ah draw, E-01 glow-plug wire gauge, and high-altitude pump Hz tuning guide for: "{model_name}".
Baseline specs: True Output={true_kw} kW ({sp['min_btu_hr']}-{sp['max_btu_hr']} BTU/hr, {duct_mm}mm duct), Ideal Space={space_cuft} cu ft, Fuel Burn={min_l_hr}-{max_l_hr} L/hr (Avg={sp['fuel_burn_avg_l_hr']} L/hr -> {sp['ten_hour_night_liters']}L / {sp['ten_hour_night_gallons']} gal per 10h night, {sp['ten_liter_tank_runtime_hrs']}h on 10L tank), 12V Draw={sp['glow_plug_startup_amps']}A Glow-Plug Surge / {sp['running_avg_amps_12v']}A Run ({sp['ten_hour_battery_ah']} Ah per 10h night -> {sp['nights_on_100ah_lifepo4']} nights on 100Ah LiFePO4, Wire={sp['recommended_12v_wire_awg']}), Altitude Pump Hz={max_hz} Hz Sea Level -> {sp['altitude_8000ft_max_hz']} Hz @ 8,000 ft.
Return ONLY a valid JSON object matching this exact schema:
{{
  "heater_name": "{model_name}",
  "duct_spec": "{duct_mm}mm Hot-Air Duct",
  "seo_title": "{model_name} kW/BTU, Fuel Burn, 12V Wire & Altitude Hz Calculator (2026)",
  "meta_description": "Calculate exact diesel heater kW/BTU output, 10-hour fuel and 12V battery Ah consumption, E-01 glow-plug wire gauge, and high-altitude pump Hz for {model_name}.",
  "specs": {{
    "true_thermal_kw": {true_kw},
    "max_btu_hr": {sp['max_btu_hr']},
    "min_btu_hr": {sp['min_btu_hr']},
    "recommended_volume_cuft": {space_cuft},
    "fuel_burn_min_l_hr": {min_l_hr},
    "fuel_burn_max_l_hr": {max_l_hr},
    "fuel_burn_avg_l_hr": {sp['fuel_burn_avg_l_hr']},
    "ten_hour_night_liters": {sp['ten_hour_night_liters']},
    "ten_hour_night_gallons": {sp['ten_hour_night_gallons']},
    "ten_liter_tank_runtime_hrs": {sp['ten_liter_tank_runtime_hrs']},
    "glow_plug_startup_amps": {sp['glow_plug_startup_amps']},
    "running_avg_amps_12v": {sp['running_avg_amps_12v']},
    "ten_hour_battery_ah": {sp['ten_hour_battery_ah']},
    "nights_on_100ah_lifepo4": {sp['nights_on_100ah_lifepo4']},
    "sea_level_max_pump_hz": {max_hz},
    "altitude_8000ft_max_hz": {sp['altitude_8000ft_max_hz']},
    "recommended_12v_wire_awg": "{sp['recommended_12v_wire_awg']}",
    "duct_diameter_mm": {duct_mm}
  }},
  "thermal_verdict": "3-sentence technical summary stating true kW/BTU output, 10-hour fuel liters/gallons and 12V battery Ah consumption, 10 AWG wire fix for E-01 glow-plug voltage drop, and 8,000-ft pump Hz derating.",
  "hardware_bundle": [
    {{
      "badge": "{true_kw:g} kW ({sp['max_btu_hr']:,} BTU) Heater",
      "title": "{model_name} w/ Plateau Altitude LCD Controller & Remote",
      "price_range": "$119 - $989",
      "amazon_query": "12V {int(round(true_kw))}kW Diesel Air Heater Plateau Controller Campervan",
      "htr_note": "1-sentence clean combustion and altitude Hz note"
    }},
    {{
      "badge": "12V 100Ah LiFePO4 & 10 AWG",
      "title": "12V 100Ah Low-Temp Cut-Off LiFePO4 Battery + 10 AWG Marine Tinned Copper Wire",
      "price_range": "$189 - $349",
      "amazon_query": "12V 100Ah LiFePO4 Battery Low Temp Cut Off 10 AWG Marine Wire",
      "htr_note": "1-sentence 15A glow-plug surge support and anti-E-01 note"
    }},
    {{
      "badge": "Stainless Turret & Wrap",
      "title": "316 Stainless Steel Floor Turret Plate + Titanium Exhaust Wrap & Muffler",
      "price_range": "$44 - $119",
      "amazon_query": "Diesel Heater Stainless Steel Turret Plate Titanium Exhaust Wrap",
      "htr_note": "1-sentence subfloor heat isolation and safe exhaust routing note"
    }},
    {{
      "badge": "Quiet Pump & {duct_mm}mm Duct",
      "title": "Ultra-Quiet Dosing Fuel Pump + Aluminum Diesel Filter & {duct_mm}mm Y-Duct Kit",
      "price_range": "$48 - $129",
      "amazon_query": "Diesel Heater Quiet Fuel Pump {duct_mm}mm Ducting Y Splitter Filter",
      "htr_note": "1-sentence pulse noise reduction and air distribution note"
    }}
  ],
  "builder_checklist": [
    "Step 1 regarding why 2kW beats 5kW/8kW in small campervans to prevent carbon sooting",
    "Step 2 regarding 10 AWG direct battery wiring to stop E-01 15A glow-plug cutouts",
    "Step 3 regarding 15-to-35 degree fuel pump mounting angle and rigid 2mm nylon fuel line",
    "Step 4 regarding high-altitude pump Hz reduction and mandatory 5-minute shutdown cooldown"
  ],
  "faqs": [
    {{"q": "How much fuel and battery power does {model_name} use overnight?", "a": "Exact L/hr, gallons per 10-hour night, 10L tank hours, and 12V Ah used."}},
    {{"q": "Why does my diesel heater show Error E-01 or E-02 on startup?", "a": "Direct electrical explanation of the 13.5A-15A glow-plug voltage drop and 10 AWG wire fix."}},
    {{"q": "How do I tune a diesel heater for high altitude above 5,000 feet?", "a": "Exact pump Hz reduction from {max_hz} Hz to {sp['altitude_8000ft_max_hz']} Hz to prevent rich black smoke."}}
  ]
}}
"""

    for model_id in get_active_gemini_model(GEMINI_API_KEY):
        for attempt in range(2):
            try:
                endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.2,
                        "responseMimeType": "application/json"
                    }
                }
                req = urllib.request.Request(
                    endpoint,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=40) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                    raw_text = re.sub(r"\s*```$", "", raw_text)
                    parsed = json.loads(raw_text)
                    if "specs" in parsed and "hardware_bundle" in parsed:
                        time.sleep(6)
                        return parsed
            except urllib.error.HTTPError as he:
                if he.code == 429:
                    print(f"[RATE-LIMIT] HTTP 429 on {model_id} (attempt {attempt + 1}). Cooling down 20s...")
                    time.sleep(20)
                else:
                    print(f"[WARN] HTTP {he.code} on {model_id} for '{model_name}': {he}")
                    break
            except Exception as e:
                print(f"[WARN] Gemini ({model_id}) notice for '{model_name}': {e}")
                break

    return det_fallback


def build_heater_html_page(data, slug, mon_cfg):
    htr_name = data.get("heater_name", "12V Diesel Air Heater System")
    sp = data.get("specs", {})
    kw = round(safe_float(sp.get("true_thermal_kw", 2.0), 2.0), 1)
    btu_max = int(safe_float(sp.get("max_btu_hr", 6824), 6824))
    vol_cu = int(safe_float(sp.get("recommended_volume_cuft", 280), 280))
    night_l = round(safe_float(sp.get("ten_hour_night_liters", 1.8), 1.8), 2)
    night_gal = round(safe_float(sp.get("ten_hour_night_gallons", 0.48), 0.48), 2)
    tank_hrs = round(safe_float(sp.get("ten_liter_tank_runtime_hrs", 55.0), 55.0), 1)
    night_ah = round(safe_float(sp.get("ten_hour_battery_ah", 19.4), 19.4), 1)
    sea_hz = round(safe_float(sp.get("sea_level_max_pump_hz", 3.2), 3.2), 1)
    alt_hz = round(safe_float(sp.get("altitude_8000ft_max_hz", 2.5), 2.5), 1)
    duct_m = int(safe_float(sp.get("duct_diameter_mm", 60), 60))

    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "12V+Diesel+Air+Heater+2kW+5kW+Turret+Plate+LiFePO4"), mon_cfg)

    schema_graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "SoftwareApplication",
                "name": f"{htr_name} Fuel, Battery Ah & Altitude Hz Calculator",
                "applicationCategory": "UtilitiesApplication",
                "operatingSystem": "Web Browser",
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": f.get("q", ""),
                        "acceptedAnswer": {"@type": "Answer", "text": f.get("a", "")}
                    } for f in data.get("faqs", [])
                ]
            }
        ]
    }

    bundle_html = ""
    for item in data.get("hardware_bundle", []):
        amz_url = build_amazon_url(item.get("amazon_query", item.get("title", "12V Diesel Air Heater")), mon_cfg)
        bundle_html += f"""
        <div class="bg-zinc-900 border border-zinc-800 rounded-xl p-5 flex flex-col justify-between hover:border-orange-500/60 transition">
          <div>
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="text-xs font-bold uppercase tracking-wider bg-orange-500/10 text-orange-400 border border-orange-500/20 px-2.5 py-0.5 rounded">{item.get('badge', 'Diesel Heater Gear')}</span>
              <span class="text-sm font-bold text-emerald-400">{item.get('price_range', '$48+')}</span>
            </div>
            <h3 class="text-base font-bold text-white mt-2">{item.get('title', '')}</h3>
            <p class="text-xs text-zinc-400 mt-2 leading-relaxed">🔥 {item.get('htr_note', '')}</p>
          </div>
          <a href="{amz_url}" target="_blank" rel="nofollow sponsored" class="mt-5 block text-center bg-orange-500 hover:bg-orange-400 text-zinc-950 font-extrabold py-2.5 px-4 rounded-lg text-sm transition shadow-lg">
            Check Price on Amazon →
          </a>
        </div>"""

    # Build Heater Size vs BTU, Fuel Burn, 12V Battery Ah & Altitude Hz Reference Matrix Table
    htr_tiers = [
        ("2kW Compact (60mm Duct)", "6,824 BTU/hr", "0.11 – 0.26 L/hr (~1.8L/Night)", "19.5 Ah / 10h Night", "1.2–3.2 Hz (2.5 Hz @ 8k ft)"),
        ("4kW Mid-Size (75mm Duct)", "13,648 BTU/hr", "0.16 – 0.44 L/hr (~2.8L/Night)", "23.0 Ah / 10h Night", "1.5–4.3 Hz (3.3 Hz @ 8k ft)"),
        ("5kW Standard (75mm Duct)", "16,378 BTU/hr", "0.18 – 0.48 L/hr (~3.0L/Night)", "25.5 Ah / 10h Night", "1.6–4.5 Hz (3.5 Hz @ 8k ft)"),
        ("'8kW' All-in-One (True 5.0 kW)", "17,060 BTU/hr", "0.20 – 0.52 L/hr (~3.3L/Night)", "26.5 Ah / 10h Night", "1.7–4.8 Hz (3.7 Hz @ 8k ft)"),
        ("Dual 5kW Shop Setup", "32,750 BTU/hr", "0.36 – 0.96 L/hr (~6.0L/Night)", "51.0 Ah / 10h Night", "2× 10 AWG Circuits (20A Fuse)")
    ]
    matrix_rows_html = ""
    for h_lbl, b_lbl, f_lbl, a_lbl, z_lbl in htr_tiers:
        matrix_rows_html += f"""
        <tr class="border-b border-zinc-800 hover:bg-zinc-800/40">
          <td class="py-3 px-4 font-bold text-white">{h_lbl}</td>
          <td class="py-3 px-4 font-bold text-orange-400">{b_lbl}</td>
          <td class="py-3 px-4 text-emerald-400 font-semibold">{f_lbl}</td>
          <td class="py-3 px-4 text-zinc-300">{a_lbl}</td>
          <td class="py-3 px-4 text-xs text-zinc-300">{z_lbl}</td>
        </tr>"""

    checklist_html = ""
    for idx, step_text in enumerate(data.get("builder_checklist", []), start=1):
        checklist_html += f"""
        <label class="flex items-start gap-3.5 bg-zinc-900 border border-zinc-800 rounded-xl p-4 cursor-pointer hover:border-zinc-700 transition">
          <input type="checkbox" class="mt-1 w-5 h-5 accent-orange-500 rounded cursor-pointer htr-check">
          <span class="text-sm text-zinc-200 leading-relaxed"><strong>Upfitter Step {idx}:</strong> {step_text}</span>
        </label>"""

    faqs_html = "".join([
        f"<div class='bg-zinc-900 border border-zinc-800 rounded-xl p-5'><h3 class='font-bold text-white text-base mb-2'>{f.get('q', '')}</h3><p class='text-sm text-zinc-300 leading-relaxed'>{f.get('a', '')}</p></div>"
        for f in data.get("faqs", [])
    ])

    canonical_url = f"{SITE_BASE_URL}/{slug}.html"
    amz_domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    amz_tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")

    html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{data.get('seo_title', htr_name)}</title>
  <meta name="description" content="{data.get('meta_description', '')}">
  <link rel="canonical" href="{canonical_url}">
  <meta property="og:title" content="{data.get('seo_title', htr_name)}">
  <meta property="og:description" content="{data.get('meta_description', '')}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{canonical_url}">
  <script src="https://cdn.tailwindcss.com"></script>
  <script type="application/ld+json">{json.dumps(schema_graph)}</script>
</head>
<body class="bg-zinc-950 text-zinc-100 antialiased min-h-screen flex flex-col">
  <header class="border-b border-zinc-800 bg-zinc-900/80 backdrop-blur sticky top-0 z-30">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <a href="index.html" class="text-lg font-black tracking-tight text-white flex items-center gap-2">
        <span class="bg-orange-500 text-zinc-950 px-2 py-0.5 rounded font-black">DIESEL</span>HeaterIndex
      </a>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-orange-500 hover:bg-orange-400 text-zinc-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop 12V Diesel Heaters & Kits →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-10 flex-1 w-full">
    <div class="mb-8">
      <div class="flex flex-wrap items-center gap-2.5 mb-3">
        <span class="text-xs font-extrabold uppercase tracking-widest bg-orange-500 text-zinc-950 px-3 py-1 rounded-full">{kw:g} kW ({btu_max:,} BTU/hr | {duct_m}mm)</span>
        <span class="text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-full">10h Night: {night_l}L ({night_gal} Gal) | {night_ah} Ah</span>
        <span class="text-xs font-semibold bg-zinc-800 text-zinc-300 px-3 py-1 rounded-full">Pump: {sea_hz} Hz ({alt_hz} Hz @ 8k ft) | 10 AWG</span>
      </div>
      <h1 class="text-3xl sm:text-4xl font-black text-white leading-tight">{data.get('seo_title', htr_name)}</h1>
      <div class="mt-4 bg-zinc-900 border-l-4 border-orange-500 p-4 rounded-r-xl text-sm text-zinc-200 leading-relaxed">
        <strong>Campervan Thermal, 12V Glow-Plug & Altitude Verdict:</strong> {data.get('thermal_verdict', '')}
      </div>
    </div>

    <!-- INTERACTIVE DIESEL HEATER KW SIZING, FUEL/BATTERY RUNTIME & ALTITUDE HZ CALCULATOR -->
    <section class="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 sm:p-8 mb-12 shadow-2xl">
      <h2 class="text-xl font-extrabold text-white mb-2">Interactive {htr_name} Fuel, Battery & Altitude Calculator</h2>
      <p class="text-xs text-zinc-400 mb-6">Adjust your campervan/tent/garage volume, heater kW tier, elevation altitude, and 12V wire length to calculate overnight fuel burn, 12V Ah draw, E-01 wire gauge, and high-altitude fuel pump Hz.</p>

      <div class="grid md:grid-cols-2 gap-8 items-center">
        <div class="space-y-5">
          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="volSlider" class="text-zinc-300">Heated Van, Tent, or Cabin Volume (Cubic Feet)</label>
              <span class="text-orange-400 font-bold"><span id="volVal">{vol_cu:,}</span> cu ft</span>
            </div>
            <input id="volSlider" type="range" min="100" max="1200" step="20" value="{vol_cu}" class="w-full accent-orange-500 cursor-pointer">
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label for="htrSelect" class="block text-xs font-medium text-zinc-400 mb-1">Heater Size & Modulation</label>
              <select id="htrSelect" class="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-orange-500">
                <option value="2.0|0.18|1.8|3.2" {"selected" if kw <= 2.5 else ""}>2kW Heater (60mm — Avg 0.18 L/hr)</option>
                <option value="4.8|0.30|2.4|4.5" {"selected" if kw > 2.5 else ""}>5kW / 8kW Heater (75mm — Avg 0.30 L/hr)</option>
              </select>
            </div>
            <div>
              <label for="altSelect" class="block text-xs font-medium text-zinc-400 mb-1">Camping Elevation (Altitude)</label>
              <select id="altSelect" class="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-orange-500">
                <option value="1.00" selected>Sea Level – 3,000 ft (100% Pump Hz)</option>
                <option value="0.86">5,000 ft Mountain (-14% Pump Hz)</option>
                <option value="0.78">8,000 ft Alpine Pass (-22% Pump Hz)</option>
                <option value="0.68">11,000 ft High Rockies (-32% Pump Hz)</option>
              </select>
            </div>
          </div>

          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="wireSlider" class="text-zinc-300">12V Power Cable Distance from Battery to Heater (Feet)</label>
              <span class="text-orange-400 font-bold"><span id="wireDistVal">10</span> ft Run</span>
            </div>
            <input id="wireSlider" type="range" min="3" max="30" step="1" value="10" class="w-full accent-orange-500 cursor-pointer">
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="bg-zinc-950 border border-orange-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-orange-400 font-bold">10-Hr Night Fuel & Tank</span>
            <div class="text-xl sm:text-2xl font-black text-white mt-1"><span id="fuelOut">{night_l}L</span> <span class="text-xs font-normal text-zinc-400">({night_gal} Gal)</span></div>
            <p id="tankHrsOut" class="text-xs text-orange-400 font-semibold mt-1">10L Tank Lasts ~{tank_hrs} Hrs</p>
          </div>

          <div class="bg-zinc-950 border border-emerald-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-emerald-400 font-bold">12V Battery & Pump Hz</span>
            <div class="text-xl sm:text-2xl font-black text-emerald-400 mt-1"><span id="ahOut">{night_ah}</span> <span class="text-xs font-normal text-zinc-400">Ah/Night</span></div>
            <p id="hzWireOut" class="text-xs text-zinc-300 font-semibold mt-1">Max {sea_hz} Hz | 10 AWG Wire</p>
          </div>
        </div>
      </div>

      <div class="mt-6 bg-orange-950/40 border border-orange-500/30 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div id="htrAdviceBanner" class="text-sm text-orange-100 font-medium"></div>
        <a id="dynamicHtrBtn" href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="shrink-0 bg-orange-500 hover:bg-orange-400 text-zinc-950 font-extrabold px-4 py-2.5 rounded-lg text-xs uppercase tracking-wider transition">
          Shop Matched Diesel Heater & Turret Kit on Amazon →
        </a>
      </div>
    </section>

    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Complete {htr_name} Heater, LiFePO4 & Turret Bundle</h2>
        <span class="text-xs text-zinc-400">Plateau Altitude Ready & E-01 Surge Protected</span>
      </div>
      <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">{bundle_html}</div>
    </section>

    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-4">12V Diesel Air Heater kW, BTU Output, Overnight Fuel Burn & Altitude Hz Chart</h2>
      <div class="overflow-x-auto bg-zinc-900 border border-zinc-800 rounded-xl">
        <table class="w-full text-left border-collapse text-sm">
          <thead>
            <tr class="border-b border-zinc-800 bg-zinc-950/60 text-zinc-400 uppercase text-xs">
              <th class="py-3.5 px-4">Heater Tier & Duct</th>
              <th class="py-3.5 px-4 text-orange-400">Max Thermal BTU</th>
              <th class="py-3.5 px-4 text-emerald-400">Fuel Burn (L/hr & Night)</th>
              <th class="py-3.5 px-4">12V Battery Draw</th>
              <th class="py-3.5 px-4">Pump Hz (Sea vs 8k ft)</th>
            </tr>
          </thead>
          <tbody>{matrix_rows_html}</tbody>
        </table>
      </div>
    </section>

    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Master Upfitter Anti-Sooting, E-01 10-AWG Wire & Fuel Pump Angle Checklist</h2>
        <span id="htrBadge" class="text-xs font-bold bg-zinc-800 text-orange-400 px-3 py-1 rounded-full">0 / 4 Completed</span>
      </div>
      <div class="space-y-3">{checklist_html}</div>
    </section>

    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-5">Frequently Asked Questions ({htr_name})</h2>
      <div class="space-y-4">{faqs_html}</div>
    </section>
  </main>

  <footer class="border-t border-zinc-800 py-8 text-center text-xs text-zinc-500 px-4">
    <p>© {datetime.now(timezone.utc).year} DieselHeaterIndex. Independent 12V/24V Diesel Air Heater Sizing, Altitude Hz & Electrical Database. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const amzDomain = "{amz_domain}";
    const amzTag = "{amz_tag}";

    const volSlider = document.getElementById('volSlider');
    const htrSelect = document.getElementById('htrSelect');
    const altSelect = document.getElementById('altSelect');
    const wireSlider = document.getElementById('wireSlider');
    const volVal = document.getElementById('volVal');
    const wireDistVal = document.getElementById('wireDistVal');
    const fuelOut = document.getElementById('fuelOut');
    const tankHrsOut = document.getElementById('tankHrsOut');
    const ahOut = document.getElementById('ahOut');
    const hzWireOut = document.getElementById('hzWireOut');
    const htrAdviceBanner = document.getElementById('htrAdviceBanner');
    const dynamicHtrBtn = document.getElementById('dynamicHtrBtn');

    function recalculateHeater() {{
      const volCu = parseInt(volSlider.value, 10);
      const htrParts = htrSelect.value.split('|');
      const kw = parseFloat(htrParts[0]);
      const avgLHr = parseFloat(htrParts[1]);
      const runAmps = parseFloat(htrParts[2]);
      const baseMaxHz = parseFloat(htrParts[3]);
      const altMult = parseFloat(altSelect.value);
      const wireFt = parseInt(wireSlider.value, 10);

      volVal.textContent = volCu.toLocaleString();
      wireDistVal.textContent = wireFt;

      const adjLHr = avgLHr * altMult;
      const nightL = (adjLHr * 10.0).toFixed(2);
      const nightGal = (parseFloat(nightL) / 3.7854).toFixed(2);
      const tankHrs = (10.0 / adjLHr).toFixed(1);

      const nightAh = (1.4 + (runAmps * 10.0)).toFixed(1);
      const maxHz = (baseMaxHz * altMult).toFixed(1);

      let wireAwg = "10 AWG";
      if (wireFt <= 8) wireAwg = "12 AWG / 10 AWG";
      else if (wireFt <= 16) wireAwg = "10 AWG Copper";
      else wireAwg = "8 AWG Copper";

      const recSize = volCu <= 340 ? "2kW (60mm Duct)" : "5kW (75mm Duct)";
      const sootWarn = (volCu < 300 && kw > 3.0) ? " ⚠️ <em>(Note: A 2kW heater is better for <300 ft³ to prevent Low-idle carbon sooting!)</em>" : "";

      fuelOut.textContent = `${{nightL}}L`;
      fuelOut.nextElementSibling.textContent = `(${{nightGal}} Gal)`;
      tankHrsOut.textContent = `10L Tank Lasts ~${{tankHrs}} Hrs`;
      ahOut.textContent = nightAh;
      hzWireOut.textContent = `Max ${{maxHz}} Hz | ${{wireAwg}}`;

      htrAdviceBanner.innerHTML = `🔥 <strong>Upfitter Spec:</strong> For ${{volCu}} ft³, install a <strong>12V ${{recSize}} Diesel Heater</strong> on a <strong>Stainless Floor Turret Plate</strong>, wired with <strong>${{wireAwg}} (20A Blade Fuse)</strong> to a <strong>12V 100Ah LiFePO4 Battery</strong>. Set max fuel pump to <strong>${{maxHz}} Hz</strong>.${{sootWarn}}`;
      dynamicHtrBtn.href = `https://${{amzDomain}}/s?k=12V+${{volCu <= 340 ? '2kW' : '5kW'}}+Diesel+Air+Heater+Stainless+Turret+Plate+100Ah+LiFePO4&tag=${{amzTag}}`;
    }}

    volSlider.addEventListener('input', recalculateHeater);
    htrSelect.addEventListener('change', recalculateHeater);
    altSelect.addEventListener('change', recalculateHeater);
    wireSlider.addEventListener('input', recalculateHeater);
    recalculateHeater();

    const checks = document.querySelectorAll('.htr-check');
    const badge = document.getElementById('htrBadge');
    checks.forEach(ch => {{
      ch.addEventListener('change', () => {{
        const done = Array.from(checks).filter(c => c.checked).length;
        badge.textContent = `${{done}} / ${{checks.length}} Completed`;
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
        f.write(html)


def rebuild_portal_sitemap_and_rss(published, mon_cfg):
    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "12V+Diesel+Air+Heater+2kW+5kW+Turret+Plate+LiFePO4"), mon_cfg)

    cards_html = ""
    for item in reversed(published):
        cards_html += f"""
        <a href="{item['slug']}.html" class="block bg-zinc-900 border border-zinc-800 hover:border-orange-500/60 rounded-xl p-5 transition group">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-black uppercase bg-orange-500 text-zinc-950 px-2.5 py-0.5 rounded">{item.get('kw', 2.0):g} kW ({item.get('btu', 6824):,} BTU)</span>
            <span class="text-xs text-zinc-400">{item.get('night_l', 1.8)}L / {item.get('night_ah', 19.4)}Ah Night</span>
          </div>
          <h2 class="text-base font-bold text-white group-hover:text-orange-400 transition">{item['heater_name']}</h2>
          <p class="text-xs text-zinc-400 mt-2 line-clamp-2">{item['description']}</p>
          <span class="inline-block mt-4 text-xs font-extrabold text-orange-400">Calculate Fuel, 12V Ah & Altitude Hz →</span>
        </a>"""

    index_html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DieselHeaterIndex — 12V Diesel Air Heater 2kW vs 5kW, Fuel Burn, Wire Gauge & Altitude Hz Calculator (2026)</title>
  <meta name="description" content="Calculate exact 12V/24V 2kW, 5kW, and 8kW diesel air heater BTU sizing, overnight fuel consumption (L/hr and gallons), 12V battery Ah draw, E-01 glow-plug wire gauge, and high-altitude pump Hz for campervans, tents, garages, and boats.">
  <link rel="canonical" href="{SITE_BASE_URL}/">
  <link rel="alternate" type="application/rss+xml" title="DieselHeaterIndex RSS Feed" href="{SITE_BASE_URL}/rss.xml">
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-zinc-950 text-zinc-100 min-h-screen flex flex-col">
  <header class="border-b border-zinc-800 bg-zinc-900/80 sticky top-0 z-30 backdrop-blur">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <div class="text-lg font-black text-white flex items-center gap-2">
        <span class="bg-orange-500 text-zinc-950 px-2 py-0.5 rounded font-black">DIESEL</span>HeaterIndex
      </div>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-orange-500 hover:bg-orange-400 text-zinc-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop 12V Diesel Heaters & Kits →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-12 flex-1 w-full">
    <div class="text-center max-w-2xl mx-auto mb-10">
      <h1 class="text-3xl sm:text-5xl font-black text-white tracking-tight">12V Diesel Air Heater 2kW vs 5kW, Fuel Burn & Altitude Hz Database</h1>
      <p class="text-zinc-400 mt-3 text-base sm:text-lg">Select your campervan, tent, garage, or diesel heater model below to calculate 2kW vs. 5kW carbon-free sizing, 10-hour fuel and 12V LiFePO4 battery consumption, E-01 wire gauge, and high-altitude pump Hz settings.</p>
      <div class="mt-6">
        <input id="filterInput" type="text" placeholder="Search heater model or vehicle (e.g. Vevor 2kW, 5kW, Webasto STC, Espar D2, Sprinter 144, Ice Shanty, E-01 Error...)" class="w-full bg-zinc-900 border border-zinc-700 rounded-xl px-4 py-3.5 text-sm text-white focus:outline-none focus:border-orange-500">
      </div>
    </div>

    <div id="htrGrid" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">{cards_html}</div>
  </main>

  <footer class="border-t border-zinc-800 py-8 text-center text-xs text-zinc-500">
    <p>© {datetime.now(timezone.utc).year} DieselHeaterIndex. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const filterInput = document.getElementById('filterInput');
    const cards = Array.from(document.getElementById('htrGrid').children);
    filterInput.addEventListener('input', (e) => {{
      const q = e.target.value.toLowerCase();
      cards.forEach(c => {{
        c.style.display = c.textContent.toLowerCase().includes(q) ? 'block' : 'none';
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls_xml = f"""  <url>
    <loc>{SITE_BASE_URL}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>\n"""

    for item in published:
        urls_xml += f"""  <url>
    <loc>{SITE_BASE_URL}/{item['slug']}.html</loc>
    <lastmod>{item.get('date', today)}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
  </url>\n"""

    with open(os.path.join(DOCS_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls_xml}</urlset>""")

    rss_items = ""
    for item in list(reversed(published))[:30]:
        rss_items += f"""    <item>
      <title>{item['title']}</title>
      <link>{SITE_BASE_URL}/{item['slug']}.html</link>
      <guid>{SITE_BASE_URL}/{item['slug']}.html</guid>
      <description>{item['description']}</description>
    </item>\n"""

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>DieselHeaterIndex 12V Diesel Air Heater & Campervan Sizing Database</title>
    <link>{SITE_BASE_URL}/</link>
    <description>Interactive 12V/24V Diesel Air Heater kW/BTU, Fuel Burn, 12V Wire & Altitude Hz Calculators</description>
    <atom:link href="{SITE_BASE_URL}/rss.xml" rel="self" type="application/rss+xml" />
    <atom:link href="https://pubsubhubbub.appspot.com/" rel="hub" />
{rss_items}  </channel>
</rss>"""

    with open(os.path.join(DOCS_DIR, "rss.xml"), "w", encoding="utf-8") as f:
        f.write(rss_xml)

    with open(os.path.join(DOCS_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_BASE_URL}/sitemap.xml\n")

    with open(os.path.join(DOCS_DIR, f"{INDEXNOW_KEY}.txt"), "w", encoding="utf-8") as f:
        f.write(INDEXNOW_KEY)


def notify_search_engines(new_urls):
    """Multi-Endpoint Search Engine Pinger (IndexNow Global + Bing + Google WebSub)."""
    if not SITE_BASE_URL or not new_urls:
        return
    parsed_host = urllib.parse.urlparse(SITE_BASE_URL).netloc
    payload = {
        "host": parsed_host,
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE_BASE_URL}/{INDEXNOW_KEY}.txt",
        "urlList": new_urls
    }
    for idx_endpoint in ["https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow"]:
        try:
            req = urllib.request.Request(
                idx_endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                print(f"[INDEXNOW] Pushed {len(new_urls)} URLs to {idx_endpoint} (HTTP {resp.status})")
                break
        except Exception as e:
            print(f"[WARN] IndexNow ({idx_endpoint}) notice: {e}")

    try:
        hub_data = urllib.parse.urlencode({
            "hub.mode": "publish",
            "hub.url": f"{SITE_BASE_URL}/rss.xml"
        }).encode("utf-8")
        req_hub = urllib.request.Request(
            "https://pubsubhubbub.appspot.com/",
            data=hub_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST"
        )
        with urllib.request.urlopen(req_hub, timeout=15) as resp_hub:
            print(f"[WEBSUB] Google PubSubHubbub ping status: {resp_hub.status}")
    except Exception as e:
        print(f"[WARN] WebSub ping notice: {e}")


def main():
    published = load_json(PUBLISHED_FILE, [])
    mon_cfg = load_json(MONETIZATION_FILE, {})
    published_slugs = {item["slug"] for item in published if "slug" in item}

    candidates = []
    if CUSTOM_HEATER:
        candidates.append((CUSTOM_HEATER.strip(), 2.0, 280, 0.26, 0.11, 3.2, 60))
    candidates.extend(SEED_HEATERS)
    candidates.extend(discover_google_heater_queries(published_slugs))

    new_urls = []
    count = 0

    for htr_tuple in candidates:
        if count >= PAGES_PER_RUN:
            break
        h_name = htr_tuple[0]
        slug = slugify(f"{h_name}-kw-fuel-wire-calculator")
        if slug in published_slugs:
            continue

        print(f"[ENGINE] Generating 12V diesel heater fuel & wire calculator for: {h_name}...")
        try:
            data = generate_heater_data(htr_tuple)
            build_heater_html_page(data, slug, mon_cfg)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            sp = data.get("specs", {})

            published.append({
                "heater_name": data.get("heater_name", h_name),
                "slug": slug,
                "title": data.get("seo_title", f"{h_name} Diesel Heater Calculator"),
                "description": data.get("meta_description", ""),
                "kw": round(safe_float(sp.get("true_thermal_kw", htr_tuple[1]), htr_tuple[1]), 1),
                "btu": int(safe_float(sp.get("max_btu_hr", 6824), 6824)),
                "night_l": round(safe_float(sp.get("ten_hour_night_liters", 1.8), 1.8), 2),
                "night_ah": round(safe_float(sp.get("ten_hour_battery_ah", 19.4), 19.4), 1),
                "date": today
            })
            published_slugs.add(slug)
            if SITE_BASE_URL:
                new_urls.append(f"{SITE_BASE_URL}/{slug}.html")
            count += 1
            if count < PAGES_PER_RUN:
                time.sleep(15)
        except Exception as e:
            print(f"[ERROR] Failed building {h_name}: {e}")

    save_json(PUBLISHED_FILE, published)
    rebuild_portal_sitemap_and_rss(published, mon_cfg)
    if new_urls and SITE_BASE_URL:
        new_urls.append(f"{SITE_BASE_URL}/")
        notify_search_engines(new_urls)
    print(f"[DONE] Published {count} new 12V diesel heater calculator pages.")


if __name__ == "__main__":
    main()
