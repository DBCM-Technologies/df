from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from http.cookies import SimpleCookie
from urllib.parse import parse_qs
from mimetypes import guess_type
from email.parser import BytesParser
from email.policy import default as default_policy
import random

BASE_DIR = Path(__file__).parent
LOGIN_PAGE = BASE_DIR / 'login.html'

PUBLIC_PAGES = {
    '/login': LOGIN_PAGE,
}

LOCAL_FILES = {
    '/cat-space.gif': BASE_DIR / 'cat-space.gif',
}

USER_FILES = {}

INDEX_PAGE = BASE_DIR / 'index.html'

ENTRY_POINTS = 'login', 'logout', 'upload'
ID_BASE = list('ABCDEFGHJKMNPQRSTUWXYZ0123456789')

def make_session_id():
    random.shuffle(ID_BASE)
    return "".join(ID_BASE[:8])

class RequestHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.cookies = None
        self.entry_points = {}
        for entry in ENTRY_POINTS:
            self.entry_points[entry] = getattr(self, 'do_'+entry)
        super().__init__(*args, **kwargs)

    def make_index(self):
        if not USER_FILES:
            html = '<h2>No User Files</h2>'
        else:
            html = '<h2>User Files</h2>\n<hr/>\n<p>Click to download (Press <kbd>Ctrl</kbd>+<kbd>S</kbd> afterwards for text files):</p>\n<ol>\n'
        for name in USER_FILES:
            html += f'<li><a href="{name}">{name}</a></li>\n'
        if USER_FILES:
            html += '</ol>\n'
        with open(INDEX_PAGE, 'r') as file:
            return file.read().replace('[INSERT CONTENT]', html).encode()

    def make_cookies(self):
        if "Cookie" in self.headers:
            cookie = SimpleCookie(self.headers["Cookie"])
            self.cookies = {key: morsel.value for key, morsel in cookie.items()}
        else:
            self.cookies = None

    def has_session(self):
        if self.cookies:
            if 'session_id' in self.cookies:
                return self.cookies['session_id'] in self.server.sessions
        return False

    def is_authenticated(self):
        return self.has_session() and self.server.sessions[self.cookies['session_id']]['authenticated']

    def do_GET(self):
        self.make_cookies()
        if self.path in PUBLIC_PAGES:
            path = PUBLIC_PAGES[self.path]
            try:
                with open(path, 'rb') as file:
                    data = file.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html;charset=utf-8')
                if not self.has_session():
                    session_id = make_session_id()
                    self.server.sessions[session_id] = {'authenticated': False}
                    self.send_header('Set-Cookie', f'session_id={session_id}; Path=/; Max-Age=3600; SameSite=Strict')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except:
                self.send_error(500)
                import traceback
                traceback.print_exc()
        elif self.path in USER_FILES and self.is_authenticated():
            data = USER_FILES[self.path]
            self.send_response(200)
            self.send_header('Content-Type', guess_type(self.path)[0])
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif self.path == '/' and self.is_authenticated():
            try:
                self.send_response(200)
                self.send_header('Content-Type', 'text/html;charset=utf-8')
                data = self.make_index()
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except:
                self.send_error(500)
        elif self.path in LOCAL_FILES and self.is_authenticated():
            path = LOCAL_FILES[self.path]
            try:
                with open(path, 'rb') as file:
                    data = file.read()
                self.send_response(200)
                self.send_header('Content-Type', guess_type(path)[0])
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except:
                self.send_error(500)
                import traceback
                traceback.print_exc()
        elif self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/login')
            self.end_headers()
        else:
            self.send_error(404)
    def do_POST(self):
        self.make_cookies()
        entry = self.path[1:]
        if entry in self.entry_points:
            handle_entry = self.entry_points[entry]
            handle_entry()
        else:
            self.send_error(404)

    def do_logout(self):
        self.send_response(301)
        if not self.has_session():
            session_id = make_session_id()
            self.server.sessions[session_id] = {'authenticated': False}
            self.send_header('Set-Cookie', f'session_id={session_id}; Path=/; Max-Age=3600; SameSite=Strict')
        else:
            session_id = self.cookies['session_id']
        self.server.sessions[session_id]['authenticated'] = False
        self.send_header('Location', '/')
        self.end_headers()

    def do_login(self):
        self.send_response(301)
        new_session = False
        if not self.has_session():
            session_id = make_session_id()
            self.server.sessions[session_id] = {}
            new_session = True
        else:
            session_id = self.cookies['session_id']
        data_len = int(self.headers['Content-Length'])
        raw_data = self.rfile.read(data_len).decode()
        data = parse_qs(raw_data)
        self.send_header('Set-Cookie', f'session_id={session_id}; Path=/; Max-Age=3600; SameSite=Strict')
        user, passwd = data.get('user'), data.get('passwd')
        if None in (user, passwd) or len(user) != 1 and len(passwd) != 1:
            return self.send_error(400)
        if user[0] == 'raju' and passwd[0] == 'raju':
            self.server.sessions[session_id]['authenticated'] = True
            self.send_header('Location', '/')
        else:
            self.send_header('Location', '/login')
        self.end_headers()

    def do_upload(self):
        if not self.is_authenticated():
            return self.send_error(401)
        self.send_response(301)
        data_len = int(self.headers['Content-Length'])
        raw_data = b'Content-Type: ' + self.headers['Content-Type'].encode() + b'\r\n' + self.rfile.read(data_len)
        data = BytesParser(policy=default_policy).parsebytes(raw_data)
        for part in data.iter_parts():
            USER_FILES['/'+part.get_filename()] = part.get_content().encode()
        self.send_header('Location', '/')
        self.end_headers()

class Server(HTTPServer):
    def __init__(self, addr, RequestHandlerClass=RequestHandler, *args, **kwargs):
        super().__init__(addr, RequestHandlerClass, *args, **kwargs)
        self.sessions = {}
