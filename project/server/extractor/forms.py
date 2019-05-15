# project/server/user/forms.py


from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
#from wtforms.validators import 


class UploadForm(FlaskForm):
    file = FileField("Document", [])
