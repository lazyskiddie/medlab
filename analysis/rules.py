import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

REFERENCE_RANGES = {
    'hemoglobin':        {'male': (13.5, 17.5), 'female': (12.0, 15.5), 'unit': 'g/dL',    'full_name': 'Hemoglobin'},
    'hb':                {'male': (13.5, 17.5), 'female': (12.0, 15.5), 'unit': 'g/dL',    'full_name': 'Hemoglobin'},
    'wbc':               {'all':  (4.5,  11.0),                          'unit': '×10³/μL', 'full_name': 'White Blood Cell Count'},
    'rbc':               {'male': (4.7,  6.1),  'female': (4.2,  5.4),  'unit': '×10⁶/μL','full_name': 'Red Blood Cell Count'},
    'platelets':         {'all':  (150,  400),                           'unit': '×10³/μL', 'full_name': 'Platelet Count'},
    'hematocrit':        {'male': (40.7, 50.3), 'female': (36.1, 44.3), 'unit': '%',       'full_name': 'Hematocrit'},
    'mcv':               {'all':  (80,   100),                           'unit': 'fL',      'full_name': 'Mean Corpuscular Volume'},
    'mch':               {'all':  (27,   33),                            'unit': 'pg',      'full_name': 'Mean Corpuscular Hemoglobin'},
    'mchc':              {'all':  (31.5, 35.7),                          'unit': 'g/dL',    'full_name': 'MCHC'},
    'glucose':           {'all':  (70,   100),                           'unit': 'mg/dL',   'full_name': 'Fasting Blood Glucose'},
    'blood glucose':     {'all':  (70,   100),                           'unit': 'mg/dL',   'full_name': 'Fasting Blood Glucose'},
    'hba1c':             {'all':  (4.0,  5.6),                           'unit': '%',       'full_name': 'HbA1c'},
    'creatinine':        {'male': (0.74, 1.35), 'female': (0.59, 1.04), 'unit': 'mg/dL',   'full_name': 'Serum Creatinine'},
    'bun':               {'all':  (7,    25),                            'unit': 'mg/dL',   'full_name': 'Blood Urea Nitrogen'},
    'urea':              {'all':  (15,   45),                            'unit': 'mg/dL',   'full_name': 'Blood Urea'},
    'uric acid':         {'male': (3.4,  7.0),  'female': (2.4,  6.0),  'unit': 'mg/dL',   'full_name': 'Uric Acid'},
    'alt':               {'male': (7,    56),   'female': (7,    45),   'unit': 'U/L',     'full_name': 'ALT (SGPT)'},
    'sgpt':              {'male': (7,    56),   'female': (7,    45),   'unit': 'U/L',     'full_name': 'SGPT (ALT)'},
    'ast':               {'male': (10,   40),   'female': (10,   30),   'unit': 'U/L',     'full_name': 'AST (SGOT)'},
    'sgot':              {'male': (10,   40),   'female': (10,   30),   'unit': 'U/L',     'full_name': 'SGOT (AST)'},
    'alp':               {'all':  (44,   147),                           'unit': 'U/L',     'full_name': 'Alkaline Phosphatase'},
    'total bilirubin':   {'all':  (0.1,  1.2),                           'unit': 'mg/dL',   'full_name': 'Total Bilirubin'},
    'direct bilirubin':  {'all':  (0.0,  0.3),                           'unit': 'mg/dL',   'full_name': 'Direct Bilirubin'},
    'albumin':           {'all':  (3.5,  5.0),                           'unit': 'g/dL',    'full_name': 'Serum Albumin'},
    'total protein':     {'all':  (6.3,  8.2),                           'unit': 'g/dL',    'full_name': 'Total Protein'},
    'tsh':               {'all':  (0.4,  4.0),                           'unit': 'mIU/L',   'full_name': 'TSH'},
    't3':                {'all':  (100,  200),                           'unit': 'ng/dL',   'full_name': 'T3'},
    't4':                {'all':  (5.1,  14.1),                          'unit': 'μg/dL',   'full_name': 'T4'},
    'free t4':           {'all':  (0.8,  1.8),                           'unit': 'ng/dL',   'full_name': 'Free T4'},
    'free t3':           {'all':  (2.3,  4.2),                           'unit': 'pg/mL',   'full_name': 'Free T3'},
    'total cholesterol': {'all':  (0,    200),                           'unit': 'mg/dL',   'full_name': 'Total Cholesterol'},
    'cholesterol':       {'all':  (0,    200),                           'unit': 'mg/dL',   'full_name': 'Total Cholesterol'},
    'hdl':               {'male': (40,   999),  'female': (50,   999),  'unit': 'mg/dL',   'full_name': 'HDL Cholesterol'},
    'ldl':               {'all':  (0,    130),                           'unit': 'mg/dL',   'full_name': 'LDL Cholesterol'},
    'triglycerides':     {'all':  (0,    150),                           'unit': 'mg/dL',   'full_name': 'Triglycerides'},
    'sodium':            {'all':  (136,  145),                           'unit': 'mEq/L',   'full_name': 'Sodium'},
    'potassium':         {'all':  (3.5,  5.1),                           'unit': 'mEq/L',   'full_name': 'Potassium'},
    'chloride':          {'all':  (98,   107),                           'unit': 'mEq/L',   'full_name': 'Chloride'},
    'calcium':           {'all':  (8.5,  10.5),                          'unit': 'mg/dL',   'full_name': 'Calcium'},
    'magnesium':         {'all':  (1.7,  2.2),                           'unit': 'mg/dL',   'full_name': 'Magnesium'},
    'serum iron':        {'male': (60,   170),  'female': (50,   170),  'unit': 'μg/dL',   'full_name': 'Serum Iron'},
    'ferritin':          {'male': (20,   500),  'female': (20,   200),  'unit': 'ng/mL',   'full_name': 'Serum Ferritin'},
    'vitamin d':         {'all':  (30,   100),                           'unit': 'ng/mL',   'full_name': 'Vitamin D'},
    'vitamin b12':       {'all':  (200,  900),                           'unit': 'pg/mL',   'full_name': 'Vitamin B12'},
    'crp':               {'all':  (0,    1.0),                           'unit': 'mg/L',    'full_name': 'C-Reactive Protein'},
    'troponin':          {'all':  (0,    0.04),                          'unit': 'ng/mL',   'full_name': 'Troponin I'},
}

CRITICAL_THRESHOLDS = {
    'glucose':    {'low': 40,   'high': 500},
    'potassium':  {'low': 2.5,  'high': 6.5},
    'sodium':     {'low': 120,  'high': 160},
    'hemoglobin': {'low': 7.0,  'high': None},
    'hb':         {'low': 7.0,  'high': None},
    'platelets':  {'low': 50,   'high': 1000},
    'creatinine': {'low': None, 'high': 10.0},
    'troponin':   {'low': None, 'high': 0.4},
}


def parse_value(raw: str) -> Optional[float]:
    match = re.search(r'[-+]?\d*\.?\d+', raw.replace(',', '.'))
    return float(match.group()) if match else None


def extract_values_from_text(text: str) -> dict:
    extracted = {}
    for line in text.split('\n'):
        lower = line.lower()
        for test_name in REFERENCE_RANGES:
            if test_name in lower:
                numbers = re.findall(r'[-+]?\d*\.?\d+', line)
                if numbers and test_name not in extracted:
                    try:
                        extracted[test_name] = {'value': float(numbers[0]), 'raw': line.strip()}
                    except ValueError:
                        continue
    return extracted


def flag_values(extracted: dict, gender: str = 'all') -> list:
    flags = []
    for test_name, data in extracted.items():
        ref   = REFERENCE_RANGES.get(test_name)
        value = data.get('value')
        if not ref or value is None: continue

        if gender in ('male', 'female') and gender in ref:
            low, high = ref[gender]
        elif 'all' in ref:   low, high = ref['all']
        elif 'male' in ref:  low, high = ref['male']
        else: continue

        flag_status = 'normal'
        if value < low:    flag_status = 'low'
        elif value > high: flag_status = 'high'

        is_critical = False
        crit = CRITICAL_THRESHOLDS.get(test_name, {})
        if crit.get('low')  is not None and value < crit['low']:  is_critical = True
        if crit.get('high') is not None and value > crit['high']: is_critical = True

        flags.append({
            'test': ref.get('full_name', test_name.title()), 'test_key': test_name,
            'value': value, 'unit': ref.get('unit', ''),
            'low': low, 'high': high,
            'status': flag_status, 'is_critical': is_critical,
            'raw_line': data.get('raw', ''),
        })
    return flags


def determine_severity(flags: list) -> str:
    if any(f['is_critical'] for f in flags): return 'severe'
    abnormal = sum(1 for f in flags if f['status'] != 'normal')
    if abnormal == 0:    return 'normal'
    elif abnormal <= 2:  return 'mild'
    elif abnormal <= 5:  return 'moderate'
    return 'severe'


def run_rule_engine(text: str, gender: str = 'all') -> dict:
    extracted = extract_values_from_text(text)
    flags     = flag_values(extracted, gender)
    return {'extracted_values': extracted, 'flagged_items': flags,
            'severity': determine_severity(flags)}