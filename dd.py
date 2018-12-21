# -*- coding: utf-8 -*-
import json
import os
import re
import urllib.request
import time

# 쓰레드, 큐를 위한 라이브러리 추가
import multiprocessing as mp
from threading import Thread

from bs4 import BeautifulSoup
from slackclient import SlackClient
from flask import Flask, request, make_response, render_template

app = Flask(__name__)

slack_token = "xoxb-504131970294-506898491265-Cb7uU3bqPpSDhZsP6H7izhUs"
slack_client_id = "AEYSHMAUE"
slack_client_secret = "11af0200bb82111caeca95ec9cb48fb8"
slack_verification = "WjmNKG6foUstnlzxwsp1bwZ5"
sc = SlackClient(slack_token)

def soup_url_load(url):
    req = urllib.request.Request(url)
    sourcecode = urllib.request.urlopen(url).read()
    soup = BeautifulSoup(sourcecode, "html.parser")

    return soup

def guide_print(result):
    result.append("사용가능한 키워드 : 소개/지원자격/지원내용/이메일/문의전화/지원자격 확인")
    return result

flag = 1

url = "https://www.ssafy.com/ksp/jsp/swp/swpMain.jsp"
qna_url = "https://www.ssafy.com/ksp/servlet/swp.faq.controller.SwpFaqServlet?p_process=select-faq-list&p_receipt_seq="
g_soup = soup_url_load(qna_url)
answer = []

# threading function
def processing_event(queue):
    while True:
        # 큐가 비어있지 않은 경우 로직 실행
        if not queue.empty():
            slack_event = queue.get()

            # Your Processing Code Block gose to here
            channel = slack_event["event"]["channel"]
            text = slack_event["event"]["text"]

            # 챗봇 크롤링 프로세스 로직 함수
            if flag == 1:
                keywords = _crawl_ssafy_keywords(text)
            elif flag == 2:
                keywords = _chk_age(text)
            elif flag == 3:
                keywords = _chk_job(text)
            elif flag == 4:
                keywords = _chk_school(text)

            # 아래에 슬랙 클라이언트 api를 호출하세요
            sc.api_call(
                "chat.postMessage",
                channel=channel,
                text=keywords
            )

def _crawl_ssafy_keywords(text):
    # 여기에 함수를 구현해봅시다.
    result = []

    for index, value in enumerate(g_soup.find_all("div", class_="replyA")):
        answer.append(value.find("div", class_="cont").get_text().strip())

    if text == "<@UEWSEEF7T> 소개":
        soup = soup_url_load(url)

        i = soup.find("div", class_="text-box")
        result.append(i.find("p").get_text())

    elif text == "<@UEWSEEF7T> 지원자격":
        soup = soup_url_load(url)

        i = soup.find("div", class_="column col").get_text().strip()
        result.append(i)

    elif text == "<@UEWSEEF7T> 지원내용":
        soup = soup_url_load(url)

        i = soup.find("div", class_="column col tal").get_text().strip()
        result.append(i)

    elif text == "<@UEWSEEF7T> 이메일":
        soup = soup_url_load(url)

        i = soup.find("dd", class_="icon-email")
        result.append(i.find("a").get_text().strip())

    elif text == "<@UEWSEEF7T> 문의전화":
        soup = soup_url_load(url)

        i = soup.find("dd", class_="icon-phone").get_text().strip()
        result.append(i)

    elif text == ("<@UEWSEEF7T> 지원자격 확인"):
        result.append("1. 만 나이를 입력해주세요. (숫자만 입력)")
        global flag
        flag = 2

    else:
        result.append("다시 입력해주세요.")
        guide_print(result)

    # 한글 지원을 위해 앞에 unicode u를 붙혀준다.
    return u'\n'.join(result)

def _chk_age(text): #30세 미만
    global flag
    result = []

    num = text.split(' ')[1]

    if num.isdigit() == True:
        if int(num) < 30:
            result.append("나이 조건 통과[1/3]")
            result.append("2. 재직여부를 입력해주세요. (Y/N)")
            flag = 3
        else:
            global answer
            result.append(answer[6])
            flag = 1
    else:
        result.append("다시 입력하십시오. 취소하시려면 EXIT를 입력하십시오.")
        flag = 1

    return u'\n'.join(result)


def _chk_job(text): #재직 여부
    global flag
    result = []

    if text == ("<@UEWSEEF7T> N"):
        result.append("재직 조건 통과[2/3]")
        result.append("3. 4년제 대학을 졸업하셨나요?(졸업예정자 가능) (Y/N)")
        flag = 4
    elif text == ("<@UEWSEEF7T> Y"):
        global answer
        result.append(answer[7])
        flag = 1
    elif text == ("<@UEWSEEF7T> EXIT"):
        guide_print(result)
        flag = 1
    else:
        result.append("다시 입력하십시오. 취소하시려면 EXIT를 입력하십시오.")

    return u'\n'.join(result)

def _chk_school(text): #졸업 여부
    global flag
    result = []

    if text == ("<@UEWSEEF7T> Y"): #졸업함
        result.append("졸업 조건 통과[3/3]")
        result.append("축하합니다!! ssafy에 지원 가능합니다.")
        result.append("https://www.ssafy.com/ksp/jsp/swp/swpMain.jsp")
        flag = 1
    elif text == ("<@UEWSEEF7T> N"):
        global answer
        result.append(answer[5])
        flag = 1
    elif text == ("<@UEWSEEF7T> EXIT"):
        guide_print(result)
        flag = 1
    else:
        result.append("다시 입력하십시오. 취소하시려면 EXIT를 입력하십시오.")

    return u'\n'.join(result)


# 이벤트 핸들하는 함수
def _event_handler(event_type, slack_event):

    if event_type == "app_mention":
        event_queue.put(slack_event)
        return make_response("App mention message has been sent", 200, )


@app.route("/listening", methods=["GET", "POST"])
def hears():
    slack_event = json.loads(request.data)

    if "challenge" in slack_event:
        return make_response(slack_event["challenge"], 200, {"content_type":
                                                                 "application/json"
                                                             })

    if slack_verification != slack_event.get("token"):
        message = "Invalid Slack verification token: %s" % (slack_event["token"])
        make_response(message, 403, {"X-Slack-No-Retry": 1})

    if "event" in slack_event:
        event_type = slack_event["event"]["type"]
        return _event_handler(event_type, slack_event)

    # If our bot hears things that are not events we've subscribed to,
    # send a quirky but helpful error response
    return make_response("[NO EVENT IN SLACK REQUEST] These are not the droids\
                        you're looking for.", 404, {"X-Slack-No-Retry": 1})


@app.route("/", methods=["GET"])
def index():
    return "<h1>Server is ready.</h1>"


if __name__ == '__main__':
    event_queue = mp.Queue()

    p = Thread(target=processing_event, args=(event_queue,))
    p.start()
    print("subprocess started")

    app.run('0.0.0.0', port=8080)
    p.join()