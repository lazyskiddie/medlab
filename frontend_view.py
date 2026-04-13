from django.http import HttpResponse
from pathlib import Path

def frontend_view(request):
    html_path = Path(__file__).parent / 'templates' / 'frontend.html'
    return HttpResponse(html_path.read_text(), content_type='text/html')