from django.urls import path
from .views import FileUploadView

urlpatterns = [
    # 'upload/' 경로를 FileUploadView와 연결하는 설정
    path('upload/', FileUploadView.as_view(), name='file-upload'),
]