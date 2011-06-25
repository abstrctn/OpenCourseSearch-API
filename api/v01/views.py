from django.http import Http404, HttpResponse
from django.conf import settings
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.db.models import Q
from django.core.paginator import Paginator
from django.core.serializers import serialize
from django.template.defaultfilters import slugify

import datetime, json

from haystack.query import SearchQuerySet

from courses.models import *
from networks.models import Network
from decorators import api_auth, jsonp, parse_facets

LIMIT = 20
#@api_auth
@jsonp
@parse_facets
def course(request):
  data = request.GET
  
  network = data.get('network', '')
  session = slugify(data.get('session', ''))
  query = data.get('query', '')
  facets = data.get('facets', '')
  if data.get('page'):
    offset = max(0, (int((data['page'])) - 1) * LIMIT)
  else:
    offset = int(data.get('offset', 0))
  
  sqs = SearchQuerySet().models(Course).filter(network=network, session=session)
  for facet in facets:
    sqs = sqs.filter(**{facet: '%s' % slugify(facets[facet])})
  sqs = sqs.auto_query(query)
  
  results = sqs[offset:offset+LIMIT]
  rendered = ",".join([r.json for r in results])
  
  response = {
    'offset': offset,
    'page': (offset / LIMIT) + 1,
    'results_per_page': LIMIT,
    'total': sqs.count(),
    'num': len(results),
    'more': (offset + len(results)) < sqs.count(),
    'results': "*****"
  }
  dumped = json.dumps(response)
  dumped = dumped.replace('"*****"', "[%s]" %rendered)
  
  return dumped
  #except:
  #  return HttpResponse(status=400)

#@api_auth
@jsonp
def network(request):
  data = request.GET
  network = data.get('network')
  
  all = SearchQuerySet().models(Network)
  sqs = SearchQuerySet().models(Network).filter(slug=network)
  dumped_json = sqs[0].json
  
  return dumped_json

#@api_auth
@jsonp
def session(request):
  data = request.GET
  network = data.get('network', '')
  session = slugify(data.get('session', ''))
  
  dumped_json = SearchQuerySet().models(Session).filter(network=network, slug=session)[0].json
  
  return dumped_json
