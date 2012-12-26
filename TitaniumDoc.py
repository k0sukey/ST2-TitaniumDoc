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
        self.thread.manager.progress = self.thread.is_alive()

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


class DownloadDocumentThread(threading.Thread):
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
        self.progress = False
        self.result = ""

    def get_panel(self):
        if len(self.panel) == 0:
            self.panel = json.loads(open(self.apidocpath + "/index.json").read())

        return self.panel

    def show_document(self, index):
        render = []
        document = json.loads(open(self.apidocpath + "/" + self.panel[index] + ".json").read())

        render.append(document["name"])
        render.append("==================================================")

        if self.settings.get('show_platforms') and document["platforms"]:
            render.append("### Platforms")

            platforms = []
            for key, value in enumerate(document["platforms"]):
                platforms.append(value["pretty_name"] + " : " + value["since"])

            render.append(", ".join(platforms))
            render.append("")

        if self.settings.get('show_summary') and document["summary"]:
            render.append("### Summary")
            render.append(self.stripper.strip(document["summary"]))
            render.append("")

        if self.settings.get('show_description') and document["description"]:
            render.append("### Description")
            render.append(self.stripper.strip(document["description"]))
            render.append("")

        if self.settings.get('show_examples') and document["examples"]:
            render.append("### Examples")

            for key, value in enumerate(document["examples"]):
                render.append(value["description"])
                render.append(self.stripper.strip(value["code"]))

            render.append("")

        if self.settings.get('show_properties') and document["properties"]:
            render.append("### Properties")

            for key, value in enumerate(document["properties"]):
                if (isinstance(value["type"], list)):
                    type = ", ".join(value["type"])
                else:
                    type = value["type"]

                render.append(value["name"] + " : " + type + "\n    " + self.stripper.strip(value["summary"].replace("\n", "")))

            render.append("")

        if self.settings.get('show_methods') and document["methods"]:
            render.append("### Methods")

            for key, value in enumerate(document["methods"]):
                returns = []
                if (isinstance(value["returns"], list)):
                    for i, j in enumerate(value["returns"]):
                        returns.append(j["type"])
                else:
                    returns.append(value["returns"]["type"])

                parameters = []
                for i, j in enumerate(value["parameters"]):
                    if (isinstance(j["type"], list)):
                        type = "/".join(j["type"])
                    else:
                        type = j["type"]

                    parameters.append(type + " " + j["name"])

                render.append("/".join(returns) + " " + value["name"] + "(" + ", ".join(parameters) + ")\n    " + self.stripper.strip(value["summary"].replace("\n", "")))

            render.append("")

        if self.settings.get('show_events') and document["events"]:
            render.append("### Events")

            adjust = 0
            events = []
            for key, value in enumerate(document["events"]):
                events.append(value)

                if len(value["name"]) > adjust:
                    adjust = len(value["name"])

            for value in events:
                render.append(value["name"].ljust(adjust) + " : " + self.stripper.strip(value["summary"].replace("\n", "")))

        window = sublime.Window.new_file(sublime.active_window())
        window.insert(window.begin_edit(), window.size(), "\n".join(render))
        window.set_scratch(True)
        window.set_read_only(True)
        window.set_name(document["name"] + " - Titanium API Document")

    def check_document(self):
        return os.path.exists(self.apidocpath)

    def download_document(self):
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


class TitaniumDocCommand(sublime_plugin.WindowCommand):
    manager = DocumentManager()

    def run(self, *args, **kwargs):
        if self.manager.progress:
            sublime.message_dialog("Titanium API Document downloading now. Please try again later.")
        elif not self.manager.check_document():
            if sublime.ok_cancel_dialog("Do you want to download the Titanium API Document?", "Download"):
                on_complete = lambda: self.manager.download_document()
                thread = DownloadDocumentThread(self.manager, str(self.manager.settings.get("apiurl")), on_complete)
                thread.start()
                ThreadProgress(thread, "Downloading API Document", "Downloaded API Document")
        else:
            self.window.show_quick_panel(self.manager.get_panel(), self._quick_panel_callback)

    def _quick_panel_callback(self, index):
        if (index > -1):
            self.manager.show_document(index)
