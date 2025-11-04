from django.contrib import admin
from .models import OnionLink, SearchSource, Investigation


@admin.register(SearchSource)
class SearchSourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'url', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'url']


@admin.register(OnionLink)
class OnionLinkAdmin(admin.ModelAdmin):
    list_display = ['url', 'status', 'status_code', 'response_time', 'source', 'last_checked']
    list_filter = ['status', 'source']
    search_fields = ['url', 'title', 'keywords']
    readonly_fields = ['last_checked', 'created_at']


@admin.register(Investigation)
class InvestigationAdmin(admin.ModelAdmin):
    list_display = ['investigated_url', 'onion_link', 'created_at', 'email_count', 'btc_count', 'monero_count', 'eth_count']
    list_filter = ['has_server_status', 'created_at']
    search_fields = ['investigated_url', 'onion_link__url']
    readonly_fields = ['created_at', 'updated_at']

    def email_count(self, obj):
        return len(obj.emails)
    email_count.short_description = 'Emails'

    def btc_count(self, obj):
        return len(obj.btc_addresses)
    btc_count.short_description = 'BTC'

    def monero_count(self, obj):
        return len(obj.monero_addresses)
    monero_count.short_description = 'Monero'

    def eth_count(self, obj):
        return len(obj.ethereum_addresses)
    eth_count.short_description = 'Ethereum'


