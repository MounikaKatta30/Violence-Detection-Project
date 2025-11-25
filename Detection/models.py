from django.db import models


class UploadedVideo(models.Model):
    video = models.FileField(upload_to='videos/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_video = models.FileField(
        upload_to='processed_videos/', blank=True, null=True)
