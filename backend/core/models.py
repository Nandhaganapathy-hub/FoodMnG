  
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('superadmin', 'Super Admin'),
        ('canteen_admin', 'Canteen Admin'),
        ('ngo', 'NGO'),
    ]
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='canteen_admin')

    def __str__(self):
        return f"{self.username} ({self.role})"

class Canteen(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='canteen_profile',
                                limit_choices_to={'role': 'canteen_admin'})
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    contact_number = models.CharField(max_length=15, blank=True)
    capacity = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class NGO(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='ngo_profile',
                                limit_choices_to={'role': 'ngo'})
    name = models.CharField(max_length=255)
    address = models.TextField()
    contact_person = models.CharField(max_length=255)
    phone = models.CharField(max_length=15)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Record(models.Model):
    canteen = models.ForeignKey(Canteen, on_delete=models.CASCADE, related_name='records')
    date = models.DateField()
    day = models.CharField(max_length=20)
    meal_menu_info = models.TextField(blank=True)
    cooked = models.PositiveIntegerField(help_text="Quantity cooked (kg/servings)")
    surplus = models.PositiveIntegerField(help_text="Surplus quantity")
    no_members = models.PositiveIntegerField(help_text="Student footfall")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['canteen', 'date']

    def __str__(self):
        return f"{self.canteen.name} - {self.date}"

class RE(models.Model):
    """Reinforcement / Model feedback record"""
    canteen = models.ForeignKey(Canteen, on_delete=models.CASCADE, related_name='re_records')
    date = models.DateField()
    model_predict = models.IntegerField(help_text="Predicted value (surplus/footfall)")
    actual_data = models.IntegerField(help_text="Actual measured value")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"RE {self.canteen} {self.date}"

class Alter(models.Model):
    """Food spoiled / at-risk alert"""
    canteen = models.ForeignKey(Canteen, on_delete=models.CASCADE, related_name='alters')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    quantity = models.PositiveIntegerField()
    meal_type = models.CharField(max_length=50, choices=[
        ('breakfast', 'Breakfast'), ('lunch', 'Lunch'), ('dinner', 'Dinner'), ('snack', 'Snack')
    ])
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Alter {self.date} {self.meal_type} - {self.canteen.name}"