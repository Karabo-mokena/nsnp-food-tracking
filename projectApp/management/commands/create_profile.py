from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from projectApp.models import UserProfile

class Command(BaseCommand):
    def handle(self, *args, **options):
        UserProfile.objects.update_or_create(
            username='manager1',
            defaults={
                'full_name': 'Karabo',
                'email': 'karabomokoena289@gmail.com',
                'password': make_password('Mok@2003'),
                'role': 'programme_manager',
                'status': 'Approved',
            }
        )
        self.stdout.write('Manager profile created/updated.')
