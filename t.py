import requests
import time
url = 'https://agents.vccfinal.net/' 

start_t = time.time()
response = requests.get(url)

if response.status_code == 200:
    print(response.json())
else:
    print("An error has occurred.")

elapse_t = time.time() - start_t
print("Time elapsed: ", elapse_t)