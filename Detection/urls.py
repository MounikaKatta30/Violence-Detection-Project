from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('about/', views.about, name='about'),
    path('upload/', views.upload_video, name='upload_video'),
    path('result/<int:pk>/', views.video_result, name='video_result'),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)