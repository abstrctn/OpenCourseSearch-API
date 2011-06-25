from django.conf.urls.defaults import *
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
  (r'^admin/', include(admin.site.urls)),
  
  url(r'^register$', 'api.views.register', name='api_register'),
  url(r'^register/submit$', 'api.views.register_submit', name='api_register_submit'),
  
  (r'^v0.1/', include('api.v01.urls')),
  (r'^0.1/', include('api.v01.urls')),

  url(r'^(?P<session_slug>[-\w]+)/(?P<slugs>.+)', 'networks.views.course', name='course_detail'),
)