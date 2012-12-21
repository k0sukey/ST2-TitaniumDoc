from HTMLParser import HTMLParser
import json
import md5
import os
import sublime
import sublime_plugin
import urllib

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

class TitaniumDocCommand(sublime_plugin.WindowCommand):
    stripper = HTMLStripper()
    settings = sublime.load_settings("TitaniumDoc.sublime-settings")
    apidocpath = os.path.dirname(os.path.abspath(__file__)) + "/" + md5.new(str(settings.get('apiurl'))).hexdigest() + ".json"

    if (not os.path.exists(apidocpath)):
        sublime.status_message("Downloading api.json...")
        urllib.urlretrieve(str(settings.get('apiurl')), apidocpath)

    apidoc = json.loads(open(apidocpath).read())

    panel = []
    for key in apidoc:
        panel.append(key)

    def run(self, *args, **kwargs):
        self.window.show_quick_panel(self.panel, self._quick_panel_callback)

    def _quick_panel_callback(self, index):
        if (index > -1):
            api = self.panel[index]

            docwindow = sublime.Window.new_file(sublime.active_window())

            docwindow.insert(docwindow.begin_edit(), docwindow.size(), self.apidoc[api]["name"] + "\n==================================================\n")

#            if (self.apidoc[api]["description"]):
#                docwindow.insert(docwindow.begin_edit(), docwindow.size(), self.stripper.strip(self.apidoc[api]["description"]) + "\n\n")

            docwindow.insert(docwindow.begin_edit(), docwindow.size(), "### Properties\n")
            if (self.apidoc[api]["properties"]):
                for key, value in enumerate(self.apidoc[api]["properties"]):
                    if (isinstance(value["type"], list)):
                        type = ", ".join(value["type"])
                    else:
                        type = value["type"]

                    docwindow.insert(docwindow.begin_edit(), docwindow.size(), value["name"] + " : " + type + " : " + self.stripper.strip(value["summary"].replace("\n", "")) + "\n")

            docwindow.insert(docwindow.begin_edit(), docwindow.size(), "\n")

            docwindow.insert(docwindow.begin_edit(), docwindow.size(), "### Methods\n")
            if (self.apidoc[api]["methods"]):
                for key, value in enumerate(self.apidoc[api]["methods"]):
                    parameters = []
                    for i, j in enumerate(value["parameters"]):
                        if (isinstance(j["type"], list)):
                            type = "/".join(j["type"])
                        else:
                            type = j["type"]

                        parameters.append(type + " " + j["name"])

                    docwindow.insert(docwindow.begin_edit(), docwindow.size(), value["name"] + "(" + ", ".join(parameters) + ") : " + self.stripper.strip(value["summary"].replace("\n", "")) + "\n")

            docwindow.insert(docwindow.begin_edit(), docwindow.size(), "\n")

            docwindow.insert(docwindow.begin_edit(), docwindow.size(), "### Events\n")
            if (self.apidoc[api]["events"]):
                for key, value in enumerate(self.apidoc[api]["events"]):
                    docwindow.insert(docwindow.begin_edit(), docwindow.size(), value["name"] + " : " + self.stripper.strip(value["summary"].replace("\n", "")) + "\n")

            docwindow.set_scratch(True)
            docwindow.set_read_only(True)
            docwindow.set_name(self.apidoc[api]["name"] + " - Titanium CheatSheet")
