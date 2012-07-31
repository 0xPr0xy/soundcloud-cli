import soundcloud
import sys
import os
import urwid


class ItemWidget (urwid.WidgetWrap):

	def __init__ (self, entry, url):
		""" Creates UI Element for every Entry"""

		if entry is not None:
			self.content = url.url
			self.item = [
				urwid.Padding(urwid.AttrWrap(
				urwid.Text('%s' % ( entry.title)),  'body', 'focus')),
			]
		w = urwid.Columns(self.item)
		self.__super.__init__(w)

	def selectable (self):
		return True

	def keypress(self, size, key):
		return key


class SoundCloud:

	def __init__(self, query, track, playlist):
		
		self.playlist = []
		self.palette = [
			('body','dark cyan', '', 'standout'),
			('focus','dark red', '', 'standout'),
			('head','light red', 'black'),
		]
		self.client = soundcloud.Client(client_id='570f56acefe61658492d4ee040a0a0cd')
		if query: self.query = query
		if track: self.findTracks()
		if playlist: self.findPlaylist()


	def play(self, url):

		os.system('./youtube_dl/__main__.py %s' % url)

	def initGui(self):
		self.listbox = urwid.ListBox(urwid.SimpleListWalker(self.playlist))
		self.view = urwid.Frame(urwid.AttrWrap(self.listbox, 'body'))
		self.loop = urwid.MainLoop(self.view, self.palette, unhandled_input=self.keystroke)
		self.loop.run()


	def findTracks(self):
		tracks = self.client.get('/tracks', q=self.query, licence='cc-by-sa')
		for track in tracks: 
			url = self.client.get(track.stream_url, allow_redirects=False)
			self.playlist.append(ItemWidget(track, url))
		self.initGui()


	def findPlaylist(self):
		playlist = self.client.get('/playlists/' + self.query)
		for track in playlist.tracks: 
			url = self.client.get(track.stream_url, allow_redirects=False)
			self.playlist.append(ItemWidget(track, url))
		self.initGui()


	def keystroke (self,input):
		""" Handle Keystrokes """
		
		if input in ('q', 'Q'):
			raise urwid.ExitMainLoop()

		if input is 'enter':
			try:
				self.focus = self.listbox.get_focus()[0].content
			except Exception as e:
				print('listbox get_focus failed:\nError: %s' % e)
			self.play(self.focus)



if len(sys.argv) == 3 and sys.argv[2] == 'track': instance = SoundCloud(sys.argv[1], True, False)
if len(sys.argv) == 3 and sys.argv[2] == 'playlist': instance = SoundCloud(sys.argv[1], False, True)
