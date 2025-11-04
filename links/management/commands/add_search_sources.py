from django.core.management.base import BaseCommand
from links.models import SearchSource


class Command(BaseCommand):
    help = 'Add default onion search engine sources'

    def handle(self, *args, **kwargs):
        sources = [
            {
                'name': 'Ahmia',
                'url': 'https://ahmia.fi/',
                'search_url_pattern': 'https://ahmia.fi/search/?q={query}',
                'is_active': True
            },
            {
                'name': 'Onionland Search',
                'url': 'http://3bbad7fauom4d6sgppalyqddsqbf5u5p56b5k5uk2zxsy3d6ey2jobad.onion/',
                'search_url_pattern': 'http://3bbad7fauom4d6sgppalyqddsqbf5u5p56b5k5uk2zxsy3d6ey2jobad.onion/search?q={query}',
                'is_active': True
            },
            {
                'name': 'Torch',
                'url': 'http://torchdeedp3i2jigzjdmfpn5ttjhthh5wbmda2rr3jvqjg5p77c54dqd.onion/',
                'search_url_pattern': 'http://torchdeedp3i2jigzjdmfpn5ttjhthh5wbmda2rr3jvqjg5p77c54dqd.onion/search?query={query}',
                'is_active': True
            },
        ]
        
        created_count = 0
        for source_data in sources:
            source, created = SearchSource.objects.get_or_create(
                name=source_data['name'],
                defaults=source_data
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'✅ Created: {source.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'⚠️ Already exists: {source.name}'))
        
        self.stdout.write(self.style.SUCCESS(f'\n🎉 Added {created_count} new search source(s)'))
        self.stdout.write(self.style.WARNING('\n⚠️ Note: All sources are disabled by default. You need to:'))
        self.stdout.write('1. Go to /admin/links/searchsource/')
        self.stdout.write('2. Verify the URLs are correct')
        self.stdout.write('3. Update search_url_pattern to match actual search engine structure')
        self.stdout.write('4. Enable sources by checking "is_active"')

