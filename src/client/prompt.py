import arcade
from arcade.gui.elements.inputbox import UIInputBox
from arcade.gui import UIManager

from client.game_config import *

def prompt(title, prompt):
	r = tk.Tk()
	r.withdraw()
	inp = simpledialog.askstring(title=title, prompt=prompt)
	return inp

class Prompt(arcade.View):
	def __init__(self, game_view, callback = None, initial = "", msg = ""):
		super().__init__()
		self.game_view = game_view
		self.ui_manager = UIManager()
		self.callback = callback
		self.initial = initial
		self.msg = msg
		self.input_box = None
	
	def get_msg(self):
		return self.input_box.text
	
	def on_show(self):
		arcade.set_background_color(arcade.color.ORANGE)
		self.input_box = UIInputBox(SCREEN_WIDTH / 2,
							SCREEN_HEIGHT / 2 - 50,
							800,
							50,
							self.initial)
		self.input_box.set_style_attrs(font_name=FONT, font_size = FONT_SIZE * 0.75)
		self.ui_manager.add_ui_element(self.input_box)
		self.ui_manager.focused_element = self.input_box
	
	def on_draw(self):
		arcade.start_render()
		
		arcade.draw_text(self.msg,
						SCREEN_WIDTH / 2,
						SCREEN_HEIGHT / 2,
						arcade.color.BLACK,
						font_size=28,
						font_name=FONT,
						anchor_x="center")
		
	def on_key_press(self, key, modifiers):
		if key == arcade.key.ENTER:
			if self.callback:
				self.callback(self.input_box.text)
			self.ui_manager.purge_ui_elements()
			self.window.show_view(self.game_view)
		elif key == arcade.key.ESCAPE:
			self.ui_manager.purge_ui_elements()
			self.window.show_view(self.game_view)
