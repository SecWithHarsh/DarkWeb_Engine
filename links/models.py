from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class SearchSource(models.Model):
    """Model for onion search engines like Ahmia, Onionland, etc."""
    name = models.CharField(max_length=100, unique=True)
    url = models.URLField(max_length=500, help_text="Base URL of the search engine")
    search_url_pattern = models.CharField(max_length=500, help_text="URL pattern with {query} placeholder")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class OnionLink(models.Model):
    """Simplified model to store onion links"""
    url = models.URLField(unique=True, max_length=500)
    title = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    keywords = models.TextField(blank=True, null=True)

    STATUS_CHOICES = [
        ('alive', 'Alive'),
        ('dead', 'Dead'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='alive')
    status_code = models.IntegerField(null=True, blank=True)
    response_time = models.FloatField(null=True, blank=True)
    last_checked = models.DateTimeField(null=True, blank=True)

    source = models.ForeignKey(SearchSource, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.url} ({self.status})"


class Investigation(models.Model):
    """Model to store investigation results from onion sites"""
    onion_link = models.ForeignKey(OnionLink, on_delete=models.CASCADE, related_name='investigations')
    investigated_url = models.URLField(max_length=500)

    # Extracted data fields
    emails = models.JSONField(default=list, blank=True)
    btc_addresses = models.JSONField(default=list, blank=True)
    monero_addresses = models.JSONField(default=list, blank=True)
    ethereum_addresses = models.JSONField(default=list, blank=True)

    # Additional findings
    has_server_status = models.BooleanField(default=False)
    server_status_content = models.TextField(blank=True, null=True)
    external_links = models.JSONField(default=list, blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['onion_link', 'investigated_url']

    def __str__(self):
        return f"Investigation of {self.investigated_url}"

    @property
    def total_findings(self):
        """Return total count of all findings"""
        return (
            len(self.emails) +
            len(self.btc_addresses) +
            len(self.monero_addresses) +
            len(self.ethereum_addresses)
        )

