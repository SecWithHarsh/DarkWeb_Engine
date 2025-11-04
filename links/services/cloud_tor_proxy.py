"""
Cloud-Friendly Tor Proxy Service
Uses public Tor2Web proxies for cloud deployment (Render, Heroku, etc.)
"""

import requests
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class CloudTorProxy:
    """
    Cloud-friendly Tor proxy using Tor2Web gateways
    Works on Render, Heroku, and other cloud platforms
    """

    def __init__(self):
        # Public Tor2Web proxies (these convert .onion to clearnet)
        self.tor2web_gateways = [
            'tor2web.org',
            'onion.to',
            'onion.ws',
            'onion.sh',
            'onion.ly',
        ]
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def convert_onion_url(self, onion_url):
        """
        Convert .onion URL to accessible clearnet URL using Tor2Web gateway
        Example: http://site.onion → http://site.onion.to
        """
        try:
            parsed = urlparse(onion_url)
            if '.onion' in parsed.netloc:
                # Try first available gateway
                gateway = self.tor2web_gateways[0]

                # Remove .onion and add gateway
                domain = parsed.netloc.replace('.onion', '')
                new_netloc = f"{domain}.{gateway}"

                # Reconstruct URL
                new_url = f"{parsed.scheme}://{new_netloc}{parsed.path}"
                if parsed.query:
                    new_url += f"?{parsed.query}"

                return new_url

            return onion_url
        except Exception as e:
            logger.error(f"Error converting onion URL: {e}")
            return onion_url

    def fetch(self, url, timeout=30):
        """Fetch content from onion URL via Tor2Web gateway"""
        try:
            converted_url = self.convert_onion_url(url)
            logger.info(f"Fetching via gateway: {converted_url}")

            response = self.session.get(
                converted_url,
                timeout=timeout,
                allow_redirects=True,
                verify=True  # Keep SSL verification for security
            )

            return {
                'success': True,
                'content': response.text,
                'binary_content': response.content,
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'url': response.url
            }
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return {
                'success': False,
                'error': str(e),
                'status_code': None
            }


# Singleton instance
_cloud_proxy = None


def get_cloud_proxy():
    """Get the global cloud proxy instance"""
    global _cloud_proxy
    if _cloud_proxy is None:
        _cloud_proxy = CloudTorProxy()
    return _cloud_proxy

