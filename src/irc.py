import pydle
import socket
import logging

MESSAGE_SPLIT_LEN = 420

class IRCEvent():
	def __init__(self, target, by, **kwargs):
		self.nick, self.mask = by, "dummy.host.mask"
		self.channel = target if target.startswith("#") else None
		for k, v in kwargs.items():
			setattr(self, k, v)

class MyBot(pydle.MinimalClient):
	def _invoke_event_handler(self, name, args=(), kwargs={}):
		if name not in self.event_handlers.keys():
			logging.warning("Unhandeled '%s' event", name)
			return
		try:
			self.event_handlers[name](*args, **kwargs)
		except Exception as e:
			logging.exception("Exception in IRC event handler")


	def on_connect(self):
		logging.info("IRC connection established")
		if self.ns_password is not None:
			self.connection.privmsg("NickServ", "IDENTIFY " + self.ns_password)
		self._invoke_event_handler("connected")
	
	def on_message(self, target, by, message):
		self._invoke_event_handler("message", [IRCEvent(target, by, message=message)])

	def on_ctcp(self, by, target, what, contents):
		if what != "ACTION":
			return
		self._invoke_event_handler("action", [IRCEvent(target, by, message=contents)])

	def on_join(self, channel, user):
		if user == self.nickname:
			return
		self._invoke_event_handler("join", [IRCEvent(channel, user)])

	def on_part(self, channel, user, message=None):
		self._invoke_event_handler("part", [IRCEvent(channel, user)])

	def on_kick(self, channel, target, by, reason=None):
		if target == self.nickname:
			self.join(channel)
			return
		self._invoke_event_handler("kick", [IRCEvent(channel, by, othernick=target)])

class IRCClient():
	def __init__(self, config):
		# Read config
		args = (config["server"], config["port"])
		kwargs = {}
		if config["ssl"]:
			kwargs["tls"] = True
			kwargs["tls_verify"] = False # this crashes it, lol
		self.cargs = ( args, kwargs )
		# Create bot
		self.bot = MyBot(config["nick"], realname="pytgbridge (IRC)")
		self.bot.event_handlers = {}
		self.bot.ns_password = config.get("nickpassword", None)
	def run(self):
		self.bot.connect(*self.cargs[0], **self.cargs[1])
		self.bot.handle_forever()
	def event_handler(self, name, func):
		self.bot.event_handlers[name] = func

	def join(self, channel):
		self.bot.join(channel)
	def privmsg(self, target, message):
		if self.bot.connection is None:
			logging.warning("Dropping message(s) because IRC not connected yet")
			return
		if len(message) < MESSAGE_SPLIT_LEN:
			msgs = [message]
		else:
			msgs = []
			for i in range(0, len(message), MESSAGE_SPLIT_LEN):
				msgs.append(message[i:i + MESSAGE_SPLIT_LEN])
		for m in msgs:
			self.bot.message(target, m)

