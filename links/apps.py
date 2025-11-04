from django.apps import AppConfig
import logging
import os

logger = logging.getLogger(__name__)


class LinksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'links'

    def ready(self):
        """Initialize the application"""        # Only initialize Tor when actually serving HTTP in the main process
        import sys
        # Determine primary Django management command (first non-flag arg)
        cmd = next((arg for arg in sys.argv[1:] if not arg.startswith('-')), '')
        is_runserver = cmd == 'runserver'
        is_main_process = os.environ.get('RUN_MAIN') == 'true'

        if not (is_runserver and is_main_process):
            # Skip Tor init for other commands like "check", "migrate", shell, tests, etc.
            return

        # Skip Tor initialization in cloud environments
        cloud_indicators = ['RENDER', 'DYNO', 'RAILWAY_ENVIRONMENT', 'VERCEL']
        is_cloud = any(os.environ.get(indicator) for indicator in cloud_indicators)

        if is_cloud:
            logger.info("Cloud environment detected - using Tor2Web gateways")
            logger.info("No local Tor service needed")
            return

        # Local environment - try to start Tor
        try:
            from links.services.tor_service import get_tor_service
            logger.info("Initializing embedded Tor service...")
            service = get_tor_service()
            if service.start() and service.is_running:
                logger.info(f"✅ Tor service ready on port {service.get_socks_port()}")
            else:
                logger.warning("⚠️ Tor service not available. Install Tor from https://www.torproject.org/download/")
        except Exception as e:
            logger.error(f"Failed to initialize Tor service: {e}")
