from django.shortcuts import render, redirect
from .models import Room, Message, User

def HomeView(request):
    if request.method == "POST":
        username = request.POST["username"]
        room_name = request.POST["room"]
        
        user, created = User.objects.get_or_create(username=username)
        
        try:
            existing_room = Room.objects.get(room_name__icontains=room_name)
        except Room.DoesNotExist:
            existing_room = Room.objects.create(room_name=room_name)
        
        existing_room.users.add(user)
        existing_room.save()
        
        return redirect("chat:room", room_name=room_name, username=username)
    return render(request, "home.html")

def RoomView(request, room_name, username):
    existing_room = Room.objects.get(room_name__icontains=room_name)
    get_messages = Message.objects.filter(room=existing_room)
    
    user = User.objects.get(username=username)
    user_rooms = user.rooms.all()
    
    context = {
        "messages": get_messages,
        "user": username,
        "room_name": existing_room.room_name,
        "rooms": user_rooms,
    }

    return render(request, "room.html", context)
