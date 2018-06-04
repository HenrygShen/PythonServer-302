from threading import Thread,Event
import urllib2

class MyThread(Thread):
    def __init__(self):
        Thread.__init__(self)
        self._stop_event = Event()

    def run(self):
        while not self._stop_event.wait(30):
            r = urllib2.urlopen(URL)
            print (r.read())
			
    def stop(self):
        self._stop_event.set()
	
    def stopped(self):
        return self._stop_event.is_set()
		
    def setURL(self, username, hashedPW, location, ip, port):
        global URL
        URL = "http://cs302.pythonanywhere.com/report?username=" + username + "&password=" + hashedPW + "&location=" + location + "&ip=" + ip + "&port=" + port