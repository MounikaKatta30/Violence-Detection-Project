import os
from django.shortcuts import render, redirect
from django.core.files.storage import FileSystemStorage
from .models import UploadedVideo
from django.conf import settings
import cv2
import numpy as np
from keras.models import load_model
import imgaug.augmenters as iaa
import io
from django.core.files.base import ContentFile
from moviepy.editor import VideoFileClip
from moviepy.video.fx.all import resize
import tempfile
import re
from django.shortcuts import render, redirect
from django.contrib.auth import logout, login, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages

@login_required(login_url='login')
def home(request):
    return render(request, 'index.html')


def about(request):
    return render(request, 'about.html')


def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, "Invalid username or password")

    return render(request, 'login.html')


def signup_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password1 = request.POST['password']
        # password2 = request.POST['password2']

        if len(username) < 3:
            messages.error(
                request, "Username must be at least 3 characters long")
            return redirect('signup')

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            messages.error(request, "Invalid email address")
            return redirect('signup')

        if len(password1) < 8:
            messages.error(
                request, "Password must be at least 8 characters long")
            return redirect('signup')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken")
            return redirect('signup')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already taken")
            return redirect('signup')

        user = User.objects.create_user(
            username=username, email=email, password=password1)
        user.save()
        messages.success(request, "New User Created")
        return redirect('signup')

    return render(request, 'signup.html')


def logout_view(request):
    logout(request)
    return redirect('home')


def logout_view(request):
    logout(request)
    return redirect('home')

# Load the pre-trained model once
model = load_model(os.path.join(settings.BASE_DIR, 'modelnew.h5'))

def process_video(video_path):
    vidcap = cv2.VideoCapture(video_path)
    ImageFrames = []
    original_frames = []

    while vidcap.isOpened():
        success, image = vidcap.read()
        if not success:
            break
        original_frames.append(image.copy())

        # Apply augmentations
        flip = iaa.Fliplr(1.0)
        zoom = iaa.Affine(scale=1.3)
        random_brightness = iaa.Multiply((1, 1.3))
        rotate = iaa.Affine(rotate=(-25, 25))

        image_aug = flip.augment_image(image)
        image_aug = random_brightness.augment_image(image_aug)
        image_aug = zoom.augment_image(image_aug)
        image_aug = rotate.augment_image(image_aug)


        rgb_img = cv2.cvtColor(image_aug, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb_img, (128, 128))
        ImageFrames.append(resized)

    vidcap.release()

    frames = np.array(ImageFrames).reshape(-1, 128, 128, 3) / 255.0
    predictions = model.predict(frames)
    preds = predictions > 0.5

    labeled_frames = []
    for i, frame in enumerate(original_frames):
        label = "Violence" if preds[i] else "No Violence"
        color = (0, 0, 255) if preds[i] else (0, 255, 0)
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(frame, label, (10, 30), font, 1, color, 2, cv2.LINE_AA)
        labeled_frames.append(frame)

    height, width, layers = original_frames[0].shape
    temp_output_path = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4').name
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_output_path, fourcc, 20.0, (width, height))

    for frame in labeled_frames:
        out.write(frame)
    out.release()

    # Convert the .avi video to .mp4 using moviepy
    with VideoFileClip(temp_output_path) as video_clip:
        video_clip_resized = resize(video_clip, width=width)
        temp_mp4_path = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4').name
        video_clip_resized.write_videofile(temp_mp4_path, codec='libx264', audio=False, verbose=False)

    # Now, read the encoded video into BytesIO
    with open(temp_mp4_path, 'rb') as f:
        video_bytes = io.BytesIO(f.read())

    # Save the encoded video to a Django FileField
    output_filename = os.path.basename(video_path).replace('.mp4', '_processed.mp4')
    output_path = os.path.join('processed_videos', output_filename)
    full_output_path = os.path.join(settings.MEDIA_ROOT, output_path)

    with open(full_output_path, 'wb') as f:
        f.write(video_bytes.getbuffer())

    return output_path


@login_required(login_url='login')
def upload_video(request):
    if request.method == 'POST' and request.FILES['video']:
        video_file = request.FILES['video']
        fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'videos'))
        filename = fs.save(video_file.name, video_file)
        video_url = fs.url(filename)

        # Save the video to the database
        uploaded_video = UploadedVideo(video=filename)
        uploaded_video.save()

        # Process the uploaded video
        output_path = process_video(os.path.join(settings.MEDIA_ROOT, 'videos', filename))
        uploaded_video.processed_video = output_path  # Assign the correct output path
        uploaded_video.save()

        return redirect('video_result', pk=uploaded_video.pk)

    return render(request, 'upload.html')

def video_result(request, pk):
    video = UploadedVideo.objects.get(pk=pk)
    return render(request, 'result.html', {'video': video})
