# project/server/extractor/views.py


import os
from flask import render_template, Blueprint, url_for, redirect, flash, request
from flask import current_app as app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.datastructures import CombinedMultiDict

from project.server import bcrypt, db
from project.server.models import User, Document
from project.server.extractor.forms import UploadForm
from project.server.extractor.services import DocumentService


extractor_blueprint = Blueprint("extractor", __name__)

ALLOWED_UPLOAD_EXTENSIONS = set(['txt', 'pdf', 'md'])

@extractor_blueprint.route("/upload", methods=["GET", "POST"])
@login_required
def document_upload():
    form = UploadForm(CombinedMultiDict((request.files, request.form)))

    if request.method == 'POST':
        if form.validate_on_submit():
            file = form.file.data
            if file is None:
                flash('No selected file', "danger")
                return render_template("extractor/upload.html", form=form)
            # if user does not select file, browser also
            # submit an empty part without filename
            if file.filename == '':
                flash('No selected file or filename is empty', "danger")
                return render_template("extractor/upload.html", form=form)
            if allowed_file(file.filename) != True:
                flash('Please upload file extensions {}'.format(ALLOWED_UPLOAD_EXTENSIONS),
                    "danger")
                return render_template("extractor/upload.html", form=form)

            
            filename = secure_filename(file.filename)

            save_to_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(current_user.id))
            if not os.path.exists(save_to_dir):
                os.makedirs(save_to_dir)
            save_to = os.path.join(save_to_dir, filename)
            file.save(save_to)
            
            app.logger.info('{} uploaded file to {}'.format(current_user.email, save_to))

            documentService = DocumentService()
            document = documentService.create(content_type=file.content_type, title=filename, 
                created_by=current_user.id, path=save_to)
            documentService.index_and_extract_skills(document)

            return render_template("extractor/upload.html", filename=filename, form=form)
     
    return render_template("extractor/upload.html", form=form)
    
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_UPLOAD_EXTENSIONS