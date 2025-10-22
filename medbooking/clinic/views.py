# clinic/views.py
from django.shortcuts import render, get_object_or_404
from .models import Doctor, Clinic

# clinic/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .models import Doctor, Clinic

def index(request):
    doctors = Doctor.objects.all()
    clinics = Clinic.objects.all()
    specializations = Doctor.objects.values_list('specialization', flat=True).distinct().order_by('specialization')
    return render(request, 'clinic/index.html', {
        'doctors': doctors,
        'clinics': clinics,
        'specializations': specializations,
    })

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        try:
            from .models import User
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "Аккаунта с такой почтой не существует.")
            return redirect('login')
        auth_user = authenticate(username=user.username, password=password)
        if auth_user:
            login(request, auth_user)
            return redirect('main')
        else:
            messages.error(request, "Неверный пароль.")
            return redirect('login')
    return render(request, 'clinic/registration/login.html')

def logout_view(request):
    logout(request)
    return redirect('login')
def book_appointment(request):
    doctors = Doctor.objects.all()
    return render(request, 'clinic/doctors/list.html', {'doctors': doctors})

def book_doctor(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    return render(request, 'clinic/doctors/list.html', {'doctors': [doctor]})

def clinic_detail(request, clinic_id):
    clinic = get_object_or_404(Clinic, id=clinic_id)
    return render(request, 'clinic/clinics/detail.html', {'clinic': clinic})