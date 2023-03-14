# Utilities
from PIL import Image
import numpy as np
import settings
import redis
import json
import time
import os

#Models
from tensorflow.keras.applications import resnet50, densenet, efficientnet
from tensorflow.keras.preprocessing import image

# Connect to Redis and assign to variable `db``
# Make use of settings.py module to get Redis settings like host, port, etc.
db = redis.Redis(
      host=settings.REDIS_IP, 
      port=settings.REDIS_PORT, 
      db=settings.REDIS_DB_ID
    )

# Load your ML model and assign to variable `model`
# See https://drive.google.com/file/d/1ADuBSE4z2ZVIdn66YDSwxKv-58U7WEOn/view?usp=sharing
# for more information about how to use this model.
model= {'ResNet50': resnet50,
        'EfficientNetB0': efficientnet, 
        'DenseNet121': densenet}


# To prevent long downloading time, the weights for each model are downloaded in weights folder.
# In case the weights are not present, download them as the model runs.

# Create a weights folder
# Download https://drive.google.com/file/d/1JPzUUBuqtN0CEzWRC7A2jFfA73OWQMT5/view?usp=sharing unzip it in the just created folder

try:
  ResNet50 = resnet50.ResNet50(include_top=True,
                               weights="/src/weights/resnet50_weights_tf_dim_ordering_tf_kernels.h5")
except:
  ResNet50 = resnet50.ResNet50(include_top=True,weights="imagenet")

try:
  EfficientNetB0 = efficientnet.EfficientNetB0(include_top=True,
                               weights="/src/weights/efficientnet_weights_tf_dim_ordering_tf_kernels.h5")
except:
  EfficientNetB0 = efficientnet.EfficientNetB0(include_top=True,weights="imagenet")

try:
  DenseNet121 = densenet.DenseNet121(include_top=True,
                              weights='/src/weights/densenet_weights_tf_dim_ordering_tf_kernels.h5')
except:
  DenseNet121 = densenet.DenseNet121(include_top=True,weights="imagenet")




def predict(image_name, Multimodel='ResNet50'):
    """
    Load image from the corresponding folder based on the image name
    received, then, run our ML model to get predictions.

    Parameters
    ----------
    image_name : str
        Image filename.
    Multimodel : str
        Keras model name to use for prediction

    Returns
    -------
    class_name, pred_probability : tuple(str, float)
        Model predicted class as a string and the corresponding confidence
        score as a number.
    """
    # Load and correct dimmension
    input_shape = 224 
    file_path = os.path.join(settings.UPLOAD_FOLDER,image_name)
    img = image.load_img(file_path, target_size=(input_shape,input_shape))
    x = image.img_to_array(img)
    x_batch = np.expand_dims(x, axis=0)

    # Preprocess input make prediction and keep the one with highest probability
    model = globals()[Multimodel]
    model_class= model[Multimodel]
    x_batch = model_class.preprocess_input(x_batch)

    # Save preprocessed image
    preprocessed_batch = (x_batch[0] + 128).astype(np.uint8)
    preprocessed_image = Image.fromarray(preprocessed_batch)
    preprocessed_image.save(os.path.join(settings.PREPROCESS_FOLDER,image_name))
    
    predictions = model.predict(x_batch)
    best_pred = model_class.decode_predictions(predictions, top=1)
    class_name = best_pred[0][0][1]
    pred_probability = best_pred[0][0][2]

    return class_name, round(float(pred_probability),3)


def classify_process():
    """
    Loop indefinitely asking Redis for new jobs.
    When a new job arrives, takes it from the Redis queue, uses the loaded ML
    model to get predictions and stores the results back in Redis using
    the original job ID so other services can see it was processed and access
    the results.

    Load image from the corresponding folder based on the image name
    received, then, run our ML model to get predictions.
    """
    while True:
      # Inside this loop you should add the code to:
      #   1. Take a new job from Redis
      #   2. Run your ML model on the given data
      #   3. Store model prediction in a dict with the following shape:
      #      {
      #         "prediction": str,
      #         "score": float,
      #      }
      #   4. Store the results on Redis using the original job ID as the key
      #      so the API can match the results it gets to the original job
      #      sent
      # Hint: You should be able to successfully implement the communication
      #       code with Redis making use of functions `brpop()` and `set()`.

      # Take a new job from Redis
      _ , job_data_str = db.brpop(settings.REDIS_QUEUE)
      
      job_data = json.loads(job_data_str.decode('utf-8'))

      # ML model
      try:
        class_name, pred_probability = predict(job_data['image_name'], job_data['Multimodel'])
      except:
        class_name, pred_probability = '', 0
      pred_dict = {
                    "prediction": class_name,
                    "score": pred_probability
                  }
      # Store the results
      db.set(job_data["id"], json.dumps(pred_dict))

      # Don't forget to sleep for a bit at the end
      time.sleep(settings.SERVER_SLEEP)


if __name__ == "__main__":
    # Now launch process
    print("Start Machine Learning Model")
    classify_process()
