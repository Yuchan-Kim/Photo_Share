######################################
# author ben lawson <balawson@bu.edu>
# Edited by: Craig Einstein <einstein@bu.edu>
######################################
# Some code adapted from
# CodeHandBook at http://codehandbook.org/python-web-application-development-using-flask-and-mysql/
# and MaxCountryMan at https://github.com/maxcountryman/flask-login/
# and Flask Offical Tutorial at  http://flask.pocoo.org/docs/0.10/patterns/fileuploads/
# see links for further understanding
###################################################
import sys
import urllib

import flask
from flask import Flask, Response, request, render_template, redirect, url_for, flash
from flaskext.mysql import MySQL
import flask_login

#for image uploading
import os, base64

mysql = MySQL()
app = Flask(__name__)
app.secret_key = 'super secret string'  # Change this!

#These will need to be changed according to your creditionals
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'Rladbcks970906!@'
app.config['MYSQL_DATABASE_DB'] = 'photoshare'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)

#begin code used for login
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

conn = mysql.connect()
cursor = conn.cursor()
cursor.execute("SELECT email from Users")
users = cursor.fetchall()

def getUserList():
	cursor = conn.cursor()
	cursor.execute("SELECT email from Users")
	return cursor.fetchall()

class User(flask_login.UserMixin):
	pass

@login_manager.user_loader
def user_loader(email):
	users = getUserList()
	if not(email) or email not in str(users):
		return
	user = User()
	user.id = email
	return user

@login_manager.request_loader
def request_loader(request):
	users = getUserList()
	email = request.form.get('email')
	if not(email) or email not in str(users):
		return
	user = User()
	user.id = email
	cursor = mysql.connect().cursor()
	cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email))
	data = cursor.fetchall()
	pwd = str(data[0][0] )
	user.is_authenticated = request.form['password'] == pwd
	return user

'''
A new page looks like this:
@app.route('new_page_name')
def new_page_function():
	return new_page_html
'''

@app.route('/login', methods=['GET', 'POST'])
def login():
	if flask.request.method == 'GET':
		return '''
			   <form action='login' method='POST'>
				<input type='text' name='email' id='email' placeholder='email'></input>
				<input type='password' name='password' id='password' placeholder='password'></input>
				<input type='submit' name='submit'></input>
			   </form></br>
		   <a href='/'>Home</a>
			   '''
	#The request method is POST (page is recieving data)
	email = flask.request.form['email']
	cursor = conn.cursor()
	#check if email is registered
	if cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email)):
		data = cursor.fetchall()
		pwd = str(data[0][0] )
		if flask.request.form['password'] == pwd:
			user = User()
			user.id = email
			flask_login.login_user(user) #okay login in user
			return flask.redirect(flask.url_for('protected')) #protected is a function defined in this file

	#information did not match
	return "<a href='/login'>Try again</a>\
			</br><a href='/register'>or make an account</a>"

@app.route('/logout')
def logout():
	flask_login.logout_user()
	return render_template('hello.html', message='Logged out', public_albums=getAlbums())

@login_manager.unauthorized_handler
def unauthorized_handler():
	return render_template('unauth.html')

#you can specify specific methods (GET/POST) in function header instead of inside the functions as seen earlier
@app.route("/register", methods=['GET'])
def register():
	return render_template('register.html', supress='True')

@app.route("/register", methods=['POST'])
def register_user():
	try:
		email=request.form.get('email')
		password=request.form.get('password')
		first_name=request.form.get('first_name')
		last_name=request.form.get('last_name')
		dob=request.form.get('dob')
		hometown=request.form.get('hometown')
		gender=request.form.get('gender')
	except:
		print("couldn't find all tokens") #this prints to shell, end users will not see this (all print statements go to shell)
		return flask.redirect(flask.url_for('register'))
	cursor = conn.cursor()
	test =  isEmailUnique(email)
	if test:
		print(cursor.execute("INSERT INTO Users (email, password, first_name, last_name, dob, hometown, gender) VALUES ('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}')".format(email, password, first_name, last_name, dob, hometown, gender)))
		conn.commit()
		#log user in
		user = User()
		user.id = email
		flask_login.login_user(user)
		return render_template('hello.html', name=email, message='Account Created!')
	else:
		print("couldn't find all tokens")
		flash('dd', 'error')
		return flask.redirect(flask.url_for('register'))


def getUserIdFromEmail(email):
	cursor = conn.cursor()
	cursor.execute("SELECT user_id  FROM Users WHERE email = '{0}'".format(email))
	return cursor.fetchone()[0]

def isEmailUnique(email):
	#use this to check if a email has already been registered
	cursor = conn.cursor()
	if cursor.execute("SELECT email  FROM Users WHERE email = '{0}'".format(email)):
		#this means there are greater than zero entries with that email
		return False
	else:
		return True

#end login code

@app.route('/profile')
@flask_login.login_required
def protected():
	email = flask_login.current_user.id
	user_id = getUserIdFromEmail(email)
	user_albums = getUsersAlbums(user_id)
	public_albums = getAlbums()
	return render_template('hello.html', 
							name=flask_login.current_user.id, 
							message="Here's your profile",
							albums = user_albums,
							public_albums = public_albums)

# Friend List, user list, recommendations
@app.route('/friends')
@flask_login.login_required
def friends():
	email = flask_login.current_user.id
	user_id = getUserIdFromEmail(email)
	user_friends = getFriends(user_id)
	users_s = getUsersExceptMe(user_id)
	recommend = getRecommendFriend(user_id)
	return render_template('friends.html', 
							name=flask_login.current_user.id, 
							message="Here's your friends",
							friends = user_friends, 
                            users = users_s,
                            recommend_friend = recommend)

#add new friends
@app.route('/friends/add/<f_id>', methods=['GET', 'POST'])
@flask_login.login_required
def add_friend(f_id):
	if request.method == 'GET':
		email = flask_login.current_user.id
		user_id = getUserIdFromEmail(email)
		user_friends = getFriends(user_id)
		users_s = getUsersExceptMe(user_id)
		cursor = conn.cursor()
		cursor.execute("INSERT INTO friends (user_id_1, friend_id) VALUES ('{0}', '{1}')".format(user_id, f_id))
		conn.commit()
		return flask.redirect(flask.url_for('protected')) #protected is a function defined in this file
	else:
		email = flask_login.current_user.id
		user_id = getUserIdFromEmail(email)
		user_friends = getFriends(user_id)
		users_s = getUsersExceptMe(user_id)
		return flask.redirect(flask.url_for('protected')) #protected is a function defined in this file

#Search friends
@app.route('/friends/search', methods=['POST'])
@flask_login.login_required
def search_friends():
    usersEmail = request.form.get('search_user')
    return render_template('friends.html',result=showUserInfo(usersEmail))

def showALLFriends(uid):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT email FROM Users
        JOIN Friendship ON Users.user_id = Friendship.friend_id
        WHERE Friendship.user_id = '{0}'
    """.format(uid))
    friends = [row[0] for row in cursor.fetchall()]
    return friends

def showUserInfo(uid):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT email FROM Users
        WHERE email = '{0}'
        LIMIT 1
    """.format(uid))
    return cursor.fetchone()[0]




# user list without my account
def getUsersExceptMe(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT user_id, email from Users  WHERE user_id <> '{0}' and user_id not in (select friend_id from Friends where user_id_1 = '{1}')".format(uid, uid))
	return cursor.fetchall() #NOTE return a list of tuples, [(imgdata, pid, caption), ...]

# get friend list
def getFriends(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT user_id_1, friend_id, email FROM Friends a, Users b WHERE a.friend_id = b.user_id and a.user_id_1 = '{0}' ".format(uid))
	return cursor.fetchall() #NOTE return a list of tuples, [(imgdata, pid, caption), ...]

#Recommended friends
def getRecommendFriend(uid):
    cursor = conn.cursor()
    cursor.execute("SELECT y.user_id, y.email FROM friends x, users y where x.friend_id = y.user_id  and x.user_id_1 in (SELECT friend_id FROM friends a WHERE user_id_1  = '{0}')  and y.user_id not in (SELECT friend_id FROM Friends WHERE user_id_1 = '{1}') and y.user_id != '{1}'".format(uid, uid))
    return cursor.fetchone() #NOTE return a list of tuples, [(imgdata, pid, caption), ...]



#begin photo uploading code
# photos uploaded using base64 encoding so they can be directly embeded in HTML
def getUsersPhotos(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT imgdata, picture_id, caption FROM Pictures WHERE user_id = '{0}'".format(uid))
	return cursor.fetchall() #NOTE return a list of tuples, [(imgdata, pid, caption), ...]

def getUsersPhotosAlbum(uid, album_id):
	cursor = conn.cursor()
	cursor.execute("SELECT  imgdata, picture_id, caption FROM Pictures WHERE user_id = '{0}' AND album_id = '{1}'".format(uid, album_id))
	return cursor.fetchall() #NOTE return a list of tuples, [(imgdata, pid, caption), ...]

# get photo info
def getPhoto(photo_id):
	cursor = conn.cursor()
	cursor.execute("SELECT  picture_id, user_id FROM Pictures WHERE picture_id = '{0}'".format(photo_id))
	return cursor.fetchone() #NOTE return a list of tuples, [(imgdata, pid, caption), ...]

# get tags of the photo
def getTags(photo_id):
	cursor = conn.cursor()
	cursor.execute("SELECT  picture_id,  tags_name FROM Tagged a, Tags b WHERE a.tag_id = b.tags_id and a.picture_id = '{0}'".format(photo_id))
	return cursor.fetchall() #NOTE return a list of tuples, [(imgdata, pid, caption), ...]

# list Top10 contributors
def getTop10Contributors():
	cursor = conn.cursor()
	cursor.execute("SELECT u.user_id, u.email, COALESCE(num_photos, 0) + COALESCE(num_replies, 0) AS total_contributions FROM users u LEFT JOIN (SELECT user_id, COUNT(DISTINCT picture_id) AS num_photos FROM pictures GROUP BY user_id) p ON u.user_id = p.user_id LEFT JOIN (SELECT user_id, COUNT(DISTINCT reply_id) AS num_replies FROM replys GROUP BY user_id) r ON u.user_id = r.user_id ORDER BY total_contributions DESC")
	return cursor.fetchall() #NOTE return a list of tuples, [(imgdata, pid, caption), ...]


ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/album/<name>/upload', methods=['GET', 'POST'])
@flask_login.login_required
def upload_file(name):
	if request.method == 'POST':
		uid = getUserIdFromEmail(flask_login.current_user.id)
		imgfile = request.files['photo']
		caption = request.form.get('caption')
		photo_data =imgfile.read()
		cursor = conn.cursor()
		album_id = getAlbumIdName(uid, name)
		cursor.execute('''INSERT INTO Pictures (imgdata, user_id, caption, album_id) VALUES (%s, %s, %s, %s )''', (photo_data, uid, caption, album_id))
		conn.commit()
		return render_template('photos.html', name=flask_login.current_user.id, message='Photo uploaded!', photos=getUsersPhotos(uid), base64=base64)
	#The method is GET so we return a  HTML form to upload the a photo.
	else:
		return render_template('upload.html', name=name)


#end photo uploading code

#begin album management code#
def getAlbums(): #get all albums across all users
	cursor = conn.cursor()
	cursor.execute("SELECT name from Albums")
	row = cursor.fetchall() #returns tuples
	return [a[0] for a in row]

def getUsersAlbums(uid): #get all albums specific to an user
	cursor = conn.cursor()
	cursor.execute("SELECT name from Albums WHERE user_id = '{0}'".format(uid))
	row = cursor.fetchall() #returns tuples
	return [a[0] for a in row]

def getAlbumIdName(uid, name): # get an album id specific to an user
	cursor = conn.cursor()
	cursor.execute("SELECT album_id, user_id FROM Albums WHERE user_id = '{0}' AND name = '{1}'".format(uid, name))
	return cursor.fetchone()[0]

def getAlbumName(uid, name): # get an album specific to an user
	cursor = conn.cursor()
	cursor.execute("SELECT album_id, user_id FROM Albums WHERE user_id = '{0}' AND name = '{1}'".format(uid, name))
	return cursor.fetchone()

def getUserIdbyAlbumName(name): # Get name of user who created the album
	cursor = conn.cursor()
	cursor.execute("SELECT user_id FROM Albums WHERE name = '{0}' ".format(name))
	return cursor.fetchone()[0]

def getReplys(picture_id): # get info by comments
	cursor = conn.cursor()
	cursor.execute("SELECT reply_id, a.user_id, email, contents from Replys a, Users b where a.user_id = b.user_id and picture_id = '{0}'".format(picture_id))
	return cursor.fetchall() #returns tuples

def getLikes(picture_id): # get how many like the photo got
	cursor = conn.cursor()
	cursor.execute("SELECT like_id, a.user_id, email from Likes a, Users b where a.user_id = b.user_id and picture_id = '{0}'".format(picture_id))
	return cursor.fetchall() #returns tuples

def isLikedUser(uid, photo_id): # get info of who liked the photo
	cursor = conn.cursor()
	if cursor.execute("SELECT like_id FROM Likes WHERE user_id = '{0}' and picture_id = '{1}'".format(uid, photo_id)):
		return True
	else:
		return False

def getBestPictures(): # Get the best pictures (based on number of tags)
	cursor = conn.cursor()
	cursor.execute("SELECT x.picture_id, y.imgdata, y.caption, y.album_id, COUNT(*) as num_tags FROM tagged x, pictures y WHERE x.picture_id = y.picture_id GROUP BY x.picture_id ORDER BY num_tags DESC LIMIT 10")
	return cursor.fetchall() #returns tuples



@app.route("/album/delete/<name>", methods=['GET','POST'])
@flask_login.login_required
def delete_album(name):
	if request.method == 'POST':
		uid = getUserIdFromEmail(flask_login.current_user.id)
		album = getAlbumName(uid, name)
		if album[1] != uid:
			return render_template('delete_album.html', name=name)            
		cursor = conn.cursor()
		cursor.execute("DELETE FROM Albums WHERE album_id= '{0}'".format(album[0]))
		conn.commit()
		return render_template('hello.html', name=flask_login.current_user.id, message='Album deleted!', base64=base64)
	else:
		return render_template('delete_album.html', name=name)


@app.route("/albums", methods=['GET','POST'])
@flask_login.login_required
def upload_album():
	if request.method == 'POST':
		uid = getUserIdFromEmail(flask_login.current_user.id)
		name = request.form.get('album_name')
		cursor = conn.cursor()
		cursor.execute("INSERT INTO Albums (name, user_id) VALUES ('{0}', '{1}' )".format(name, uid))
		conn.commit()
		return render_template('hello.html', name=flask_login.current_user.id, message='Album uploaded!', base64=base64)
	else:
		return render_template('albums.html', public_albums=getAlbums())

@app.route("/album/<name>", methods=['GET'])
@flask_login.login_required
def view_album(name):
	uid = getUserIdFromEmail(flask_login.current_user.id)
	album_id = getAlbumIdName(uid,name)
	photos = getUsersPhotosAlbum(uid, album_id)
	l_photos = list(photos)
	idx = 0    
	for photo in l_photos:
		l_photo = list(photo)
		l_photo.append(getTags(photo[1]))
		l_photo.append(getReplys(photo[1]))
		l_photo.append(getLikes(photo[1]))
		l_photos[idx] = tuple(l_photo)
		idx = idx+1
	photos = tuple(l_photos)
	return render_template('photos.html', name = name, album_id = album_id, photos =photos, public= False, base64=base64)

@app.route("/album/public/<name>", methods=['GET'])
def view_public_album(name):
	uid = getUserIdbyAlbumName(name)
	album_id = getAlbumIdName(uid, name)
	photos = getUsersPhotosAlbum(uid, album_id)
	l_photos = list(photos)
	idx = 0    
	for photo in l_photos:
		l_photo = list(photo)
		l_photo.append(getTags(photo[1]))
		l_photo.append(getReplys(photo[1]))
		l_photo.append(getLikes(photo[1]))
		l_photos[idx] = tuple(l_photo)
		idx = idx+1
	photos = tuple(l_photos)
	return render_template('photos.html', name = name, album_id = album_id, photos = photos, public = True, base64=base64)

# Find albums
@app.route("/album/search", methods=['GET'])
def album_search():
		cursor = conn.cursor()
		album_name= request.args.get('album')
		where = "select album_id, name from albums where name = '{0}'".format(album_name)
		cursor.execute(where)
		conn.commit()
		return render_template('hello.html', name=flask_login.current_user.id, s_albums = cursor.fetchall(), base64=base64)


@app.route("/reply/search", methods=['GET'])
def reply_search():
    cursor = conn.cursor()
    reply= request.args.get('reply')
    where = "select picture_id, imgdata, album_id from pictures where picture_id in  (select picture_id from replys where contents like '%{0}%')".format(reply)
    cursor.execute(where)
    photos = cursor.fetchall()
    l_photos = list(photos)
    idx = 0    
    for photo in l_photos:
        l_photo = list(photo)
        l_photo.append(getReplys(photo[0]))
        l_photos[idx] = tuple(l_photo)
        idx = idx+1
    photos = tuple(l_photos)
    conn.commit()
    return render_template('hello.html', name=flask_login.current_user.id, s_photos = photos, base64=base64)

# Delete photos
@app.route("/delete_photo", methods=['POST'])
@flask_login.login_required
def delete_photo():
		cursor = conn.cursor()
		photo_id= request.form.get('delete_photo')
		cursor.execute("DELETE FROM Pictures WHERE picture_id= '{0}'".format(photo_id))
		conn.commit()
		return render_template('hello.html', name=flask_login.current_user.id, message='Photo deleted!', base64=base64)

# put tags on photos
@app.route("/photo/tag", methods=['POST'])
@flask_login.login_required
def photo_tag():
		cursor = conn.cursor()
		tagname= request.form.get('tagname')
		photo_id= request.form.get('photo_id')
		cursor.execute("INSERT INTO Tags (tags_name) VALUES ('{0}' )".format(tagname))
		tag_id = conn.insert_id()
		cursor.execute("INSERT INTO Tagged (picture_id, tag_id) VALUES ('{0}', '{1}' )".format(photo_id, tag_id))
		conn.commit()
		return flask.redirect(flask.url_for('protected')) #protected is a function defined in this file

# Leave comments on photos
@app.route("/photo/reply", methods=['POST'])
@flask_login.login_required
def photo_reply():
		cursor = conn.cursor()
		uid = getUserIdFromEmail(flask_login.current_user.id)
		reply= request.form.get('reply')
		photo_id= request.form.get('photo_id')
		photo = getPhoto(photo_id)
		if uid == photo[1]:
			return flask.redirect(flask.url_for('protected'))            
		album_name= request.form.get('album_name')
		cursor.execute("INSERT INTO Replys (contents, picture_id, user_id) VALUES ('{0}', '{1}', '{2}' )".format(reply, photo_id, uid))
		conn.commit()
		#return flask.redirect(flask.url_for('view_album', name=album_name))
		return flask.redirect(flask.url_for('protected')) #protected is a function defined in this file

# Like system 
@app.route("/photo/like", methods=['POST'])
@flask_login.login_required
def photo_like():
		cursor = conn.cursor()
		uid = getUserIdFromEmail(flask_login.current_user.id)
		photo_id= request.form.get('like')
		if isLikedUser(uid, photo_id) == True:
			return flask.redirect(flask.url_for('protected'))
		cursor.execute("INSERT INTO Likes (picture_id, user_id) VALUES ('{0}', '{1}')".format( photo_id, uid))
		conn.commit()
		return flask.redirect(flask.url_for('protected')) #protected is a function defined in this file

# Search photos by tags
@app.route("/photo/search", methods=['GET'])
def photo_search():
		cursor = conn.cursor()
		tag= request.args.get('tag')
		tags_name = tag.split(' ')
		where = ''
		if len(tags_name) == 1:
			where = "SELECT picture_id, imgdata, album_id from pictures where picture_id in (SELECT a.picture_id FROM Tagged a, Pictures b, Tags c WHERE a.picture_id = b.picture_id and a.tag_id = c.tags_id and tags_name = '{0}')".format(tag)
		else:
			where = "SELECT picture_id, imgdata, album_id from pictures where picture_id in (SELECT a.picture_id FROM Tagged a, Pictures b, Tags c WHERE a.picture_id = b.picture_id and a.tag_id = c.tags_id and tags_name in {0} group by a.picture_id having count(a.picture_id) >= {1})".format(tuple(tags_name), len(tags_name))
		cursor.execute(where)
		conn.commit()
		return render_template('hello.html', name=flask_login.current_user.id, photos = cursor.fetchall(), base64=base64)

# Most popular top 3 tags
@app.route("/tags", methods=['GET'])
def tags():
		cursor = conn.cursor()
		where = "select tags_name, count(*) as cnt from tags a group by tags_name order by cnt desc limit 3;"
		cursor.execute(where)
		conn.commit()
		return render_template('hello.html', name=flask_login.current_user.id, tags = cursor.fetchall())
    
#default page
@app.route("/", methods=['GET'])
def hello():
	return render_template('hello.html', message='Welcome to Photoshare', public_albums = getAlbums(), best = getBestPictures(), top10 = getTop10Contributors(), base64=base64)


if __name__ == "__main__":
	#this is invoked when in the shell  you run
	#$ python app.py
	app.run(port=5000, debug=True)
