# Generated manually

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('links', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Investigation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('investigated_url', models.URLField(max_length=500)),
                ('emails', models.JSONField(blank=True, default=list)),
                ('btc_addresses', models.JSONField(blank=True, default=list)),
                ('monero_addresses', models.JSONField(blank=True, default=list)),
                ('ethereum_addresses', models.JSONField(blank=True, default=list)),
                ('has_server_status', models.BooleanField(default=False)),
                ('server_status_content', models.TextField(blank=True, null=True)),
                ('external_links', models.JSONField(blank=True, default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('onion_link', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='investigations', to='links.onionlink')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='investigation',
            unique_together={('onion_link', 'investigated_url')},
        ),
    ]

