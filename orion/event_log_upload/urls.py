from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import re_path
from django.views.static import serve

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("upload_eventlog", views.upload_page, name="upload_page"),
    path("update_pm_slider", views.update_pm_slider, name="update_pm_slider"),
    path("detect_dynamic_event_attributes", views.detect_dynamic_event_attributes, name="detect_dynamic_event_attributes"),
    path("classify_data_type", views.classify_data_type, name="classify data type"),
    path("switch_data_type", views.switch_data_type, name="switch_data_type"),
    path("conclude_dynamic_attribute_detection", views.conclude_dynamic_attribute_detection, name="conclude_dynamic_detection"),
    path("detect_context_aware_activities", views.detect_context_aware_activities, name="detect_context_aware_activities"),
    path("set_recurring_activities", views.set_recurring_activity, name="set_recurring_activity"),
    path("update_context_slider", views.update_context_slider, name="update_context_slider"),
    path("remove_context_from_activity", views.remove_context_from_activity, name="remove_context_from_activity"),
    path("conclude_context_aware_activities", views.conclude_context_aware_activities, name="conclude_context_aware_activities"),
    path("set_mandatory_attributes", views.set_mandatory_attributes, name="set_mandatory_attributes"),
    path("detect_change_patterns", views.detect_change_patterns, name="detect_change_patterns"),
    path("detect_relationships", views.detect_relationships, name="detect_relationships"),
    path("explore_change_patterns", views.explore_change_patterns, name="explore_change_patterns"),
    re_path(r'^media/(?P<path>.*)$', serve,{'document_root': settings.MEDIA_ROOT}), 
    re_path(r'^static/(?P<path>.*)$', serve,{'document_root': settings.STATIC_ROOT}), 
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += staticfiles_urlpatterns()