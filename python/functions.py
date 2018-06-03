import os
import cherrypy
import json
import urllib2
import sqlite3
import base64
import mimetypes
import time
from itertools import cycle, izip
from threading import Event
from hashlib import sha256
import atexit
	
#Gets the list of online users and returns it on the right side of the page
def getUsers(userLogged, Page):
    #Gets the list of online users
    data = urllib2.urlopen("http://cs302.pythonanywhere.com/getList?username={0}&password={1}&enc=0&json=1".format(cherrypy.session['username'], cherrypy.session['password'])).read()
    dict = json.loads(data)
    #Connect to the User database
    db = sqlite3.connect("db/Users.db")
    cursor = db.cursor()
    #Save data for online users and display them on the screen
    Page += '<div class="online-users">'
    Page += '<hr><b class="font-color1">Online Users </b><hr>'
    onlineUsers = ()
    for id, info in dict.items():
        # Check if the user does not exist and create it
        try:
            cursor.execute('INSERT INTO Profile(UPI, Name, Position, Description, Location, Picture, IP, Port) VALUES(?,?,?,?,?,?,?,?)', (info['username'],"","","","","","",""))
        except:
            pass
        onlineUsers = onlineUsers + (info['username'],)
        #Update IP Address
        cursor.execute('UPDATE Profile SET IP = ? WHERE UPI = ?', (info['ip'], info['username']))
        cursor.execute('UPDATE Profile SET Port = ? WHERE UPI = ?', (info['port'], info['username']))
        if (info['username'] != userLogged):
            Page += info['username'] + "<br/>"
            #Button for viewing an online user's profile
            Page += '<form action="/saveInfo" method="post" enctype="multipart/form-data">'
            Page += '<button name="UPI" value="{}" class="message-button"/>View Profile</button></form>'.format(info['username'])
            #Button for messaging an online user
            Page += '<form action="/messaging?destination={}" method="post" enctype="multipart/form-data">'.format(info['username'])
            Page += '<input class= "message-button" type="submit" value="Message"></form>'
    #Display offline users
    cursor.execute("SELECT UPI FROM Profile")
    UPI = cursor.fetchall()
    Page += '<hr><b class="font-color1">Offline Users </b><hr>'
    for name in UPI:
        if (name[0] not in onlineUsers):
            Page += '{}<br/>'.format(name[0])
			#Button for viewing an offline user's profile
            Page += '<form action="/saveInfo" method="post" enctype="multipart/form-data">'
            Page += '<button name="UPI" value="{}" class="message-button"/>View Profile</button></form>'.format(name[0])
    Page += '</div>'
    db.commit()
    db.close()
    return Page
		
#Read user data stored in the database
def readUserData(user):
    #Opening database and reading user info
    db = sqlite3.connect("db/Users.db")
    c = db.cursor()
    c.execute('SELECT * FROM Profile WHERE UPI = ?',(user,))
    #User info stored into a tuple, row
    row = c.fetchone()
    #Close db
    db.close()
    return row

#Opening Html files to return to the page		
def readHtml(html):
    #Open and read html file
    file = open("html/{}.html".format(html), "r")
    Page = file.read()
    file.close()
    return Page
		
#Writing message to the db
def saveMessage(user, UPI, sender, message, stamp, type):
    db = sqlite3.connect("db/Conversation.db")
    cursor = db.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS {}(UPI TEXT NOT NULL, Sender TEXT NOT NULL, Message TEXT NOT NULL, Stamp TEXT NOT NULL, Type TEXT NOT NULL)'.format(user))
    cursor.execute('INSERT INTO {}(UPI, SENDER, Message, Stamp, Type) VALUES (?,?,?,?,?)'.format(user), (UPI, sender, message, stamp, type))
    db.commit()
    db.close()
    return '0'
		
#Called to make sure you are logged in before being able to do anything which requires authentication e.g. profile editing or messaging
def checkLogged():
    try:
        username = cherrypy.session['username']
        password = cherrypy.session['password']
    except KeyError: #No logged in user
        raise cherrypy.HTTPRedirect('/errorPage')
    return
		
#Adds the stored messages to the page
def formatMessage(name, message, stamp, mType, Page):
    if (mType == "notstring"):
        filePath = message.split("/")
        type = mimetypes.guess_type(filePath[3],strict = True)
        if (type[0] == 'image/jpeg' or type[0] == 'image/png'):
            Page += '{0}<br/>{1} :<br/> <img src="{2}" width="200" height="200"><br/>'.format(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(stamp))), name, message)
        elif (type[0] == 'video/mp4'):
            Page += '{0}<br/>{1} :<br/> <video width="200" height="200" controls><source src="{2}" type="{3}"></video><br/>'.format(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(stamp))), name, message, type[0])
        elif (type[0] == 'audio/mpeg'):
            Page += '{0}<br/>{1} :<br/> <audio controls><source src="{2}" type="{3}"></audio><br/>'.format(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(stamp))), name, message, type[0])
        else:
            Page += '{0}<br/>{1} :<br/> <video width="320" height="240" controls><source src="{2}" type="{3}"></video><br/>'.format(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(stamp))), name, message, type[0])
    else:
        Page += '{0}<br/>{1} : {2}<br/>'.format(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(stamp))), name, message)
    return Page
		
#enctype = 1
def XOREncryption(text, key="\b10010110"):
    return ''.join(chr(ord(x) ^ ord(y)) for (x,y) in izip(text, cycle(key)))
	
#Called on exit. If a user is logged in, it will log out the current user
def exit_handler():
    try:
        r = urllib2.urlopen("http://cs302.pythonanywhere.com/logoff?username={0}&password={1}".format(cherrypy.session['username'], cherrypy.session['password']))
    except:
        pass

atexit.register(exit_handler)