# project/server/extractor/services.py

from flask import current_app as app

from project.server import db
from project.server.models import Document

class DocumentService():

    def create(self, content_type, title, created_by, path) -> Document:
        document = Document(content_type=content_type, title=title, created_by=created_by
            , path=path)
        db.session.add(document)
        db.session.commit()

        return document

    def index_and_extract_skills(self, document: Document):
        if (document is None or document.id is None):
            return

        app.logger.info('Index & extract skill for document {} '.format(document.title))     
        