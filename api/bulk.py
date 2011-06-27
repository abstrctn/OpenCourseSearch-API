import csv, codecs, cStringIO, zipfile
from django.conf import settings

BULK_ROOT = settings.BULK_ROOT

class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

def generate_bulk(network, session):
    from networks.models import Network
    from courses.models import Session, Course, Section
    
    network = Network.objects.get(slug=network)
    session = Session.objects.get(id=session)
    
    print "Dumping data for %s..." % (session)
    
    f = open(BULK_ROOT + '%s-%s-courses.csv' % (network.slug, session.slug), 'w')
    csv_writer = UnicodeWriter(f, delimiter=',', quotechar='"')
    fields = ['id', 'name', 'classification_name', 'classification_code', 'college_name', 'college_id', 'level', 'level_id', 'description', 'grading']
    csv_writer.writerow(fields)
    
    courses = Course.objects.filter(network=network, session=session)
    
    for course in courses:
      data = [course.id, course.name, course.classification.name if course.classification else '', course.classification.code if course.classification else '', course.college.name if course.college else '', course.college.id if course.college else '', course.level.name if course.level else '', course.level.id if course.level else '', course.description, course.grading]
      data = [unicode(cell) if cell else '' for cell in data]
      csv_writer.writerow(data)
    f.close()

    f = open(BULK_ROOT + '%s-%s-sections.csv' % (network.slug, session.slug), 'w')
    csv_writer = UnicodeWriter(f, delimiter=',', quotechar='"')
    fields = ['course_id', 'reference_code', 'number', 'component', 'notes', 'units', 'prof', 'status_label', 'status_seats_available', 'status_seats_taken', 'status_seats_total', 'status_waitlist_available', 'status_waitlist_taken', 'status_waitlist_total', 'meet1_days', 'meet1_location', 'meet1_room', 'meet1_start', 'meet1_end', 'meet2_days', 'meet2_location', 'meet2_room', 'meet2_start', 'meet2_end', 'meet3_days', 'meet3_location', 'meet3_room', 'meet3_start', 'meet3_end']
    csv_writer.writerow(fields)

    sections = Section.objects.filter(network=network, course__session=session)
    
    for section in sections:
      data = [section.course.id, section.reference_code, section.number, section.component, section.notes, section.units, section.prof, section.status, section.seats_available, section.seats_taken, section.seats_capacity, section.waitlist_available, section.waitlist_taken, section.waitlist_capacity]
      for meet in section.meeting_set.all():
        data.extend([meet.day, meet.location, meet.room, meet.start, meet.end])
      
      data = [unicode(cell) if cell else '' for cell in data]
      csv_writer.writerow(data)
    f.close()
    
    print "Zipping..."
    # zip up the files
    for fileset in ['courses', 'sessions']:
      myzip = zipfile.ZipFile(BULK_ROOT + '%s-%s-%s.zip' % (network.slug, session.slug, fileset), 'w')
      myzip.write(BULK_ROOT + '%s-%s-%s.csv' % (network.slug, session.slug, fileset))
      myzip.close()
