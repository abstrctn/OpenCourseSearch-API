from django.db import models
from django.conf import settings
from django.template.defaultfilters import slugify, title

import datetime, itertools, json

from networks.models import Network, NetworkManager

class Institution(models.Model):
  slug = models.CharField(max_length=20)
  name = models.CharField(max_length=200)
  
  def __unicode__(self):
    return self.name
    
class College(models.Model):
  network = models.ForeignKey(Network, null=True, blank=True)
  institution = models.ForeignKey(Institution, null=True, blank=True)
  name = models.CharField(max_length=255)
  slug = models.SlugField()
  short_name = models.CharField(max_length=255)
  #level = models.CharField(max_length=20)
  
  objects = NetworkManager()
  
  def __unicode__(self):
    return self.name
  
  class Meta:
    ordering = ('id',)
  
  def save(self, *args, **kwargs):
    if self.name:
      self.slug = slugify(self.name)[:60]
    super(College, self).save(*args, **kwargs)
  
  def get_short_name(self):
    if self.short_name:
      return self.short_name
    return self.name

class Session(models.Model):
  network = models.ForeignKey(Network)
  classifications = models.ManyToManyField('Classification', blank=True)
  colleges = models.ManyToManyField('College', blank=True)
  levels = models.ManyToManyField('Level', blank=True)
  
  name = models.CharField(max_length=40)
  slug = models.SlugField()
  system_code = models.CharField(max_length=20, null=True, blank=True)
  start_date = models.DateField()
  end_date = models.DateField()
  
  active = models.BooleanField(default=False)
  
  objects = NetworkManager()
  
  def __unicode__(self):
    return "%s: %s" % (self.network, self.name)
  
  @models.permalink
  def get_absolute_url(self):
    return ('networks.views.session_home', (), {
      'session_slug': self.slug,
    })

class SessionInfo(models.Model):
  session = models.ForeignKey(Session)
  info_type = models.CharField(max_length=100)
  info_value = models.CharField(max_length=100)

class Classification(models.Model):
  network = models.ForeignKey(Network)
  institution = models.ForeignKey(Institution)
  college = models.ForeignKey(College, blank=True, null=True)
  
  code = models.CharField(max_length=20)
  name = models.CharField(max_length=100, blank=True)
  slug = models.SlugField()
  
  objects = NetworkManager()
  
  def __unicode__(self):
    return self.code
  
  class Meta:
    ordering = ('name',)
  
  def save(self, *args, **kwargs):
    if self.name:
      self.slug = slugify(self.name)[:60]
    super(Classification, self).save(*args, **kwargs)
  
  def get_level(self):
    if self.code[-2] == 'U':
      return "Undergraduate"
    elif self.code[-2] in ['G', 'D']:
      return "Graduate"
    elif self.code[-2] == 'A':
      return "NYUAD"
    return

class Level(models.Model):
  network = models.ForeignKey(Network, null=True, blank=True)
  institution = models.ForeignKey(Institution)
  name = models.CharField(max_length=50)
  slug = models.SlugField()
  
  def __unicode__(self):
    return self.name
  
  def save(self, *args, **kwargs):
    if self.name:
      self.slug = slugify(self.name)[:60]
    super(Level, self).save(*args, **kwargs)

class Course(models.Model):
  updated_at = models.DateTimeField(default=datetime.datetime.now())
  
  network = models.ForeignKey(Network, null=True, blank=True)
  institution = models.ForeignKey(Institution, null=True, blank=True)
  college = models.ForeignKey(College, null=True, blank=True)
  classification = models.ForeignKey(Classification, null=True, blank=True)
  session = models.ForeignKey(Session)
  
  number = models.CharField(max_length=10)
  
  description = models.TextField(blank=True)
  grading = models.CharField(max_length=50)       # CAS Graded
  #location_code = models.CharField(max_length=10) # WS
  name = models.CharField(max_length=255)  # Animals & Society
  slug = models.SlugField()
  profs = models.TextField()
  level = models.ForeignKey(Level, null=True, blank=True)
  
  objects = NetworkManager()
  
  def __unicode__(self):
    return "%s (%s-%s)" % (self.name, self.classification, self.number)
  
  class Meta:
    ordering = ('classification', 'number')
  
  def save(self, *args, **kwargs):
    sections = self.sections.all()
    profs = [s.prof for s in sections]
    self.profs = " ".join(profs)
    if self.name:
      self.slug = slugify(self.name)[:60]
    return super(Course, self).save(*args, **kwargs)
  
  @models.permalink
  def get_absolute_url(self):
    slugs = "/".join(filter(None, [self.classification.slug, self.slug, "-".join([self.classification.code, self.number])]))
    return ('course_detail', (), {
      'session_slug': self.session.slug,
      'slugs': slugs
    })
  
  def get_status(self):
    statuses = self.sections.values_list('status', flat=True).distinct()
    if "Open" in statuses:
      return "Open"
    elif "Wait List" in statuses:
      return "Wait List"
    else:
      return "Closed"
  
  def prepare_json(self):
    data = {
      'name': self.smart_name(),
      'id': self.id,
      'number': self.number,
      'classification': {
        'code': self.classification.code,
        'name': self.classification.name,
        'college': {
          'name': self.college.name,
          'slug': self.college.slug,
        } if self.college else None
      },
      'level': self.level.name if self.level else None,
      'grading': self.grading,
      'description': self.smart_description(),
      'status': self.get_status(),
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
        } for section in self.sections.all()
      ]
    }
    
    available_stats = {}
    for field in ['number', 'name', 'status.label', 'status.seats', 'status.waitlist',
                    'component', 'prof', 'units', 'notes', 'meets.day', 'meets.start',
                    'meets.end', 'meets.location', 'meets.room', 'component']:
      available_stats[field] = False
      for section in data['sections']:
        if self.get_attr(section, field):
          available_stats[field] = True
    data['available_stats'] = available_stats
    
    return json.dumps(data)
  
  def get_attr(self, section, attribute_string):
    obj = section
    for attr in attribute_string.split('.'):
      if type(obj) == list:
        obj = [item.get(attr) for item in obj if item.get(attr)]
      else:
        obj = obj.get(attr)
    return obj
  
  ##
  # Intelligent casing
  def smart_name(self):
    return title(self.name).strip()
  
  ##
  # Sometimes, schools will put what's really the class description in the "notes" field
  # the section. When there is no description for a class, and every section has identical
  # notes, display the sections' note as the course description.
  def smart_description(self):
    desc_bits = [self.description]
    notes = self.sections.values_list('notes', flat=True).distinct()
    if len(notes) == 1:
      desc_bits.append(notes[0])
    return " ".join(desc_bits)


ORDERED_DAYS = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun', 'TBA', '')
class Section(models.Model):
  updated_at = models.DateTimeField(default=datetime.datetime.now())
  
  network = models.ForeignKey(Network, null=True, blank=True)
  institution = models.ForeignKey(Institution, blank=True, null=True)
  course = models.ForeignKey(Course, related_name='sections')
  
  status = models.CharField(max_length=20)
  
  number = models.CharField(max_length=20)
  name = models.CharField(max_length=255, blank=True)   # Topics: Animal Minds
  notes = models.TextField(blank=True)
  #section = models.IntegerField()                 # 001
  #section = models.CharField(max_length=10)
  prof = models.CharField(max_length=255)
  units = models.CharField(max_length=10)
  component = models.CharField(max_length=20)     # Lecture, Recitation
  reference_code = models.CharField(max_length=10, blank=True) # school's internal id for class
  
  seats_capacity = models.IntegerField(blank=True, null=True)
  seats_taken = models.IntegerField(blank=True, null=True)
  seats_available = models.IntegerField(blank=True, null=True)
  waitlist_capacity = models.IntegerField(blank=True, null=True)
  waitlist_taken = models.IntegerField(blank=True, null=True)
  waitlist_available = models.IntegerField(blank=True, null=True)
  
  # moved to meeting
  location = models.CharField(max_length=100)
  room = models.CharField(max_length=20)
  
  objects = NetworkManager()
  
  def __unicode__(self):
    return "%s .%s" % (self.course, self.number)
  
  class Meta:
    ordering = ('course','number')
  
  def get_number(self):
    return str(self.number).rjust(3, "0")
  
  def grouped_meetings(self):
    meetings = self.meeting_set.all()
    try:
      sorted_meetings = sorted(meetings, key=lambda x: ORDERED_DAYS.index(x.day))#sorted(meetings, key=lambda x: [x.start, x.end, x.location, x.room])
      grouper = itertools.groupby(sorted_meetings, key=lambda x: [x.start, x.end, x.location, x.room])
      m = []
      for key, groups in grouper:
        m.append(list(groups))
      return m
    except: return [meetings]
  
  def get_profs(self):
    return self.prof.split(', ')
  
  ##
  # See Course.smart_description()
  # If this section's note is being used as the course's description, don't display a note.
  def smart_notes(self):
    if len(self.course.sections.values_list('notes', flat=True).distinct()) == 1:
      return ''
    return self.notes

DAY_CHOICES = (
  ('Mon', 'Mon'),
  ('Tue', 'Tue'),
  ('Wed', 'Wed'),
  ('Thu', 'Thu'),
  ('Fri', 'Fri'),
  ('Sat', 'Sat'),
  ('Sun', 'Sun'),
)
class Meeting(models.Model):
  section = models.ForeignKey(Section)
  day = models.CharField(max_length=3, choices=DAY_CHOICES)
  start = models.TimeField(blank=True, null=True)
  end = models.TimeField(blank=True, null=True)
  location = models.CharField(max_length=100)
  room = models.CharField(max_length=20)
  
  def __unicode__(self):
    return "%s: %s - %s" % (self.day, self.start, self.end)
