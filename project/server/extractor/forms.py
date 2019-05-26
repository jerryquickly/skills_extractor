# project/server/user/forms.py


from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import StringField
# from wtforms.validators import


class UploadForm(FlaskForm):
    file = FileField("Document", [])


class SearchForm(FlaskForm):
    q = StringField(
        label="",
        validators=[],
    )
