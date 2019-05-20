# project/server/extractor/services.py

import os
import json
from typing import List

import PyPDF2
from flask import current_app as app
from elasticsearch import Elasticsearch
from celery import Task

from project.server import db
from project.server.models import Document
from project.server import celery
from project.server.extractor.indexes import extract_skills_in_document


class DocumentService():

    def __init__(self):
        self.es_host = app.config["ELASTICSEARCH_HOST"]
        self.es_index = app.config["ELASTICSEARCH_INDEX"]

    def create(self, content_type, title, created_by, filename, path) -> Document:
        document = Document(content_type=content_type, title=title,
                            created_by=created_by, filename=filename, path=path)
        db.session.add(document)
        db.session.commit()

        return document

    def find_indexed(self, id):
        es = Elasticsearch(self.es_host)
        res = es.get(index=self.es_index, doc_type='document', id=id)
        app.logger.debug(res['_source'])
        return json.loads(res['_source'])

    def index_and_extract_skills_async(self, document_id):
        args =  tuple([document_id])
        index_and_extract_skills.apply_async(args=(document_id,), )


#@celery.task(bind=True, default_retry_delay=60, max_retries=180, acks_late=True)
@celery.task(name='tasks.index_and_extract_skills', default_retry_delay=60, max_retries=200, acks_late=True)
def index_and_extract_skills(document_id):
    if document_id is None:
        app.logger.info('Document id is required')
        return

    document = Document.query.filter_by(id=document_id).first()
    if (document is None):
        app.logger.info('Document {} is not found'.format(document_id))
        return

    index_document(document=document)

    app.logger.debug(
        'Extract skill for document {}: {} '.format(document.id, document.title))

    try:
        skill_extracts = extract_skills_in_document(document_id)

        skills = list(set(skill_extract.name for skill_extract in skill_extracts))
        skill_extracts_list = [skill_extract.__dict__ for skill_extract in skill_extracts]
        update_data = {
            "skills": skills,
            "skill_extracts": skill_extracts_list
        }

        app.logger.debug(
            "Extracted skills for document {}:\n skills: {} \n skill_extracts: {}".format(document.id, skills, skill_extracts_list))
        update_index_doc(document_id, update_data)
    except BaseException as ex:
        update_index_doc(document_id, {"skill_extracts_exception": str(ex)})
        raise


def index_document(document: Document):
    es_host = app.config["ELASTICSEARCH_HOST"]
    index = app.config["ELASTICSEARCH_INDEX"]

    document_content = get_document_content(document)
    n_words = 0 if document_content is None else len(document_content.split())

    doc = {
        "id": document.id,
        "title": document.title,
        "content_type": document.content_type,
        "created_on": document.created_on,
        "created_by": document.created_by,
        "content": document_content,
        "n_words": n_words
    }

    es = Elasticsearch(es_host)
    res = es.index(index=index, doc_type='document', id=document.id, body=doc)
    es.indices.refresh(index=index)


def update_index_doc(id, update_data, doc_type='document'):
    es_host = app.config["ELASTICSEARCH_HOST"]
    index = app.config["ELASTICSEARCH_INDEX"]

    body = {"doc": update_data}

    es = Elasticsearch(es_host)
    res = es.update(index=index, doc_type=doc_type, id=id, body=body)
    es.indices.refresh(index=index)


def search_index_skills(ids: List=None) -> dict:
    if len(ids) == 0:
        return dict()

    es_host = app.config["ELASTICSEARCH_HOST"]
    index = app.config["ELASTICSEARCH_INDEX"]

    es = Elasticsearch(es_host)
    res = es.search(index=index, body={
        "_source" : ["skills", "skill_extracts"],
        "size" : len(ids),
        "query": {
            "terms" : { "id" : ids} 
        }
    })
    
    result = dict()
    for doc in res['hits']['hits']:
        id = int(doc["_id"])
        try:
            skills = doc['_source']['skills']
            result[id] = skills
        except KeyError:
            result[id] = "Skills've not extracted yet"
        
    return result


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
