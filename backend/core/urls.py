from django.urls import path
from .views import FileUploadView, ProcessDataView

urlpatterns = [
    # 'upload/' 경로를 FileUploadView와 연결하는 설정
    path('upload/', FileUploadView.as_view(), name='file-upload'),

    path('process/', ProcessDataView.as_view(), name='process-data'),
]