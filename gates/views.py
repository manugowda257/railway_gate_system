from django.shortcuts import render, redirect
from django.http import JsonResponse,HttpResponse
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from .models import RailwayGate, GateOperator, Taluk, TalukChangeRequest,TalukRequest, GateActivityLog
import math
from django.contrib.auth import logout
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone
from django.http import JsonResponse
from django.utils.timezone import localtime


def home(request):
    gates = RailwayGate.objects.filter(is_approved=True)
    return render(request, 'home.html', {'gates': gates})




def find_nearest_gate(request):
    user_lat = float(request.GET.get('lat'))
    user_lon = float(request.GET.get('lon'))

    gates = RailwayGate.objects.filter(is_approved=True)

    nearest_gate = None
    min_distance = float('inf')

    for gate in gates:
        distance = haversine(user_lat, user_lon, gate.latitude, gate.longitude)
        if distance < min_distance:
            min_distance = distance
            nearest_gate = gate

    # 🛡 Safety check (very important)
    if not nearest_gate:
        return JsonResponse({
            'error': 'No approved gates available'
        })

    return JsonResponse({
        'gate_name': nearest_gate.gate_name,
        'taluk': nearest_gate.taluk.name,
        'status': nearest_gate.status,
        'last_updated': localtime(nearest_gate.last_updated).strftime("%Y-%m-%d %H:%M:%S"),
        'closed_at': nearest_gate.closed_at.isoformat() if nearest_gate.closed_at else None,
        'distance': round(min_distance, 2)
    })

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in KM

    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)

    a = (math.sin(dLat/2) * math.sin(dLat/2) +
         math.cos(math.radians(lat1)) *
         math.cos(math.radians(lat2)) *
         math.sin(dLon/2) * math.sin(dLon/2))

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c

def operator_login(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            return render(request, 'login.html', {'error': 'Invalid credentials'})

    return render(request, 'login.html')

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from .models import GateOperator, GateActivityLog

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import GateOperator, GateActivityLog


@login_required
def dashboard(request):
    operator = GateOperator.objects.get(user=request.user)
    gate = operator.assigned_gate  # Can be None

    # Handle status update (only if POST and gate exists)
    if request.method == "POST" and gate:
        new_status = request.POST.get("status")

        # Initialize channel layer once
        channel_layer = get_channel_layer()

        # 🔴 CLOSE GATE
        if new_status == "CLOSED" and gate.status != "CLOSED":
            gate.status = "CLOSED"
            gate.closed_at = timezone.now()
            gate.save()

            # Create activity log
            GateActivityLog.objects.create(
                gate=gate,
                operator=request.user,
                action="CLOSED"
            )

            # 🔥 REAL-TIME BROADCAST (WebSocket)
            async_to_sync(channel_layer.group_send)(
                "gate_updates",
                {
                    "type": "gate_update",
                    "gate_id": gate.id,
                    "status": gate.status,
                    "closed_at": gate.closed_at.isoformat() if gate.closed_at else None,
                }
            )

        # 🟢 OPEN GATE
        elif new_status == "OPEN" and gate.status != "OPEN":
            gate.status = "OPEN"
            gate.closed_at = None
            gate.save()

            # Create activity log
            GateActivityLog.objects.create(
                gate=gate,
                operator=request.user,
                action="OPEN"
            )

            # 🔥 REAL-TIME BROADCAST (WebSocket)
            async_to_sync(channel_layer.group_send)(
                "gate_updates",
                {
                    "type": "gate_update",
                    "gate_id": gate.id,
                    "status": gate.status,
                    "closed_at": None,
                }
            )

    return render(request, "dashboard.html", {
        "gate": gate,
        "current_taluk": operator.current_taluk
    })

@login_required
def add_gate(request):
    operator = GateOperator.objects.get(user=request.user)

    gate_name = None
    landmark = None
    latitude = None
    longitude = None

    if request.method == "POST":
        gate_name = request.POST.get("gate_name")
        landmark = request.POST.get("landmark")
        latitude = request.POST.get("latitude")
        longitude = request.POST.get("longitude")

    # Check if location was fetched
    if not latitude or not longitude:
        return render(request, "add_gate.html", {
            "current_taluk": operator.current_taluk,
            "error": "⚠ Please fetch your location before submitting."
        })

    latitude = float(latitude)
    longitude = float(longitude)

    # Duplicate location check (within 50 meters)
    existing_gates = RailwayGate.objects.all()
    for gate in existing_gates:
        distance = haversine(latitude, longitude, gate.latitude, gate.longitude)
        if distance < 0.05:
            return render(request, "add_gate.html", {
                "current_taluk": operator.current_taluk,
                "error": "⚠ Gate already exists near this location (within 50 meters)."
            })

    RailwayGate.objects.create(
        gate_name=gate_name,
        taluk=operator.current_taluk,
        latitude=latitude,
        longitude=longitude,
        landmark=landmark,
        status="OPEN",
        is_approved=False,
        created_by=request.user
    )

    return render(request, "add_gate.html", {
        "current_taluk": operator.current_taluk,
        "success": "✅ Gate submitted successfully. Waiting for admin approval."
    })

@login_required
def request_taluk_change(request):
    operator = GateOperator.objects.get(user=request.user)
    taluks = Taluk.objects.all()

    if request.method == "POST":
        taluk_id = request.POST.get("taluk_id")
        requested_taluk = Taluk.objects.get(id=taluk_id)

        # Prevent duplicate request
        existing_request = TalukChangeRequest.objects.filter(
            operator=request.user,
            requested_taluk=requested_taluk,
            is_approved=False
        ).exists()

        if existing_request:
            return render(request, "request_taluk_change.html", {
                "taluks": taluks,
                "current_taluk": operator.current_taluk,
                "error": "⚠ You already requested this taluk change. Waiting for admin approval."
            })

        TalukChangeRequest.objects.create(
            operator=request.user,
            requested_taluk=requested_taluk
        )

        return render(request, "request_taluk_change.html", {
            "taluks": taluks,
            "current_taluk": operator.current_taluk,
            "success": "✅ Taluk change request submitted. Waiting for admin approval."
        })

    return render(request, "request_taluk_change.html", {
        "taluks": taluks,
        "current_taluk": operator.current_taluk
    })


def operator_logout(request):
    logout(request)
    return redirect('home')

@login_required
def request_new_taluk(request):
    operator = GateOperator.objects.get(user=request.user)

    if request.method == "POST":
        taluk_name = request.POST.get("taluk_name")
        district = request.POST.get("district")

        # Prevent duplicate request
        existing = TalukRequest.objects.filter(
            requested_name__iexact=taluk_name,
            is_approved=False
        ).exists()

        if existing:
            return render(request, "request_new_taluk.html", {
                "error": "⚠ This taluk request is already pending admin approval."
            })

        TalukRequest.objects.create(
            requested_name=taluk_name,
            district=district,
            requested_by=request.user
        )

        return render(request, "request_new_taluk.html", {
            "success": "✅ New taluk request submitted successfully. Waiting for admin approval."
        })

    return render(request, "request_new_taluk.html")

def live_map(request):
    gates = RailwayGate.objects.filter(is_approved=True)
    return render(request, "map.html", {"gates": gates})

@login_required
def activity_logs(request):
    operator = GateOperator.objects.get(user=request.user)
    gate = operator.assigned_gate

    logs = []
    if gate:
        logs = GateActivityLog.objects.filter(gate=gate).order_by("-timestamp")[:50]

    return render(request, "activity_logs.html", {
        "logs": logs,
        "gate": gate
    })