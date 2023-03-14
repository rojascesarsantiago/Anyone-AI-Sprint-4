import os

import settings
import utils
from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from werkzeug.utils import secure_filename
from middleware import model_predict

router = Blueprint("app_router", __name__, template_folder="templates")

@router.route("/new_prediction", methods=["GET"])
def new_upload():
  context = {
              'models' : settings.MULTI_MODEL
            }
  return render_template("index.html", context=context, scroll="upload_image")

@router.route("/", methods=["GET", "POST"])
def index():
  """
  GET: Index endpoint, renders our HTML code.

  POST: Used in our frontend so we can upload and show an image.
  When it receives an image from the UI, it also calls our ML model to
  get and display the predictions.
  """
  if request.method == "GET":
    context = {
                'models' : settings.MULTI_MODEL
              }
    return render_template("index.html", context=context)

  if request.method == "POST":
    # No file received, show basic UI
    if "file" not in request.files:
      flash("** No file part")
      return redirect(request.url)

    # File received but no filename is provided, show basic UI
    file = request.files["file"]
    if file.filename == "":
      flash("** No image selected for uploading")
      return redirect(request.url, scroll="upload_image")

    # File received and it's an image, we must show it and get predictions
    if file and utils.allowed_file(file.filename):
      # Store image to disk with a unique file name.
      hashed_name = utils.get_file_hash(file)
      file_path = os.path.join(settings.UPLOAD_FOLDER, hashed_name)
      file.save(file_path)
      if 'rbtn_model_selection' in request.form:
        Multimodel = request.form['rbtn_model_selection']
      else:
        flash("** Please select a model")
        return redirect(request.url+"#upload_image")

      # Send the file to be processed by the `model` service
      prediction, score = model_predict(hashed_name, Multimodel)
      
      # Update `render_template()` parameters
      context = {
                  "prediction": prediction,
                  "score": score,
                  "filename": hashed_name,
                  "model": Multimodel,
                }
      return render_template("index.html", filename=hashed_name, context=context, scroll="show_results")
    # File received and but it is not an image
    else:
      flash("** Please select a valid image.")
      flash("   Allowed image types are -> png, jpg, jpeg, gif")
      return redirect(request.url + "#upload_image")


@router.route("/display/<filename>")
def display_image(filename):
  """
  Display uploaded image in our UI.
  """
  return redirect(url_for("static", filename="uploads/" + filename), code=301)

@router.route("/display_preprocessed/<filename>")
def display_preprocessed_image(filename):
  """
  Display preprocessed uploaded image in our UI.
  """
  return redirect(url_for("static", filename="uploads/preprocessed/" + filename), code=301)


@router.route("/predict", methods=["POST"])
def predict():
  """
  Endpoint used to get predictions without need to access the UI.

  Parameters
  ----------
  file : str
      Input image we want to get predictions from.

  Returns
  -------
  flask.Response
      JSON response from our API having the following format:
          {
              "success": bool,
              "prediction": str,
              "score": float,
          }

      - "success" will be True if the input file is valid and we get a
        prediction from our ML model.
      - "prediction" model predicted class as string.
      - "score" model confidence score for the predicted class as float.
  """
  
  rpse = {"success": False, "prediction": None, "score": None}

  if request.method == "POST":
    # Check if POST request has the file part
    if "file" not in request.files:
      flash("No file part")
      return rpse, 400

    file = request.files.get("file")
    # Check if file was submitted by the user
    if file.filename == '':
      flash("No file received!")
      return rpse, 400
    
    # Check if file is a valid one
    if file and utils.allowed_file(file.filename):

      # Store image to disk with a unique file name.
      hashed_name = utils.get_file_hash(file)
      file_path = os.path.join(settings.UPLOAD_FOLDER, hashed_name)
      file.save(file_path)
      flash('File saved', 'message')

      # Send the file to be processed by the `model` service
      prediction, score = model_predict(hashed_name)

      # In case there were an exeption in the ml service, report an error code
      if score ==0:
        return rpse, 400

      # Update `response`
      rpse["success"] = True
      rpse["prediction"] = prediction
      rpse["score"] = score
      return rpse
    else:
      return rpse, 415
  else:
    return rpse, 405


@router.route("/feedback", methods=["GET", "POST"])
def feedback():
  """
  Store feedback from users about wrong predictions on a plain text file.

  Parameters
  ----------
  report : request.form
      Feedback given by the user with the following JSON format:
          {
              "filename": str,
              "prediction": str,
              "score": float
          }

      - "filename" corresponds to the image used stored in the uploads
        folder.
      - "prediction" is the model predicted class as string reported as
        incorrect.
      - "score" model confidence score for the predicted class as float.
  """
  report = request.form.get("report")

  # Store the reported data to settings.FEEDBACK_FILEPATH
  if request.method =='POST':
    report = request.form.get("report")
    with open(settings.FEEDBACK_FILEPATH, 'a') as file:
      if os.path.getsize(settings.FEEDBACK_FILEPATH):
        file.write(f'\n{report}')
      else:
        file.write(f'{report}')
  
  context = {
              'models' : settings.MULTI_MODEL
            } 
  return render_template("index.html", context=context, scroll="upload_image")
