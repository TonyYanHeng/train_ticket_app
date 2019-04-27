#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import urllib.request
import re
import base64
import time
import os
import shutil
from PIL import Image
import requests
import json
import jieba
from xml.etree import ElementTree

get_img64_url = "https://kyfw.12306.cn/passport/captcha/captcha-image64?login_site=E&module=login&rand=sjrand"
login_url = "https://kyfw.12306.cn/passport/web/login"
home_url = "https://kyfw.12306.cn/otn/login/userLogin"
sub_img_location = {
    '0_0.png': '35,35',
    '0_1.png': '105,35',
    '0_2.png': '175,35',
    '0_3.png': '245,35',
    '1_0.png': '35,105',
    '1_1.png': '105,105',
    '1_2.png': '175,105',
    '1_3.png': '245,105',
}


def delete_old_images(images_path):
    if os.path.exists(images_path):
        shutil.rmtree(images_path)
    time.sleep(1)
    os.mkdir(images_path)


def get_baidu_ocr_result(img_path):
    """
    利用百度OCR识别图像中的文字
    :param img_path:
    :return:
    """
    access_token = "24.8b8c1b26658a9639e649b039e1897180.2592000.1557905618.282335-16020567"
    url = "https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic?access_token=" + access_token
    params = {}
    with open(img_path, 'rb') as f:
        params = {"image": base64.b64encode(f.read())}
        params = urllib.parse.urlencode(params).encode('utf8')
    request = urllib.request.Request(url, params)
    request.add_header('Content-Type', 'application/x-www-form-urlencoded')
    response = urllib.request.urlopen(request)
    content = response.read()
    target_words = []
    if content:
        str_content = str(content, encoding='utf8')
        pattern = re.compile(r"请点击下图中所有的(.*?)\"")
        target_words = pattern.findall(str_content)
    return target_words


def get_baidu_shitu_result(img_path):
    """
    利用百度图像识别来识别图像内容
    :param img_path:
    :return:
    """
    ret = []
    access_token = "24.f13eb376facef034a3448b464d33fdcd.2592000.1557926182.282335-16025381"
    url = "https://aip.baidubce.com/rest/2.0/image-classify/v2/advanced_general?access_token=" + access_token
    params = {}
    with open(img_path, 'rb') as f:
        params = {"image": base64.b64encode(f.read())}
        params = urllib.parse.urlencode(params).encode('utf8')
    request = urllib.request.Request(url, params)
    request.add_header('Content-Type', 'application/x-www-form-urlencoded')
    response = urllib.request.urlopen(request)
    content = response.read()
    if content:
        str_content = str(content, encoding='utf8')
        pattern = re.compile(r"keyword\": \"(.*?)\"}")
        ret = pattern.findall(str_content)
    return ret


class LoginIns(object):
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/70.0.3538.67 Safari/537.36"
        }

    def get_image(self, img_path):
        """
        下载图形验证码
        :param img_path:
        :return:
        """
        print("get_image start running!")
        url = "https://kyfw.12306.cn/passport/captcha/captcha-image?login_site=E&module=login&rand=sjrand"
        response = self.session.get(url=url, headers=self.headers, verify=False)
        with open(img_path, 'wb') as f:
            f.write(response.content)
        print("get_image end!")

    def verify_image(self, locations):
        """
        验证图形验证码
        :param locations:
        :return:
        """
        location_info = ','.join(locations)
        url = "https://kyfw.12306.cn/passport/captcha/captcha-check"
        data = {
            "answer": location_info,
            "rand": "sjrand",
            "login_site": "E"
        }
        response = self.session.post(url, data=data, headers=self.headers, verify=False)
        content = json.loads(response.content)
        code = content["result_code"]
        if code == '4':
            return True
        else:
            return False

    def get_sub_img(self, img, x, y):
        assert 0 <= x <= 3
        assert 0 <= y <= 2
        # WITH = HEIGHT = 68
        left = 5 + (67 + 5) * x
        top = 41 + (67 + 5) * y
        right = left + 67
        bottom = top + 67
        return img.crop((left, top, right, bottom))

    def generate_8_sub_images(self, source_img_path):
        src_img = Image.open(source_img_path)
        cur_dir = os.path.dirname(source_img_path)
        sub_images_path = []
        for y in range(2):
            for x in range(4):
                sub_img = self.get_sub_img(src_img, x, y)
                sub_img_name = "%s_%s.png" % (y, x)
                sub_img_path = os.path.join(cur_dir, sub_img_name)
                sub_img.save(sub_img_path)
                sub_images_path.append(sub_img_path)
        return sub_images_path

    def find_locations(self, img_path):
        locations = []
        # step1: 清空images目录下的所有文件
        delete_old_images(os.path.dirname(img_path))
        # step2: 下载验证码图片
        self.get_image(img_path)
        # step3：利用百度OCR识别验证码图片中的汉字
        target_words = get_baidu_ocr_result(img_path)
        if len(target_words) == 0 or target_words == [""]:
            print("百度OCR未能识别出当前图像中的文字！")
            locations = self.find_locations(img_path)
        else:
            print("当前图像中的目标文字为：%s" % target_words)
        # step4: 切割验证码图片为8个小图片
        sub_img_paths = self.generate_8_sub_images(img_path)
        # step5：利用百度识图逐个识别子图并得到满足条件的子图位置
        for cur_sub_image_path in sub_img_paths:
            cur_shitu_result = get_baidu_shitu_result(cur_sub_image_path)
            cur_sub_image = os.path.basename(cur_sub_image_path)
            print("子图%s的百度识图结果为：%s." % (cur_sub_image, cur_shitu_result))
            if len(cur_shitu_result) == 0:
                continue
            for target_word in target_words:
                for cur_result in cur_shitu_result:
                    if target_word in cur_result or cur_result in target_word:
                        locations.append(sub_img_location[cur_sub_image])
        if len(locations) == 0:
            print("百度图像识别没有找到目标子图！")
            locations = self.find_locations(img_path)
        else:
            locations = list(set(locations))
            print("百度图像识别找到的目标子图位置为：%s。" % locations)
        return locations

    def close_session(self):
        self.session.close()

    def login_home(self, locations):
        location_info = ','.join(locations)
        username = "719492067@qq.com"
        password = "Hyh20180225"
        data = {
            "username": username,
            "password": password,
            "appid": "otn",
            "answer": location_info,
        }
        login_headers = self.headers
        login_headers["Host"] = "kyfw.12306.cn"
        login_headers["Accept"] = "application/json, text/javascript, */*; q=0.01"
        login_headers["Accept-Language"] = "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2"
        login_headers["Accept-Encoding"] = "gzip, deflate, br"
        login_headers["Referer"] = "https://kyfw.12306.cn/otn/resources/login.html"
        login_headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        # login_headers["Content-Length"] = "85"
        login_headers["Connection"] = "keep-alive"
        # data = json.dumps(data)
        response = self.session.post(login_url, data=data, headers=login_headers, verify=False)
        response.encoding = 'utf-8'
        # node = ElementTree.XML(response.text)
        content = str(response.content)
        if content.startswith(u'\ufeff'):
            content = content[3:]
        content = json.loads(content)
        code = content["result_code"]
        if code == '0':
            print("登录成功！")
            return True
        else:
            return False

    def redirect_to_home(self):
        res = self.session.get(home_url, headers=self.headers, verify=False)
        content = res.content
        print("这是首页！")


if __name__ == '__main__':
    cur_file_path = os.path.realpath(__file__)
    cur_dir_path = os.path.dirname(cur_file_path)
    images_dir_path = os.path.join(cur_dir_path, 'images')
    original_img_path = os.path.join(images_dir_path, 'original.jpg')
    try:
        loginIns = LoginIns()
        imgCheckFlag = False
        loginFlag = False
        while not loginFlag:
            sub_img_locations = loginIns.find_locations(original_img_path)
            imgCheckFlag = loginIns.verify_image(sub_img_locations)
            if not imgCheckFlag:
                print("图形验证码验证失败！")
                continue
            else:
                print("图形验证码验证成功！")
                loginFlag = loginIns.login_home(sub_img_locations)
        print("登录成功！")
    except Exception as e:
        print("Exception happened, the detail is: %s!" % e)
    finally:
        loginIns.close_session()
        print("2222")
