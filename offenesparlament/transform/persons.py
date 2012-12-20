#coding: utf-8
import logging

import sqlaload as sl

from offenesparlament.core import etl_engine
from offenesparlament.data.lib.text import url_slug
from offenesparlament.data.lib.reference import resolve_person, \
    BadReference

log = logging.getLogger(__name__)

def make_long_name(data):
    pg = lambda n: data.get(n) if data.get(n) and data.get(n) != 'None' else ''
    # dept. names are long and skew levenshtein otherwise:
    #ressort = hashlib.sha1(pg('ressort').encode('utf-8')).hexdigest()[:5]
    ressort = "".join([x[0] for x in pg('ressort').split(' ') if len(x)])
    fraktion = pg('fraktion').replace(u"BÜNDNIS ", "B")
    return "%s %s %s %s %s" % (pg('titel'),
            pg('vorname'), pg('nachname'), pg('ort'),
            fraktion or ressort)

def make_person(beitrag, fp, engine):
    try:
        fp = resolve_person(fp)
        person = {
            'fingerprint': fp,
            'vorname': beitrag['vorname'],
            'nachname': beitrag['nachname'],
            'ort': beitrag.get('ort'),
            'ressort': beitrag.get('ressort'),
            'land': beitrag.get('land'),
            'fraktion': beitrag.get('fraktion')
        }
        sl.upsert(engine, sl.get_table(engine, 'person'), person,
                  unique=['fingerprint'])
    except BadReference:
        pass
    return fp

def generate_person_long_names(engine):
    log.info("Generating person fingerprints and slugs...")
    Person = sl.get_table(engine, 'person')
    for person in sl.find(engine, Person):
        try:
            long_name = make_long_name(person)
            long_name = resolve_person(long_name)
            log.info(" -> %s" % long_name.strip())
            sl.upsert(engine, Person, {
                             'fingerprint': long_name,
                             'slug': url_slug(long_name),
                             'id': person['id']},
                             unique=['id'])
        except BadReference:
            pass

    log.info("Updating 'rollen' to have fingerprints...")
    Rolle = sl.get_table(engine, 'rolle')
    for person in sl.find(engine, Person):
        if person['mdb_id']:
            sl.upsert(engine, Rolle, {
                'mdb_id': person['mdb_id'],
                'fingerprint': person['fingerprint']
                }, unique=['mdb_id'])
        elif person['source_url']:
            sl.upsert(engine, Rolle, {
                'person_source_url': person['person_source_url'],
                'fingerprint': person['fingerprint']
                }, unique=['person_source_url'])

if __name__ == '__main__':
    engine = etl_engine()
    print "DESTINATION", engine
    generate_person_long_names(engine)

