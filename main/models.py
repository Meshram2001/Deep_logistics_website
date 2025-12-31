from django.db import models
import uuid

class Partner(models.Model):
    PARTNER_CHOICES = [
        ('AGENT', 'Agent'),
        ('BROKER', 'Broker'),
        ('DRIVER', 'Truck Driver'),
    ]
    name = models.CharField(max_length=100)
    partner_type = models.CharField(max_length=10, choices=PARTNER_CHOICES)
    phone = models.CharField(max_length=15)
    email = models.EmailField(unique=True)
    city = models.CharField(max_length=100)
    experience = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_partner_type_display()})"

class Consignment(models.Model):
    STATUS_CHOICES = [
        ('BOOKED', 'Booked'),
        ('IN_TRANSIT', 'In Transit'),
        ('OUT_FOR_DELIVERY', 'Out for Delivery'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
    ]
    consignment_number = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    origin = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    current_location = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='BOOKED')
    estimated_delivery = models.DateField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.consignment_number