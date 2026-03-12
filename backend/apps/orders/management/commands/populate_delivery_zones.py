"""
Management command to populate sample delivery zones.
"""
from django.core.management.base import BaseCommand
from apps.orders.models import DeliveryZone


class Command(BaseCommand):
    help = 'Populate sample delivery zones for PIN code based delivery'

    def handle(self, *args, **options):
        # Clear existing zones
        DeliveryZone.objects.all().delete()
        
        # Use dict to avoid duplicate PIN codes
        zones_dict = {
            # Local Tamil Nadu (Dharmapuri district and nearby)
            '636701': {'city': 'Dharmapuri', 'state': 'Tamil Nadu', 'zone_type': 'local', 'delivery_charge': 40, 'min_delivery_days': 1, 'max_delivery_days': 2},
            '635201': {'city': 'Hosur', 'state': 'Tamil Nadu', 'zone_type': 'local', 'delivery_charge': 50, 'min_delivery_days': 2, 'max_delivery_days': 3},
            '635001': {'city': 'Vellore', 'state': 'Tamil Nadu', 'zone_type': 'local', 'delivery_charge': 50, 'min_delivery_days': 2, 'max_delivery_days': 3},
            '600001': {'city': 'Chennai', 'state': 'Tamil Nadu', 'zone_type': 'local', 'delivery_charge': 60, 'min_delivery_days': 2, 'max_delivery_days': 4},
            
            # South India
            '560001': {'city': 'Bangalore', 'state': 'Karnataka', 'zone_type': 'south', 'delivery_charge': 70, 'min_delivery_days': 3, 'max_delivery_days': 5},
            '500001': {'city': 'Hyderabad', 'state': 'Telangana', 'zone_type': 'south', 'delivery_charge': 80, 'min_delivery_days': 3, 'max_delivery_days': 5},
            '682001': {'city': 'Kochi', 'state': 'Kerala', 'zone_type': 'south', 'delivery_charge': 80, 'min_delivery_days': 3, 'max_delivery_days': 5},
            '695001': {'city': 'Thiruvananthapuram', 'state': 'Kerala', 'zone_type': 'south', 'delivery_charge': 90, 'min_delivery_days': 4, 'max_delivery_days': 6},
            '620001': {'city': 'Trichy', 'state': 'Tamil Nadu', 'zone_type': 'south', 'delivery_charge': 60, 'min_delivery_days': 2, 'max_delivery_days': 4},
            '625001': {'city': 'Madurai', 'state': 'Tamil Nadu', 'zone_type': 'south', 'delivery_charge': 60, 'min_delivery_days': 2, 'max_delivery_days': 4},
            '638001': {'city': 'Erode', 'state': 'Tamil Nadu', 'zone_type': 'south', 'delivery_charge': 50, 'min_delivery_days': 2, 'max_delivery_days': 3},
            '641001': {'city': 'Coimbatore', 'state': 'Tamil Nadu', 'zone_type': 'south', 'delivery_charge': 55, 'min_delivery_days': 2, 'max_delivery_days': 3},
            
            # Rest of India (National)
            '110001': {'city': 'New Delhi', 'state': 'Delhi', 'zone_type': 'national', 'delivery_charge': 120, 'min_delivery_days': 5, 'max_delivery_days': 7},
            '400001': {'city': 'Mumbai', 'state': 'Maharashtra', 'zone_type': 'national', 'delivery_charge': 120, 'min_delivery_days': 5, 'max_delivery_days': 7},
            '700001': {'city': 'Kolkata', 'state': 'West Bengal', 'zone_type': 'national', 'delivery_charge': 130, 'min_delivery_days': 5, 'max_delivery_days': 8},
            '302001': {'city': 'Jaipur', 'state': 'Rajasthan', 'zone_type': 'national', 'delivery_charge': 130, 'min_delivery_days': 5, 'max_delivery_days': 8},
            '380001': {'city': 'Ahmedabad', 'state': 'Gujarat', 'zone_type': 'national', 'delivery_charge': 120, 'min_delivery_days': 5, 'max_delivery_days': 7},
            '411001': {'city': 'Pune', 'state': 'Maharashtra', 'zone_type': 'national', 'delivery_charge': 110, 'min_delivery_days': 4, 'max_delivery_days': 6},
            
            # Remote Areas
            '744101': {'city': 'Port Blair', 'state': 'Andaman & Nicobar', 'zone_type': 'remote', 'delivery_charge': 200, 'min_delivery_days': 7, 'max_delivery_days': 12},
            '795001': {'city': 'Imphal', 'state': 'Manipur', 'zone_type': 'remote', 'delivery_charge': 180, 'min_delivery_days': 6, 'max_delivery_days': 10},
            '796001': {'city': 'Aizawl', 'state': 'Mizoram', 'zone_type': 'remote', 'delivery_charge': 180, 'min_delivery_days': 6, 'max_delivery_days': 10},
            '797001': {'city': 'Kohima', 'state': 'Nagaland', 'zone_type': 'remote', 'delivery_charge': 180, 'min_delivery_days': 6, 'max_delivery_days': 10},
            '794001': {'city': 'Shillong', 'state': 'Meghalaya', 'zone_type': 'remote', 'delivery_charge': 170, 'min_delivery_days': 6, 'max_delivery_days': 9},
            '781001': {'city': 'Guwahati', 'state': 'Assam', 'zone_type': 'remote', 'delivery_charge': 150, 'min_delivery_days': 5, 'max_delivery_days': 8},
            '755001': {'city': 'Bhubaneswar', 'state': 'Odisha', 'zone_type': 'remote', 'delivery_charge': 140, 'min_delivery_days': 5, 'max_delivery_days': 8},
            '834001': {'city': 'Ranchi', 'state': 'Jharkhand', 'zone_type': 'remote', 'delivery_charge': 140, 'min_delivery_days': 5, 'max_delivery_days': 8},
        }
        
        for pincode, data in zones_dict.items():
            DeliveryZone.objects.create(pincode=pincode, **data)
        
        self.stdout.write(self.style.SUCCESS(f'Successfully created {len(zones_dict)} delivery zones'))
        
        # Print summary
        local_count = DeliveryZone.objects.filter(zone_type='local').count()
        south_count = DeliveryZone.objects.filter(zone_type='south').count()
        national_count = DeliveryZone.objects.filter(zone_type='national').count()
        remote_count = DeliveryZone.objects.filter(zone_type='remote').count()
        
        self.stdout.write(f'Local (TN): {local_count}')
        self.stdout.write(f'South India: {south_count}')
        self.stdout.write(f'National: {national_count}')
        self.stdout.write(f'Remote: {remote_count}')
