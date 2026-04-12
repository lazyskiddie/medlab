from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        PATIENT = 'patient', 'Patient'
        DOCTOR  = 'doctor',  'Doctor'
        ADMIN   = 'admin',   'Admin'

    role          = models.CharField(max_length=10, choices=Role.choices, default=Role.PATIENT)
    phone         = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender        = models.CharField(
        max_length=10,
        choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')],
        blank=True,
    )

    def __str__(self):
        return f'{self.username} ({self.role})'