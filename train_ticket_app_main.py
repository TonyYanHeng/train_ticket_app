#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import urllib.request
import re
import base64
import time
import os
import shutil
from PIL import Image
from selenium.webdriver.firefox import options
from selenium.webdriver.common.action_chains import ActionChains
from selenium import webdriver
import jieba

train_ticket_url = "https://www.12306.cn/index/"
get_img64_url = "https://kyfw.12306.cn/passport/captcha/captcha-image64?login_site=E&module=login&rand=sjrand"
login_url = "https://kyfw.12306.cn/passport/web/login"
home_url = "https://kyfw.12306.cn/otn/login/userLogin"
username = "719492067@qq.com"
password = "XXXXX"  # 你自己的登录密码
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
    """清空images目录下的内容"""
    if os.path.exists(images_path):
        shutil.rmtree(images_path)
    time.sleep(1)
    os.mkdir(images_path)


def generate_one_sub_img(source_img_path, x, y):
    """生成一张子图"""
    src_img = Image.open(source_img_path)
    left = 5 + (67 + 5) * x
    top = 41 + (67 + 5) * y
    right = left + 67
    bottom = top + 67
    sub_img_name = "%s_%s.png" % (y, x)
    sub_img_path = os.path.join(os.path.dirname(source_img_path), sub_img_name)
    sub_img = src_img.crop((left, top, right, bottom))
    sub_img.save(sub_img_path)
    return sub_img_path


def generate_8_sub_images(source_img_path):
    """生成8个子图"""
    result = []
    for y in range(2):
        for x in range(4):
            sub_img_path = generate_one_sub_img(source_img_path, x, y)
            result.append(sub_img_path)
    return result


def get_baidu_ocr_result(img_path):
    """
    利用百度OCR识别图像中的文字
    :param img_path:
    :return:
    """
    access_token = "24.8b8c1b26658a9639e649b039e1897180.2592000.1557905618.282335-16020567"
    url = "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic?access_token=" + access_token
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


class LoginBySelenium(object):
    def __init__(self):
        self.browser = webdriver.Firefox()

    def prepare_for_download_img64(self):
        self.browser.get(train_ticket_url)
        time.sleep(1)
        login_a = self.browser.find_element_by_xpath('/html/body/div[2]/div/div[1]/div/div/ul/li[3]/a[1]')
        login_a.click()
        time.sleep(1)
        account_login_a = self.browser.find_element_by_xpath('/html/body/div[2]/div[2]/ul/li[2]/a')
        account_login_a.click()
        time.sleep(1)
        self.input_username_and_password()

    def input_username_and_password(self):
        username_input = self.browser.find_element_by_xpath('//*[@id="J-userName"]')
        username_input.clear()
        username_input.send_keys(username)
        password_input = self.browser.find_element_by_xpath('//*[@id="J-password"]')
        password_input.clear()
        password_input.send_keys(password)
        time.sleep(1)

    def download_img64(self, img64_path):
        print("开始下载验证码图片！")
        delete_old_images(os.path.dirname(img64_path))
        img64_element = self.browser.find_element_by_xpath('//*[@id="J-loginImg"]')
        img64_url = img64_element.get_attribute("src")
        urllib.request.urlretrieve(img64_url, img64_path)
        print("验证码图片下载完成！")

    def find_sub_img_location(self, img64_path):
        results = []
        self.refresh_img64()
        self.download_img64(img64_path)
        target_words = get_baidu_ocr_result(img64_path)
        if len(target_words) == 0 or target_words == [""]:
            print("未能识别出当前验证码图片中的文字！")
            results = self.find_sub_img_location(img64_path)
        else:
            print("当前验证码图片中的目标文字为：%s" % target_words)
            sub_img_paths = generate_8_sub_images(img64_path)
            for cur_target_word in target_words:
                fenci_results = jieba.cut(cur_target_word)
                for cur_fenci_result in fenci_results:
                    print("当前目标文字'%s'的jieba分词结果为：%s" % (cur_target_word, cur_fenci_result))
                    for cur_sub_image_path in sub_img_paths:
                        cur_shitu_results = get_baidu_shitu_result(cur_sub_image_path)
                        cur_sub_image_name = os.path.basename(cur_sub_image_path)
                        print("子图%s的识图结果为：%s。" % (cur_sub_image_name, cur_shitu_results))
                        if len(cur_shitu_results) == 0:
                            continue
                        for cur_shitu_result in cur_shitu_results:
                            if cur_fenci_result in cur_shitu_result or cur_shitu_result in cur_fenci_result:
                                results.append(sub_img_location[cur_sub_image_name])
            if len(results) == 0:
                print("没找到对应的目标子图！")
                results = self.find_sub_img_location(img64_path)
            else:
                results = list(set(results))
                print("找到的目标子图位置为：%s。" % results)
        return results

    def add_randcode_in_html(self, locations):
        """选择验证码"""
        html = ""
        for cur_location in locations:
            detail_location = cur_location.split(",")
            top = str(int(detail_location[1]) + 16)
            left = str(int(detail_location[0]) - 13)
            style_value = "top: " + top + "px; left: " + left + "px;"
            html += "<div randCode=\"+\"" + cur_location + "\"+\" class=\"+\"lgcode-active\"+\" style='%s'></div>" % style_value
        js = "document.getElementById(\"J-passCodeCoin\").innerHTML=\"%s\";" % html
        self.browser.execute_script(js)

    def click_login_button(self):
        login_button = self.browser.find_element_by_xpath('//*[@id="J-login"]')
        login_button.click()

    def get_current_url(self):
        return self.browser.current_url

    def refresh_img64(self):
        js = "document.getElementsByClassName(\"lgcode-refresh\")[0].className='lgcode-refresh lgcode-refresh-click';"
        self.browser.execute_script(js)
        refresh_button = self.browser.find_element_by_css_selector('.lgcode-refresh')
        refresh_button.click()

    def close_browser(self):
        self.browser.close()


if __name__ == '__main__':
    cur_file_path = os.path.realpath(__file__)
    cur_dir_path = os.path.dirname(cur_file_path)
    images_dir_path = os.path.join(cur_dir_path, 'images')
    original_img_path = os.path.join(images_dir_path, 'original.jpg')
    try:
        cur_url = "https://kyfw.12306.cn/otn/resources/login.html"
        login_ins = LoginBySelenium()
        login_ins.prepare_for_download_img64()
        while cur_url == "https://kyfw.12306.cn/otn/resources/login.html":
            sub_img_locations = login_ins.find_sub_img_location(original_img_path)
            login_ins.add_randcode_in_html(sub_img_locations)
            login_ins.click_login_button()
            time.sleep(3)
            cur_url = login_ins.get_current_url()
        print("登录成功！")
    except Exception as e:
        print("Exception happened, the detail is: %s!" % e)
    finally:
        login_ins.close_browser()
