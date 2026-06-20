from django.db import migrations, models
import django.db.models.deletion
import django.core.validators

class Migration(migrations.Migration):

    dependencies = [
        ('main', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='ride',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('confirmed', 'Confirmed'), ('in_progress', 'In Progress'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], default='pending', max_length=20),
        ),
        migrations.AddField(
            model_name='driverprofile',
            name='is_verified',
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name='DriverDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('doc_type', models.CharField(choices=[('LICENSE_WITH_ID', 'Driver License with Self ID Card')], default='LICENSE_WITH_ID', max_length=20)),
                ('file', models.FileField(upload_to='driver_docs/')),
                ('status', models.CharField(choices=[('PENDING', 'Pending Review'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected')], default='PENDING', max_length=20)),
                ('admin_note', models.TextField(blank=True)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('driver', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='main.user')),
            ],
        ),
        migrations.CreateModel(
            name='Rating',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stars', models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ('comment', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('driver', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ratings_received', to='main.user')),
                ('passenger', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ratings_given', to='main.user')),
                ('ride', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='rating', to='main.ride')),
            ],
        ),
    ]
