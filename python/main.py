""" main.py

    COMPSYS302 - Software Design
    Author: Henry Shen (hshe440@aucklanduni.ac.nz)
    Last Edited: 06/06/2018

    This program uses the CherryPy web server (from www.cherrypy.org).
"""
# Requires:  CherryPy 3.2.2  (www.cherrypy.org)
#            Python  (We use 2.7)

# The address we listen for connections on
listen_ip = "0.0.0.0"
listen_port = 10010

import os
import cherrypy
import json
import urllib2
import sqlite3
import base64
import mimetypes
import time
import socket
import logging
from itertools import cycle, izip
from threading import Event
import myThread
import functions
from hashlib import sha256

class MainApp(object):

    #CherryPy Configuration
    _cp_config = {'tools.encode.on': True, 
                  'tools.encode.encoding': 'utf-8',
                  'tools.sessions.on' : 'True',
                 }                 
				 

    # If they try somewhere we don't know, catch it here and send them to the right place.
    @cherrypy.expose
    def default(self, *args, **kwargs):
        """The default page, given when we don't recognise where the request is for."""
        Page = "I don't know where you're trying to go, so have a 404 Error."
        cherrypy.response.status = 404
        return Page

    #Default page, prompts the user to log in
    @cherrypy.expose
    def index(self):
        return functions.readHtml("index")
    
    #Login page    
    @cherrypy.expose
    def login(self, ec=None):
        Page = functions.readHtml("login")
        try:
            if (ec == "2"):
                Page += "Your username and/or password was incorrect"
            elif (ec == "3"):
                Page += "You have supplied an incorrect location"
        except:
            pass
        return Page
    
  
    # LOGGING IN AND OUT
    @cherrypy.expose
    def signin(self, username, password, location):
        #Use SHA256 to hash the password
        hashedPW = sha256(password + username).hexdigest()
        #If location = 0, use local IP, otherwise use external ip
        ip = socket.gethostbyname(socket.gethostname())
        splitIP = ip.split(".")
        if (location == "0"):
            data = {'ip':socket.gethostbyname(socket.gethostname())}
        elif (splitIP[0] == "10"):
            location = "4"
        else:
            try:
                data = json.loads(urllib2.urlopen("http://ip.jsontest.com/").read())
            except:
                logging.debug('Not able to retrieve info from the website, http://ip.jsontest.com/')
                #hardcoded values for when the site is down/overloaded
                if (location == "1"):
                    data = {'ip':'202.36.244.33'}
                else:
                    data = {'ip':'121.74.247.219'}
        try:
            r = urllib2.urlopen("http://cs302.pythonanywhere.com/report?username={0}&password={1}&location={2}&ip={3}&port={4}".format(username,hashedPW,location,data['ip'],str(listen_port)), timeout=4)
            string = r.read()
            if (string == '0, User and IP logged'):
                cherrypy.session['username'] = username;
                cherrypy.session['password'] = hashedPW;
                #creating a thread for periodic reports
                global thread
                thread = myThread.MyThread()
                thread.daemon = True
                thread.setURL(username,hashedPW,location,data['ip'],str(listen_port))
                thread.start()
                raise cherrypy.HTTPRedirect('/profile?user={}'.format(username))
            elif (string == '2, Unauthenticated user'):
                raise cherrypy.HTTPRedirect('/login?ec=2')
            elif (string == '3, False IP address or location reported'):
                raise cherrypy.HTTPRedirect('/login?ec=3')
        except socket.timeout, e:
            logging.debug('Request to login server timed out')
            raise cherrypy.HTTPRedirect('/login')
            

	#Manual signout
    @cherrypy.expose
    def logoff(self,username,password):
        """Logs the current user out, expires their session"""
        functions.checkLogged()
        thread.stop()
        try:
            r = urllib2.urlopen("http://cs302.pythonanywhere.com/logoff?username={0}&password={1}".format(username, password), timeout=4)
        except socket.timeout, e:
            logging.debug('Request to login server timed out')
        except urllib2.URLError, e:
            logging.debug('Unable to contact the login server')
        cherrypy.lib.sessions.expire()
        raise cherrypy.HTTPRedirect('/')
	
    #Profile page
    @cherrypy.expose
    def profile(self, user):
        #profile page
        functions.checkLogged()
        #Open and read html file
        Page = functions.readHtml("profile")
        #Get online user list
        Page = functions.getUsers(cherrypy.session['username'], Page)
        data = functions.readUserData(user)
        #Displays user info
        Page += '<img src={} width="400" height="400"><br/>'.format(data[5])
        Page += u"<b>Name: {}</b><br/>".format(data[1])
        Page += u"<b>Position: {}</b><br/>".format(data[2])
        Page += u"<b>Description: {}</b><br/>".format(data[3])
        Page += u"<b>Location: {}</b><br/>".format(data[4])
        if (cherrypy.session['username'] == user):
            #Button for profile editing
            Page += '<form action="/editProfile" method="post" enctype="multipart/form-data">'
            Page += '<input class= "button" type="submit" value="Edit Profile"/></form>'
            #Button to signout
            Page += '<form action="/logoff?username={0}&password={1}" method="post" enctype="multipart/form-data">'.format(cherrypy.session['username'], cherrypy.session['password'])
            Page += '<input class= "button" type="submit" value="Signout"/></form>'
        else:
            Page += '<form action="/profile" method="post" enctype="multipart/form-data">'
            Page += '<button name="user" value="{}" class="button"/>Return to Profile</button></form>'.format(cherrypy.session['username'])
        return Page
		
    #getProfile API
    @cherrypy.expose
    @cherrypy.tools.json_in()
    def getProfile(self):
        dataDict = cherrypy.request.json
        #Gets the user profile of the person logged in
        print dataDict['sender'] + " has tried to retrieve your profile"
        userData = functions.readUserData(dataDict['profile_username'])
        outputData = {"fullname": userData[1], "position": userData[2], "description": userData[3], "location": userData[4], "picture": "http://{0}:{1}{2}".format(userData[6], userData[7], userData[5]), "lastUpdated": userData[8]}
        returnData = json.dumps(outputData)
        return returnData
        

    #Page for the user to edit their profile details
    @cherrypy.expose
    def editProfile(self):
        functions.checkLogged()
        data = functions.readUserData(cherrypy.session['username'])
        Page = functions.readHtml("editProfile")
        return Page.format(data[1], data[2], data[3], data[4])
	
    #Used to update the database with new user info
    @cherrypy.expose
    def writeInfo(self, name=None, position=None, description=None, picture=None, location=None):
        functions.checkLogged()
        if (str(picture.type) != "application/octet-stream"):
            #Get the file type and save a copy of the file to the working directory
            ext = mimetypes.guess_extension(str(picture.type))
            fName = "displaypics/{0}{1}".format(cherrypy.session['username'], ext)
            functions.saveFile(picture, fName)
        #Update your profile details
        db = sqlite3.connect("db/Users.db")
        cursor = db.cursor()
        cursor.execute("UPDATE Profile SET Name = ? WHERE UPI = ? ", (name.partition("<")[0], cherrypy.session['username']))
        cursor.execute("UPDATE Profile SET Position = ? WHERE UPI = ? ", (position.partition("<")[0], cherrypy.session['username']))
        cursor.execute("UPDATE Profile SET Description = ? WHERE UPI = ? ", (description.partition("<")[0], cherrypy.session['username']))
        cursor.execute("UPDATE Profile SET Location = ? WHERE UPI = ? ", (location.partition("<")[0], cherrypy.session['username']))
        if (str(picture.type) != "application/octet-stream"):
            cursor.execute("UPDATE Profile SET Picture = ? WHERE UPI = ? ", ("/static/displaypics/{0}{1}".format(cherrypy.session['username'],ext), cherrypy.session['username']))
        cursor.execute("UPDATE Profile SET stamp = ? WHERE UPI = ? ", (time.time(), cherrypy.session['username']))
        db.commit()
        db.close()
        raise cherrypy.HTTPRedirect('/profile?user={}'.format(cherrypy.session['username']))
		
    #Used to save the profile info retrieved from someone else
    @cherrypy.expose
    def saveInfo(self, UPI):
        functions.checkLogged()
        #Get user info
        data = functions.readUserData(UPI)
        try:
            #Ping recipient
            urllib2.urlopen('http://{0}:{1}/ping?sender={2}'.format(data[6], data[7], cherrypy.session['username']), timeout=10)
            #Create a dictionary with the input parameters to be encoded
            dict = { "sender": cherrypy.session['username'], "profile_username": UPI }
            jsonData = json.dumps(dict)
            try:
                req = urllib2.Request('http://{0}:{1}/getProfile'.format(data[6], data[7]), jsonData, {"Content-Type": 'application/json'})
                response = urllib2.urlopen(req, timeout=4)
                #read the response and decode it to a dictionary
                userData = json.loads(response.read())
                db = sqlite3.connect("db/Users.db")
                cursor = db.cursor()
                #Update user info
                cursor.execute("UPDATE Profile SET Name = ? WHERE UPI = ? ", (userData['fullname'].partition("<")[0], UPI))
                cursor.execute("UPDATE Profile SET Position = ? WHERE UPI = ? ", (userData['position'].partition("<")[0], UPI))
                cursor.execute("UPDATE Profile SET Description = ? WHERE UPI = ? ", (userData['description'].partition("<")[0], UPI))
                cursor.execute("UPDATE Profile SET Location = ? WHERE UPI = ? ", (userData['location'].partition("<")[0], UPI))
                try:
                    if (userData['picture'] == ""):
                        cursor.execute("UPDATE Profile SET Picture = ? WHERE UPI = ? ", ("static/displaypics/anon.png", UPI))
                    else:
                        #Save the picture to the working directory
                        fName = "displaypics/{0}.jpg".format(UPI)
                        f = open(fName,'wb')
                        f.write(urllib2.urlopen(userData['picture']).read())
                        f.close()
                    cursor.execute("UPDATE Profile SET Picture = ? WHERE UPI = ? ", ("static/displaypics/{0}.jpg".format(UPI), UPI))
                except:
                    cursor.execute("UPDATE Profile SET Picture = ? WHERE UPI = ? ", ("static/displaypics/anon.png", UPI))
                db.commit()
                db.close()
                raise cherrypy.HTTPRedirect('/profile?user={}'.format(UPI))
            except urllib2.URLError, e:
                logging.debug('Request to get profile failed')
            except socket.timeout, e:
                logging.debug('Request to get profile timed out')
        #Exceptions for ping
        except socket.timeout, e:
            logging.debug('Ping to recipient timed out')
        except urllib2.URLError, e:
            logging.debug('Request to call ping failed')
        raise cherrypy.HTTPRedirect('/errorPage?ec=3&user={}'.format(UPI))

    #Messaging page. Displays all of the messages between the user and recipient and
    #allows the user to message and send files to online users.
    @cherrypy.expose
    def messaging(self, destination):
        functions.checkLogged()
        #Read the message html
        Page = functions.readHtml("messaginghead").format(cherrypy.session['username'])
        #Get online user list
        Page = functions.getUsers(cherrypy.session['username'], Page)
        db = sqlite3.connect("db/Conversation.db")
        cursor = db.cursor()
        #If it is the first time the user uses messaging, create a new table for that user
        cursor.execute('CREATE TABLE IF NOT EXISTS {}(UPI TEXT NOT NULL, Sender TEXT NOT NULL, Message TEXT NOT NULL, Stamp TEXT NOT NULL, Type TEXT NOT NULL)'.format(cherrypy.session['username']))
        cursor.execute('SELECT * FROM {} WHERE UPI = ?'.format(cherrypy.session['username']), (destination,))
        all_rows = cursor.fetchall()
        Page += '<div id="message-box" class="message-box">'
        for row in all_rows:
            #Display your messages in blue
            if (row[1] == cherrypy.session['username']):
                Page += '<span class="font-color1">'
                Page = functions.formatMessage(row[1], row[2], row[3], row[4], Page)
                Page += '</span>'
            #Display other person's message in red
            else:
                Page = functions.formatMessage(row[1], row[2], row[3], row[4], Page)
        db.close()
        Page += "</div>"
        #User input for message, and the send button
        Page += '<form action="/sendMessage"method="post" enctype="multipart/form-data">'
        Page += 'Message: <input type="text" id="input-box" name="message" required class="message-input"/><button name="destination" value="{0}" class="message-button"/>Send</button></form>'.format(destination)
        Page += '<form action="/sendFile"method="post" enctype="multipart/form-data">'
        Page += '<input type="file" name="fData" id="upload" required><button name="destination" value="{0}" class="message-button"/>Send File</button></form>'.format(destination)
        return Page
		
    #Send Message API. Uses the recieveMessage API to communicate to other nodes
    @cherrypy.expose
    def sendMessage(self, message, destination):
        functions.checkLogged()
		#Check if message is valid
        if (message.strip() == ""):
            raise cherrypy.HTTPRedirect('/messaging?destination={}'.format(destination))
        #Read destination user's data
        data = functions.readUserData(destination)
        try:
            #Ping recipient
            urllib2.urlopen('http://{0}:{1}/ping?sender={2}'.format(data[6], data[7], cherrypy.session['username']), timeout=10)
            #Create a dictionary with the arguments and encode it to JSON
            stamp = time.time()
            dict = { "sender": cherrypy.session['username'], "message": message, "destination": destination, "stamp": stamp }
            jsonData = json.dumps(dict)
            try:
                req = urllib2.Request('http://{0}:{1}/receiveMessage'.format(data[6], data[7]), jsonData, {'Content-Type': 'application/json'})
                response = urllib2.urlopen(req, timeout=4)
                if (response.read() == '0'):
                    #If message was successfully sent, save the message into the database
                    functions.saveMessage(cherrypy.session['username'], destination, cherrypy.session['username'], message, stamp, "string")
                raise cherrypy.HTTPRedirect('/messaging?destination={}'.format(destination))
            #Exceptions for recieveMessage
            except socket.timeout, e:
                logging.debug('Request to recipient timed out(sendMessage)')
            except urllib2.URLError, e:
                logging.debug('Request to call receiveMessage failed')
        #Exceptions for ping
        except socket.timeout, e:
            logging.debug('Ping to recipient timed out')
        except urllib2.URLError, e:
            logging.debug('Request to call ping failed')
        raise cherrypy.HTTPRedirect('/errorPage?ec=2&user={}'.format(destination))
					
    #Recieve Message API. This is called by other nodes that want to send a message to this node
    @cherrypy.expose
    @cherrypy.tools.json_in()
    def receiveMessage(self):
        dataDict = cherrypy.request.json
        db = sqlite3.connect('db/Conversation.db')
        functions.saveMessage(dataDict['destination'], dataDict['sender'], dataDict['sender'], dataDict['message'].partition("<")[0], dataDict['stamp'], "string")
        return '0'
	
	#Send File API. Will only send a message 
    @cherrypy.expose
    def sendFile(self, destination, fData, stamp=None):
        #Read User Data to get ip and port
        data = functions.readUserData(destination)
        try:
            #Ping recipient
            urllib2.urlopen('http://{0}:{1}/ping?sender={2}'.format(data[6], data[7], cherrypy.session['username']))
            #Time
            stamp = time.time()
            #Get the file type and save a copy of the file to the working directory
            ext = mimetypes.guess_extension(str(fData.type))
            if (ext == None):
                ext = ".mp3"
            fName = "files/{0}{1}".format(str(stamp), ext)
            if fData.file:
                outfile = file(fName, 'wb')
                outfile.write(fData.file.read())
                outfile.close()
		    #Read the file and encode it to send
            fileToSend = open(fName, 'rb')
            encodeFile = base64.encodestring(fileToSend.read())
            fileToSend.close()
            dict = {"sender": cherrypy.session['username'], "destination": destination, "file": encodeFile, "filename": "{0}{1}".format(str(stamp), ext), "content_type": str(fData.type), "stamp": stamp}
            jsonData = json.dumps(dict)
            try:
                req = urllib2.Request('http://{0}:{1}/receiveFile'.format(data[6], data[7]), jsonData, {'Content-Type': 'application/json'})
                response = urllib2.urlopen(req)
                if (response.read() == "0"):
                    #If message was successfully sent, save the message into the database
                    functions.saveMessage(cherrypy.session['username'], destination, cherrypy.session['username'], '/static/files/{0}{1}'.format(str(stamp), ext), stamp, "notstring")
                    raise cherrypy.HTTPRedirect('/messaging?destination={}'.format(destination))
            #Exceptions for recieveMessage
            except socket.timeout, e:
                logging.debug('Request to recipient timed out(sendFile)')
            except urllib2.URLError, e:
                logging.debug('Request to call receiveFile failed')
        #Exceptions for ping
        except socket.timeout, e:
            logging.debug('Ping to recipient timed out')
        except urllib2.URLError, e:
            logging.debug('Request to call ping failed')
        raise cherrypy.HTTPRedirect('/errorPage?ec=4&user={}'.format(destination))
		
    #Recieve Message API
    @cherrypy.expose
    @cherrypy.tools.json_in()
    def receiveFile(self):
        #sender,destination,file,filename,content_type,stamp,
        dataDict = cherrypy.request.json
        #Save the file to the working directory
        encodedData = base64.decodestring(dataDict['file'])
        result = open('files/{}'.format(dataDict['filename']), 'wb')
        result.write(encodedData)
        result.close()
        #Save the sent file directory in the database
        functions.saveMessage(dataDict['destination'], dataDict['sender'], dataDict['sender'], '/static/files/{}'.format(dataDict['filename']), dataDict['stamp'], "notstring")
        return '0'
	
    #Ping API
    @cherrypy.expose
    def ping(self, sender):
        return '0'
	
	#Page to display when trying to access particular pages while not logged in
    @cherrypy.expose
    def errorPage(self, ec, user=None):
        Page = ""
        if (ec == '1'):	
            Page += "You must login first.<br/>"
            Page += "Click here to <a href='login'>login</a>."
        elif (ec == '2'):
            Page += "Failed to send message.<br/>"
            Page += "Click here to <a href='messaging?destination={}'>return to the conversation</a>.".format(user)
        elif (ec == '3'):
            Page += "Failed to retrieve profile.<br/>"
            Page += "Click here to <a href='profile?user={}'>view their old profile</a>.".format(user)
        elif (ec == '4'):
            Page += "Failed to send File.<br/>"
            Page += "Click here to <a href='messaging?destination={}'>return to the conversation</a>.".format(user)
        return Page
		
          
def runMainApp():
    # Create an instance of MainApp and tell Cherrypy to send all requests under / to it. (ie all of them)
    conf={
		'/static' : {
					'tools.staticdir.on'  : True,
					'tools.staticdir.dir' : os.getcwd()
					
				}
    }
    cherrypy.tree.mount(MainApp(), "/", conf)
    logging.basicConfig(filename='Log.log',level=logging.DEBUG)

    # Tell Cherrypy to listen for connections on the configured address and port.
    cherrypy.config.update({'server.socket_host': listen_ip,
                            'server.socket_port': listen_port,
                            'engine.autoreload.on': True,
                           })

    print "========================="
    print "University of Auckland"     "COMPSYS302 - Software Design Application"
    print "========================================"                       
    
    # Start the web server
    cherrypy.engine.start()

    # And stop doing anything else. Let the web server take over.
    cherrypy.engine.block()


#Run the function to start everything
runMainApp()
