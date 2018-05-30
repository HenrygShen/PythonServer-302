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
from threading import Event
import myThread
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
        return self.readHtml("index")
    
    #Login page    
    @cherrypy.expose
    def login(self):
        return self.readHtml("login")
    
  
    # LOGGING IN AND OUT
    @cherrypy.expose
    def signin(self, username, password, location):
        """Check their name and password and send them either to the main page, or back to the main login screen."""
        hashedPW = sha256(password + username).hexdigest()
        try:
            data = json.loads(urllib2.urlopen("http://ip.jsontest.com/").read())
        except:
            #home = {'ip':'121.74.247.219'}
            #uni wifi = {'ip':'202.36.244.33'}
            data = {'ip':'121.74.247.219'}
        #If location = 0, use local IP, location = 2, use external ip
        #socket.gethostbyname(socket.gethostname())
        r = urllib2.urlopen("http://cs302.pythonanywhere.com/report?username=" + username + "&password=" + hashedPW + "&location=" + location + "&ip=" + data['ip'] + "&port=" + str(listen_port))
        string = r.read()
        if (string == '0, User and IP logged'):
            cherrypy.session['username'] = username;
            cherrypy.session['password'] = hashedPW;
            #creating a thread for periodic reports
            global thread
            thread = myThread.MyThread()
            thread.setURL(username,hashedPW,location,data['ip'],str(listen_port))
            thread.start()
            raise cherrypy.HTTPRedirect('/profile?user=' + username)
        elif (string == '2, Unauthenticated user'):
            raise cherrypy.HTTPRedirect('/login')

	#Manual signout
    @cherrypy.expose
    def signout(self):
        """Logs the current user out, expires their session"""
        self.checkLogged()
        thread.stop()
        r = urllib2.urlopen("http://cs302.pythonanywhere.com/logoff?username=" + cherrypy.session['username'] + "&password=" + cherrypy.session['password'])
        cherrypy.lib.sessions.expire()
        raise cherrypy.HTTPRedirect('/')
	
    #Profile page
    @cherrypy.expose
    def profile(self, user):
        #profile page
        self.checkLogged()
        data = self.readUserData(user)
        #Open and read html file
        Page = self.readHtml("profile")
        #Displays user info
        Page += "<img src='/static/files/potato.jpg' alt='potato' width='400' height='400'><br/>"
        Page += "<b>Name: " + data[1] + "</b><br/>"
        Page += "<b>Position: " + data[2] + "</b><br/>"
        Page += "<b>Description: " + data[3] + "</b><br/>"
        Page += "<b>Location: " + data[4] + "</b><br/>"
        #Button for Displaying online users
        Page += '<form action="/getUsers" method="post" enctype="multipart/form-data">'
        Page += '<input class= "button" type="submit" value="Display Online Users"/></form>'
        if (cherrypy.session['username'] == user):
            #TODO: make profile editing secure
            #Button for profile editing
            Page += '<form action="/editProfile" method="post" enctype="multipart/form-data">'
            Page += '<input class= "button" type="submit" value="Edit Profile"/></form>'
            #Button to signout
            Page += '<form action="/signout" method="post" enctype="multipart/form-data">'
            Page += '<input class= "button" type="submit" value="Signout"/></form>'
        return Page
		
    #getProfile API
    @cherrypy.expose
    @cherrypy.tools.json_in()
    def getProfile(self):
        dataDict = cherrypy.request.json
        #hardcoded UPI
        if ("hshe440" == dataDict['profile_username']):
            print dataDict['sender'] + " has tried to retrieve your profile"
            userData = self.readUserData(dataDict['profile_username'])
            outputData = {"lastUpdated": userData[8], "fullname": userData[1], "position": userData[2], "description": userData[3], "location": userData[4], "picture": userData[5]}
            returnData = json.dumps(outputData)
            return returnData
        else:
            return 'Failed'
        

    #Page for the user to edit their profile details
    @cherrypy.expose
    def editProfile(self):
        self.checkLogged()
        data = self.readUserData(cherrypy.session['username'])
        Page = self.readHtml("editProfile")
        return Page.format(data[1], data[2], data[3], data[4])
	
	#Used to update the database with new user info
    @cherrypy.expose
    def writeInfo(self, name=None, position=None, description=None, picture=None, location=None):
        self.checkLogged()
        db = sqlite3.connect("db/Users.db")
        cursor = db.cursor()
        cursor.execute("UPDATE Profile SET Name = ? WHERE UPI = ? ", (name, cherrypy.session['username']))
        cursor.execute("UPDATE Profile SET Position = ? WHERE UPI = ? ", (position, cherrypy.session['username']))
        cursor.execute("UPDATE Profile SET Description = ? WHERE UPI = ? ", (description, cherrypy.session['username']))
        cursor.execute("UPDATE Profile SET Location = ? WHERE UPI = ? ", (location, cherrypy.session['username']))
        #cursor.execute("UPDATE Profile SET Picture = ? WHERE UPI = ? ", (picture, cherrypy.session['username']))
        cursor.execute("UPDATE Profile SET stamp = ? WHERE UPI = ? ", (time.time(), cherrypy.session['username']))
        img = open('files/hshe440.jpg', 'wb')
        img = picture.read_into_file(fp_out=None)
        img.close()
        db.commit()
        db.close()
        raise cherrypy.HTTPRedirect('/profile?user=' + cherrypy.session['username'])
		
    #Used to save the profile info retrieved from someone else
    @cherrypy.expose
    def saveInfo(self, UPI):
        self.checkLogged()
        #Get user info
        data = self.readUserData(UPI)
        #Create a dictionary with the input parameters to be encoded
        dict = { "sender": cherrypy.session['username'], "profile_username": UPI }
        jsonData = json.dumps(dict)
        req = urllib2.Request('http://' + data[6] + ':' + data[7] + '/getProfile', jsonData, {"Content-Type": 'application/json'})
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
        raise cherrypy.HTTPRedirect('/profile?user=' + UPI)
        #except:       
        #    raise cherrypy.HTTPRedirect('/getUsers')

    #Temp messaging page(Still not sure what to do here)
    @cherrypy.expose
    def messaging(self, destination):
        self.checkLogged()
        Page = self.readHtml("messaginghead")
        db = sqlite3.connect("db/Conversation.db")
        cursor = db.cursor()
        #If it is the first time the user uses messaging, create a new table for that user
        cursor.execute('CREATE TABLE IF NOT EXISTS ' + cherrypy.session['username'] + '(UPI TEXT NOT NULL, Sender TEXT NOT NULL, Message TEXT NOT NULL, Stamp TEXT NOT NULL)')
        cursor.execute("SELECT * FROM " + cherrypy.session['username'] + " WHERE UPI='" + destination + "'")
        all_rows = cursor.fetchall()
        for row in all_rows:
            if (row[1] == cherrypy.session['username']):
                Page += '<span class="font-color1">'
                if (row[4] == "notstring"):
                    Page += '{0}<br/>{1} :<br/> <img src="{2}" width="200" height="200"><br/>'.format(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(row[3]))), row[1], row[2])
                else:
                    Page += '{0}<br/>{1} : {2}<br/>'.format(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(row[3]))), row[1], row[2])
                Page += '</span>'
            else:
                if (row[4] == "notstring"):
                    Page += '{0}<br/>{1} :<br/> <img src="{2}" width="200" height="200"><br/>'.format(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(row[3]))), row[1], row[2])
                else:
                    Page += '{0}<br/>{1} : {2}<br/>'.format(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(row[3]))), row[1], row[2])
        db.close()
        Page += "</div>"
        #User input for message, and the send button
        Page += '<form action="/sendMessage"method="post" enctype="multipart/form-data">'
        Page += 'Message: <input type="text" size="75" name="message"/><button name="destination" value="' + destination +'" class="message-button"/>Send</button></form>'
        Page += '<form action="/sendFile"method="post" enctype="multipart/form-data">'
        Page += '<input type="file" name="filePath" id="upload"><button name="destination" value="'+ destination +'" class="message-button"/>Send File</button></form>'
        return Page
		
    #Send Message API
    @cherrypy.expose
    def sendMessage(self, message, destination):
        self.checkLogged()
		#Check if message is valid
        if (message.strip() == ""):
            raise cherrypy.HTTPRedirect('/messaging?destination=' + destination)
        #Read destination user's data
        data = self.readUserData(destination)
        #Ping recipient
        if (urllib2.urlopen('http://' + data[6] + ':' + data[7] + '/ping?sender=' + cherrypy.session['username']).read() == '0'):
            #Create a dictionary with the arguments and encode it to JSON
            stamp = time.time()
            dict = { "sender": cherrypy.session['username'], "message": message, "destination": destination, "stamp": stamp }
            jsonData = json.dumps(dict)
            req = urllib2.Request('http://' + data[6] + ':' + data[7] + '/receiveMessage', jsonData, {'Content-Type': 'application/json'})
            response = urllib2.urlopen(req)
            if (response.read() == '0'):
                #If message was successfully sent, save the message into the database
                self.saveMessage(cherrypy.session['username'], destination, cherrypy.session['username'], message, stamp, "string")
                raise cherrypy.HTTPRedirect('/messaging?destination=' + destination)
            else:
                return response.read() + ",IT DIDN'T WORK"
					
    #Recieve Message API
    @cherrypy.expose
    @cherrypy.tools.json_in()
    def receiveMessage(self):
        dataDict = cherrypy.request.json
        db = sqlite3.connect('db/Conversation.db')
        self.saveMessage(dataDict['destination'], dataDict['sender'], dataDict['sender'], dataDict['message'], dataDict['stamp'], "string")
        return '0'
	
	
    @cherrypy.expose
    def sendFile(self, destination, filePath, filename=None, stamp=None):
        print filePath
        #How the heck do you get the filepath
        data = self.readUserData(destination)
        fileToSend = open('files/potato.jpg', 'rb')
        fileRead = fileToSend.read()
        encodeFile = base64.encodestring(fileRead)
        type = mimetypes.guess_type("potato.jpg",strict = True)
        stamp = time.time()
        dict = {"sender": cherrypy.session['username'], "destination": destination, "file": encodeFile, "filename": "potato.jpg", "content_type": type, "stamp": stamp}
        jsonData = json.dumps(dict)
        req = urllib2.Request('http://' + data[6] + ':' + data[7] + '/receiveFile', jsonData, {'Content-Type': 'application/json'})
        response = urllib2.urlopen(req)
        if (response.read() == '0'):
            #If message was successfully sent, save the message into the database
            self.saveMessage(cherrypy.session['username'], destination, cherrypy.session['username'], '/static/files/potato.jpg', stamp, "notstring")
            raise cherrypy.HTTPRedirect('/messaging?destination=' + destination)
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
        result = open('files/' + dataDict['filename'], 'wb')
        result.write(encodedData)
        result.close()
        self.saveMessage(dataDict['destination'], dataDict['sender'], dataDict['sender'], '/static/files/' + dataDict['filename'], dataDict['stamp'], "notstring")
        return '0'
	
    #Ping API
    @cherrypy.expose
    def ping(self, sender):
        return '0'
    
    #Gets the list of online users
    @cherrypy.expose
    def getUsers(self):
        self.checkLogged()
        data = urllib2.urlopen("http://cs302.pythonanywhere.com/getList?username=" + cherrypy.session['username'] + "&password=" + cherrypy.session['password'] + "&enc=0&json=1").read()
        dict = json.loads(data)
        Page = self.readHtml("onlineUsers")
        db = sqlite3.connect("db/Users.db")
        cursor = db.cursor()
        for id, info in dict.items():
            # Check if the user does not exist and create it
            try:
                cursor.execute('INSERT INTO Profile(UPI, Name, Position, Description, Location, Picture, IP, Port) VALUES(?,?,?,?,?,?,?,?)', (info['username'],"","","","","","",""))
            except:
                pass
            #Update IP Address
            cursor.execute('UPDATE Profile SET IP = ? WHERE UPI = ?', (info['ip'], info['username']))
            cursor.execute('UPDATE Profile SET Port = ? WHERE UPI = ?', (info['port'], info['username']))
            if (info['username'] != cherrypy.session['username']):
                Page += info['username'] + "<br/>"
                #Button for viewing an online user's profile
                Page += '<form action="/saveInfo" method="post" enctype="multipart/form-data">'
                Page += '<button name="UPI" value="' + info['username'] + '" class="button"/>View Profile</button></form>'
                #Button for messaging an online user
                Page += '<form action="/messaging" method="post" enctype="multipart/form-data">'
                Page += '<button name="destination" value="' + info['username'] + '" class="button"/>Message</button></form>'
        db.commit()
        db.close()
        return Page
	
	#Page to display when trying to access particular pages while not logged in
    @cherrypy.expose
    def errorPage(self):
        Page = "You must login first.<br/>"
        Page += "Click here to <a href='login'>login</a>."
        return Page
    
    #Called to make sure you are logged in before being able to do anything which requires authentication e.g. profile editing or messaging
    def checkLogged(self):
        try:
            username = cherrypy.session['username']
            password = cherrypy.session['password']
        except KeyError: #No logged in user
            raise cherrypy.HTTPRedirect('/errorPage')
        return
    
    #Read user data stored in the database
    def readUserData(self, user):
        #Opening database and reading user info
        db = sqlite3.connect("db/Users.db")
        c = db.cursor()
        c.execute('SELECT * FROM Profile WHERE UPI="' + user + '"')
        #User info stored into a tuple, row
        row = c.fetchone()
        #Close db
        db.close()
        return row

    #Opening Html files to return to the page		
    def readHtml(self, html):
        #Open and read html file
        file = open("html/" + html + ".html", "r")
        Page = file.read()
        file.close()
        return Page
		
    #Opening Html files to return to the page		
    def browseFile(self):
        #Something for file browsing idk
        Tk().withdraw()
        filename = askopenfilename() # show an "Open" dialog box and return the path to the selected file
        print(filename)
		
    #Writing message to the db
    def saveMessage(self, user, UPI, sender, message, stamp, type):
        db = sqlite3.connect("db/Conversation.db")
        cursor = db.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS ' + user + '(UPI TEXT, Sender TEXT, Message TEXT, Stamp TEXT, Type TEXT)')
        cursor.execute('INSERT INTO ' + user + '(UPI, SENDER, Message, Stamp, Type) VALUES (?,?,?,?,?)', (UPI, sender, message, stamp, type))
        db.commit()
        db.close()
        return '0'
		
    def myFunction(self):
        Tkinter.Tk().withdraw() # Close the root window
        in_path = tkFileDialog.askopenfilename()
        print in_path

		

          
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
