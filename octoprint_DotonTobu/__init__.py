# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
import socket
from iot_message.message import Message
from iot_message.cryptor.aes_sha1 import Cryptor as AES
from urllib import request, parse


class DotontobuPlugin(octoprint.plugin.StartupPlugin,
					  	octoprint.plugin.EventHandlerPlugin,
						octoprint.plugin.SettingsPlugin,
					  	octoprint.plugin.TemplatePlugin):
#                       octoprint.plugin.AssetPlugin,

	_socket = None,
	_address = None,

	##~~ SettingsPlugin mixin

	def get_settings_defaults(self):
		return dict(
			# put your plugin's default settings here
			aes_staticiv="",
			aes_ivkey="",
			aes_datakey="",
			aes_passphrase="",
			node_name="printer",
			broadcast_ip="<broadcast>",
			port="5053",
			use_proxy=False,
			proxy_address='',
		)

	def on_settings_save(self, data):
		node_name_old = self._settings.get(["node_name"])
		ip_address_old = self._settings.get(["broadcast_ip"])

		octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

		node_name = self._settings.get(["node_name"])
		ip_address = self._settings.get(["broadcast_ip"])

		if node_name_old != node_name:
			self._logger.info("Changing name to %s ", node_name)
			Message.node_name = node_name

		if ip_address_old != ip_address:
			self._logger.info("Changing IP to %s ", ip_address)
			self._address = (ip_address, int(self._settings.get_int(["port"])))

	##~~ AssetPlugin mixin

	def get_assets(self):
		# Define your plugin's asset files to automatically include in the
		# core UI here.
		return dict(
			js=["js/DotonTobu.js"],
			css=["css/DotonTobu.css"],
			less=["less/DotonTobu.less"]
		)

	def get_template_configs(self):
		return [
			dict(type="settings", custom_bindings=False)
		]

	##~~ Softwareupdate hook

	def get_update_information(self):
		# Define the configuration for your plugin to use with the Software Update
		# Plugin here. See https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html
		# for details.
		return dict(
			DotonTobu=dict(
				displayName="Dotontobu Plugin",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="bkosciow",
				repo="OctoPrint-Dotontobu",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/bkosciow/OctoPrint-Dotontobu/archive/{target_version}.zip"
			)
		)

	def on_after_startup(self):
		node_name = self._settings.get(["node_name"])
		ip_address = self._settings.get(["broadcast_ip"])
		port = self._settings.get_int(["port"])

		if ip_address and port:
			self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
			self._address = (ip_address, int(port))
			self._logger.info("Socket ready %s:%d ", ip_address, port)

		if node_name and self._settings.get(["aes_staticiv"]) and self._settings.get(["aes_ivkey"]) and self._settings.get(["aes_datakey"]) and self._settings.get(["aes_passphrase"]):
			Message.node_name = node_name
			Message.add_encoder(AES(
				self._settings.get(["aes_staticiv"]),
				self._settings.get(["aes_ivkey"]),
				self._settings.get(["aes_datakey"]),
				self._settings.get(["aes_passphrase"]),
			))
			self._logger.info("Message ready")

	def on_event(self, event, payload):
		# print(event)
		data = {}
		# if event == "PrinterStateChanged":
		# 	print("PrinterStateChanged")
		# 	print(payload)

		if event == "Connected":
			data['event'] = 'connected'

		if event == "Disconnected":
			data['event'] = 'disconnected'

		if event == "PrintStarted":
			data['event'] = 'start'

		if event == "PrintCancelled":
			data['event'] = 'abort'

		if event == "DisplayLayerProgress_progressChanged":
			data['event'] = 'progress'
			data['parameters'] = {
				'percentage': payload['progress'],
				'printTimeLeftInSeconds': payload['printTimeLeftInSeconds'],
				'estimatedEndTime': payload['estimatedEndTime']
			}

		if event == "PrintDone":
			data['event'] = 'done'

		if data:
			message = Message()
			message.set(data)
			if not self._settings.get_boolean(["use_proxy"]) and self._socket is not None:
				self._socket.sendto(bytes(message), self._address)
				self._logger.info("Message by socket")
			if self._settings.get_boolean(["use_proxy"]) and self._settings.get(["proxy_address"]):
				data = {
					"message": bytes(message),
					"ip": self._settings.get(["broadcast_ip"]),
					"port": self._settings.get_int(["port"])
				}
				req = request.Request(self._settings.get(["proxy_address"]), data=parse.urlencode(data).encode())
				req.add_header('Content-Type', 'application/json;')
				resp = request.urlopen(req)
				self._logger.info("Message by proxy")

# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "Dotontobu Plugin"

# Starting with OctoPrint 1.4.0 OctoPrint will also support to run under Python 3 in addition to the deprecated
# Python 2. New plugins should make sure to run under both versions for now. Uncomment one of the following
# compatibility flags according to what Python versions your plugin supports!
#__plugin_pythoncompat__ = ">=2.7,<3" # only python 2
__plugin_pythoncompat__ = ">=3,<4" # only python 3
#__plugin_pythoncompat__ = ">=2.7,<4" # python 2 and 3

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = DotontobuPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}

