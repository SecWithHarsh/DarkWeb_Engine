import requests
from bs4 import BeautifulSoup
import re
import time
from typing import Dict, List, Set
import logging

logger = logging.getLogger(__name__)


class OnionInvestigator:
    """
    Investigation service to extract sensitive information from onion sites.
    Based on the HIFR tool functionality.
    """

    def __init__(self, timeout=30):
        self.timeout = timeout
        self.session = requests.Session()
        # Configure SOCKS5 proxy for Tor
        self.session.proxies = {
            'http': 'socks5h://127.0.0.1:9150',
            'https': 'socks5h://127.0.0.1:9150',
        }
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def investigate(self, url: str) -> Dict:
        """
        Investigate an onion URL and extract all possible information.

        Args:
            url: The onion URL to investigate

        Returns:
            dict: Dictionary containing all extracted information
        """
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'http://' + url

        result = {
            'url': url,
            'success': False,
            'emails': [],
            'btc_addresses': [],
            'monero_addresses': [],
            'ethereum_addresses': [],
            'external_links': [],
            'has_server_status': False,
            'server_status_content': None,
            'error': None
        }

        try:
            # Fetch the main page
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            source_code = response.text

            # Extract emails
            result['emails'] = self._extract_emails(source_code)

            # Extract cryptocurrency addresses
            result['btc_addresses'] = self._extract_btc_addresses(source_code)
            result['monero_addresses'] = self._extract_monero_addresses(source_code)
            result['ethereum_addresses'] = self._extract_ethereum_addresses(source_code)

            # Extract external links
            result['external_links'] = self._extract_links(source_code, url)

            # Check for server-status
            server_status = self._check_server_status(url)
            result['has_server_status'] = server_status['found']
            result['server_status_content'] = server_status.get('content')

            result['success'] = True
            logger.info(f"Successfully investigated {url}")

        except requests.exceptions.Timeout:
            result['error'] = 'Request timed out'
            logger.error(f"Timeout investigating {url}")
        except requests.exceptions.ConnectionError:
            result['error'] = 'Connection failed'
            logger.error(f"Connection error investigating {url}")
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Error investigating {url}: {str(e)}")

        return result

    def _extract_emails(self, source_code: str) -> List[str]:
        """Extract email addresses from source code"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
        emails = re.findall(email_pattern, source_code)
        # Return unique emails
        return list(set(emails))

    def _extract_btc_addresses(self, source_code: str) -> List[str]:
        """Extract Bitcoin addresses from source code"""
        # Bitcoin address pattern (P2PKH and P2SH)
        btc_pattern = r'\b[13][a-km-zA-HJ-NP-Z0-9]{26,33}\b'
        addresses = re.findall(btc_pattern, source_code)
        # Return unique addresses
        return list(set(addresses))

    def _extract_monero_addresses(self, source_code: str) -> List[str]:
        """Extract Monero (XMR) addresses from source code"""
        # Monero address pattern (starts with 4)
        monero_pattern = r'\b(?:4[0-9AB][1-9A-HJ-NP-Za-km-z]{93})\b'
        addresses = re.findall(monero_pattern, source_code)
        # Return unique addresses
        return list(set(addresses))

    def _extract_ethereum_addresses(self, source_code: str) -> List[str]:
        """Extract Ethereum addresses from source code"""
        # Ethereum address pattern (0x followed by 40 hex chars)
        eth_pattern = r'\b(?:0x)[0-9a-fA-F]{40}\b'
        addresses = re.findall(eth_pattern, source_code)
        # Return unique addresses
        return list(set(addresses))

    def _extract_links(self, source_code: str, base_url: str) -> List[str]:
        """Extract all external links from the page"""
        try:
            soup = BeautifulSoup(source_code, 'html.parser')
            links = []

            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                # Only include external links (http/https)
                if href.startswith('http://') or href.startswith('https://'):
                    links.append(href)

            # Return unique links (limit to 50 to avoid huge lists)
            return list(set(links))[:50]
        except Exception as e:
            logger.error(f"Error extracting links: {str(e)}")
            return []

    def _check_server_status(self, url: str) -> Dict:
        """Check if server-status page exists"""
        server_status_url = url.rstrip('/') + '/server-status'

        try:
            response = self.session.get(server_status_url, timeout=self.timeout)
            if response.status_code == 200:
                logger.info(f"server-status found at {server_status_url}")
                return {
                    'found': True,
                    'content': response.text[:5000]  # Limit content size
                }
        except Exception as e:
            logger.debug(f"No server-status at {server_status_url}: {str(e)}")

        return {'found': False}

    def bulk_investigate(self, urls: List[str], progress_callback=None) -> List[Dict]:
        """
        Investigate multiple URLs.

        Args:
            urls: List of URLs to investigate
            progress_callback: Optional callback function(result) called after each URL

        Returns:
            list: List of investigation results
        """
        results = []

        for i, url in enumerate(urls):
            logger.info(f"Investigating {i+1}/{len(urls)}: {url}")
            result = self.investigate(url)
            results.append(result)

            if progress_callback:
                progress_callback(result)

            # Be polite - wait between requests
            if i < len(urls) - 1:
                time.sleep(2)

        return results

