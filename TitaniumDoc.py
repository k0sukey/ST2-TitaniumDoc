from HTMLParser import HTMLParser
import json
import md5
import os
import sublime
import sublime_plugin
import threading
import urllib2

class HTMLStripper(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)

    def handle_data(self, data):
        self.string += data

    def strip(self, html):
        self.string = ""
        self.feed(html)
        self.close()
        return self.string

class ThreadProgress():
    def __init__(self, thread, message, success_message):
        self.thread = thread
        self.message = message
        self.success_message = success_message
        self.addend = 1
        self.size = 8
        sublime.set_timeout(lambda: self.run(0), 100)

    def run(self, i):
        if not self.thread.is_alive():
            if hasattr(self.thread, 'result') and not self.thread.result:
                sublime.status_message('')
                return
            sublime.status_message(self.success_message)
            return

        before = i % self.size
        after = (self.size - 1) - before

        sublime.status_message('%s [%s=%s]' % \
            (self.message, ' ' * before, ' ' * after))

        if not after:
            self.addend = -1
        if not before:
            self.addend = 1
        i += self.addend

        sublime.set_timeout(lambda: self.run(i), 100)

class DownloadDocuemntThread(threading.Thread):
    def __init__(self, manager, apiurl, on_complete):
        self.manager = manager
        self.apiurl = apiurl
        self.on_complete = on_complete
        threading.Thread.__init__(self)

    def run(self):
        try:
            response = urllib2.urlopen(self.apiurl)
            self.manager.result = response.read()
        finally:
            if self.on_complete:
                sublime.set_timeout(self.on_complete, 1)

class DocumentManager():
    def __init__(self):
        self.settings = sublime.load_settings("TitaniumDoc.sublime-settings")
        self.stripper = HTMLStripper()
        self.apidocpath = os.path.dirname(os.path.abspath(__file__)) + "/" + md5.new(str(self.settings.get('apiurl'))).hexdigest()
        self.panel = []
        self.thread = False
        self.result = ""

    def get_panel(self):
        if len(self.panel) == 0:
            self.panel = json.loads(open(self.apidocpath + "/index.json").read())

        return self.panel

    def show_document(self, index):
        document = json.loads(open(self.apidocpath + "/" + self.panel[index] + ".json").read())

        window = sublime.Window.new_file(sublime.active_window())

        window.insert(window.begin_edit(), window.size(), document["name"] + "\n")
        window.insert(window.begin_edit(), window.size(), "==================================================\n")

#        if (docuemnt["description"]):
#            window.insert(window.begin_edit(), window.size(), self.stripper.strip(docuemnt["description"]) + "\n\n")

        window.insert(window.begin_edit(), window.size(), "### Properties\n")
        if (document["properties"]):
            for key, value in enumerate(document["properties"]):
                if (isinstance(value["type"], list)):
                    type = ", ".join(value["type"])
                else:
                    type = value["type"]

                window.insert(window.begin_edit(), window.size(), value["name"] + " : " + type + " : " + self.stripper.strip(value["summary"].replace("\n", "")) + "\n")

        window.insert(window.begin_edit(), window.size(), "\n")

        window.insert(window.begin_edit(), window.size(), "### Methods\n")
        if (document["methods"]):
            for key, value in enumerate(document["methods"]):
                parameters = []
                for i, j in enumerate(value["parameters"]):
                    if (isinstance(j["type"], list)):
                        type = "/".join(j["type"])
                    else:
                        type = j["type"]

                    parameters.append(type + " " + j["name"])

                window.insert(window.begin_edit(), window.size(), value["name"] + "(" + ", ".join(parameters) + ") : " + self.stripper.strip(value["summary"].replace("\n", "")) + "\n")

        window.insert(window.begin_edit(), window.size(), "\n")

        window.insert(window.begin_edit(), window.size(), "### Events\n")
        if (document["events"]):
            for key, value in enumerate(document["events"]):
                window.insert(window.begin_edit(), window.size(), value["name"] + " : " + self.stripper.strip(value["summary"].replace("\n", "")) + "\n")

        window.set_scratch(True)
        window.set_read_only(True)
        window.set_name(document["name"] + " - Titanium API Document")

    def check_document(self):
        return os.path.exists(self.apidocpath)

    def download_docuemnt(self):
        os.mkdir(self.apidocpath)

        apiindex = []
        apidoc = json.loads(self.result)
        for key in apidoc:
            apiindex.append(key)
            f = open(self.apidocpath + "/" + key + ".json", "w")
            f.write(json.dumps(apidoc[key]))
            f.close()

        apiindex.sort()
        f = open(self.apidocpath + "/index.json", "w")
        f.write(json.dumps(apiindex))
        f.close()

        self.thread = False

class TitaniumDocCommand(sublime_plugin.WindowCommand):
    manager = DocumentManager()

    def run(self, *args, **kwargs):
        if self.manager.thread:
            sublime.message_dialog("Titanium API Document downloading now. Please try again later.")
        elif not self.manager.check_document():
            sublime.message_dialog("Titanium API Document download.")
            self.manager.thread = True
            on_complete = lambda: self.manager.download_docuemnt()
            thread = DownloadDocuemntThread(self.manager, str(self.manager.settings.get("apiurl")), on_complete)
            thread.start()
            ThreadProgress(thread, "Downloading API Document", "Downloaded API Document")
        else:
            self.window.show_quick_panel(self.manager.get_panel(), self._quick_panel_callback)

    def _quick_panel_callback(self, index):
        if (index > -1):
            self.manager.show_document(index)
