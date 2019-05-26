# project/server/extractor/views.py


import os
import datetime

from flask import render_template, Blueprint, flash, request, send_file
from flask import current_app as app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.datastructures import CombinedMultiDict
from elasticsearch.exceptions import NotFoundError as ElasticsearchNotFoundError

from project.server.models import Document
from project.server.extractor.forms import UploadForm, SearchForm
from project.server.extractor.services import DocumentService, search_index_skills
from project.server.extractor.indexes import search_index_content

extractor_blueprint = Blueprint("extractor", __name__)

ALLOWED_UPLOAD_EXTENSIONS = set(['txt', 'pdf', 'md'])


@extractor_blueprint.route("/upload", methods=["GET", "POST"])
@login_required
def document_upload():
    """Upload document"""
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
            if allowed_file(file.filename) is not True:
                flash('Please upload file extensions {}'.format(ALLOWED_UPLOAD_EXTENSIONS),
                      "danger")
                return render_template("extractor/upload.html", form=form)

            filename = secure_filename(file.filename)

            save_to_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(current_user.id))
            if not os.path.isabs(save_to_dir):
                save_to_dir = os.path.join(app.instance_path, save_to_dir)
            if not os.path.exists(save_to_dir):
                os.makedirs(save_to_dir)

            current_milli_time = datetime.datetime.now().microsecond
            save_to = os.path.join(save_to_dir, "{}-{}".format(str(current_milli_time), filename))
            file.save(save_to)

            app.logger.info('{} uploaded file to {}'.format(current_user.email, save_to))

            documentService = DocumentService()
            document = documentService.create(content_type=file.content_type, title=filename,
                                              created_by=current_user.id, filename=filename,
                                              path=save_to)
            app.logger.info("Call index_and_extract_skills asynch")
            documentService.index_and_extract_skills_async(document.id)

            return render_template("extractor/upload.html", filename=filename, form=form)

    return render_template("extractor/upload.html", form=form)


@extractor_blueprint.route("/mydocuments", methods=["GET"])
@login_required
def mydocuments():
    """List my documents uploaded"""

    form = SearchForm(request.form)

    q = request.args.get("q")
    documents = None
    total_documents = 0

    if q is not None and len(q.strip()) > 0:
        form.q.data = q
        ids = search_index_content(q)
        ids = list(map(int, ids))

        app.logger.debug("q: {}. ids: {}".format(q, ids))

        documents = Document.query.filter(
            Document.id.in_(ids)).order_by(Document.created_on.desc()).all()
        total_documents = Document.query.filter_by(
            created_by=current_user.id).count()
    else:
        documents = Document.query.filter_by(
            created_by=current_user.id).order_by(Document.created_on.desc()).all()
        total_documents = len(documents)

    app.logger.debug("Found {} my documents".format(len(documents)))

    try:
        ids = [doc.id for doc in documents]
        skills_dict = search_index_skills(ids)
        for document in documents:
            document.path = None  # hide
            try:
                document.skills = skills_dict[document.id]
                if len(document.skills) == 0:
                    document.skills = "Not found"
            except KeyError:
                document.skills = "Document's not indexed yet"
    except ElasticsearchNotFoundError as ex:
        app.logger.info("{}. Elasticsearch is not start or index has not created yet".format(ex))

    return render_template("extractor/mydocuments.html", documents=documents,
                           form=form, total_documents=total_documents)


@extractor_blueprint.route("/mydocuments/<id>", methods=["GET"])
@login_required
def download_my_document(id):
    """Document download"""

    document = Document.query.filter_by(id=id).first()
    if document is not None and document.created_by == current_user.id:
        path = document.path
        if not os.path.isabs(path):
            path = os.path.join(app.instance_path, path)
        print('Path {}: {}'.format(document.title, path))
        if os.path.isfile(path):
            try:
                return send_file(path, as_attachment=True)
            except FileNotFoundError:
                return render_template("errors/404.html")
    return render_template("errors/404.html")


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_UPLOAD_EXTENSIONS
