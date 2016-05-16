import sublime
import sublime_plugin
import threading

if int(sublime.version()) >= 3000:
    from . import requests
else:
    import requests


def error(err):
    print("[Hipster Ipsum: " + err + "]")


class HipsterIpsumCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        s = sublime.load_settings("Hipster Ipsum.sublime-settings")
        default_paras = s.get("paragraphs", 1)
        ipsum_type = s.get("ipsum_type", "hipster-centric")
        use_HTML = "false" if s.get("html", False) == False else "true"

        selections = self.view.sel()
        all_threads = []
        passed_threads = 0
        skipped_threads = 0

        for sel in selections:
            substring = self.view.substr(sel)
            if len(substring) == 0:
                new_thread = HipsterIpsumAPICall(sel, default_paras,
                                                ipsum_type, use_HTML, "")
                all_threads.append(new_thread)
                new_thread.start()
                passed_threads += 1

            else:
                try:
                    paras = int(substring)

                except ValueError:
                    new_thread = HipsterIpsumAPICall(sel, default_paras,
                                                    ipsum_type, use_HTML, substring)
                    all_threads.append(new_thread)
                    new_thread.start()
                    passed_threads += 1

                else:
                    if paras < 1:
                        error("%i is too few paragraphs." % paras)
                        error("Select a number between 1 and 99.")
                        sublime.status_message("Hipster Ipsum: Too few paragraphs (%i)."
                                               % paras)
                        skipped_threads += 1

                    elif paras > 99:
                        error("%i is too many paragraphs." % paras)
                        error("Select a number between 1 and 99.")
                        sublime.status_message("Hipster Ipsum: Too many paragraphs (%i)."
                                               % paras)
                        skipped_threads += 1

                    else:
                        new_thread = HipsterIpsumAPICall(sel, paras,
                                                         ipsum_type, use_HTML, substring)
                        all_threads.append(new_thread)
                        new_thread.start()
                        passed_threads += 1

        if passed_threads > 0:
            self.view.sel().clear()
            self.manage_threads(all_threads)

        else:
            sublime.status_message("Hipster Ipsum: No authentic selections.")
            error("Skipped %i selections." % skipped_threads)

    def manage_threads(self, threads, offset=0, i=0, direction=1):
        next_threads = []
        for thread in threads:
            if thread.is_alive():
                next_threads.append(thread)
                continue

            if thread.result == False:
                continue

            offset = self.replace(thread, offset)
        threads = next_threads

        if len(threads):
            before = i % 8
            after = 7 - before
            if not after:
                direction = -1

            if not before:
                direction = 1

            i += direction
            self.view.set_status("hipster_ipsum",
                                 "Gentrifying... [%s=%s]" % (" " * before, " " * after))

            sublime.set_timeout(lambda: self.manage_threads(threads, offset,
                                                           i, direction), 100)
            return

        self.view.erase_status("hipster_ipsum")
        selections = len(self.view.sel())
        sublime.status_message("%s area%s gentrified." % (selections,
                                                          '' if selections == 1 else 's'))

    def replace(self, thread, offset):
        selection = thread.selection
        original = thread.original
        result = thread.result

        if offset:
            selection = sublime.Region(selection.begin() + offset, selection.end() + offset)

        result = self.normalize_line_endings(result)
        self.view.run_command("hipster_ipsum_replace",
                              {"begin": selection.begin(),
                               "end": selection.end(),
                               "data": result})

        endpoint = selection.begin() + len(result)
        self.view.sel().add(sublime.Region(endpoint, endpoint))

        return offset + len(result) - len(original)

    def normalize_line_endings(self, string):
        string = string.replace('\n', '\n\n')
        string = string.replace('\r\n', '\n').replace('\r', '\n')
        line_endings = self.view.settings().get('default_line_ending')
        if line_endings == 'windows':
            string = string.replace('\n', '\r\n')
        elif line_endings == 'mac':
            string = string.replace('\n', '\r')
        return string


class HipsterIpsumAPICall(threading.Thread):
    def __init__(self, sel, num_paras, ipsum_type, use_HTML, orig_str):
        self.selection = sel
        self.paragraphs = num_paras
        self.ipsum_type = ipsum_type
        self.use_HTML = use_HTML
        self.original = orig_str
        self.result = None
        threading.Thread.__init__(self)

    def run(self):
        params = {"paras": self.paragraphs, "type": self.ipsum_type, "html": self.use_HTML}

        try:
            r = requests.get("http://hipsterjesus.com/api/", params=params)

        except Exception as e:
            error("Exception: %s" % e)
            self.result = False

        else:
          data = r.json()
          self.result = data["text"]


class HipsterIpsumReplaceCommand(sublime_plugin.TextCommand):
    def run(self, edit, begin, end, data):
        a = long(begin) if int(sublime.version()) < 3000 else begin
        b = long(end) if int(sublime.version()) < 3000 else end
        region = sublime.Region(a, b)
        self.view.replace(edit, region, data)
