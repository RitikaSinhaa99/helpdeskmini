from django.shortcuts import render

def home(request):
    return render(request, "index.html")

def tickets_page(request):
    return render(request, "tickets.html")

def login_page(request):
    return render(request, "login.html")
