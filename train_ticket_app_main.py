#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import urllib.request
import re
import base64, time, os
import shutil
from PIL import Image

train_ticket_url = "https://www.12306.cn/index/"
baidu_shitu_url = "http://image.baidu.com/?fr=shitu"
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


def delete_old_images():
    cur_file_path = os.path.realpath(__file__)
    root_path = os.path.dirname(cur_file_path)
    images_path = os.path.join(root_path, 'images')
    if os.path.exists(images_path):
        shutil.rmtree(images_path)
    time.sleep(1)
    os.mkdir(images_path)
    return images_path


def download_original_image(driver, src_img_path):
    delete_old_images()
    driver.get(train_ticket_url)
    time.sleep(1)
    # 1.点击首页右上角的“登录”
    login_a = driver.find_element_by_xpath('//*[@id="J-header-login"]/a[1]')
    ActionChains(driver).click(login_a).perform()
    time.sleep(1)
    # 2.点击“账号登录”，由于生产验证码图片比较慢，所以需要等待的时间设置较长
    account_login_a = driver.find_element_by_xpath('/html/body/div[2]/div[2]/ul/li[2]/a')
    ActionChains(driver).click(account_login_a).perform()
    time.sleep(3)
    # 3.下载当前的验证码图片
    target_img_src = driver.find_element_by_xpath('//*[@id="J-loginImg"]').get_property("src")
    urllib.request.urlretrieve(target_img_src, src_img_path)


def get_sub_img(im, x, y):
    assert 0 <= x <= 3
    assert 0 <= y <= 2
    WITH = HEIGHT = 68
    left = 5 + (67 + 5) * x
    top = 41 + (67 + 5) * y
    right = left + 67
    bottom = top + 67
    return im.crop((left, top, right, bottom))


def generate_8_sub_images(source_img_path):
    src_img = Image.open(source_img_path)
    cur_dir = os.path.dirname(source_img_path)
    sub_images = []
    for y in range(2):
        for x in range(4):
            sub_img = get_sub_img(src_img, x, y)
            sub_img_name = "%s_%s.png" % (y, x)
            sub_img_path = os.path.join(cur_dir, sub_img_name)
            sub_images.append(sub_img_path)
            sub_img.save(sub_img_path)
    return sub_images


def get_target_word_from_original_image(original_img):
    access_token = "24.8b8c1b26658a9639e649b039e1897180.2592000.1557905618.282335-16020567"
    url = "https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic?access_token=" + access_token
    params = {}
    with open(original_img, 'rb') as f:
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
        """
        if "请点击下图中所有的" in str_content:
            str_list1 = re.split(r'请点击下图中所有的', str_content)
            if len(str_list1) > 1:
                new_str1 = str_list1[1]  # new_str1为str_content中'请点击下图中所有的'之后的内容
                str_list2 = new_str1.split(r'"')
                new_str2 = str_list2[0]  # new_str2为new_str1中'"'之前的内容
                if "和" in new_str2:
                    str_list3 = new_str2.split(r'和')
                    for cur_str in str_list3:
                        target_words.append(cur_str)
                else:
                    target_words.append(new_str2)
    """
    return target_words


def get_shitu_result(img_path):
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


def find_locations(driver, src_img_path):
    # step1: 下载当前验证码图片
    download_original_image(driver, src_img_path)
    # step2: 切割原图片为8个小图片
    sub_img_paths = generate_8_sub_images(src_img_path)
    # step3：利用百度OCR识别图片中的汉字
    target_words = get_target_word_from_original_image(src_img_path)
    if len(target_words) == 0 or target_words == [""]:
        find_locations(driver, src_img_path)
    print("Current target words are %s" % target_words)
    # step4：利用百度识图逐个识别子图并得到满足条件的子图位置
    locations = []
    for cur_sub_image_path in sub_img_paths:
        cur_shitu_result = get_shitu_result(cur_sub_image_path)
        print("Current shitu result is %s." % cur_shitu_result)
        if len(cur_shitu_result) == 0:
            continue
        for target_word in target_words:
            if target_word in cur_shitu_result:
                cur_sub_image = os.path.basename(cur_sub_image_path)
                locations.append(sub_img_location[cur_sub_image])
    if len(locations) == 0:
        find_locations(driver, src_img_path)
    print("Current sub image locations are %s" % locations)
    return locations


if __name__ == '__main__':
    # step1: 清除上一次下载和切割产生的图片
    local_img_path = delete_old_images()
    original_img_path = os.path.join(local_img_path, 'original.jpg')
    try:
        firefox_options = Options()
        # firefox_options.add_argument('--headless')
        browser = webdriver.Firefox(options=firefox_options)
        location_list = find_locations(browser, original_img_path)
    except Exception as e:
        print("Exception happened, the detail is: %s!" % e)
    finally:
        browser.close()
