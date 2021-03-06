# -*- coding: utf-8 -*-
import os
import logging
import datetime
import base64
from qcloud_cos_v5 import CosConfig
from qcloud_cos_v5 import CosS3Client
from qcloud_cos_v5 import CosServiceError
from qcloud_cos_v5 import CosClientError
from qcloud_image import Client
from qcloud_image import CIUrl, CIFile, CIBuffer, CIUrls, CIFiles, CIBuffers
import sys

print('Loading function')

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger()
logger.setLevel(level=logging.INFO)

appid = os.environ.get('appid')  # 请在函数配置中添加环境变量appid，并填入您的 APPID
secret_id = os.environ.get('secret_id')  # 请在函数配置中添加环境变量secret_id，并填入您的 SecretId
secret_key = os.environ.get('secret_key')  # 请在函数配置中添加环境变量secret_key，并填入您的 SecretKey
bucket_region = os.environ.get('bucket_region') # 请在函数配置中添加环境变量bucket_region，并填入您COS Bucket所在的地域
token = ''
bucket_upload = os.environ.get('bucket_upload')  # 请在函数配置中添加环境变量bucket_upload，并填入您要用来存放图片的Bucket名

config = CosConfig(Secret_id=secret_id, Secret_key=secret_key, Region=bucket_region, Token=token)
client_cos = CosS3Client(config)


def delete_local_file(src):
    logger.info("delete files and folders")
    if os.path.isfile(src):
        try:
            os.remove(src)
        except:
            pass
    elif os.path.isdir(src):
        for item in os.listdir(src):
            itemsrc = os.path.join(src, item)
            delete_file_folder(itemsrc)
        try:
            os.rmdir(src)
        except:
            pass


def main_handler(event, context):
    logger.info("start main handler")
    if "requestContext" not in event.keys():
        return {"code": 410, "errorMsg": "event is not come from api gateway"}
    if event["body"] == "":
        return {"code": 412, "errorMsg": "there is no file from api gateway"}

    # save api gateway file to local temp file
    logger.info("Start to download images from APIGW")
    time = datetime.datetime.now()
    file_name = '{}'.format(time) + "-test.jpg"
    logger.info("file_name is : %s" % file_name)
    local_path = u'/tmp/{}'.format(file_name)
    logger.info("local_path is : %s" % local_path)
    with open(local_path, 'w') as wfile:
        wfile.write(base64.b64decode(event['body']))

    # start to upload to cos
    logger.info("Start to upload images to cos")
    res_cos = client_cos.put_object_from_local_file(
        Bucket=bucket_upload,
        LocalFilePath=local_path,
        Key='{}'.format(file_name))
    logger.info("upload to cos result is : %s" % res_cos)

    # start to detection
    logger.info("Start to detection")
    client_ai = Client(appid, secret_id, secret_key,bucket_upload)
    client_ai.use_http()
    client_ai.set_timeout(30)
    res_ai = client_ai.word_detect(CIFile(local_path))
    res_text = "  "
    print len(res_ai["data"]["items"])
    for i in range(len(res_ai["data"]["items"])):
        res_text = res_text + str(res_ai["data"]["items"][i]["itemstring"].encode('utf-8'))

    delete_local_file(local_path)
    response = {
        "isBase64Encoded": False,
        "statusCode": 200,
        "headers": {"Content-Type": "text", "Access-Control-Allow-Origin": "*"},
        "body": res_text
    }

    return response