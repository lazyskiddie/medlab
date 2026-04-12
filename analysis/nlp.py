import logging
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)

_ner_pipeline  = None
_summ_pipeline = None


def _get_ner_pipeline():
    global _ner_pipeline
    if _ner_pipeline is None:
        try:
            from transformers import pipeline
            local = Path(settings.LOCAL_NER_PATH)
            name  = str(local) if local.exists() else settings.NER_MODEL_NAME
            logger.info(f'Loading NER model: {name}')
            _ner_pipeline = pipeline('ner', model=name,
                                     aggregation_strategy='simple', device=-1)
        except Exception as e:
            logger.error(f'NER load failed: {e}')
    return _ner_pipeline


def _get_summarizer_pipeline():
    global _summ_pipeline
    if _summ_pipeline is None:
        try:
            from transformers import pipeline
            local = Path(settings.LOCAL_SUMMARIZER_PATH)
            ft    = Path(settings.MODELS_DIR) / 'summarizer_finetuned'
            if ft.exists() and any(ft.iterdir()):
                name = str(ft)
            elif local.exists():
                name = str(local)
            else:
                name = settings.SUMMARIZER_MODEL_NAME
            logger.info(f'Loading summarizer: {name}')
            _summ_pipeline = pipeline('text2text-generation', model=name, device=-1)
        except Exception as e:
            logger.error(f'Summarizer load failed: {e}')
    return _summ_pipeline


def generate_summary(flagged_items: list, extracted_values: dict) -> str:
    pipe = _get_summarizer_pipeline()
    if pipe is None:
        return _fallback_summary(flagged_items)

    abnormal = [f for f in flagged_items if f['status'] != 'normal']
    critical = [f for f in flagged_items if f['is_critical']]

    if not abnormal:
        prompt = ('The following medical lab report shows all values within normal ranges. '
                  'Write a brief patient-friendly summary confirming no abnormalities.')
    else:
        lines = ['Analyze this medical lab report and provide a patient-friendly summary:\n']
        if critical:
            lines.append('CRITICAL VALUES:')
            for f in critical:
                lines.append(f"  - {f['test']}: {f['value']} {f['unit']} "
                             f"(CRITICAL, reference: {f['low']}–{f['high']})")
        lines.append('\nABNORMAL VALUES:')
        for f in abnormal:
            direction = 'HIGH' if f['status'] == 'high' else 'LOW'
            lines.append(f"  - {f['test']}: {f['value']} {f['unit']} "
                         f"({direction}, reference: {f['low']}–{f['high']})")
        lines.append('\nWrite a clear non-technical explanation of what these results mean '
                     'and whether the patient should see a doctor urgently.')
        prompt = '\n'.join(lines)

    try:
        result = pipe(prompt, max_new_tokens=300, min_new_tokens=50, do_sample=False)
        return result[0]['generated_text'].strip()
    except Exception as e:
        logger.error(f'Summarizer error: {e}')
        return _fallback_summary(flagged_items)


def _fallback_summary(flagged_items: list) -> str:
    if not flagged_items:
        return ('All tested values are within normal reference ranges. '
                'No abnormalities were detected in this lab report.')
    abnormal = [f for f in flagged_items if f['status'] != 'normal']
    critical = [f for f in flagged_items if f['is_critical']]
    parts    = []
    if critical:
        names = ', '.join(f['test'] for f in critical)
        parts.append(f'CRITICAL: {names} requires immediate medical attention. '
                     'Please contact a doctor or go to an emergency room right away.')
    if abnormal:
        high = [f for f in abnormal if f['status'] == 'high']
        low  = [f for f in abnormal if f['status'] == 'low']
        if high:
            parts.append('Elevated: ' +
                         ', '.join(f"{f['test']} ({f['value']} {f['unit']})" for f in high) + '.')
        if low:
            parts.append('Below normal: ' +
                         ', '.join(f"{f['test']} ({f['value']} {f['unit']})" for f in low) + '.')
        parts.append('Please consult your doctor to discuss these findings.')
    else:
        parts.append('All values are within normal reference ranges.')
    return ' '.join(parts)


def detect_conditions(flagged_items: list) -> list:
    conditions = []
    flags_map  = {f['test_key']: f for f in flagged_items if f['status'] != 'normal'}

    if any(k in flags_map and flags_map[k]['status'] == 'low'
           for k in ('hemoglobin', 'hb', 'rbc')):
        conditions.append({'name': 'Possible Anaemia', 'confidence': 'high'})

    if 'glucose' in flags_map and flags_map['glucose']['status'] == 'high':
        conditions.append({'name': 'Elevated Blood Glucose (possible Diabetes)', 'confidence': 'medium'})

    if 'hba1c' in flags_map and flags_map['hba1c']['status'] == 'high':
        conditions.append({'name': 'Elevated HbA1c (poor glycaemic control)', 'confidence': 'high'})

    if 'tsh' in flags_map:
        if flags_map['tsh']['status'] == 'high':
            conditions.append({'name': 'Possible Hypothyroidism', 'confidence': 'medium'})
        elif flags_map['tsh']['status'] == 'low':
            conditions.append({'name': 'Possible Hyperthyroidism', 'confidence': 'medium'})

    if any(k in flags_map and flags_map[k]['status'] == 'high'
           for k in ('creatinine', 'bun', 'urea')):
        conditions.append({'name': 'Possible Kidney Dysfunction', 'confidence': 'medium'})

    if any(k in flags_map and flags_map[k]['status'] == 'high'
           for k in ('alt', 'sgpt', 'ast', 'sgot', 'alp', 'total bilirubin')):
        conditions.append({'name': 'Possible Liver Dysfunction', 'confidence': 'medium'})

    if any(k in flags_map and flags_map[k]['status'] == 'high'
           for k in ('total cholesterol', 'cholesterol', 'ldl', 'triglycerides')):
        conditions.append({'name': 'Elevated Lipid Levels (cardiovascular risk)', 'confidence': 'medium'})

    if 'wbc' in flags_map and flags_map['wbc']['status'] == 'high':
        conditions.append({'name': 'Possible Infection or Inflammation', 'confidence': 'low'})

    if 'crp' in flags_map and flags_map['crp']['status'] == 'high':
        conditions.append({'name': 'Elevated CRP (inflammation)', 'confidence': 'medium'})

    if 'vitamin d' in flags_map and flags_map['vitamin d']['status'] == 'low':
        conditions.append({'name': 'Vitamin D Deficiency', 'confidence': 'high'})

    if 'vitamin b12' in flags_map and flags_map['vitamin b12']['status'] == 'low':
        conditions.append({'name': 'Vitamin B12 Deficiency', 'confidence': 'high'})

    return conditions