"""
This file fetches and unpacks all the files on the cdn and pushes to the git.
Should be run on a cron job.
"""
import requests
import zipfile
from io import BytesIO
import json
import cdn_pb2 as CDN
from datetime import datetime, timedelta
import os
import time
from google.protobuf.json_format import MessageToJson



def file_content_from_zip_url(url, filename):
    r = requests.get(url,timeout=5)
    with zipfile.ZipFile(BytesIO(r.content)) as zippy:
        with zippy.open(filename, "r") as fp:
            return fp.read()


def avalible_data():
    content = file_content_from_zip_url(
        "https://productie.coronamelder-dist.nl/v1/manifest", "content.bin"
    )

    for key,data in json.loads(content).items():
        if isinstance(data,list):
            for item in data:
                yield (key,item)
        else:
            yield (key,data)


lookup = {
    "exposureKeySets":"exposurekeyset"
}

def get_data():
    for folder,item in avalible_data():
        if folder in lookup:
            folder = lookup[folder]
        path = os.path.join(folder,item)
        if not os.path.isdir(path):
            if not os.path.isdir(folder):
                os.mkdir(folder)
            os.mkdir(path)
            url = f"https://productie.coronamelder-dist.nl/v1/{folder}/{item}"
            meta = {
                'url':url,
                'unix timestamp fetched':int(time.time()),
            }
            with open(os.path.join(path,"META.json"),"w") as fp:
                json.dump(meta,fp)

            r = requests.get(url)
            print(url)
            with open(os.path.join(path,"data.zip"),"wb") as fp:
                fp.write(r.content)

            os.mkdir(os.path.join(path,"data"))
            with zipfile.ZipFile(os.path.join(path,"data.zip"), 'r') as zip_ref:
                zip_ref.extractall(os.path.join(path,"data"))
            if os.path.isfile(os.path.join(path,"data","export.bin")):
                handle_keyset(os.path.join(path,"data"))


def handle_keyset(path):
    with open(os.path.join(path,"export.bin"),"rb") as fp:
        fp.read(16)
        content = fp.read()
    export = CDN.TemporaryExposureKeyExport()
    export.ParseFromString(content)
    with open(os.path.join(path,"export.json"),"w") as fp:
        fp.write(MessageToJson(export))

if __name__ == "__main__":
    get_data()
    os.system("git add -A")
    os.system(f"git commit -m \"Update {int(time.time())}\"")
    os.system("git push")
