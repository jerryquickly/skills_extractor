# project/server/tests/test_user.py


import datetime
import unittest
import re
import io

from flask_login import current_user

from base import BaseTestCase
from project.server import bcrypt, db
from project.server.models import User, Document
from project.server.user.forms import LoginForm
from project.server.extractor.services import index_and_extract_skills

class TestUserBlueprint(BaseTestCase):

    def test_upload(self):
        """Test upload."""
        self.login("test@min.com", "test_user")
        
        filename = "codeconventions-150003.pdf"
        data = dict(
            #file=(io.BytesIO(b'This is a file for java developer. You should see skill java'), filename)
            file=(open("project/tests/upload_files/codeconventions-150003.pdf", "rb"), filename)
        )

        response = self.client.post(
            "/upload", 
            data=data, follow_redirects=True,
            content_type='multipart/form-data'
        )
        self.assertIn(b'uploaded', response.data)
        
        documents = Document.query.filter_by(filename=filename).all()
        self.assertTrue(len(documents) > 0)

        index_and_extract_skills(documents[0].id)

    def test_mydocuments(self):
        """Test mydocuments."""
        self.login("test@min.com", "test_user")
        
        response = self.client.get(
            "/mydocuments"
        )

        try:
            self.assertIn(b'Upload on', response.data)
        except BaseException:
            self.assertIn(b"haven't uploaded", response.data)


    def test_download(self):
        """Test download."""
        self.login("test@min.com", "test_user")

        user = User.query.filter_by(email="test@min.com").first()
        user_id = int(user.id)

        documents = Document.query.filter_by(created_by=user_id).all()
        if len(documents) > 0:
            response = self.client.get(
                "/mydocuments/" + str(documents[0].id) 
            )
        else:
            self.test_upload()
            documents = Document.query.filter_by(created_by=user_id).all()
            self.assertTrue(len(documents) > 0)
            response = self.client.get(
                "/mydocuments/" + str(documents[0].id) 
            )

            

if __name__ == "__main__":
    unittest.main()
