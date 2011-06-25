from django.http import HttpResponse
from django.conf import settings
import functools, redis, re

def api_auth(method):
  @functools.wraps(method)
  def wrapper(request, *args, **kwargs):
    key = request.GET.get('api-key', '')
    r = redis.Redis(settings.REDIS_HOST)
    state = r.get('%s:status' % key)
    if state in ['pending', 'active']:
      r.incr('%s:requests' % key)
      return method(request, *args, **kwargs)
    elif state in ['inactive', '']:
     return HttpResponse('403 Developer Inactive', status=403)
    else:
     return HttpResponse('403 Developer Inactive', status=403)
      
  return wrapper

##
# if a callback parameter was passed to the API, wrap the resulting json in a callback function.
def jsonp(method):
  @functools.wraps(method)
  def wrapper(request, *args, **kwargs):
    response = method(request, *args, **kwargs)
    callback = request.GET.get('callback', '')
    if callback:
      response = "%s(%s)" % (callback, response)
      return HttpResponse(response, mimetype='text/javascript')
    return HttpResponse(response, mimetype='application/json')
  return wrapper

##
# strip all facets of the type "facet: value" out of @query and into a list of @facets
# of the form {'facet': value}
def parse_facets(method):
  @functools.wraps(method)
  def wrapper(request, *args, **kwargs):
    params = request.GET.copy()
    params['facets'] = {}
    
    query = params.get('query', '')
    facets = re.findall('(\w+): "([^"]*)"', query)
    for facet, value in facets:
      params['facets'][facet] = value
      query = query.replace('%s: "%s"' % (facet, value), '')
    params['query'] = query
    
    request.GET = params
    
    return method(request, *args, **kwargs)
  return wrapper
