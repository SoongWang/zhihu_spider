#!/usr/bin/python
# -*- coding: utf-8 -*-
# Filename : ZhiHuSpider.py

import time
import re
import requests
import http.cookiejar
from PIL import Image
import json
from bs4 import BeautifulSoup
from urllib import request
import os
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class ZhiHuSpider(object):
    def __init__(self):
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 '
                                      '(KHTML, like Gecko) Chrome/57.0.2987.98 Safari/537.36',
                        "Host": "www.zhihu.com",
                        "Referer": "https://www.zhihu.com/",
                        }
        # 建立一个会话，可以把同一用户的不同请求联系起来；直到会话结束都会自动处理cookies
        self.session = requests.Session()
        self.session.keep_alive = True
        # 建立LWPCookieJar实例，可以存Set-Cookie3类型的文件。
        # 而MozillaCookieJar类是存为'/.txt'格式的文件
        self.session.cookies = http.cookiejar.LWPCookieJar('cookie')
        #session.cookies = cookielib.LWPCookieJar(filename='cookies')
        # 若本地有cookie则不用再post数据了
        try:
            self.session.cookies.load(ignore_discard=True)
            print('Cookie加载成功！')
        except IOError:
            print('Cookie未加载！')

    def get_xsrf(self):
        """
        获取参数_xsrf
        """
        response = self.session.get('https://www.zhihu.com', headers=self.headers)
        html = response.text
        pattern = r'name="_xsrf" value="(.*?)"'
        # 这里的_xsrf 返回的是一个list
        #_xsrf = re.findall(pattern, html)
        _xsrf = 'e0397bf0-1b4c-425d-aa16-d57daf508cac'
        return _xsrf[0]

    def get_captcha(self):
        """
        获取验证码本地显示
        返回你输入的验证码
        """
        t = str(int(time.time() * 1000))
        captcha_url = 'http://www.zhihu.com/captcha.gif?r=' + t + "&type=login"
        response = self.session.get(captcha_url, headers=self.headers)
        with open('cptcha.gif', 'wb') as f:
            f.write(response.content)
        # Pillow显示验证码
        im = Image.open('cptcha.gif')
        im.show()
        captcha = input('本次登录需要输入验证码： ')
        return captcha

    def login(self, username, password):
        """
        输入自己的账号密码，模拟登录知乎
        """
        # 检测到11位数字则是手机登录
        if re.match(r'\d{11}$', username):
            url = 'http://www.zhihu.com/login/phone_num'
            data = {'_xsrf': self.get_xsrf(),
                    'password': password,
                    'remember_me': 'true',
                    'phone_num': username
                    }
        else:
            url = 'https://www.zhihu.com/login/email'
            data = {'_xsrf': self.get_xsrf(),
                    'password': password,
                    'remember_me': 'true',
                    'email': username
                    }
        # 若不用验证码，直接登录
        result = self.session.post(url, data=data, headers=self.headers)
        # 打印返回的响应，r = 1代表响应失败，msg里是失败的原因
        # loads可以反序列化内置数据类型，而load可以从文件读取
        if (json.loads(result.text))["r"] == 1:
            # 要用验证码，post后登录
            data['captcha'] = self.get_captcha()
            result = self.session.post(url, data=data, headers=self.headers)
            print((json.loads(result.text))['msg'])
            # 保存cookie到本地
            self.session.cookies.save(ignore_discard=True, ignore_expires=True)

    def isLogin(self):
        # 通过查看用户个人信息来判断是否已经登录
        url = "https://www.zhihu.com/settings/account"
        # 禁止重定向，否则登录失败重定向到首页也是响应200
        login_code = self.session.get(url, headers=self.headers, allow_redirects=False,verify=False).status_code
        if login_code == 200:
            return True
        else:
            return False

    def getUserInfo(self, userId):
        url = 'https://www.zhihu.com/people/' + userId + '/activities'
        response = self.session.get(url, headers=self.headers)
        soup = BeautifulSoup(response.content, 'lxml')
        name = soup.find_all('span', {'class': 'ProfileHeader-name'})[0].string
        print(name)

    def getQsAnswer(self, questionId):

        # 每次我们取10条回答
        limit = 10
        # 获取答案时的偏移量
        offset = 0

        # 开始时假设当前有这么多的回答，得到请求后我再解析
        total = 2 * limit;

        # 我们当前已记录的回答数量
        record_num = 0

        # 定义问题的标题，为了避免获取失败，我们在此先赋值
        title = questionId

        # 存储所有的答案信息
        answer_info = []


        print('Fetch info start...')
        while record_num < total:
            # 开始获取数据
            # 我们获取数据的URL格式是什么样呢？
            # https://www.zhihu.com/api/v4/questions/39162814/answers?
            # sort_by=default&include=data[*].is_normal,content&limit=5&offset=0
            url = 'https://www.zhihu.com/api/v4/questions/' \
                  + questionId + '/answers' \
                                 '?sort_by=default&include=data[*].is_normal,voteup_count,content' \
                                 '&limit=' + str(limit) + '&offset=' + str(offset)
            print(url)
            response = self.session.get(url, headers=self.headers)

            #下载图片
            self.download_pic(url, questionId)

            # 返回的信息为json类型
            response = json.loads(response.content)

            # 其中的paging实体包含了前一页&下一页的URL，可据此进行循环遍历获取回答的内容
            # 我们先来看下总共有多少回答
            total = response['paging']['totals']

            # 本次请求返回的实体信息数组
            datas = response['data']

            # 遍历信息并记录
            if datas is not None:

                if total <= 0:
                    break

                for data in datas:
                    dr = re.compile(r'<[^>]+>', re.S)
                    content = dr.sub('', data['content'])
                    answer = data['author']['name'] + ' ' + str(data['voteup_count']) + ' 人点赞' + '\n'
                    answer = answer + 'Answer:' + content + '\n'
                    answer_info.append('\n')
                    answer_info.append(answer)
                    answer_info.append('\n')
                    answer_info.append('------------------------------')
                    answer_info.append('\n')
                    # 获取问题的title
                    title = data['question']['title']


                # 请求的向后偏移量
                offset += len(datas)
                record_num += len(datas)

                # 如果获取的数组size小于limit,循环结束
                if len(datas) < limit:
                    break;

        print('Fetch info end...')
        answer_info.insert(0, title + '\n')
        self.write2File(title + '.txt', answer_info)

    def write2File(self, filePath, answerInfo):
        print('Write info to file:Start...')
        # 将文件内容写到文件中
        with open(filePath, 'a', encoding='utf-8') as f:
            f.writelines('\n\n')
            for text in answerInfo:
                f.writelines(text)
            f.writelines('\n\n')
            print('Write info to file:end...')

    def download_pic(self, url, questionId):
        html = request.urlopen(url).read().decode('utf-8')
        soup = BeautifulSoup(html, 'html.parser')
        # print(soup.prettify())
        # 使用BeautifulSoup结合正则表达式来提取包含所有图片链接（img标签中，class='origin_image zh-lightbox-thumb',以.jpg结尾的链接）的语句
        links = re.findall(r"img src=\\\"https(.+?)\\\" ", str(soup.prettify()))
        # print(links)
        # 设置图片保存路径，否则会保存程序当前路径
        path = r'D:\Autotest\lianshou\images' + questionId  # r保持字符串的原始值，不进行转义
        isExists = os.path.exists(path)
        if not isExists:
            os.makedirs(path)
        for link in links:
            link = 'https' + link
            # print(link)
            # print(link.attrs['src'])
            # 保存链接并命名，time.time()返回当前时间戳以防止命名冲突
            # time.sleep(0.1)
            request.urlretrieve(link, path + '\%s.jpg' % time.time())



if __name__ == '__main__':
    spider = ZhiHuSpider()
    # if spider.isLogin():
    #     print('您已经登录')
    # else:
    #     account = ''  #input('输入账号：')
    #     secret = ''  #input('输入密码：')
    #     spider.login(account, secret)

    # spider.getQsAnswer('39162814')
    # spider.getQsAnswer('57702309')
    spider.getQsAnswer('297715922')
