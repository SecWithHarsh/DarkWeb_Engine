"""
Django management command to manage the embedded Tor service
"""

from django.core.management.base import BaseCommand
from links.services.tor_service import get_tor_service
import sys


class Command(BaseCommand):
    help = 'Manage the embedded Tor service (start/stop/status)'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            type=str,
            choices=['start', 'stop', 'restart', 'status'],
            help='Action to perform on Tor service'
        )

    def handle(self, *args, **options):
        action = options['action']
        service = get_tor_service()

        if action == 'start':
            self.stdout.write('Starting Tor service...')
            if service.start():
                self.stdout.write(self.style.SUCCESS(f'✅ Tor service started on port {service.get_socks_port()}'))
            else:
                self.stdout.write(self.style.ERROR('❌ Failed to start Tor service'))
                self.stdout.write('')
                self.stdout.write('Please ensure Tor is installed:')
                self.stdout.write('  Windows: Download Tor Browser from https://www.torproject.org/download/')
                self.stdout.write('  Or install Tor Expert Bundle')
                sys.exit(1)

        elif action == 'stop':
            self.stdout.write('Stopping Tor service...')
            service.stop()
            self.stdout.write(self.style.SUCCESS('✅ Tor service stopped'))

        elif action == 'restart':
            self.stdout.write('Restarting Tor service...')
            service.stop()
            if service.start():
                self.stdout.write(self.style.SUCCESS(f'✅ Tor service restarted on port {service.get_socks_port()}'))
            else:
                self.stdout.write(self.style.ERROR('❌ Failed to restart Tor service'))

        elif action == 'status':
            if service.is_running:
                self.stdout.write(self.style.SUCCESS(f'✅ Tor service is RUNNING on port {service.get_socks_port()}'))
            else:
                self.stdout.write(self.style.WARNING('⚠️ Tor service is NOT running'))
                self.stdout.write('')
                self.stdout.write('Start it with: python manage.py tor start')

