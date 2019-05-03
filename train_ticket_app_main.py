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
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.by import By
import jieba
import configparser

cur_file_path = os.path.realpath(__file__)
cur_dir_path = os.path.dirname(cur_file_path)
seat_type_dic = {
    '硬座': '1',
    '硬卧': '3',
    '软卧': '4',
    '二等座': '0',
    '动卧': 'F',
    '高级动卧': 'A',
    '一等座': 'M',
}
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


def get_cfg_info_from_ini_file():
    ret = {}
    ini_file_path = os.path.join(cur_dir_path, 'conf.ini')
    conf = configparser.ConfigParser()
    with open(ini_file_path, 'r') as f:
        conf.read_file(f)
        ret["username"] = conf.get('cfg', 'username')
        ret["password"] = conf.get('cfg', 'password')
        ret["from_station"] = conf.get('cfg', 'from_station')
        ret["to_station"] = conf.get('cfg', 'to_station')
        ret["train_date"] = conf.get('cfg', 'train_date')
        ret["passenger_name"] = conf.get('cfg', 'passenger_name')
        ret["seat_type"] = conf.get('cfg', 'seat_type')
    return ret


def get_original_img_path():
    images_dir_path = os.path.join(cur_dir_path, 'images')
    return os.path.join(images_dir_path, 'original.jpg')


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


def optimize_baitu_shitu_result(ret_list):
    for cur_ret in ret_list:
        cur_index = ret_list.index(cur_ret)
        if cur_ret == "书房灯":
            ret_list[cur_index] = "路灯"
        if "转速表" in cur_ret or "仪表" in cur_ret or "速度表" in cur_ret:
            ret_list[cur_index] = "仪表盘"
        if "耳机" in cur_ret:
            ret_list[cur_index] = "耳塞"
        if "拌菜" in cur_ret:
            ret_list[cur_index] = "沙拉"
        if "青豆" in cur_ret:
            ret_list[cur_index] = "绿豆"
        if "球拍" in cur_ret:
            ret_list[cur_index] = "网球拍"
        if cur_ret == "无线电留声机" or cur_ret == "蘑菇拍拍灯":
            ret_list[cur_index] = "锣"
        if cur_ret == "NBA" or (cur_ret == "体育用品" and "草丛" in ret_list) or \
                (cur_ret == "单面花束" and "蛋糕" in ret_list) or cur_ret == "绳球":
            ret_list[cur_index] = "篮球"
        if (cur_ret == "容器" and "瓷器" in ret_list) or (cur_ret == "垫圈" and "瓶子" in ret_list):
            ret_list[cur_index] = "茶盅"
        if cur_ret == "笋丝":
            ret_list[cur_index] = "薯条"
        if cur_ret == "软叶刺葵":
            ret_list[cur_index] = "珊瑚"
        if cur_ret == "油画" or (cur_ret == "图画" and "卡通动漫人物" in ret_list):
            ret_list[cur_index] = "调色板"
        if cur_ret == "艾灸盒":
            ret_list[cur_index] = "文具盒"
        if cur_ret == "行政区划图" or "项链" in cur_ret or cur_ret == "金莺鸟":
            ret_list[cur_index] = "铃铛"
        if cur_ret == "手提袋":
            ret_list[cur_index] = "档案袋"
        if cur_ret == "绝缘子" or cur_ret == "口味蛇" or cur_ret == "万向联轴器" or \
                (cur_ret == "餐巾纸" and "镂空剪纸" in ret_list):
            ret_list[cur_index] = "鞭炮"
        if cur_ret == "红小豆":
            ret_list[cur_index] = "红豆"
        if cur_ret == "锅具" or cur_ret == "阿迪锅" or cur_ret == "漏锅" or \
                cur_ret == "球形摄像机":
            ret_list[cur_index] = "电饭煲"
        if cur_ret == "手套" or cur_ret == "手" or \
                ("绘画" in ret_list and "非主流空间素材" in ret_list) or \
                (cur_ret == "地图" and ("图表" in ret_list or "简笔画" in ret_list)):
            ret_list[cur_index] = "手掌印"
        if cur_ret == "玉玺" or cur_ret == "瓶塞":
            ret_list[cur_index] = "印章"
        if cur_ret == "杨梅干" or cur_ret == "牛肉粒":
            ret_list[cur_index] = "话梅"
        if cur_ret == "灰鲸" or "舰" in cur_ret or (cur_ret == "山峦" and "城楼" in ret_list):
            ret_list[cur_index] = "航母"
        if cur_ret == "车门限位器" or cur_ret == "哨子":
            ret_list[cur_index] = "口哨"
        if "蜥" in cur_ret or cur_ret == "变色龙" or cur_ret == "鹰嘴龟" or cur_ret == "金丝蝾螈":
            ret_list[cur_index] = "蜥蜴"
        if "台历" in cur_ret:
            ret_list[cur_index] = "日历"
        if "鸥" in cur_ret or cur_ret == "白腿小隼" or "鸟" in cur_ret:
            ret_list[cur_index] = "海鸥"
        if "酱" in cur_ret:
            ret_list[cur_index] = "辣椒酱"
        if cur_ret == "洗耳球":
            ret_list[cur_index] = "漏斗"
        if cur_ret == "孔明灯" or cur_ret == "玻璃烛台" or cur_ret == "熔浆" or \
                cur_ret == "电视背景墙" or cur_ret == "洞穴溶洞":
            ret_list[cur_index] = "蜡烛"
        if cur_ret == "葡萄酒":
            ret_list[cur_index] = "红酒"
        if cur_ret == "轮毂" or "风机" in cur_ret or "风扇" in cur_ret:
            ret_list[cur_index] = "排风机"
        if cur_ret == "记事本" or cur_ret == "笔记本" or cur_ret == "百洁布" or \
           cur_ret == "包装袋/盒" or cur_ret == "文件夹" or cur_ret == "便签纸" or \
           cur_ret == "辉铜矿" or cur_ret == "麂皮织物" or cur_ret == "名片夹":
            ret_list[cur_index] = "本子"
        if cur_ret == "铁粉" or cur_ret == "钛铁矿" or (cur_ret == "板材" and "章鱼丸机" not in ret_list):
            ret_list[cur_index] = "海苔"
        if cur_ret == "章鱼丸机" or cur_ret == "电视柜" or cur_ret == "矩形大键琴":
            ret_list[cur_index] = "茶几"
        if cur_ret == "条码纸" or cur_ret == "首饰/饰品" or "胶" in cur_ret or \
                cur_ret == "商品标签" or cur_ret == "浴霸":
            ret_list[cur_index] = "双面胶"
        if cur_ret == "无缝方矩管" or cur_ret == "显示屏":
            ret_list[cur_index] = "黑板"
        if cur_ret == "吊袋" or cur_ret == "灭火器" or cur_ret == "电喷泵" or cur_ret == "U盘":
            ret_list[cur_index] = "沙包"
        if cur_ret == "吊灯" or cur_ret == "前桅" or cur_ret == "麻花钻":
            ret_list[cur_index] = "风铃"
        if cur_ret == "面包篮" or cur_ret == "规整填料" or cur_ret == "草篓":
            ret_list[cur_index] = "蒸笼"
        if cur_ret == "体重秤" or "秤" in cur_ret:
            ret_list[cur_index] = "电子秤"
        if cur_ret == "历史遗迹" or (cur_ret == "山峦" and "城楼" not in ret_list):
            ret_list[cur_index] = "金字塔"
        if cur_ret == "锥柄立铣刀":
            ret_list[cur_index] = "冰箱"
        if cur_ret == "棉花球" or cur_ret == "身体乳" or "药" in cur_ret or \
                cur_ret == "奶油蘑菇汤" or (cur_ret == "糖果" and "电子原器件" in ret_list) or \
                cur_ret == "燕麦":
            ret_list[cur_index] = "药片"
        if cur_ret == "靴子":
            ret_list[cur_index] = "雨靴"
        if cur_ret == "线缆" or cur_ret == "钢编管" or cur_ret == "护套线" \
                or "保险丝" in cur_ret:
            ret_list[cur_index] = "电线"
        if cur_ret == "阿迪达斯" or cur_ret == "吹风机" or cur_ret == "活塞杆" or \
                cur_ret == "蓝牙适配器":
            ret_list[cur_index] = "护腕"
        if cur_ret == "毛绒玩具" or cur_ret == "针线" or cur_ret == "洗衣球" or cur_ret== "文胸":
            ret_list[cur_index] = "毛线"
        if  "勺" in ret_list:
            ret_list[cur_index] = "锅铲"
        if cur_ret == "拍子" or cur_ret == "杯刷":
            ret_list[cur_index] = "苍蝇拍"
        if cur_ret == "扇子" or "绣" in cur_ret:
            ret_list[cur_index] = "刺绣"
        if "碟" in cur_ret or "碗" in cur_ret or "盘" in cur_ret or \
                (cur_ret == "厨具/餐具" and "烟灰缸" in ret_list):
            ret_list[cur_index] = "盘子"
        if cur_ret == "牌楼":
            ret_list[cur_index] = "牌坊"
        if cur_ret == "九脚网眼" or ("卡" in cur_ret and "卡通" not in cur_ret) or \
                cur_ret == "喷墨盒":
            ret_list[cur_index] = "公交卡"
        if "蜂" in cur_ret or cur_ret == "大波斯菊" or cur_ret == "鹿蛾":
            ret_list[cur_index] = "蜜蜂"
        if ("钟" in cur_ret and cur_ret != "钟角蛙") or cur_ret == "表带" or cur_ret == "含生草":
            ret_list[cur_index] = "钟表"
        if "旗" in cur_ret:
            ret_list[cur_index] = "锦旗"
        if cur_ret == "拖布":
            ret_list[cur_index] = "拖把"
    print("优化后的识图结果为：%s" % ret_list)
    return ret_list


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
    print("优化前的识图结果为：%s" % ret)
    ret = optimize_baitu_shitu_result(ret)
    return ret


class LoginBySelenium(object):
    def __init__(self):
        self.browser = webdriver.Firefox()
        self.index_url = "https://www.12306.cn/index/"
        self.login_url = "https://kyfw.12306.cn/otn/resources/login.html"
        self.home_url = "https://kyfw.12306.cn/otn/view/index.html"
        self.query_ticket_url = "https://kyfw.12306.cn/otn/leftTicket/init?linktypeid=dc"
        self.cfg_info = get_cfg_info_from_ini_file()

    def prepare_for_download_img64(self):
        self.browser.get(self.index_url)
        time.sleep(2)
        # 等待index页面加载完成后再点击“登录”
        login_a_xpath = '/html/body/div[2]/div/div[1]/div/div/ul/li[3]/a[1]'
        # WebDriverWait(self.browser, 100).until(
        #     expected_conditions.text_to_be_present_in_element((By.XPATH, login_a_xpath), '登录')
        # )
        login_a = self.browser.find_element_by_xpath(login_a_xpath)
        login_a.click()
        time.sleep(2)
        # 等待默认的login页面加载完成后再点击“账号登录”
        # WebDriverWait(self.browser, 100).until(
        #     expected_conditions.visibility_of_element_located((By.XPATH, '//*[@id="J-login-code-loading"]'))
        # )
        account_login_a_xpath = '/html/body/div[2]/div[2]/ul/li[2]/a'
        account_login_a = self.browser.find_element_by_xpath(account_login_a_xpath)
        account_login_a.click()
        time.sleep(3)
        shaoma_login_css_selector = '.login-code'
        WebDriverWait(self.browser, 100).until(
            expected_conditions.invisibility_of_element_located((By.CSS_SELECTOR, shaoma_login_css_selector))
        )
        self.input_username_and_password()
        # time.sleep(5)

    def input_username_and_password(self):
        username_input = self.browser.find_element_by_xpath('//*[@id="J-userName"]')
        username_input.clear()
        username_input.send_keys(self.cfg_info.get('username', ''))
        password_input = self.browser.find_element_by_xpath('//*[@id="J-password"]')
        password_input.clear()
        password_input.send_keys(self.cfg_info.get('password', ''))

    def download_img64(self, img64_path):
        print("开始下载验证码图片！")
        delete_old_images(os.path.dirname(img64_path))
        img64_element = self.browser.find_element_by_xpath('//*[@id="J-loginImg"]')
        img64_url = img64_element.get_attribute("src")
        urllib.request.urlretrieve(img64_url, img64_path)
        print("验证码图片下载完成！")

    def find_sub_img_location(self, img64_path):
        results = []
        self.download_img64(img64_path)
        target_words = get_baidu_ocr_result(img64_path)
        if len(target_words) == 0 or target_words == [""]:
            print("未能识别出当前验证码图片中的文字！")
            self.refresh_img64()
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
                self.refresh_img64()
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
        WebDriverWait(self.browser, 1000).until(
            expected_conditions.element_to_be_clickable((By.XPATH, '//*[@id="J-login"]'))
        )
        login_button.click()
        time.sleep(15)

    def get_current_url(self):
        return self.browser.current_url

    def refresh_img64(self):
        js = "document.getElementsByClassName(\"lgcode-refresh\")[0].className='lgcode-refresh lgcode-refresh-click';"
        self.browser.execute_script(js)
        refresh_button = self.browser.find_element_by_css_selector('.lgcode-refresh')
        refresh_button.click()
        time.sleep(5)

    def query_ticket(self):
        # 打开查票网页
        self.browser.get(self.query_ticket_url)
        from_station_input_xpath = '//*[@id="fromStationText"]'
        WebDriverWait(self.browser, 1000).until(
            expected_conditions.visibility_of_element_located((By.XPATH, from_station_input_xpath))
        )
        # 输入出发地
        js = "document.getElementById(\"fromStationText\").className='inp-txt inp_selected';"
        self.browser.execute_script(js)
        from_station_input = self.browser.find_element_by_xpath(from_station_input_xpath)
        from_station_input.clear()
        from_station_input.send_keys(self.cfg_info.get('from_station', ''))
        js = "document.getElementById(\"fromStation\").value='CDW';"
        self.browser.execute_script(js)
        # 输入目的地
        to_station_input_xpath = '//*[@id="toStationText"]'
        js = "document.getElementById(\"toStationText\").className='inp-txt inp_selected';"
        self.browser.execute_script(js)
        to_station_input = self.browser.find_element_by_xpath(to_station_input_xpath)
        to_station_input.clear()
        to_station_input.send_keys(self.cfg_info.get('to_station', ''))
        js = "document.getElementById(\"toStation\").value='MYW';"
        self.browser.execute_script(js)
        # 输入出发日
        train_date_xpath = '//*[@id="train_date"]'
        js = "document.getElementById(\"train_date\").removeAttribute('readonly');"
        self.browser.execute_script(js)
        train_date_input = self.browser.find_element_by_xpath(train_date_xpath)
        train_date_input.clear()
        train_date_input.send_keys(self.cfg_info.get('train_date', ''))
        query_button = self.browser.find_element_by_xpath('//*[@id="query_ticket"]')
        query_button.click()
        time.sleep(2)

    def book_ticket(self):
        tr_list = self.browser.find_elements_by_xpath('//*[@id="queryLeftTable"]/tr[not(@datatran)]')
        for tr in tr_list:
            has_ticket = False
            left_ticket = tr.find_element_by_xpath('.//td[10]').text
            if left_ticket == "有" or left_ticket.isdigit():
                has_ticket = True
            if has_ticket:
                print("有满足条件的[硬座]车票！")
                book_button = tr.find_element_by_xpath('.//td[13]/a')
                book_button.click()
                time.sleep(10)
                self.set_seat_type(self.cfg_info.get('seat_type', ''))
                self.set_passenger(self.cfg_info.get('passenger_name', ''))
                submit_button = self.browser.find_element_by_xpath('//*[@id="submitOrder_id"]')
                WebDriverWait(self.browser, 1000).until(
                    expected_conditions.element_to_be_clickable((By.XPATH, '//*[@id="submitOrder_id"]'))
                )
                submit_button.click()
                time.sleep(5)
                print("111111111111")

    def set_passenger(self, passenger_name):
        passenger_li_list = self.browser.find_elements_by_xpath('//*[@id="normal_passenger_id"]/li')
        for passenger_li in passenger_li_list:
            cur_label_text = passenger_li.find_element_by_xpath('.//label').text
            if cur_label_text == passenger_name:
                cur_input = passenger_li.find_element_by_xpath('.//input')
                cur_input.click()
                time.sleep(1)
                break

    def set_seat_type(self, seat_type):
        target_seat_value = seat_type_dic.get(seat_type, '')
        seat_options = self.browser.find_elements_by_xpath('//*[@id="seatType_1"]/option')
        for cur_option in seat_options:
            if cur_option.get_attribute("selected"):
                cur_value = cur_option.get_attribute("value")
                if cur_value != target_seat_value:
                    js = "arguments[0].removeAttribute('selected');"
                    self.browser.execute_script(js, cur_option)
                else:
                    break
            if cur_option.get_attribute("value") == target_seat_value:
                js = "arguments[0].setAttribute('selected', 'selected');"
                self.browser.execute_script(js, cur_option)

    def close_browser(self):
        self.browser.close()


if __name__ == '__main__':
    try:
        login_ins = LoginBySelenium()
        login_ins.prepare_for_download_img64()
        original_img_path = get_original_img_path()
        cur_url = login_ins.login_url
        while cur_url == login_ins.login_url:
            sub_img_locations = login_ins.find_sub_img_location(original_img_path)
            login_ins.add_randcode_in_html(sub_img_locations)
            login_ins.click_login_button()
            cur_url = login_ins.get_current_url()
            print("当前网页的URL是：%s" % cur_url)
        print("登录成功！")
        if cur_url == login_ins.home_url:
            login_ins.query_ticket()
            login_ins.book_ticket()
        print("1111")
    except Exception as e:
        print("Exception happened, the detail is: %s!" % e)
    finally:
        login_ins.close_browser()
