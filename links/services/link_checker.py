import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.utils import timezone
from links.models import OnionLink
import time
import logging
import os

logger = logging.getLogger(__name__)


class OnionLinkCheckerService:
    """
    Service to check onion links status.
    Automatically detects environment:
    - Local: Uses Tor SOCKS proxy (if available)
    - Cloud (Render/Heroku): Uses Tor2Web gateways
    """

    def __init__(self, timeout=30):
        self.timeout = timeout
        self.is_cloud = self._detect_cloud_environment()

        if self.is_cloud:
            # Cloud environment - use Tor2Web gateways
            logger.info("Cloud environment detected - using Tor2Web gateways")
            from .cloud_tor_proxy import get_cloud_proxy
            self.cloud_proxy = get_cloud_proxy()
            self.session = requests.Session()
        else:
            # Local environment - try to use Tor SOCKS proxy
            logger.info("Local environment detected - using Tor proxy")
            self.session = requests.Session()
            self._setup_tor_proxy()

    def _detect_cloud_environment(self):
        """Detect if running in cloud environment (Render, Heroku, etc.)"""
        # Check for common cloud environment variables
        cloud_indicators = [
            'RENDER',  # Render
            'DYNO',  # Heroku
            'RAILWAY_ENVIRONMENT',  # Railway
            'VERCEL',  # Vercel
            'NETLIFY',  # Netlify
            'AWS_EXECUTION_ENV',  # AWS Lambda
        ]

        return any(os.environ.get(indicator) for indicator in cloud_indicators)

    def _setup_tor_proxy(self):
        """Setup Tor SOCKS proxy for local environment"""
        try:
            from .tor_service import ensure_tor_running
            tor_port = ensure_tor_running()

            if tor_port:
                self.session.proxies = {
                    'http': f'socks5h://127.0.0.1:{tor_port}',
                    'https': f'socks5h://127.0.0.1:{tor_port}',
                }
                logger.info(f"Using Tor proxy on port {tor_port}")
            else:
                logger.warning("Tor not available. Direct connections will be attempted")
                self.session.proxies = {}
        except Exception as e:
            logger.error(f"Error setting up Tor proxy: {e}")
            self.session.proxies = {}

    def _fetch_with_cloud_proxy(self, url):
        """Fetch using cloud-friendly Tor2Web gateway"""
        result = self.cloud_proxy.fetch(url, timeout=self.timeout)
        return result

    def _fetch_with_tor_proxy(self, url):
        """Fetch using local Tor SOCKS proxy"""
        try:
            response = self.session.get(url, timeout=self.timeout)
            return {
                'success': True,
                'content': response.text,
                'binary_content': response.content,
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'url': response.url
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'status_code': None
            }

    def check_single_link(self, link_obj):
        """
        Check a single onion link for 200 OK status.
        Automatically uses correct method based on environment.
        """
        try:
            start_time = time.time()

            if self.is_cloud:
                result = self._fetch_with_cloud_proxy(link_obj.url)
            else:
                result = self._fetch_with_tor_proxy(link_obj.url)

            response_time = time.time() - start_time

            if result['success'] and result['status_code'] == 200:
                link_obj.status = 'alive'
                link_obj.status_code = result['status_code']
                link_obj.response_time = response_time
                link_obj.last_checked = timezone.now()
                link_obj.save()

                return {
                    'url': link_obj.url,
                    'status': 'alive',
                    'status_code': result['status_code'],
                    'response_time': response_time
                }
            else:
                return self._handle_dead_link(link_obj, result.get('error', 'non_200_status'))

        except Exception as e:
            return self._handle_dead_link(link_obj, str(e))

    def _handle_dead_link(self, link_obj, reason):
        """Handle a dead link by updating database"""
        link_obj.status = 'dead'
        link_obj.last_checked = timezone.now()
        link_obj.save()

        return {
            'url': link_obj.url,
            'status': 'dead',
            'reason': reason
        }

    def check_links_bulk(self, links_queryset, max_workers=20, progress_callback=None):
        alive_links = []
        dead_links = []
        results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_link = {
                executor.submit(self.check_single_link, link): link
                for link in links_queryset
            }

            for future in as_completed(future_to_link):
                result = future.result()
                results.append(result)

                if result['status'] == 'alive':
                    alive_links.append(result)
                else:
                    dead_links.append(result)

                # Call progress callback if provided
                if progress_callback:
                    progress_callback(result)

                # Small delay to avoid overwhelming Tor network
                time.sleep(0.5)

        return len(alive_links), len(dead_links), results

    def fetch_content(self, url, timeout=None):
        """Fetch HTML content from onion URL"""
        try:
            if self.is_cloud:
                result = self.cloud_proxy.fetch(url, timeout=timeout or self.timeout)
                return result
            else:
                response = self.session.get(
                    url,
                    timeout=timeout or self.timeout,
                    allow_redirects=True
                )
                return {
                    'success': True,
                    'content': response.text,
                    'status_code': response.status_code,
                    'headers': dict(response.headers),
                    'url': response.url
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'status_code': None
            }

    def fetch_resource(self, url, timeout=None):
        """Fetch any resource (CSS, JS, image, etc.)"""
        try:
            if self.is_cloud:
                result = self.cloud_proxy.fetch(url, timeout=timeout or self.timeout)
                if result['success']:
                    # Guess content type from URL if not provided
                    content_type = result.get('headers', {}).get('Content-Type', 'application/octet-stream')
                    return {
                        'success': True,
                        'content': result['binary_content'],
                        'content_type': content_type,
                        'status_code': result['status_code']
                    }
                return result
            else:
                response = self.session.get(
                    url,
                    timeout=timeout or self.timeout,
                    allow_redirects=True
                )
                return {
                    'success': True,
                    'content': response.content,
                    'content_type': response.headers.get('Content-Type', 'application/octet-stream'),
                    'status_code': response.status_code
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

