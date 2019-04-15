#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import urllib.request
import re, base64, time, os


if __name__ == '__main__':
    local_img = r'E:\test.png'
    try:
        firefox_options = Options()
        firefox_options.add_argument('--headless')
        browser = webdriver.Firefox(options=firefox_options)
        train_ticket_url = "https://www.12306.cn/index/"
        browser.get(train_ticket_url)
        # 1.点击首页右上角的“登录”
        login_a = browser.find_element_by_xpath('//*[@id="J-header-login"]/a[1]')
        ActionChains(browser).click(login_a).perform()
        time.sleep(1)
        # 2.点击“账号登录”，由于生产验证码图片比较慢，所以需要等待的时间设置较长
        account_login_a = browser.find_element_by_xpath('/html/body/div[2]/div[2]/ul/li[2]/a')
        ActionChains(browser).click(account_login_a).perform()
        time.sleep(3)
        # 3.下载当前的验证码图片
        target_img_src = browser.find_element_by_xpath('//*[@id="J-loginImg"]').get_property("src")
        print(target_img_src)
        if os.path.exists(local_img):
            os.remove(local_img)
        urllib.request.urlretrieve(target_img_src, local_img)
        # 4.利用百度OCR识别图片中的汉字
        access_token = "24.8b8c1b26658a9639e649b039e1897180.2592000.1557905618.282335-16020567"
        url = "https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic?access_token=" + access_token
        params = {}
        with open(local_img, 'rb') as f:
            params = {"image": base64.b64encode(f.read())}
            params = urllib.parse.urlencode(params).encode('utf8')
        request = urllib.request.Request(url, params)
        request.add_header('Content-Type', 'application/x-www-form-urlencoded')
        response = urllib.request.urlopen(request)
        content = response.read()
        target_words = []
        if (content):
            str_content = str(content, encoding='utf8')
            # print(str_content)
            if ("请点击下图中所有的" in str_content):
                str_list1 = re.split(r'请点击下图中所有的', str_content)
                if (len(str_list1) > 1):
                    new_str1 = str_list1[1]  # new_str1为str_content中'请点击下图中所有的'之后的内容
                    # print(new_str1)
                    str_list2 = new_str1.split(r'"')
                    new_str2 = str_list2[0]  # new_str2为new_str1中'"'之前的内容
                    # print(new_str2)
                    if ("和" in new_str2):
                        str_list3 = new_str2.split(r'和')
                        for cur_str in str_list3:
                            target_words.append(cur_str)
                    else:
                        target_words.append(new_str2)
        print(target_words)
    except Exception as e:
        print("Exception happened!")
    finally:
        browser.close()


