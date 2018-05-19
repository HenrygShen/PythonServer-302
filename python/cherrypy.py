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
listen_port = 1234

import os
import cherrypy
import json
import urllib2
import sqlite3
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
        Page = "Welcome! This is a test website for COMPSYS302!<br/>"
        Page += "Click here to <a href='login'>login</a>."
        return Page
        
    @cherrypy.expose
    def login(self, bool=0):
        Page = '<form action="/signin" method="post" enctype="multipart/form-data">'
        Page += 'Username: <input type="text" name="username"/><br/>'
        Page += 'Password: <input type="password" name="password"/>'
        Page += '<input type="submit" value="Login"/></form>'
        if (bool == 1):
            Page += "Unauthenticated User"
        return Page
    
    @cherrypy.expose    
    def sum(self, a=0, b=0): #All inputs are strings by default
        output = int(a)+int(b)
        return str(output)
        
    # LOGGING IN AND OUT
    @cherrypy.expose
    def signin(self, username=None, password=None):
        """Check their name and password and send them either to the main page, or back to the main login screen."""
        hashedPW = sha256(password + username).hexdigest()
        r = urllib2.urlopen("http://cs302.pythonanywhere.com/report?username=" + username + "&password=" + hashedPW + "&location=2&ip=172.23.183.96&port=10001")
        string = r.read()
        if (string == '0, User and IP logged'):
            cherrypy.session['username'] = username;
            cherrypy.session['password'] = hashedPW;
            raise cherrypy.HTTPRedirect('/profile')
        elif (string == '2, Unauthenticated user'):
            raise cherrypy.HTTPRedirect('/login?bool=')

    @cherrypy.expose
    def signout(self):
        """Logs the current user out, expires their session"""
        self.checkLogged()
        r = urllib2.urlopen("http://cs302.pythonanywhere.com/logoff?username=" + cherrypy.session['username'] + "&password=" + cherrypy.session['password'])
        cherrypy.lib.sessions.expire()
        raise cherrypy.HTTPRedirect('/')
	
    @cherrypy.expose
    def profile(self):
        #profile page
        self.checkLogged()
        data = self.readUserData()
        #Open and read html file
        file = open("html/profile.html", "r")
        Page = file.read()
        file.close()
        #Buttons for Displaying online users and signout
        Page += '<form action="/getUsers" method="post" enctype="multipart/form-data"><br/>'
        Page += '<input type="submit" value="Display Online Users"/></form>'
        Page += '<form action="/editProfile" method="post" enctype="multipart/form-data"><br/>'
        Page += '<input type="submit" value="Edit Profile"/></form>'
        Page += '<form action="/signout" method="post" enctype="multipart/form-data"><br/>'
        Page += '<input type="submit" value="Signout"/></form>'
        Page += "<b style='color:tomato'>Name: " + str(data[0]) + "</b><br/>"
        Page += "<b style='color:tomato'>Position: " + str(data[1]) + "</b><br/>"
        Page += "<b style='color:tomato'>Description: " + str(data[2]) + "</b><br/>"
        Page += "<b style='color:tomato'>Location: " + str(data[3]) + "</b><br/>"
        return Page

    @cherrypy.expose
    def editProfile(self):
        self.checkLogged()
        data = self.readUserData()
        Page = '<form action="/writeInfo" method="post" enctype="multipart/form-data">'
        Page += 'Name: <input type="text" value="default value" name="name"/><br/>'
        Page += 'Position: <input type="text" value="default value" name="position"/><br/>'
        Page += 'Description: <input type="text" value="default value" name="description"/><br/>'
        Page += 'Location: <input type="text" value="default value" name="location"/><br/>'
        Page += '<input type="submit" value="Login"/></form>'
        return Page
	
	#Used to update the database with new user info
    @cherrypy.expose
    def writeInfo(self, name=None, position=None, description=None, location=None):
        self.checkLogged()
        db = sqlite3.connect("db/Users.db")
        cursor = db.cursor()
        cursor.execute("UPDATE User SET Name = ? WHERE UPI = ? ", (name, cherrypy.session['username']))
        cursor.execute("UPDATE User SET Position = ? WHERE UPI = ? ", (position, cherrypy.session['username']))
        cursor.execute("UPDATE User SET Description = ? WHERE UPI = ? ", (description, cherrypy.session['username']))
        cursor.execute("UPDATE User SET Location = ? WHERE UPI = ? ", (location, cherrypy.session['username']))
        db.commit()
        db.close()
        raise cherrypy.HTTPRedirect('/profile')
		
    @cherrypy.expose
    def getUsers(self):
        self.checkLogged()
        r = urllib2.urlopen("http://cs302.pythonanywhere.com/getList?username=" + cherrypy.session['username'] + "&password=" + cherrypy.session['password'])
        Page = r.read()
        return Page

	#Page to display when trying to access particular pages while not logged in
    @cherrypy.expose
    def errorPage(self):
        Page = "You must login first.<br/>"
        Page += "Click here to <a href='login'>login</a>."
        return Page

    def checkLogged(self):
        try:
            username = cherrypy.session['username']
            password = cherrypy.session['password']
        except KeyError: #No logged in user
            raise cherrypy.HTTPRedirect('/errorPage')
        return
		
    def readUserData(self):
        #Opening database and reading user info
        conn = sqlite3.connect("db/Users.db")
        c = conn.cursor()
        c.execute('SELECT Name,Position,Description,Location FROM User WHERE UPI="' + cherrypy.session['username'] + '"')
        #User info stored into a tuple, row
        row = c.fetchone()
        #Close db
        conn.close()
        return row
		

          
def runMainApp():
    # Create an instance of MainApp and tell Cherrypy to send all requests under / to it. (ie all of them)
    cherrypy.tree.mount(MainApp(), "/")

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
