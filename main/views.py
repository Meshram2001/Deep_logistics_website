from django.shortcuts import render
from django.http import JsonResponse
from .models import Consignment, Partner

def home(request):
    """Renders the home page."""
    return render(request, 'main/home.html')

def about(request):
    """Renders the about us page."""
    return render(request, 'main/about.html')

def service(request):
    """Renders the services page."""
    return render(request, 'main/service.html')

def contact(request):
    """Renders the contact page and handles form submission."""
    return render(request, 'main/contact.html')

def join_with_us(request):
    """Renders the partner registration page and handles form submission."""
    return render(request, 'main/join_with_us.html')

def know_your_consignment(request):
    """Renders the consignment tracking page."""
    if 'consignment_number' in request.GET:
        consignment_number = request.GET.get('consignment_number')
        try:
            consignment = Consignment.objects.get(consignment_number=consignment_number)
            data = {
                'status': 'success',
                'consignment': {
                    'consignment_number': consignment.consignment_number,
                    'origin': consignment.origin,
                    'destination': consignment.destination,
                    'current_location': consignment.current_location,
                    'status': consignment.get_status_display(),
                    'estimated_delivery': consignment.estimated_delivery.strftime('%B %d, %Y'),
                    'updated_at': consignment.updated_at.strftime('%I:%M %p, %B %d, %Y'),
                }
            }
        except Consignment.DoesNotExist:
            data = {'status': 'error', 'message': 'Consignment not found.'}
        return JsonResponse(data)
    return render(request, 'main/know_your_consignment.html')