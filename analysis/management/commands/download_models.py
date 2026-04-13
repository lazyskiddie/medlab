from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path


class Command(BaseCommand):
    help = 'Download NLP models from Hugging Face to local disk.'

    def handle(self, *args, **options):
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline

        Path(settings.MODELS_DIR).mkdir(parents=True, exist_ok=True)

        ner_path = Path(settings.LOCAL_NER_PATH)
        if ner_path.exists():
            self.stdout.write(f'NER model already exists, skipping.')
        else:
            self.stdout.write(f'Downloading NER: {settings.NER_MODEL_NAME} ...')
            p = pipeline('ner', model=settings.NER_MODEL_NAME, aggregation_strategy='simple')
            p.model.save_pretrained(str(ner_path))
            p.tokenizer.save_pretrained(str(ner_path))
            self.stdout.write(self.style.SUCCESS(f'  ✓ NER saved to {ner_path}'))

        summ_path = Path(settings.LOCAL_SUMMARIZER_PATH)
        if summ_path.exists():
            self.stdout.write(f'Summarizer already exists, skipping.')
        else:
            self.stdout.write(f'Downloading summarizer: {settings.SUMMARIZER_MODEL_NAME} ...')
            tokenizer = AutoTokenizer.from_pretrained(settings.SUMMARIZER_MODEL_NAME)
            model     = AutoModelForSeq2SeqLM.from_pretrained(settings.SUMMARIZER_MODEL_NAME)
            tokenizer.save_pretrained(str(summ_path))
            model.save_pretrained(str(summ_path))
            self.stdout.write(self.style.SUCCESS(f'  ✓ Summarizer saved to {summ_path}'))

        self.stdout.write(self.style.SUCCESS('All models downloaded.'))