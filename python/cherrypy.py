#!/usr/bin/python
""" cherrypy_example.py

    COMPSYS302 - Software Design
    Author: Andrew Chen (andrew.chen@auckland.ac.nz)
    Last Edited: 19/02/2018

    This program uses the CherryPy web server (from www.cherrypy.org).
"""
# Requires:  CherryPy 3.2.2  (www.cherrypy.org)
#            Python  (We use 2.7)

# The address we listen for connections on
listen_ip = "0.0.0.0"
listen_port = 15010

import os
import cherrypy
import json
import urllib2
import sqlite3
import time
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
        data = json.loads(urllib2.urlopen("http://ip.jsontest.com/").read())
        #If location = 0, use local IP, location = 2, use external ip
        #socket.gethostbyname(socket.gethostname())
        r = urllib2.urlopen("http://cs302.pythonanywhere.com/report?username=" + username + "&password=" + hashedPW + "&location=" + location + "&ip=" + data['ip'] + "&port=" + str(listen_port))
        string = r.read()
        if (string == '0, User and IP logged'):
            cherrypy.session['username'] = username;
            cherrypy.session['password'] = hashedPW;
            raise cherrypy.HTTPRedirect('/profile')
        elif (string == '2, Unauthenticated user'):
            raise cherrypy.HTTPRedirect('/login')

	#Manual signout
    @cherrypy.expose
    def signout(self):
        """Logs the current user out, expires their session"""
        self.checkLogged()
        r = urllib2.urlopen("http://cs302.pythonanywhere.com/logoff?username=" + cherrypy.session['username'] + "&password=" + cherrypy.session['password'])
        cherrypy.lib.sessions.expire()
        raise cherrypy.HTTPRedirect('/')
	
    #Profile page
    @cherrypy.expose
    def profile(self):
        #profile page
        self.checkLogged()
        data = self.readUserData(cherrypy.session['username'])
        #Open and read html file
        file = open("html/profile.html", "r")
        Page = file.read()
        file.close()
        #Displays user info
        Page += "<b style='color:tomato'>Name: " + str(data[1]) + "</b><br/>"
        Page += "<b style='color:tomato'>Position: " + str(data[2]) + "</b><br/>"
        Page += "<b style='color:tomato'>Description: " + str(data[3]) + "</b><br/>"
        Page += "<b style='color:tomato'>Location: " + str(data[4]) + "</b><br/>"
        #Button for Displaying online users
        Page += '<form action="/getUsers" method="post" enctype="multipart/form-data">'
        Page += '<input class= "button" type="submit" value="Display Online Users"/></form>'
        #Button for profile editing
        Page += '<form action="/editProfile" method="post" enctype="multipart/form-data">'
        Page += '<input class= "button" type="submit" value="Edit Profile"/></form>'
        #Button to signout
        Page += '<form action="/signout" method="post" enctype="multipart/form-data">'
        Page += '<input class= "button" type="submit" value="Signout"/></form>'
        Page += '<button class="button" type="button" onclick="myFunction()">Send</button>'
        return Page

    #Page for the user to edit their profile details
    @cherrypy.expose
    def editProfile(self):
        self.checkLogged()
        data = self.readUserData(cherrypy.session['username'])
        Page = '<form action="/writeInfo" method="post" enctype="multipart/form-data">'
        Page += 'Name: <input type="text" value="' + str(data[0]) + '" name="name"/><br/>'
        Page += 'Position: <input type="text" value="' + str(data[1]) + '" name="position"/><br/>'
        Page += 'Description: <input type="text" value="' + str(data[2]) + '" name="description"/><br/>'
        Page += 'Location: <input type="text" value="' + str(data[3]) + '" name="location"/><br/>'
        Page += '<input type="submit" value="Save"/></form>'
        return Page
	
	#Used to update the database with new user info
    @cherrypy.expose
    def writeInfo(self, name=None, position=None, description=None, location=None):
        self.checkLogged()
        db = sqlite3.connect("db/Users.db")
        cursor = db.cursor()
        cursor.execute("UPDATE Profile SET Name = ? WHERE UPI = ? ", (name, cherrypy.session['username']))
        cursor.execute("UPDATE Profile SET Position = ? WHERE UPI = ? ", (position, cherrypy.session['username']))
        cursor.execute("UPDATE Profile SET Description = ? WHERE UPI = ? ", (description, cherrypy.session['username']))
        cursor.execute("UPDATE Profile SET Location = ? WHERE UPI = ? ", (location, cherrypy.session['username']))
        db.commit()
        db.close()
        raise cherrypy.HTTPRedirect('/profile')

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
            # row[0] returns the first column in the query (name), row[1] returns email column.
            Page += '{0} : {1}<br/> {2}<br/>'.format(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(row[3]))), row[1], row[2])
        db.close()
        Page += "</div>"
        Page += '<form action="/sendMessage?destination=' + destination + '" method="post" enctype="multipart/form-data">'
        Page += '<p class="font-color">Message: <input type="text" size="75" name="message"/><input type="submit" value="Send" class="message-button"/></form></p>'
        return Page
		
    #Send Message API
    @cherrypy.expose
    def sendMessage(self, message = None, destination = None):
        self.checkLogged()
        #Read destination user's data
        data = self.readUserData(destination)
        try:
            #Ping recipient
            if (urllib2.urlopen('http://' + data[6] + ':' + data[7] + '/ping?sender=' + cherrypy.session['username']).read() == '0'):
                #Create a dictionary with the arguments and encode it to JSON
                dict = { "sender": cherrypy.session['username'], "message": message, "destination": destination, "stamp": str(time.time()) }
                jsonData = json.dumps(dict)
                req = urllib2.Request('http://' + data[6] + ':' + data[7] + '/receiveMessage', jsonData, {"Content-Type": 'application/json'})
                response = urllib2.urlopen(req)
                if (response.read() == '0'):
                    #If message was successfully sent, save the message into the database
                    self.saveMessage(cherrypy.session['username'], destination, cherrypy.session['username'], message, time.time())
                    raise cherrypy.HTTPRedirect('/sendMessage')
                else:
                    return response.read() + ",IT DIDN'T WORK"
        except:
            return "SOMETHING WENT WRONG"
		
    #Recieve Message API
    @cherrypy.expose
    @cherrypy.tools.json_in()
    def receiveMessage(self):
        dataDict = cherrypy.request.json
        db = sqlite3.connect('db/Conversation.db')
        self.saveMessage(dataDict['destination'], dataDict['sender'], dataDict['sender'], dataDict['message'], dataDict['stamp'])
        return '0'
	
    #Ping API
    @cherrypy.expose
    def ping(self, sender):
        return '0'
    
    #Gets the list of online users
    @cherrypy.expose
    def getUsers(self):
        self.checkLogged()
        r = urllib2.urlopen("http://cs302.pythonanywhere.com/getList?username=" + cherrypy.session['username'] + "&password=" + cherrypy.session['password'] + "&enc=0&json=1")
        html = r.read()
        dict = json.loads(html)
        Page = ""
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
                #Button for messaging an online user
                Page += '<form action="/messaging?destination=' + info['username'] + '" method="post" enctype="multipart/form-data"><br/>'
                Page += '<input type="submit" value="Message"/></form>'
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
        self.checkLogged()
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
		
    #Writing message to the db
    def saveMessage(self, user, UPI, sender, message, stamp):
        db = sqlite3.connect("db/Conversation.db")
        cursor = db.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS ' + user + '(UPI TEXT NOT NULL, Sender TEXT NOT NULL, Message TEXT NOT NULL, Stamp TEXT NOT NULL)')
        cursor.execute('INSERT INTO ' + user + '(UPI, SENDER, Message, Stamp) VALUES (?,?,?,?)', (UPI, sender, message, stamp))
        db.commit()
        db.close()
        return '0'

          
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
    print "University of Auckland"
    print "COMPSYS302 - Software Design Application"
    print "========================================"                       
    
    # Start the web server
    cherrypy.engine.start()

    # And stop doing anything else. Let the web server take over.
    cherrypy.engine.block()
 
#Run the function to start everything
runMainApp()
