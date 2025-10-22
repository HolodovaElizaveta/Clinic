# clinic/views.py
from django.shortcuts import render
from .models import Doctor, Clinic

def index(request):
    doctors = Doctor.objects.select_related('user').all()
    clinics = Clinic.objects.all()

    context = {
        'doctors': doctors,
        'clinics': clinics,
        'specializations': Doctor.objects.values_list('specialization', flat=True).distinct().order_by('specialization'),
    }
    return render(request, 'clinic/index.html', context)