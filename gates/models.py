from django.db import models
from django.contrib.auth.models import User


class Taluk(models.Model):
    name = models.CharField(max_length=100)
    district = models.CharField(max_length=100, default="Dakshina Kannada")
    state = models.CharField(max_length=100, default="Karnataka")

    def __str__(self):
        return self.name


class RailwayGate(models.Model):
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('CLOSED', 'Closed'),
    ]

    gate_name = models.CharField(max_length=200)
    taluk = models.ForeignKey(Taluk, on_delete=models.CASCADE)
    latitude = models.FloatField()
    longitude = models.FloatField()
    landmark = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='OPEN')
    last_updated = models.DateTimeField(auto_now=True)
    is_approved = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.gate_name


class GateOperator(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    current_taluk = models.ForeignKey(Taluk, on_delete=models.SET_NULL, null=True, blank=True)
    assigned_gate = models.ForeignKey(RailwayGate, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.user.username


class TalukRequest(models.Model):
    requested_name = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.requested_name


class TalukChangeRequest(models.Model):
    operator = models.ForeignKey(User, on_delete=models.CASCADE)
    requested_taluk = models.ForeignKey(Taluk, on_delete=models.CASCADE)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.operator.username} → {self.requested_taluk.name}"

class GateActivityLog(models.Model):
    ACTION_CHOICES = [
        ("OPEN", "Opened"),
        ("CLOSED", "Closed"),
    ]

    gate = models.ForeignKey("RailwayGate", on_delete=models.CASCADE)
    operator = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.gate.gate_name} - {self.action} by {self.operator.username}"