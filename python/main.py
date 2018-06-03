#!/usr/bin/python
""" main.py

    COMPSYS302 - Software Design
    Author: Henry Shen (hshe440@aucklanduni.ac.nz)
    Last Edited: 19/02/2018

    This program uses the CherryPy web server (from www.cherrypy.org).
"""
# Requires:  CherryPy 3.2.2  (www.cherrypy.org)
#            Python  (We use 2.7)

# The address we listen for connections on
listen_ip = "0.0.0.0"
listen_port = 10010
#data = urllib2.urlopen(req,timeout= 4).read()
#except URLError,exception:
#if isinstance()
import os
import cherrypy
import json
import urllib2
import sqlite3
import base64
import mimetypes
import time
import socket
from itertools import cycle, izip
from threading import Event
import myThread
import functions
from hashlib import sha256
from Tkinter import Tk
from tkFileDialog import askopenfilename

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

    # PAGES (which return HTML that can be viewed in browser)
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
        if (location == "0"):
            data = {'ip':socket.gethostbyname(socket.gethostname())}
        else:
            try:
                data = json.loads(urllib2.urlopen("http://ip.jsontest.com/").read())
            except:
			    #hardcoded values for when the site is down/overloaded
                if (location == "1"):
                    data = {'ip':'202.36.244.33'}
                else:
                    data = {'ip':'121.74.247.219'}
        r = urllib2.urlopen("http://cs302.pythonanywhere.com/report?username={0}&password={1}&location={2}&ip={3}&port={4}".format(username,hashedPW,location,data['ip'],str(listen_port)))
        string = r.read()
        if (string == '0, User and IP logged'):
            cherrypy.session['username'] = username;
            cherrypy.session['password'] = hashedPW;
            #creating a thread for periodic reports
            global thread
            thread = myThread.MyThread()
            thread.setURL(username,hashedPW,location,data['ip'],str(listen_port))
            thread.start()
            raise cherrypy.HTTPRedirect('/profile?user={}'.format(username))
        elif (string == '2, Unauthenticated user'):
            raise cherrypy.HTTPRedirect('/login?ec=2')
        elif (string == '3, False IP address or location reported'):
            raise cherrypy.HTTPRedirect('/login?ec=3')
            

	#Manual signout
    @cherrypy.expose
    def signout(self,username,password):
        """Logs the current user out, expires their session"""
        functions.checkLogged()
        thread.stop()
        r = urllib2.urlopen("http://cs302.pythonanywhere.com/logoff?username={0}&password={1}".format(username, password))
        cherrypy.lib.sessions.expire()
        raise cherrypy.HTTPRedirect('/')
	
    #Profile page
    @cherrypy.expose
    def profile(self, user):
        #profile page
        functions.checkLogged()
        data = functions.readUserData(user)
        #Open and read html file
        Page = functions.readHtml("profile")
        #Get online user list
        Page = functions.getUsers(cherrypy.session['username'], Page)
        #Displays user info
        Page += "<img src='/static/files/potato.jpg' alt='potato' width='400' height='400'><br/>"
        Page += "<b>Name: {}</b><br/>".format(data[1])
        Page += "<b>Position: {}</b><br/>".format(data[2])
        Page += "<b>Description: {}</b><br/>".format(data[3])
        Page += "<b>Location: {}</b><br/>".format(data[4])
        if (cherrypy.session['username'] == user):
            #TODO: make profile editing secure
            #Button for profile editing
            Page += '<form action="/editProfile" method="post" enctype="multipart/form-data">'
            Page += '<input class= "button" type="submit" value="Edit Profile"/></form>'
        #Button to signout
        Page += '<form action="/signout?username={0}&password={1}" method="post" enctype="multipart/form-data">'.format(cherrypy.session['username'], cherrypy.session['password'])
        Page += '<input class= "button" type="submit" value="Signout"/></form>'
        return Page
		
    #getProfile API
    @cherrypy.expose
    @cherrypy.tools.json_in()
    def getProfile(self):
        dataDict = cherrypy.request.json
        #Gets the user profile of the person logged in
        if (cherrypy.session['username'] == dataDict['profile_username']):
            print dataDict['sender'] + " has tried to retrieve your profile"
            userData = functions.readUserData(dataDict['profile_username'])
            outputData = {"fullname": userData[1], "position": userData[2], "description": userData[3], "location": userData[4], "lastUpdated": userData[8]}
            returnData = json.dumps(outputData)
            return returnData
        else:
            return 'Failed'
        

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
        db = sqlite3.connect("db/Users.db")
        cursor = db.cursor()
        cursor.execute("UPDATE Profile SET Name = ? WHERE UPI = ? ", (name, cherrypy.session['username']))
        cursor.execute("UPDATE Profile SET Position = ? WHERE UPI = ? ", (position, cherrypy.session['username']))
        cursor.execute("UPDATE Profile SET Description = ? WHERE UPI = ? ", (description, cherrypy.session['username']))
        cursor.execute("UPDATE Profile SET Location = ? WHERE UPI = ? ", (location, cherrypy.session['username']))
        #cursor.execute("UPDATE Profile SET Picture = ? WHERE UPI = ? ", (picture, cherrypy.session['username']))
        cursor.execute("UPDATE Profile SET stamp = ? WHERE UPI = ? ", (time.time(), cherrypy.session['username']))
        print picture.files[0]
        fileData = picture.read()
        #encodedData = base64.decodestring(fileData)
        #img = open('files/hshe440.jpg', 'w')
        #img = img.write(fileData)
        #img.close()
        db.commit()
        db.close()
        raise cherrypy.HTTPRedirect('/profile?user={}'.format(cherrypy.session['username']))
		
    #Used to save the profile info retrieved from someone else
    @cherrypy.expose
    def saveInfo(self, UPI):
        functions.checkLogged()
        #Get user info
        data = functions.readUserData(UPI)
        #Create a dictionary with the input parameters to be encoded
        dict = { "sender": cherrypy.session['username'], "profile_username": UPI }
        jsonData = json.dumps(dict)
        req = urllib2.Request('http://{0}:{1}/getProfile'.format(data[6], data[7]), jsonData, {"Content-Type": 'application/json'})
        response = urllib2.urlopen(req)
        #read the response and decode it to a dictionary
        userData = json.loads(response.read())
        db = sqlite3.connect("db/Users.db")
        cursor = db.cursor()
        cursor.execute("UPDATE Profile SET Name = ? WHERE UPI = ? ", (userData['fullname'], UPI))
        cursor.execute("UPDATE Profile SET Position = ? WHERE UPI = ? ", (userData['position'], UPI))
        cursor.execute("UPDATE Profile SET Description = ? WHERE UPI = ? ", (userData['description'], UPI))
        cursor.execute("UPDATE Profile SET Location = ? WHERE UPI = ? ", (userData['location'], UPI))
        #cursor.execute("UPDATE Profile SET Picture = ? WHERE UPI = ? ", (userData['picture'], UPI))
        db.commit()
        db.close()
        raise cherrypy.HTTPRedirect('/profile?user={}'.format(UPI))
        #except:       
        #    raise cherrypy.HTTPRedirect('/getUsers')

    #Temp messaging page(Still not sure what to do here)
    @cherrypy.expose
    def messaging(self, destination):
        functions.checkLogged()
        #Read the message html
        Page = functions.readHtml("messaginghead")
        #Get online user list
        Page = functions.getUsers(cherrypy.session['username'], Page)
        db = sqlite3.connect("db/Conversation.db")
        cursor = db.cursor()
        #If it is the first time the user uses messaging, create a new table for that user
        cursor.execute('CREATE TABLE IF NOT EXISTS {}(UPI TEXT NOT NULL, Sender TEXT NOT NULL, Message TEXT NOT NULL, Stamp TEXT NOT NULL, Type TEXT NOT NULL)'.format(cherrypy.session['username']))
        cursor.execute('SELECT * FROM {} WHERE UPI = ?'.format(cherrypy.session['username']), (destination,))
        all_rows = cursor.fetchall()
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
        Page += 'Message: <input type="text" class="message-input" name="message"/><button name="destination" value="{}" class="message-button"/>Send</button></form>'.format(destination)
        Page += '<form action="/sendFile"method="post" enctype="multipart/form-data">'
        Page += '<input type="file" name="filePath" id="upload"><button name="destination" value="{}" class="message-button"/>Send File</button></form>'.format(destination)
        Page += '<form action="/profile?user={}" method="post" enctype="multipart/form-data">'.format(cherrypy.session['username'])
        Page += '<input type="submit" value="Back to Profile" class="button button-pos"/></form>'
        return Page
		
    #Send Message API
    @cherrypy.expose
    def sendMessage(self, message, destination):
        functions.checkLogged()
		#Check if message is valid
        if (message.strip() == ""):
            raise cherrypy.HTTPRedirect('/messaging?destination={}'.format(destination))
        #Read destination user's data
        data = functions.readUserData(destination)
        #Ping recipient
        if (urllib2.urlopen('http://{0}:{1}/ping?sender={2}'.format(data[6], data[7], cherrypy.session['username'])).read() == '0'):
            #Create a dictionary with the arguments and encode it to JSON
            stamp = time.time()
            dict = { "sender": cherrypy.session['username'], "message": message, "destination": destination, "stamp": stamp }
            jsonData = json.dumps(dict)
            req = urllib2.Request('http://{0}:{1}/receiveMessage'.format(data[6], data[7]), jsonData, {'Content-Type': 'application/json'})
            response = urllib2.urlopen(req)
            if (response.read() == '0'):
                #If message was successfully sent, save the message into the database
                functions.saveMessage(cherrypy.session['username'], destination, cherrypy.session['username'], message, stamp, "string")
                raise cherrypy.HTTPRedirect('/messaging?destination={}'.format(destination))
            else:
                return response.read() + ",IT DIDN'T WORK"
					
    #Recieve Message API
    @cherrypy.expose
    @cherrypy.tools.json_in()
    def receiveMessage(self):
        dataDict = cherrypy.request.json
        db = sqlite3.connect('db/Conversation.db')
        functions.saveMessage(dataDict['destination'], dataDict['sender'], dataDict['sender'], dataDict['message'], dataDict['stamp'], "string")
        return '0'
	
	
    @cherrypy.expose
    def sendFile(self, destination, filePath, filename=None, stamp=None):
        print filePath
        #How the heck do you get the filepath
        data = functions.readUserData(destination)
        fileToSend = open('files/123.mp3', 'rb')
        fileRead = fileToSend.read()
        encodeFile = base64.encodestring(fileRead)
        type = mimetypes.guess_type("123.mp3",strict = True)
        stamp = time.time()
        dict = {"sender": cherrypy.session['username'], "destination": destination, "file": encodeFile, "filename": "123.mp3", "content_type": type, "stamp": stamp}
        jsonData = json.dumps(dict)
        req = urllib2.Request('http://{0}:{1}/receiveFile'.format(data[6], data[7]), jsonData, {'Content-Type': 'application/json'})
        response = urllib2.urlopen(req)
        if (response.read() == '0'):
            #If message was successfully sent, save the message into the database
            functions.saveMessage(cherrypy.session['username'], destination, cherrypy.session['username'], '/static/files/123.mp3', stamp, "notstring")
            raise cherrypy.HTTPRedirect('/messaging?destination={}'.format(destination))
        else:
            return response.read() + ",IT DIDN'T WORK"
		
    #Recieve Message API
    @cherrypy.expose
    @cherrypy.tools.json_in()
    def receiveFile(self):
        #sender,destination,file,filename,content_type,stamp,
        dataDict = cherrypy.request.json
        #Need to limit it to 5MB
        #Need to save the sent file directory in the database
        encodedData = base64.decodestring(dataDict['file'])
        result = open('files/{}'.format(dataDict['filename']), 'wb')
        result.write(encodedData)
        result.close()
        functions.saveMessage(dataDict['destination'], dataDict['sender'], dataDict['sender'], '/static/files/{}'.format(dataDict['filename']), dataDict['stamp'], "notstring")
        return '0'
	
    #Ping API
    @cherrypy.expose
    def ping(self, sender):
        return '0'
	
	#Page to display when trying to access particular pages while not logged in
    @cherrypy.expose
    def errorPage(self):
        Page = "You must login first.<br/>"
        Page += "Click here to <a href='login'>login</a>."
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
