import os
import json
import string, random, requests
from flask import Flask, request, redirect, url_for, jsonify, send_file, Response, render_template
from werkzeug.utils import secure_filename
from azure.storage.blob import BlobServiceClient, BlobClient
import time
import pandas as pd
import json
from databricks_api import DatabricksAPI

app = Flask(__name__, instance_relative_config=True)
# app.secret_key = "secret key" # for encrypting the session
# #It will allow below 16MB contents only, you can change it
# # app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
path = os.getcwd()
# # file Upload
UPLOAD_FOLDER = os.path.join(path, 'uploads')
# # Make directory if "uploads" folder not exists
if not os.path.isdir(UPLOAD_FOLDER):
    os.mkdir(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = set(['parquet', 'json','csv'])


# Define your Azure storage account and container information
account_name = "blob1089"
account_key = "B7qHyq0CmVsBAtT4NHi6kShsKGKvv8oBfkAt82w4RmuVq0giSd8rVc4YzOeBpRcduHn8nOLE3XJO+AStUyViBw=="
container_name =  'filestore'
# personal_access_token = 'dapi506245e280d4bb9c0d71c59687a78932'
account_url = f"https://{account_name}.blob.core.windows.net"

personal_access_token = "dapi0629c0ac25c7037e1a7d470b7973550a"

# Initialize a BlobServiceClient object to interact with the Azure Blob Storage service
blob_service_client = BlobServiceClient.from_connection_string(f"DefaultEndpointsProtocol=https;AccountName={account_name};AccountKey={account_key}")
blob_uri = f"https://{account_name}.blob.core.windows.net"

container_client = blob_service_client.get_container_client(container='filestore')
blob_list = container_client.list_blobs()

# for blob in blob_list:
#     if 'output/' in blob.name:
#         print(blob)
#         blob_name = blob.name.split('/')[1]
#         blob_client = blob_service_client.get_blob_client(container='validated', blob=blob)
#         with open(file= blob_name , mode="wb") as sample_blob:
#             download_stream = blob_client.download_blob()
#             sample_blob.write(download_stream.readall())


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Define a route to display the file data on a webpage
# @app.route('/files', methods=['GET','POST'])
# def display_files():
#     if request.method == 'POST':
#         value = request.form.get("query").split('/')
#         read_csv = pd.read_csv(f'downloads/{value[0]}.csv', delimiter=',')  # or delimiter = ';'
#         table = read_csv.to_html(classes='table table-striped')
#         return render_template('display.html', table=table, title=value[1])
#     return render_template('query.html')
    # with open(file=os.path.join('downloads/', 'CountsOfCounty'), encoding='utf-8') as file:
    #     data = pd.read_csv(file)
    #     table = data.to_html(classes='table table-striped')
    # return render_template('display.html', table=table)

@app.route('/files', methods=['GET','POST'])
def display_files():
    if request.method == 'POST':
        question = request.form.get("query")
        k, title = question.split('/')
        # read_csv = pd.read_csv(f'downloads/{value[0]}.json', delimiter=',')  # or delimiter = ';'
        # table = read_csv.to_html(classes='table table-striped')
        # return render_template('display.html', table=table, title=value[1])
        value = ""
        with open("/home/viral/Data engineering Learnings/ADF And databricks project/downloads/results.json") as f:
            data = json.load(f)
            value = data[k]
        
        return render_template('queryjson.html', question=question, value=value, title=title, k=k)

    return render_template('queryjson.html')

# Define a route to download a file
@app.route('/downloads',methods=['GET','POST'])
def download_file():
    for blob in blob_list:
        if 'output/' in blob.name:
            print(blob)
            blob_name = blob.name.split('/')[1]
            blob_client = blob_service_client.get_blob_client(container='filestore', blob=blob)
            try:
                os.mkdir("downloads")
            except:
                pass
            with open(file= os.path.join('downloads',blob_name) , mode="wb") as sample_blob:
                download_stream = blob_client.download_blob()
                sample_blob.write(download_stream.readall())
    return redirect(url_for('download_file'))


@app.route('/date-filter', methods=['GET','POST'])
def datefilter():
    CountyName = request.form.get('county-name')
    StationName = request.form.get('station-name')
    criteria = request.form.get('criteria')
    filter = request.form.get('filter')
    startDate = request.form.get('start-date')
    endDate = request.form.get('end-date')
    
    
    # typeOfQuery = request.form.get('typeOfQuery')
    print(CountyName, StationName, startDate, endDate, filter, criteria)
    job_id = 849796415978378
    # Set up the API endpoint and headers
    api_endpoint = f'https://adb-1655970843981316.16.azuredatabricks.net/api/2.0/jobs/run-now'
    headers = {'Authorization': f'Bearer {personal_access_token}', 'Content-Type': 'application/json'}

    # Define the API parameters
    params = {
        "county" : CountyName,
        "station" : StationName,
        "criteria" : criteria,
        "filter": filter,
        "startDate": startDate,
        "endDate": endDate
    }
    data = {
        'job_id': job_id,
        "python_params": json.dumps(params),
    }
    # Make the POST request to start the job
    response = requests.post(api_endpoint, headers=headers, data=json.dumps(data))
    run_id = response.json()["run_id"]
    # Set up the API endpoint and headers
    api_endpoint = 'https://adb-1655970843981316.16.azuredatabricks.net/api/2.0/jobs/runs/get'
    headers = {'Authorization': f'Bearer {personal_access_token}', 'Content-Type': 'application/json'}

    # Make the GET request to retrieve the job run details
    status = None
    while True:
        response = requests.get(api_endpoint, headers=headers, params={'run_id': run_id})
        status = response.json()['state']['life_cycle_state']
        print(status)
        if status in ['TERMINATED', 'SKIPPED', 'INTERNAL_ERROR']:
            break
        time.sleep(4)

    # Define the Azure Databricks API endpoint and authentication token
    # run_id = 103292
    api_endpoint = f'https://adb-1655970843981316.16.azuredatabricks.net/2.1/jobs/runs/get-output?run_id={run_id}'
    api_token = personal_access_token
    # Create an instance of the Azure Databricks API client
    db = DatabricksAPI(host=api_endpoint, token=api_token)
    output = db.jobs.get_run_output(run_id)
    print(output['logs'])
    output = json.loads(output['logs'])
    dict_list = [json.loads(d) for d in output]
    return render_template('queryjson.html', table=dict_list[0], title=f"{filter} {criteria} of {CountyName} - {StationName} between {startDate} and {endDate}")


@app.route('/', methods=['GET', 'POST'])
def uploadToStorage():
     
    if request.method == 'POST':
        files = request.files.getlist("file")
        out = []
        # Iterate for each file in the files List, and Save them
        for file in files:
            # file.save(file.filename)    
            # out.append(file.filename)
            # filename = secure_filename(file.filename)
            # fileextension = filename.rsplit('.',1)[1]
            # randomfilename = id_generator()
            # filename = randomfilename + '.' + fileextension

            blob_client = blob_service_client.get_blob_client(container=container_name, blob=file.filename)
            blob_client.upload_blob(file.read(), overwrite=True)
            print('uploaded')
    
        return redirect(url_for('display_files'))

    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form action="" method="POST" enctype="multipart/form-data">
    <p><input type="file" name="file">
    <input type="submit" value="Upload">
    </form>
    '''

# @app.route('/fetch')
# def fetch_files():
#     # blob_name = "output.json"
#
#     # block_blob_service = BlockBlobService(account_name=account_name, account_key=account_key)
#     # json_str = '\n'.join(json_data)
#     # block_blob_service.create_blob_from_text(container_name, blob_name, json_str)
#
#     STORAGEACCOUNTURL = f"https://{account_name}.blob.core.windows.net"
#     STORAGEACCOUNTKEY = account_key
#     CONTAINERNAME = 'validated/output'
#     BLOBNAME = 'average.json'
#
#     blob_service_client_instance = BlobServiceClient(
#         account_url=STORAGEACCOUNTURL, credential=STORAGEACCOUNTKEY)
#
#     blob_client_instance = blob_service_client_instance.get_blob_client(
#         CONTAINERNAME, BLOBNAME, snapshot=None)
#
#     blob_data = blob_client_instance.download_blob()
#     data = blob_data.readall()
#     # data = json.loads(data)
#     print(data)
#     return jsonify(data)

def id_generator(size=32, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

if __name__ == '__main__':
    app.run(debug=True)