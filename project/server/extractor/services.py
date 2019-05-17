# project/server/extractor/services.py

import os
import json
import PyPDF2

from flask import current_app as app
from elasticsearch import Elasticsearch
from celery import Task

from project.server import db
from project.server.models import Document
from project.server import celery


class DocumentService():

    def __init__(self):
        self.index = app.config["ELASTICSEARCH_INDEX"]

    def create(self, content_type, title, created_by, filename, path) -> Document:
        document = Document(content_type=content_type, title=title,
                            created_by=created_by, filename=filename, path=path)
        db.session.add(document)
        db.session.commit()

        return document

    def find_indexed(self, id):
        es = Elasticsearch()
        res = es.get(index=self.index, doc_type='document', id=id)
        app.logger.debug(res['_source'])
        return json.loads(res['_source'])

    def index_and_extract_skills_async(self, document_id):
        index_and_extract_skills.delay(document_id=document_id)

# @celery.task(name="skills_extractor.sum_ned", bind=True, default_retry_delay=60, max_retries=120, acks_late=True)
@celery.task()
def sum_ne(a, b):
    app.logger.info('Sum {} {}: {}'.format(a, b, a + b))
    return a + b

# @celery.task(bind=True, default_retry_delay=60, max_retries=120, acks_late=True)
@celery.task()
def index_and_extract_skills(document_id):
    if document_id is None:
        app.logger.info('Document id is required')
        return

    document = Document.query.filter_by(id=document_id).first()
    if (document is None):
        app.logger.info('Document {} is not found'.format(document_id))
        return

    index_document(document=document)

    app.logger.info(
        'TODO: Extract skill for document {}: {} '.format(document.id, document.title))


def index_document(document: Document):
    index = app.config["ELASTICSEARCH_INDEX"]
    doc = {
        "id": document.id,
        "title": document.title,
        "content_type": document.content_type,
        "created_on": document.created_on,
        "created_by": document.created_by
    }

    document_content = get_document_content(document)
    doc['content'] = document_content

    es = Elasticsearch()
    res = es.index(index=index, doc_type='document', id=document.id, body=doc)
    es.indices.refresh(index=index)


def get_document_content(document: Document) -> str:
    content = None

    path = document.path
    if path is not None and not os.path.isabs(path):
        path = os.path.join(app.instance_path, path)

    app.logger.debug('get_document_content from {}'.format(path))

    if document.content_type.endswith("/pdf") or document.content_type.endswith("x-pdf"):
        try:
            content = get_document_content_by_PyPDF2(document=document)
        except (IOError, FileNotFoundError) as e:
            app.logger.warning("Error {}: Failed parse file {}".format(
                e.__class__.__name__, document.filename))
    elif os.path.isabs(path):
        try:
            f = open(path, "r")
            content = f.read()
        except (IOError, FileNotFoundError) as e:
            app.logger.warning("Error {}: Failed read file {}".format(
                e.__class__.__name__, document.filename))
        finally:
            if f != None:
                f.close()

    return content

def get_document_content_by_PyPDF2(document: Document) -> str:
    content = None

    path = document.path
    if path is not None and not os.path.isabs(path):
        path = os.path.join(app.instance_path, path)

    app.logger.debug('get_document_content_by_PyPDF2 from {}'.format(path))

    if os.path.isabs(path):
        try:
            pdfFileObject = open(path, 'rb')
            pdfReader = PyPDF2.PdfFileReader(pdfFileObject)
            count = pdfReader.numPages
            app.logger.debug('Document has {} page'.format(count))
            pagesText = ""
            for i in range(count):
                page = pdfReader.getPage(i)
                pageText = page.extractText()
                pagesText += pageText
            content = pagesText
        except (IOError, FileNotFoundError) as e:
            app.logger.warning("Error {}: PyPDF2 failed on file {}".format(
                e.__class__.__name__, document.filename))

    return content
