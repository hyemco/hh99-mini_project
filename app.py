from pymongo import MongoClient
import jwt
import datetime
import hashlib
from flask import Flask, render_template, jsonify, request, redirect, url_for
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config['UPLOAD_FOLDER'] = "./static/profile_pics"

SECRET_KEY = 'SPARTA'

# 서버용 mongodb
client = MongoClient('3.35.17.197', 27017, username="test", password="test")

# 로컬호스트용 mongodb
db = client.dbmini_project

####### 페이지 이동
@app.route('/')
def home():
    plant_card = list(db.plants.find({}, {'_id': False}).limit(30))
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])

        return render_template('index.html', plant_card=plant_card)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))

# 로그인
@app.route('/login')
def login():
    msg = request.args.get("msg")
    return render_template('login.html', msg=msg)

# 상세 페이지
@app.route('/detail/<keyword>')
def detail(keyword):
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        plant = db.plants.find_one({"title": keyword}, {"_id": False})
        details = db.plant_detail.find_one({"title": keyword}, {"_id": False})
        post = db.posts.find_one({"target": keyword}, {"_id": False})
        return render_template('detail.html', plant=plant, details=details, post=post ,target=keyword)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))


# 로그인
@app.route('/sign_in', methods=['POST'])
def sign_in():
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']

    pw_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    result = db.users.find_one({'username': username_receive, 'password': pw_hash})

    if result is not None:
        payload = {
            'id': username_receive,
            'exp': datetime.utcnow() + timedelta(seconds=60 * 60 * 24)  # 로그인 24시간 유지
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256').decode('utf-8')

        return jsonify({'result': 'success', 'token': token})
    # 찾지 못하면
    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})


# 회원가입 - 서버 저장
@app.route('/sign_up/save', methods=['POST'])
def sign_up():
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']
    password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    doc = {
        "username": username_receive,  # 아이디
        "password": password_hash,  # 비밀번호
    }
    db.users.insert_one(doc)
    return jsonify({'result': 'success'})


# 회원가입 - 중복확인
@app.route('/sign_up/check_dup', methods=['POST'])
def check_dup():
    username_receive = request.form['username_give']
    exists = bool(db.users.find_one({"username": username_receive}))
    return jsonify({'result': 'success', 'exists': exists})


# DB 데이터 가져오기(메인페이지-식물 리스트) : jinja2로 index.html에서 나타내기
@app.route('/listing', methods=['GET'])
def listing():
    plant_card = list(db.plants.find({}).limit(30))
    for card in plant_card:
        card['_id'] = str(card['_id'])
    return jsonify({'plant_card': plant_card})


# API - DB 데이터 가져오기(상세페이지-식물 detail) : jinja2로 detail.html에서 나타냈음
@app.route('/detail/', methods=['GET'])
def get_details():
    detail_box = list(db.plant_detail.find({}, {'_id': False}))
    return jsonify({'detail_box': detail_box})


# API - 댓글 작성하기
@app.route('/posting', methods=['POST'])
def posting():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])

        user_info = db.users.find_one({"username": payload["id"]})
        comment_receive = request.form["comment_give"]
        target_receive = request.form["target_give"]
        date_receive = request.form["date_give"]

        doc = {
            "username": user_info["username"],
            "comment": comment_receive,
            "target": target_receive,
            "date": date_receive
        }
        db.posts.insert_one(doc)
        return jsonify({"result": "success", 'msg': '등록 완료'})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))


# API - 댓글 나타내기
@app.route("/get_posts/", methods=['GET'])
def get_posts():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        # 해당 페이지 식물 이름(target) 받아오기
        target_receive = request.args.get("target_give")
        # db에서 해당 페이지의 리뷰를 찾아 15개까지 보여줌
        posts = list(db.posts.find({"target": target_receive}).sort("date", -1).limit(15))
        for post in posts:
            post["_id"] = str(post["_id"])
        return jsonify({"result": "success", "msg": "포스팅을 가져왔습니다.", "posts": posts})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))


# API - 댓글 삭제
@app.route('/delete', methods=['POST'])
def delete_star():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        comment_receive = request.form['comment_give']
        # 받아온 comment 값과 일치하는 딕셔너리 삭제
        db.posts.delete_one({'comment': comment_receive})
        return jsonify({'msg': '삭제되었습니다.!'})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

# # 상세 페이지 크롤링
# import requests
# from bs4 import BeautifulSoup
#
# headers = {'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'}
# data = requests.get('https://www.fuleaf.com/plants',headers=headers)
#
# soup = BeautifulSoup(data.text, 'html.parser')
#
# main_list = soup.select('#plants_list > ul > div')
#
# for list in main_list:
#     main_image = list.select_one('a > div.plant__image').get('style').replace('background-image: url(', '').replace(');', '')
#     image = main_image
#     title = list.select_one('a > div.plant__title-flex > h3').text
#     print(title, image)
#     doc = {
#         'title':title,
#         'image':image
#     }
#     db.plants.insert_one(doc)

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)