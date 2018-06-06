from threading import Thread,Event
import urllib2

class MyThread(Thread):
    def __init__(self):
        Thread.__init__(self)
        self._stop_event = Event()

    #While not stopped, report to the login server every 30 seconds
    def run(self):
        while not self._stop_event.wait(30):
            r = urllib2.urlopen(URL)
            print (r.read())
    
    #Stops the thread from running
    def stop(self):
        self._stop_event.set()
	
    #Sets the URL to open, in this case it is the URL for the login server report
    def setURL(self, username, hashedPW, location, ip, port):
        global URL
        URL = "http://cs302.pythonanywhere.com/report?username=" + username + "&password=" + hashedPW + "&location=" + location + "&ip=" + ip + "&port=" + port