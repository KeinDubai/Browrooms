import wx
import wx.html
import socket
import urllib.parse
import ssl
import threading
import wx.html2

class Website:
    """Handles HTTP requests and responses for a specified URL."""
    
    def __init__(self, url: str) -> None:
        """
        Initializes the Website object by parsing the URL and establishing a socket connection.
        
        Args:
            url (str): The URL to connect to.
        """
        self.url = url
        self.__parse_url()

        # Create an SSL context for secure connections
        context = ssl._create_unverified_context()
        self.browser_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            # Wrap the socket in SSL if using HTTPS
            if self.port == 443:
                self.browser_socket = context.wrap_socket(self.browser_socket, server_hostname=self.host)
            #print(f"Connecting to {self.host}:{self.port}")
            self.browser_socket.connect((self.host, int(self.port)))
        except socket.error as e:
            #print(f"Error connecting to {self.host}: {e}")
            self.browser_socket = None

    def __parse_url(self) -> None:
        """Parses the URL to extract components like scheme, host, and port."""
        self.parsed = urllib.parse.urlparse(self.url)
        self.scheme = self.parsed.scheme
        self.netloc = self.parsed.netloc
        self.host = self.netloc.split(':')[0]

        # Determine port based on scheme; default is 443 for HTTPS, 80 for HTTP
        self.port = 443 if self.scheme == "https" else 80

        # Use specified port if present in the URL
        if ':' in self.netloc:
            self.port = int(self.netloc.split(':')[1])

        # Construct path with any additional components
        self.cmd = f'{self.parsed.path}{self.parsed.params}{self.parsed.query}{self.parsed.fragment}'

    def get_html(self) -> str:
        """
        Sends a GET request to the server and retrieves HTML content.
        
        Returns:
            str: The HTML content of the page or an error message.
        """
        if not self.browser_socket:
            return "<p>Error: Could not establish connection.</p>"
        
        try:
            # Build the HTTP GET request
            path = self.parsed.path if self.parsed.path else '/'
            request = f"GET {path} HTTP/1.1\r\nHost: {self.host}\r\nConnection: close\r\n\r\n"
            #print(67)
            self.browser_socket.sendall(request.encode())
            #print(69)
            response_utf8 = ''
            response_latin1 = ''
            response_iso = ''

            #print('Retrieving content...')
            while True:
                data = self.browser_socket.recv(512)
                if not data:
                    break

                response_utf8 += data.decode('utf-8', errors='replace')
                response_latin1 += data.decode('latin-1', errors='replace')
                response_iso += data.decode('ISO-8859-1', errors='replace')


                if '�' not in response_utf8: response = response_utf8
                elif '�' not in response_latin1: response = response_latin1
                elif '�' not in response_iso: response = response_iso
                else: return "<p>Error: Unknown Encoding</p>"

                #print(response)
            #print('Content retrieved.')

            if not response:
                return "<p>Error: Empty response from the server.</p>"
            return self.handle_status(response)

        except Exception as e:
            #print(f"Error receiving data: {e}")
            return "<p>Error receiving data.</p>"

    def handle_status(self, response: str) -> str:
        """
        Handles HTTP status codes, particularly redirects (3xx).
        
        Args:
            response (str): The full HTTP response from the server.
        
        Returns:
            str: HTML content from the final URL after any redirections.
        """
        #print(f'Handling response: {response}')
        
        if "HTTP/1.1 301 Moved Permanently" in response or "HTTP/1.1 302 Found" in response:
            #print('Redirection detected')
            new_location = self.get_location(response)
            #print(f'Redirecting to: {new_location}')

            if new_location:
                redirect = Website(new_location)
                source = redirect.get_html()
                redirect.close()
                return source
            else:
                return "<p>Error: No new location provided.</p>"
        
        return response

    def get_location(self, response: str) -> str | None:
        """
        Extracts the 'Location' header from the HTTP response for redirection.
        
        Args:
            response (str): The HTTP response as a string.
        
        Returns:
            str | None: URL to redirect to, or None if not found.
        """
        for line in response.split('\r\n'):
            if line.lower().startswith("location:"):
                return line.split(":", 1)[1].strip()
        return None

    def close(self) -> None:
        """Closes the socket connection if it is open."""
        if self.browser_socket:
            self.browser_socket.close()

class Browser(wx.Frame):
    """Main browser application frame with a basic navigation toolbar and HTML viewer."""
    
    def __init__(self, *args, **kwargs):
        super(Browser, self).__init__(*args, **kwargs)
        
        # Create main panel and layout sizers
        self.panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        toolbar_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # Define desired width and height for the images
        width, height = 50, 50

        self.history:list = []
        self.historyPointer:int = -1

        # Load and resize images for navigation buttons
        img_back = wx.Bitmap("img/back.png", wx.BITMAP_TYPE_PNG).ConvertToImage().Scale(width, height).ConvertToBitmap()
        img_forward = wx.Bitmap("img/forward.png", wx.BITMAP_TYPE_PNG).ConvertToImage().Scale(width, height).ConvertToBitmap()
        img_refresh = wx.Bitmap("img/refresh.png", wx.BITMAP_TYPE_PNG).ConvertToImage().Scale(width, height).ConvertToBitmap()
        img_home = wx.Bitmap("img/home.png", wx.BITMAP_TYPE_PNG).ConvertToImage().Scale(width, height).ConvertToBitmap()
        
        # Create navigation buttons using resized images
        btn_back = wx.BitmapButton(self.panel, bitmap=img_back)
        btn_forward = wx.BitmapButton(self.panel, bitmap=img_forward)
        btn_refresh = wx.BitmapButton(self.panel, bitmap=img_refresh)
        btn_home = wx.BitmapButton(self.panel, bitmap=img_home, )
        
        # Add buttons to the toolbar
        toolbar_sizer.Add(btn_back, 0, wx.ALL, 5)
        toolbar_sizer.Add(btn_forward, 0, wx.ALL, 5)
        toolbar_sizer.Add(btn_refresh, 0, wx.ALL, 5)
        toolbar_sizer.Add(btn_home, 0, wx.ALL, 5)

        # Add a spacer to push the URL entry away from the home button
        
        #toolbar_sizer.AddStretchSpacer(1)

        # Add URL entry field to the toolbar
        font = wx.Font(20, wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, u'Consolas')
        self.url_entry = wx.TextCtrl(self.panel, style=wx.TE_PROCESS_ENTER, size=(500,50))
        self.url_entry.SetFont(font)
        toolbar_sizer.Add(self.url_entry, wx.ALL, wx.EXPAND | wx.ALL, 5)

        # Add a spacer between URL entry and the search button
        toolbar_sizer.AddStretchSpacer(1)
        
        # Load "Go" button image, resize, and create button
        img_go = wx.Bitmap("img/search.png", wx.BITMAP_TYPE_PNG).ConvertToImage().Scale(width, height).ConvertToBitmap()
        btn_go = wx.BitmapButton(self.panel, bitmap=img_go)
        toolbar_sizer.Add(btn_go, 0, wx.ALL, 5)
        
        
        # Add toolbar to main layout
        main_sizer.Add(toolbar_sizer, 0, wx.EXPAND)
        
        self.webView = wx.html2.WebView.New(self.panel)
        main_sizer.Add(self.webView, 1, wx.EXPAND | wx.ALL, 10)


        # Create and configure HTML display window
        #self.html_window = wx.html.HtmlWindow(self.panel, style=wx.NO_BORDER)

        # Load landing page content
        with open('index.html', 'r') as html_content:
            self.content = html_content.read()
        
        # Display initial content in the HTML window
        #self.html_window.SetPage(content)
        
        # Add HTML window to main layout
        #main_sizer.Add(self.html_window, 1, wx.EXPAND | wx.ALL, 10)
        
        # Set panel layout and frame properties
        self.panel.SetSizer(main_sizer)
        self.SetSize((800, 600))
        self.SetTitle("Browrooms-net")
        self.Centre()

        # Bind events for navigation
        self.Bind(wx.EVT_BUTTON, self.backward, btn_back)
        self.Bind(wx.EVT_BUTTON, self.forward, btn_forward)
        self.Bind(wx.EVT_BUTTON, self.refreshPage, btn_refresh)
        self.Bind(wx.EVT_BUTTON, self.home,  btn_home)
        self.Bind(wx.EVT_BUTTON, self.load_page, btn_go)
        self.Bind(wx.EVT_TEXT_ENTER, self.load_page, self.url_entry)

        wx.CallAfter(self.webView.SetPage, self.content, "")

    def load_page(self, event):
        """Loads a page from the URL entered in the address bar."""
        url:str = self.url_entry.GetValue()

        # Add scheme if missing
        if not url.startswith(("http://", "https://")):
            url = "https://" + url 

        # Create a new thread for loading the page content
        self.thread = threading.Thread(target=self.fetch_html, args=(url,))
        self.thread.start()

    def fetch_html(self, url: str):
        """
        Fetches HTML content for the given URL and updates the display.
        
        Args:
            url (str): The URL to fetch.
        """
        if url:
            web = Website(url=url)
            source = web.get_html()

            # Update HTML window with fetched content
            if source:
                wx.CallAfter(self.webView.SetPage, source, "")
                #self.html_window.SetPage(source)
                web.close()
            else:
                source = "<p>Failed to load content.</p>"
                wx.CallAfter(self.webView.SetPage, source, "")

            self.historyPointer += 1
            try:
                self.history[self.historyPointer] = url
            except IndexError:
                self.history.append(url)

    def home(self, event=None) -> None:
        """Loads the home page of the browser."""

        REFRESH = '---Refreshing_Page---'
        BACKWARD =  '---Going_Backward---'

        wx.CallAfter(self.webView.SetPage, self.content, "")
        if event not in (REFRESH, BACKWARD):
            try:
                self.history[self.historyPointer] = 'Home'
            except IndexError:
                self.history.append('Home')

    def getWeb(self):
        
        web = Website(url=self.history[self.historyPointer])
        source = web.get_html()

        # Update HTML window with fetched content
        if source:
            wx.CallAfter(self.webView.SetPage, source, "")
            #self.html_window.SetPage(source)
            web.close()
        else:
            source = "<p>Failed to load content.</p>"
            wx.CallAfter(self.webView.SetPage, source, "")

    def refreshPage(self, event) -> None:
        if self.historyPointer == -1 or self.history[self.historyPointer] == 'Home':
            self.home('---Refreshing_Page---')
        else:
            self.getWeb()
            
    def backward(self, event):
        if self.historyPointer > 0:
            self.historyPointer -= 1
            self.getWeb()

        elif self.historyPointer == 0:
            self.historyPointer -= 1
            self.home('---Going_Backward---')
        
                
    def forward(self, event):
        if self.historyPointer < len(self.history) - 1:
            self.historyPointer += 1
            self.getWeb()


# Initialize the application and display the main browser window
app = wx.App(False)
frame = Browser(None)
frame.Show()
app.MainLoop()