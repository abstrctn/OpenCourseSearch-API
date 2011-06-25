import json

from haystack.indexes import *
from haystack import site

from django.template.defaultfilters import slugify

from courses.models import Course, Session

class CourseIndex(RealTimeSearchIndex):
  text = CharField(document=True, use_template=True)
  json = CharField(indexed=False)
  
  network = FacetCharField(model_attr='network')
  session = FacetCharField(model_attr='session')
  
  #name = CharField(model_attr='name')
  level = FacetCharField(model_attr='level')
  college = FacetCharField(model_attr='college')
  subject = FacetCharField(model_attr='classification')
  status = FacetCharField()
  professor = MultiValueField()
  
  #description = CharField(model_attr='description')
  #number = CharField(model_attr='number')
  
  def index_queryset(self):
    return Course.objects.all()
  
  def prepare_network(self, obj):
    return obj.network.slug
  
  def prepare_session(self, obj):
    return obj.session.slug
  
  def prepare_level(self, obj):
    return obj.level.slug if obj.level else ''
  
  def prepare_college(self, obj):
    return obj.college.slug if obj.college else ''
  
  def prepare_subject(self, obj):
    return obj.classification.slug if obj.classification else ''
  
  def prepare_status(self, obj):
    statuses = obj.sections.values_list('status', flat=True).distinct()
    if "Open" in statuses:
      return slugify("Open")
    elif "Wait List" in statuses:
      return slugify("Wait List")
    else:
      return slugify("Closed")
  
  def prepare_professor(self, obj):
    return [section.prof for section in obj.sections.all()]
  
  def prepare_json(self, obj):
    data = {
      'name': obj.smart_name(),
      'id': obj.id,
      'number': obj.number,
      'classification': {
        'code': obj.classification.code,
        'name': obj.classification.name,
        'college': {
          'name': obj.college.name,
          'slug': obj.college.slug,
        } if obj.college else None
      },
      'level': obj.level.name if obj.level else None,
      'grading': obj.grading,
      'description': obj.smart_description(),
      'sections': [
        {
          'id': section.id,
          'reference_code': section.reference_code,
          'number': section.number,
          'name': section.name.strip(),
          'status': {
            'label': section.status,
            'seats': {
              'total': section.seats_capacity,
              'taken': section.seats_taken,
              'available': section.seats_available
            } if section.seats_taken else None,
            'waitlist': {
              'total': section.waitlist_capacity,
              'taken': section.waitlist_taken,
              'available': section.waitlist_available
            } if section.waitlist_capacity or section.waitlist_taken else None
          },
          'component': section.component,
          'prof': section.prof,
          'units': section.units,
          'notes': section.smart_notes(),
          'meets': [
            {
              'day': ", ".join([meeting.get_day_display() for meeting in meetings]),
              'start': meetings[0].start.strftime('%I:%M %p') if meetings and meetings[0].start else None,
              'end': meetings[0].end.strftime('%I:%M %p') if meetings and meetings[0].end else None,
              'location': meetings[0].location if meetings else None,
              'room': meetings[0].room if meetings else None,
            } for meetings in section.grouped_meetings()
          ]
        } for section in obj.sections.all()
      ]
    }
    return json.dumps(data)
site.register(Course, CourseIndex)

class SessionIndex(SearchIndex):
  text = CharField(document=True, use_template=True)
  json = CharField(indexed=False)
  
  network = FacetCharField(model_attr='network')
  slug = CharField(model_attr='slug')
  
  def index_queryset(self):
    return Session.objects.all()
  
  def prepare_network(self, obj):
    return obj.network.slug
  
  def prepare_slug(self, obj):
    return obj.slug
  
  def prepare_json(self, obj):
    data = {
      'slug': obj.slug,
      'name': obj.name,
      'start_date': obj.start_date.strftime('%Y-%m-%d'),
      'end_date': obj.end_date.strftime('%Y-%m-%d'),
      'code': obj.system_code,
      'id': obj.id,
      'colleges': [
        {
          'slug': college.slug,
          'name': college.name.strip(),
          'short_name': college.short_name,
          'id': college.id
        } for college in obj.colleges.all()
      ],
      'subjects': [
        {
          'code': classification.code,
          'name': classification.name.strip(),
          'slug': classification.slug,
          'id': classification.id,
          'college': classification.college.id if classification.college else None,
        } for classification in obj.classifications.all()
      ],
      'levels': [
        {
          'name': level.name.strip(),
          'slug': level.slug,
          'id': level.id
        } for level in obj.levels.all()
      ]
    }
    return json.dumps(data)
site.register(Session, SessionIndex)