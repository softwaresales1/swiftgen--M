from django.db import models
from django.utils import timezone

class Room(models.Model):
    room_name = models.CharField(max_length=255)
    users = models.ManyToManyField('User', related_name='rooms')

class Message(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    sender = models.CharField(max_length=255)
    message = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)  # Set a default value

class User(models.Model):
    username = models.CharField(max_length=255, unique=True)
