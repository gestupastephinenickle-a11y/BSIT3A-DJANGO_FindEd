from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

User = get_user_model()

MAX_FAILED_ATTEMPTS = 5
LOCK_DURATION = timedelta(minutes=1)
INVALID_LOGIN_MESSAGE = 'Invalid username or password.'
LOCKED_MESSAGE = 'Too many failed attempts. Locked for 1 minute.'


def _reset_lock_state(request):
    request.session['failed_attempts'] = 0
    request.session['lock_time'] = None


def _get_lock_state(request):
    failed_attempts = request.session.get('failed_attempts', 0)
    lock_time = request.session.get('lock_time')

    if not lock_time:
        return failed_attempts, None

    try:
        unlock_time = timezone.datetime.fromisoformat(lock_time)
    except (TypeError, ValueError):
        _reset_lock_state(request)
        return 0, None

    if timezone.now() < unlock_time:
        remaining = int((unlock_time - timezone.now()).total_seconds())
        return failed_attempts, remaining

    _reset_lock_state(request)
    return 0, None


def _set_lock_state(request):
    lock_until = timezone.now() + LOCK_DURATION
    request.session['failed_attempts'] = MAX_FAILED_ATTEMPTS
    request.session['lock_time'] = lock_until.isoformat()
    return int(LOCK_DURATION.total_seconds())


def _validate_registration_data(data):
    errors = {}

    username = data.get('username', '').strip()
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')

    if not username:
        errors['username'] = 'Username is required.'
    elif User.objects.filter(username=username).exists():
        errors['username'] = 'Username already taken.'

    if not first_name:
        errors['first_name'] = 'First name is required.'

    if not last_name:
        errors['last_name'] = 'Last name is required.'

    if not email:
        errors['email'] = 'Email is required.'
    else:
        try:
            validate_email(email)
        except ValidationError:
            errors['email'] = 'Enter a valid email address.'
        else:
            if User.objects.filter(email=email).exists():
                errors['email'] = 'Email already registered.'

    if not password:
        errors['password'] = 'Password is required.'
    elif len(password) < 8:
        errors['password'] = 'Password must be at least 8 characters.'
    else:
        try:
            validate_password(password)
        except ValidationError as exc:
            errors['password'] = ' '.join(exc.messages)

    if password != confirm_password:
        errors['confirm_password'] = 'Passwords do not match.'

    return errors


@require_http_methods(['GET', 'POST'])
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    failed_attempts, remaining = _get_lock_state(request)
    if remaining is not None:
        messages.error(request, f'Too many failed attempts. Try again in {remaining} seconds.')
        return render(request, 'auth/login.html', {'locked': True, 'remaining': remaining})

    if request.method == 'GET':
        return render(request, 'auth/login.html')

    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '')
    user = authenticate(request, username=username, password=password)

    if user is not None:
        _reset_lock_state(request)
        login(request, user)
        return redirect('dashboard')

    failed_attempts += 1
    request.session['failed_attempts'] = failed_attempts
    if failed_attempts >= MAX_FAILED_ATTEMPTS:
        remaining = _set_lock_state(request)
        messages.error(request, LOCKED_MESSAGE)
        return render(request, 'auth/login.html', {'locked': True, 'remaining': remaining})

    remaining_attempts = MAX_FAILED_ATTEMPTS - failed_attempts
    messages.error(request, f'{INVALID_LOGIN_MESSAGE} {remaining_attempts} attempts remaining.')
    return render(request, 'auth/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


def home(request):
    # Public guide — no login needed so new students can find rooms.
    # Starter campus data for Kabankalan Catholic College (KCC)
    # Guanzon St., Brgy. 1, Kabankalan City. Edit freely — later move to DB.
    buildings = [
        {
            "id": "main",
            "name": "Main / Admin Building",
            "short": "MAIN",
            "type": "office",
            "floors": 3,
            "desc": "Registrar, Accounting, President's Office. Enter via Main Gate on Guanzon St.",
            "rooms": [
                {"code": "Registrar", "floor": "G/F", "detail": "Enrollment, records, Form 137"},
                {"code": "Accounting", "floor": "G/F", "detail": "Payments, balances"},
                {"code": "Guidance", "floor": "2F", "detail": "Counseling, SHS strand advice"},
                {"code": "President's Office", "floor": "2F", "detail": "Admin"},
                {"code": "Faculty Room", "floor": "3F", "detail": "Instructors"},
            ],
        },
        {
            "id": "basiced",
            "name": "Basic Education Building",
            "short": "BASIC ED",
            "type": "classroom",
            "floors": 3,
            "desc": "Grade School & Junior High. West wing, near flagpole.",
            "rooms": [
                {"code": "Grade 7 - St. John", "floor": "G/F", "detail": "Adviser: J. Cruz • 45 seats"},
                {"code": "Grade 8 - St. Matthew", "floor": "G/F", "detail": "45 seats"},
                {"code": "Grade 9 - St. Mark", "floor": "2F", "detail": "46 seats"},
                {"code": "Grade 10 - St. Luke", "floor": "2F", "detail": "46 seats"},
                {"code": "Science Lab 1", "floor": "3F", "detail": "JHS experiments"},
                {"code": "Computer Lab 1", "floor": "3F", "detail": "40 units"},
            ],
        },
        {
            "id": "shs",
            "name": "Senior High Building",
            "short": "SHS",
            "type": "classroom",
            "floors": 3,
            "desc": "Grades 11–12: STEM, ABM, HUMSS, TVL. Northwest block.",
            "rooms": [
                {"code": "STEM 11-A", "floor": "G/F", "detail": "40 seats"},
                {"code": "ABM 11-B", "floor": "G/F", "detail": "42 seats"},
                {"code": "HUMSS 11-C", "floor": "2F", "detail": "42 seats"},
                {"code": "STEM 12-A", "floor": "2F", "detail": "40 seats"},
                {"code": "ABM 12-B", "floor": "3F", "detail": "42 seats"},
                {"code": "TVL-ICT 12", "floor": "3F", "detail": "Computer / cookery"},
            ],
        },
        {
            "id": "coed",
            "name": "COED / CAS Building",
            "short": "COED·CAS",
            "type": "classroom",
            "floors": 3,
            "desc": "College of Teacher Education & Arts and Sciences. East of quad.",
            "rooms": [
                {"code": "BEED 1-A", "floor": "G/F", "detail": "45 seats"},
                {"code": "BSED 2-A", "floor": "G/F", "detail": "45 seats"},
                {"code": "BS Psych 2-A", "floor": "2F", "detail": "40 seats"},
                {"code": "BSED 3-A", "floor": "2F", "detail": "44 seats"},
                {"code": "BEED 4-A", "floor": "3F", "detail": "43 seats"},
                {"code": "Lecture Hall", "floor": "3F", "detail": "120 seats"},
            ],
        },
        {
            "id": "cbaccj",
            "name": "CBA / CCJ Building (BSIT Home)",
            "short": "CBA·CCJ",
            "type": "classroom",
            "floors": 4,
            "desc": "Business, Criminology & IT. BSIT 3A is here — 3rd floor, south side.",
            "rooms": [
                {"code": "BSBA 1-A", "floor": "G/F", "detail": "48 seats"},
                {"code": "BSCRIM 1-A", "floor": "G/F", "detail": "50 seats"},
                {"code": "BSIT 1-A", "floor": "2F", "detail": "40 seats • Lab beside"},
                {"code": "BSIT 2-A", "floor": "2F", "detail": "42 seats"},
                {"code": "BSIT 3-A", "floor": "3F", "detail": "38 seats • Capstone room"},
                {"code": "BSBA 3-B", "floor": "3F", "detail": "45 seats"},
                {"code": "BSCRIM 3-A", "floor": "4F", "detail": "50 seats"},
                {"code": "AVR / Moot Room", "floor": "4F", "detail": "Presentations"},
            ],
        },
        {
            "id": "library",
            "name": "KCC Library",
            "short": "LIBRARY",
            "type": "office",
            "floors": 2,
            "desc": "College Library on Guanzon St. side. Quiet rooms, e-library.",
            "rooms": [
                {"code": "Reading Hall", "floor": "G/F", "detail": "Open 8am–6pm"},
                {"code": "E-Library", "floor": "2F", "detail": "30 PCs, WiFi"},
            ],
        },
        {
            "id": "chapel",
            "name": "Chapel",
            "short": "CHAPEL",
            "type": "faith",
            "floors": 1,
            "desc": "Heart of Catholic identity. Daily rosary, First Friday Mass.",
            "rooms": [
                {"code": "Main Sanctuary", "floor": "G/F", "detail": "200 seats"},
            ],
        },
        {
            "id": "gym",
            "name": "Gym / Covered Court",
            "short": "GYM",
            "type": "assembly",
            "floors": 1,
            "desc": "Intramurals, Hinugyaw, graduations. South-east corner.",
            "rooms": [
                {"code": "Main Court", "floor": "G/F", "detail": "Basketball / volleyball"},
                {"code": "Stage", "floor": "G/F", "detail": "Programs"},
                {"code": "PE Room", "floor": "G/F", "detail": "Equipment"},
            ],
        },
        {
            "id": "canteen",
            "name": "Canteen",
            "short": "CANTEEN",
            "type": "office",
            "floors": 1,
            "desc": "Beside quad — snacks, lunch, school supplies.",
            "rooms": [
                {"code": "Food Stalls", "floor": "G/F", "detail": "6 stalls"},
            ],
        },
    ]
    return render(request, 'home.html', {'buildings': buildings})


@require_http_methods(['GET', 'POST'])
def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'GET':
        return render(request, 'auth/register.html')

    form_data = {
        'username': request.POST.get('username', ''),
        'first_name': request.POST.get('first_name', ''),
        'last_name': request.POST.get('last_name', ''),
        'email': request.POST.get('email', ''),
        'password': request.POST.get('password', ''),
        'confirm_password': request.POST.get('confirm_password', ''),
    }

    errors = _validate_registration_data(form_data)
    if errors:
        return render(request, 'auth/register.html', {'errors': errors, 'form_data': form_data})

    user = User.objects.create_user(
        username=form_data['username'].strip(),
        first_name=form_data['first_name'].strip(),
        last_name=form_data['last_name'].strip(),
        email=form_data['email'].strip(),
        password=form_data['password'],
    )
    login(request, user)
    return redirect('dashboard')
