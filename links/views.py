from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from .models import OnionLink, SearchSource, Investigation
from .services.link_checker import OnionLinkCheckerService
from .services.scraper import OnionSearchScraper
from .services.investigator import OnionInvestigator
import uuid
import re
from urllib.parse import urljoin, urlparse
import base64
import threading
from django.core.cache import cache


def home(request):
    sources = SearchSource.objects.filter(is_active=True)
    recent_links = OnionLink.objects.filter(status='alive').order_by('-last_checked')[:20]
    stats = {
        'total_links': OnionLink.objects.count(),
        'alive_links': OnionLink.objects.filter(status='alive').count(),
        'dead_links': OnionLink.objects.filter(status='dead').count(),
    }
    context = {
        'sources': sources,
        'recent_links': recent_links,
        'stats': stats,
    }
    return render(request, 'links/home.html', context)


@require_http_methods(["POST"])
def search_and_check(request):
    keyword = request.POST.get('keyword', '').strip()
    if not keyword:
        messages.error(request, 'Please enter a search keyword')
        return redirect('home')
    sources = SearchSource.objects.filter(is_active=True)
    if not sources.exists():
        messages.error(request, 'No search sources configured. Please add them via admin panel.')
        return redirect('home')
    scraper = OnionSearchScraper()
    all_links = []
    for source in sources:
        try:
            links = scraper.scrape_from_source(source, keyword)
            all_links.extend(links)
        except Exception as e:
            messages.warning(request, f'Error scraping {source.name}: {str(e)}')
    if not all_links:
        messages.warning(request, 'No links found for your search')
        return redirect('home')
    saved_links = []
    for link_data in all_links:
        link, _ = OnionLink.objects.get_or_create(
            url=link_data['url'],
            defaults={
                'title': link_data.get('title', ''),
                'description': link_data.get('description', ''),
                'keywords': keyword,
                'source': link_data.get('source')
            }
        )
        saved_links.append(link)
    search_id = str(uuid.uuid4())
    cache.set(f'search_{search_id}_total', len(saved_links), timeout=3600)
    cache.set(f'search_{search_id}_checked', 0, timeout=3600)
    cache.set(f'search_{search_id}_alive', [], timeout=3600)
    cache.set(f'search_{search_id}_complete', False, timeout=3600)

    def check_links_async():
        checker = OnionLinkCheckerService(timeout=30)

        def progress_callback(result):
            checked_count = cache.get(f'search_{search_id}_checked', 0) + 1
            cache.set(f'search_{search_id}_checked', checked_count, timeout=3600)
            if result['status'] == 'alive':
                alive_links = cache.get(f'search_{search_id}_alive', [])
                link = OnionLink.objects.get(url=result['url'])
                alive_links.append({
                    'id': link.id,
                    'url': link.url,
                    'title': link.title,
                    'description': link.description,
                    'status_code': link.status_code,
                    'response_time': link.response_time,
                    'last_checked': link.last_checked.isoformat() if link.last_checked else None
                })
                cache.set(f'search_{search_id}_alive', alive_links, timeout=3600)
        checker.check_links_bulk(saved_links, max_workers=20, progress_callback=progress_callback)
        cache.set(f'search_{search_id}_complete', True, timeout=3600)

    thread = threading.Thread(target=check_links_async)
    thread.daemon = True
    thread.start()
    messages.success(request, f'Found {len(saved_links)} links. Checking status now...')
    return redirect('search_results_progressive', keyword=keyword, search_id=search_id)


def search_results(request, keyword):
    links = OnionLink.objects.filter(keywords__icontains=keyword, status='alive').order_by('-last_checked')
    context = {
        'keyword': keyword,
        'links': links,
        'total': links.count(),
    }
    return render(request, 'links/search_results.html', context)


def search_results_progressive(request, keyword, search_id):
    context = {
        'keyword': keyword,
        'search_id': search_id,
        'total': cache.get(f'search_{search_id}_total', 0),
    }
    return render(request, 'links/search_results_progressive.html', context)


@require_http_methods(["GET"])
def check_progress(request, search_id):
    total = cache.get(f'search_{search_id}_total', 0)
    checked = cache.get(f'search_{search_id}_checked', 0)
    alive_links = cache.get(f'search_{search_id}_alive', [])
    complete = cache.get(f'search_{search_id}_complete', False)
    return JsonResponse({
        'total': total,
        'checked': checked,
        'alive_count': len(alive_links),
        'alive_links': alive_links,
        'complete': complete,
        'progress_percent': int((checked / total * 100)) if total > 0 else 0
    })


@require_http_methods(["GET"])
def sandbox_proxy(request, link_id):
    link = get_object_or_404(OnionLink, id=link_id, status='alive')
    checker = OnionLinkCheckerService(timeout=60)
    result = checker.fetch_content(link.url)
    if result['success']:
        html_content = result['content']
        base_url = link.url
        html_content = rewrite_html_urls(html_content, base_url, link_id)
        return JsonResponse({
            'success': True,
            'content': html_content,
            'url': link.url,
            'title': link.title or 'Onion Site'
        })
    else:
        return JsonResponse({'success': False, 'error': result['error']}, status=500)


def rewrite_html_urls(html, base_url, link_id):
    def replace_url(match):
        attr = match.group(1)
        quote = match.group(2)
        url = match.group(3)
        if url.startswith('data:') or url.startswith('javascript:') or url.startswith('#'):
            return match.group(0)
        absolute_url = urljoin(base_url, url)
        parsed = urlparse(absolute_url)
        if parsed.netloc and '.onion' in parsed.netloc:
            encoded_url = base64.urlsafe_b64encode(absolute_url.encode()).decode()
            proxy_url = f'/sandbox/resource/{link_id}/{encoded_url}/'
            return f'{attr}={quote}{proxy_url}{quote}'
        return match.group(0)

    html = re.sub(r'(href|src)=(["\'])([^"\']+)\2', replace_url, html, flags=re.IGNORECASE)

    def replace_css_url(match):
        quote = match.group(1)
        url = match.group(2)
        if url.startswith('data:') or url.startswith('javascript:'):
            return match.group(0)
        absolute_url = urljoin(base_url, url)
        parsed = urlparse(absolute_url)
        if parsed.netloc and '.onion' in parsed.netloc:
            encoded_url = base64.urlsafe_b64encode(absolute_url.encode()).decode()
            proxy_url = f'/sandbox/resource/{link_id}/{encoded_url}/'
            return f'url({quote}{proxy_url}{quote})'
        return match.group(0)

    html = re.sub(r'url\((["\']?)([^)]+)\1\)', replace_css_url, html, flags=re.IGNORECASE)
    return html


@require_http_methods(["GET"])
def sandbox_resource_proxy(request, link_id, encoded_url):
    try:
        _ = get_object_or_404(OnionLink, id=link_id)
        decoded_url = base64.urlsafe_b64decode(encoded_url.encode()).decode()
        checker = OnionLinkCheckerService(timeout=30)
        result = checker.fetch_resource(decoded_url)
        if result['success']:
            content_type = result.get('content_type', 'application/octet-stream')
            if 'text/html' in content_type:
                url_lower = decoded_url.lower()
                if url_lower.endswith('.css'):
                    content_type = 'text/css'
                elif url_lower.endswith('.js'):
                    content_type = 'application/javascript'
                elif url_lower.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp')):
                    ext = url_lower.split('.')[-1]
                    content_type = f'image/{ext.replace("jpg", "jpeg")}'
                elif url_lower.endswith('.woff') or url_lower.endswith('.woff2'):
                    content_type = 'font/woff2' if url_lower.endswith('.woff2') else 'font/woff'
                elif url_lower.endswith('.ttf'):
                    content_type = 'font/ttf'
            response = HttpResponse(result['content'], content_type=content_type)
            response['X-Frame-Options'] = 'SAMEORIGIN'
            response['Cache-Control'] = 'public, max-age=3600'
            return response
        else:
            return HttpResponse(f"Error loading resource: {result.get('error', 'Unknown error')}", status=404, content_type='text/plain')
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500, content_type='text/plain')


@require_http_methods(["GET", "POST"])
def investigate_link(request, link_id):
    link = get_object_or_404(OnionLink, id=link_id)
    if request.method == 'POST':
        investigator = OnionInvestigator(timeout=60)
        result = investigator.investigate(link.url)
        if result['success']:
            investigation, _ = Investigation.objects.update_or_create(
                onion_link=link,
                investigated_url=link.url,
                defaults={
                    'emails': result['emails'],
                    'btc_addresses': result['btc_addresses'],
                    'monero_addresses': result['monero_addresses'],
                    'ethereum_addresses': result['ethereum_addresses'],
                    'external_links': result['external_links'],
                    'has_server_status': result['has_server_status'],
                    'server_status_content': result['server_status_content'],
                }
            )
            messages.success(request, f'Investigation complete! Found {investigation.total_findings} items.')
            return redirect('investigation_detail', investigation_id=investigation.id)
        else:
            messages.error(request, f'Investigation failed: {result["error"]}')
            return redirect('home')
    existing_investigation = Investigation.objects.filter(
        onion_link=link,
        investigated_url=link.url
    ).first()
    context = {'link': link, 'existing_investigation': existing_investigation}
    return render(request, 'links/investigate.html', context)


@require_http_methods(["GET"])
def investigation_detail(request, investigation_id):
    investigation = get_object_or_404(Investigation, id=investigation_id)
    context = {'investigation': investigation}
    return render(request, 'links/investigation_detail.html', context)


@require_http_methods(["GET"])
def all_investigations(request):
    investigations = Investigation.objects.all().order_by('-created_at')
    stats = {
        'total_investigations': investigations.count(),
        'total_emails': sum(len(inv.emails) for inv in investigations),
        'total_btc': sum(len(inv.btc_addresses) for inv in investigations),
        'total_monero': sum(len(inv.monero_addresses) for inv in investigations),
        'total_ethereum': sum(len(inv.ethereum_addresses) for inv in investigations),
    }
    context = {'investigations': investigations[:50], 'stats': stats}
    return render(request, 'links/all_investigations.html', context)


@require_http_methods(["GET", "POST"])
def investigate_by_url(request):
    if request.method == 'POST':
        url = request.POST.get('url', '').strip()
        if not url:
            messages.error(request, 'Please enter a valid URL')
            return redirect('investigate_by_url')
        if '.onion' not in url.lower():
            messages.error(request, 'Please enter a valid .onion URL')
            return redirect('investigate_by_url')
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'http://' + url
        existing_investigation = Investigation.objects.filter(investigated_url=url).first()
        if existing_investigation and request.POST.get('use_existing') != 'no':
            messages.info(request, 'Using existing investigation results')
            return redirect('investigation_detail', investigation_id=existing_investigation.id)
        link, _ = OnionLink.objects.get_or_create(
            url=url,
            defaults={'title': 'Direct Investigation', 'description': 'Investigated directly via URL'}
        )
        investigator = OnionInvestigator(timeout=60)
        result = investigator.investigate(url)
        if result['success']:
            investigation, _ = Investigation.objects.update_or_create(
                investigated_url=url,
                defaults={
                    'onion_link': link,
                    'emails': result['emails'],
                    'btc_addresses': result['btc_addresses'],
                    'monero_addresses': result['monero_addresses'],
                    'ethereum_addresses': result['ethereum_addresses'],
                    'external_links': result['external_links'],
                    'has_server_status': result['has_server_status'],
                    'server_status_content': result['server_status_content'],
                }
            )
            messages.success(request, f'Investigation complete! Found {investigation.total_findings} items.')
            return redirect('investigation_detail', investigation_id=investigation.id)
        else:
            messages.error(request, f'Investigation failed: {result["error"]}')
            return render(request, 'links/investigate_by_url.html')
    return render(request, 'links/investigate_by_url.html', {})
