# helpdeskmini_project/views.py
from django.http import HttpResponse

def home(request):
    return HttpResponse("HelpDesk Mini API is running!")
