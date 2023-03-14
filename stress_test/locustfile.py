from locust import HttpUser, task, between


class APIUser(HttpUser):
    wait_time = between(1, 5)
    
    # Load test predict/ endpoint
    @task(10)
    def predict_post(self):
      with open("../tests/dog.jpeg", "rb") as file:
        self.client.post("/predict",files={'file': file})

    # Load test feedback/ endpoint
    @task(1)
    def feedback_post(self):
      data = {
          "report": "{'filename': 'test', 'prediction': 'angora_cat', 'score': 0.95 }"
      }
      self.client.post("/feedback", data=data)


    def on_start(self):
       self.client.get("/")
