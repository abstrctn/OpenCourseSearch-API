from django.conf.urls.defaults import *

urlpatterns = patterns('api.v01.views',
  url(r'^course$', 'course', name='api_v01_course'),
  url(r'^network$', 'network', name='api_v01_course'),
  url(r'^session$', 'session', name='api_v01_course'),
  url(r'^bulk$', 'bulk', name='api_v01_bulk'),
)